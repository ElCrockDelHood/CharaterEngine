"""Authorization decision engine for CHARACTER ENGINE backend (C6).

Implements the deterministic decision priority of the C6 specification
(section 6.3):

1. Authentication check            -> DENY NOT_AUTHENTICATED (401)
2. Actor state check               -> DENY ACTOR_STATE_INVALID (401)
3. Resource state check            -> DENY RESOURCE_STATE_INVALID (404)
4. System permission check         -> ALLOW if actor is SYSTEM and holds the
                                      ``scope=system`` permission
5. Ownership check                 -> DENY OWNERSHIP_VIOLATION (404) when the
                                      resource is not owned by the actor and
                                      the actor lacks the ``scope=any`` permission
6. Permission check                -> ALLOW own/any permission, else DENY
                                      PERMISSION_DENIED (403)
7. Default deny                    -> DENY PERMISSION_DENIED (403)

Security properties
-------------------
- Default deny: unregistered resource/action combinations are always denied.
- No global bypass: SYSTEM actors only pass through explicit ``scope=system``
  permissions and are subject to every other check.
- IDOR protection: ownership violations map to 404, never 403.
- The actor identity is taken from the ``ActorContext`` (built from the C5
  session), never from request payloads.
- Every decision is optionally persisted to ``audit_entries`` without secrets.
"""

import json
from datetime import datetime, timezone
from typing import Iterable, Optional, Set

from sqlalchemy.orm import Session

from backend.authorization.authorization_domain import (
    AccessDeniedError,
    Action,
    ActorContext,
    ActorType,
    AuthorizationDecision,
    DenialReason,
    Resource,
    Scope,
)
from backend.authorization.permission_service import PermissionService
from backend.authorization.role_service import RoleService
from backend.database.models import AuditEntry

ACTIVE_STATE = "active"

# Resources that have no owner (spec 7.2). Ownership checks are skipped for
# them, so access is decided purely by ``any``/``system`` permissions.
UNOWNED_RESOURCES = frozenset({"event", "reward_definition", "audit_entry", "idempotency_record"})


class AuthorizationService:
    """Authorization decision engine (pure logic + optional audit persistence)."""

    # ------------------------------------------------------------------
    # Permission resolution
    # ------------------------------------------------------------------
    @staticmethod
    def resolve_permissions(actor: ActorContext, roles: Iterable[str]) -> Set[str]:
        """Compute the effective permission set of an actor.

        USER/ADMIN actors receive the union of their role permissions. SYSTEM
        actors receive the explicit system permission set (spec 4.3).
        """
        if not actor.authenticated:
            return set()
        if actor.actor_type == ActorType.SYSTEM:
            return PermissionService.get_system_permissions()
        return PermissionService.get_permissions_for_roles(roles)

    @staticmethod
    def load_actor_permissions(db: Session, actor: ActorContext) -> Set[str]:
        """Load active roles from the database and resolve permissions."""
        if not actor.authenticated or actor.actor_id is None:
            return set()
        if actor.actor_type == ActorType.SYSTEM:
            return AuthorizationService.resolve_permissions(actor, ())
        roles = RoleService.get_user_roles(db, actor.actor_id)
        return AuthorizationService.resolve_permissions(actor, roles)

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------
    @staticmethod
    def decide(
        actor: ActorContext,
        resource: Resource,
        action: Action,
        actor_permissions: Set[str],
    ) -> AuthorizationDecision:
        """Evaluate the deterministic decision flow. Pure function (no I/O)."""
        # 1. Authentication
        if not actor.authenticated:
            return AuthorizationDecision.deny(DenialReason.NOT_AUTHENTICATED)

        # 2. Actor state (account + session must be ACTIVE)
        if not AuthorizationService._is_active(actor.account_status) or \
           not AuthorizationService._is_active(actor.session_status):
            return AuthorizationDecision.deny(DenialReason.ACTOR_STATE_INVALID)

        # 3. Resource state
        if not AuthorizationService._is_active(resource.state):
            return AuthorizationDecision.deny(DenialReason.RESOURCE_STATE_INVALID)

        # 4. System permission (SYSTEM actors only; still explicit, no bypass)
        system_pid = PermissionService.find_permission_id(resource.resource_type, action, Scope.SYSTEM)
        if actor.actor_type == ActorType.SYSTEM and system_pid and system_pid in actor_permissions:
            return AuthorizationDecision.allow(system_pid)

        any_pid = PermissionService.find_permission_id(resource.resource_type, action, Scope.ANY)
        own_pid = PermissionService.find_permission_id(resource.resource_type, action, Scope.OWN)
        has_any = any_pid is not None and any_pid in actor_permissions
        has_own = own_pid is not None and own_pid in actor_permissions

        # 5. Ownership (only meaningful for owned resources)
        is_unowned = resource.resource_type in UNOWNED_RESOURCES or resource.owner_id is None
        owned_by_actor = (not is_unowned) and resource.owner_id == actor.actor_id

        if not is_unowned and not owned_by_actor and not has_any:
            # Hide existence of other users' resources (IDOR) -> 404
            return AuthorizationDecision.deny(DenialReason.OWNERSHIP_VIOLATION)

        # 6. Permission
        if has_any:
            return AuthorizationDecision.allow(any_pid)
        if owned_by_actor and has_own:
            return AuthorizationDecision.allow(own_pid)
        # ADMIN (non-SYSTEM) actors may hold scope=system permissions on unowned
        # resources (e.g. reward_definition:create). Spec 6.2 third ALLOW branch
        # restricts it to the SYSTEM actor type, but ADMIN role explicitly owns
        # these permission IDs (spec 4.2/5.1), so honour them for unowned resources.
        if is_unowned and system_pid and system_pid in actor_permissions:
            return AuthorizationDecision.allow(system_pid)

        # 7. Default deny
        return AuthorizationDecision.deny(DenialReason.PERMISSION_DENIED)

    @staticmethod
    def authorize(
        db: Session,
        actor: ActorContext,
        resource: Resource,
        action: Action,
        audit: bool = True,
    ) -> AuthorizationDecision:
        """Load permissions, decide and (optionally) persist an audit entry."""
        permissions = AuthorizationService.load_actor_permissions(db, actor)
        decision = AuthorizationService.decide(actor, resource, action, permissions)
        if audit:
            AuthorizationService.record_audit(db, actor, resource, action, decision)
        return decision

    @staticmethod
    def require(
        db: Session,
        actor: ActorContext,
        resource: Resource,
        action: Action,
        audit: bool = True,
    ) -> AuthorizationDecision:
        """Like ``authorize`` but raises ``AccessDeniedError`` on DENY."""
        decision = AuthorizationService.authorize(db, actor, resource, action, audit=audit)
        if not decision.allowed:
            raise AccessDeniedError(decision)
        return decision

    # ------------------------------------------------------------------
    # Audit (spec section 12) - never logs secrets/tokens
    # ------------------------------------------------------------------
    @staticmethod
    def record_audit(
        db: Session,
        actor: ActorContext,
        resource: Resource,
        action: Action,
        decision: AuthorizationDecision,
    ) -> Optional[AuditEntry]:
        """Persist an ``authorization.decision`` audit entry. Failures never break the decision."""
        details = {
            "actor_type": actor.actor_type.value,
            "session_id": actor.session_id,
            "resource_type": resource.resource_type,
            "action": action.value,
            "allowed": decision.allowed,
            "denial_reason": decision.denial_reason.value if decision.denial_reason else None,
            "matched_permission": decision.matched_permission,
        }
        entry = AuditEntry(
            event_type="authorization.decision",
            actor_id=actor.actor_id,
            resource_type=resource.resource_type,
            resource_id=resource.resource_id[:36] if resource.resource_id else None,
            action=action.value,
            result="SUCCESS" if decision.allowed else "FAILURE",
            details=json.dumps(details, sort_keys=True),
            ip_address=actor.ip_address,
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        try:
            db.add(entry)
            db.commit()
            return entry
        except Exception:
            db.rollback()
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _is_active(state: Optional[str]) -> bool:
        if state is None:
            return False
        value = getattr(state, "value", state)
        return str(value).lower() == ACTIVE_STATE
