"""Tests for C6 - AUTHORIZATION FOUNDATION (roles, permissions, decision engine).

Coverage map (spec docs/audit/C6_AUTHORIZATION_IMPLEMENTATION_SPEC.md):
- 4.1/4.2/4.4  Role model, admin rules, append-only revocation
- 5.1/5.2      Permission registry and lookup
- 6.2/6.3      Deterministic decision priority
- 8            IDOR protection (404 on ownership violations)
- 12           Audit entries without secrets
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from backend.authorization import (
    ADMIN_ROLE_ID,
    USER_ROLE_ID,
    AccessDeniedError,
    Action,
    ActorContext,
    ActorType,
    AuthorizationDecision,
    AuthorizationService,
    DenialReason,
    LastAdminError,
    Permission,
    PermissionService,
    Resource,
    Role,
    RoleAlreadyExistsError,
    RoleAssignmentError,
    RoleNotFoundError,
    RoleService,
    Scope,
)
from backend.config.config import Config, Environment
from backend.database.connection import DatabaseManager
from backend.database.models import AuditEntry
from backend.database.models import UserRole as UserRoleModel
from backend.identity.user_domain import CreateUserRequest
from backend.identity.user_service import UserService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def db_manager():
    config = Config(environment=Environment.TEST)
    manager = DatabaseManager(config)
    manager.create_tables()
    yield manager
    manager.drop_tables()


@pytest.fixture
def session(db_manager):
    with db_manager.get_session() as session:
        yield session


@pytest.fixture
def roles(session):
    RoleService.bootstrap_roles(session)
    return session


def _make_user(session, email: str) -> str:
    user = UserService.create_user(session, CreateUserRequest(email=email))
    return user.user_id


@pytest.fixture
def alice(roles):
    user_id = _make_user(roles, "alice@example.com")
    RoleService.assign_user_role_on_creation(roles, user_id)
    return user_id


@pytest.fixture
def bob(roles):
    user_id = _make_user(roles, "bob@example.com")
    RoleService.assign_user_role_on_creation(roles, user_id)
    return user_id


@pytest.fixture
def admin(roles):
    user_id = _make_user(roles, "admin@example.com")
    RoleService.assign_user_role_on_creation(roles, user_id)
    RoleService.assign_role(roles, user_id=user_id, role_id=ADMIN_ROLE_ID, assigned_by=None)  # bootstrap admin
    return user_id


def actor(user_id: str, actor_type: ActorType = ActorType.USER,
          account_status: str = "active", session_status: str = "active") -> ActorContext:
    return ActorContext.from_session(
        actor_id=user_id,
        account_id=f"acc-{user_id}",
        session_id=f"sess-{user_id}",
        account_status=account_status,
        session_status=session_status,
        actor_type=actor_type,
    )


def resource(resource_type: str, owner_id, state: str = "active", resource_id: str = "res-1") -> Resource:
    return Resource(resource_type=resource_type, resource_id=resource_id, owner_id=owner_id, state=state)


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------
class TestDomainModels:
    def test_anonymous_actor_context(self):
        anon = ActorContext.anonymous(ip_address="127.0.0.1")
        assert anon.authenticated is False
        assert anon.actor_type == ActorType.ANONYMOUS
        assert anon.actor_id is None

    def test_authenticated_actor_requires_ids(self):
        with pytest.raises(ValueError):
            ActorContext(
                actor_id=None, account_id="a", session_id="s",
                actor_type=ActorType.USER, authenticated=True,
                authentication_timestamp=None, ip_address=None, user_agent=None,
                account_status="active", session_status="active",
            )

    def test_unauthenticated_actor_must_be_anonymous(self):
        with pytest.raises(ValueError):
            ActorContext(
                actor_id=None, account_id=None, session_id=None,
                actor_type=ActorType.USER, authenticated=False,
                authentication_timestamp=None, ip_address=None, user_agent=None,
                account_status=None, session_status=None,
            )

    def test_role_invariants(self):
        with pytest.raises(ValueError):
            Role(role_id="", role_name="x", description=None, created_at=datetime.now(timezone.utc))

    def test_permission_invariants(self):
        with pytest.raises(ValueError):
            Permission(permission_id="p", resource="user", action="read", scope=Scope.OWN)  # type: ignore[arg-type]

    def test_decision_requires_reason_when_denied(self):
        with pytest.raises(ValueError):
            AuthorizationDecision(allowed=False, denial_reason=None)

    def test_decision_rejects_reason_when_allowed(self):
        with pytest.raises(ValueError):
            AuthorizationDecision(allowed=True, denial_reason=DenialReason.PERMISSION_DENIED)

    def test_http_status_mapping(self):
        assert DenialReason.NOT_AUTHENTICATED.http_status == 401
        assert DenialReason.ACTOR_STATE_INVALID.http_status == 401
        assert DenialReason.PERMISSION_DENIED.http_status == 403
        assert DenialReason.OWNERSHIP_VIOLATION.http_status == 404
        assert DenialReason.RESOURCE_STATE_INVALID.http_status == 404
        assert AuthorizationDecision.allow("user:read_own").http_status == 200


# ---------------------------------------------------------------------------
# Permission registry
# ---------------------------------------------------------------------------
class TestPermissionService:
    def test_registry_has_15_permissions(self):
        assert len(PermissionService.all_permission_ids()) == 15

    def test_registry_ids_match_definitions(self):
        for pid, permission in PermissionService.PERMISSION_REGISTRY.items():
            assert pid == permission.permission_id

    def test_role_permissions_are_registered(self):
        registered = PermissionService.all_permission_ids()
        for role_id, pids in PermissionService.ROLE_PERMISSIONS.items():
            assert pids <= registered, f"{role_id} references unknown permissions"
        assert PermissionService.SYSTEM_PERMISSIONS <= registered

    def test_user_role_has_only_own_scope(self):
        for pid in PermissionService.get_role_permissions(USER_ROLE_ID):
            assert PermissionService.get_permission(pid).scope == Scope.OWN

    def test_admin_is_superset_of_user(self):
        assert PermissionService.get_role_permissions(USER_ROLE_ID) < PermissionService.get_role_permissions(ADMIN_ROLE_ID)

    def test_admin_cannot_grant_rewards(self):
        # reward_grant:grant / revoke belong exclusively to the SYSTEM actor (spec 10.3)
        admin_perms = PermissionService.get_role_permissions(ADMIN_ROLE_ID)
        assert "reward_grant:grant" not in admin_perms
        assert "reward_grant:revoke" not in admin_perms

    def test_find_permission_id(self):
        assert PermissionService.find_permission_id("user", Action.READ, Scope.OWN) == "user:read_own"
        assert PermissionService.find_permission_id("user", Action.READ, Scope.ANY) == "user:read_any"
        assert PermissionService.find_permission_id("reward_definition", Action.CREATE, Scope.SYSTEM) == "reward_definition:create"
        assert PermissionService.find_permission_id("user", Action.DELETE, Scope.OWN) is None

    def test_has_permission_uses_registry(self):
        perms = PermissionService.get_role_permissions(USER_ROLE_ID)
        assert PermissionService.has_permission(perms, "user", Action.READ, Scope.OWN)
        assert not PermissionService.has_permission(perms, "user", Action.READ, Scope.ANY)
        assert not PermissionService.has_permission(perms, "user", Action.DELETE, Scope.OWN)

    def test_unknown_role_has_no_permissions(self):
        assert PermissionService.get_role_permissions("superuser") == set()

    def test_format_permission_id(self):
        assert PermissionService.format_permission_id("user", Action.READ, Scope.OWN) == "user:read_own"
        assert PermissionService.format_permission_id("asset", Action.DELETE, Scope.SYSTEM) == "asset:delete"
        assert PermissionService.format_permission_id("asset", Action.LIST, Scope.ANY) == "asset:list_any"


# ---------------------------------------------------------------------------
# Role service (persistence)
# ---------------------------------------------------------------------------
class TestRoleService:
    def test_bootstrap_creates_user_and_admin(self, roles):
        assert RoleService.get_role(roles, USER_ROLE_ID).role_name == "User"
        assert RoleService.get_role(roles, ADMIN_ROLE_ID).role_name == "Administrator"

    def test_bootstrap_twice_fails(self, roles):
        with pytest.raises(RoleAlreadyExistsError):
            RoleService.bootstrap_roles(roles)

    def test_create_invalid_role_id(self, session):
        with pytest.raises(RoleAssignmentError):
            RoleService.create_role(session, "superuser", "Super")

    def test_get_missing_role_returns_none(self, session):
        assert RoleService.get_role(session, USER_ROLE_ID) is None

    def test_assign_without_bootstrap_fails(self, session):
        user_id = _make_user(session, "x@example.com")
        with pytest.raises(RoleNotFoundError):
            RoleService.assign_role(session, user_id, USER_ROLE_ID, assigned_by=None)

    def test_user_role_assigned_on_creation(self, alice, roles):
        assert RoleService.get_user_roles(roles, alice) == [USER_ROLE_ID]
        history = RoleService.get_role_history(roles, alice)
        assert len(history) == 1
        assert history[0].is_system_assignment and history[0].is_active

    def test_user_role_stores_role_surrogate_key(self, alice, roles):
        """Regression: UserRole.role_id must reference roles.id (FK), not the label."""
        row = roles.execute(select(UserRoleModel).where(UserRoleModel.user_id == alice)).scalar_one()
        role_pk = roles.execute(
            select(UserRoleModel.role_id)
        ).scalars().first()
        assert row.role_id == role_pk
        assert row.role_id != USER_ROLE_ID
        assert len(row.role_id) == 36  # UUID string

    def test_duplicate_active_assignment_rejected(self, alice, roles):
        with pytest.raises(RoleAssignmentError):
            RoleService.assign_role(roles, alice, USER_ROLE_ID, assigned_by=None)

    def test_admin_self_assignment_prohibited(self, alice, roles):
        with pytest.raises(RoleAssignmentError):
            RoleService.assign_role(roles, alice, ADMIN_ROLE_ID, assigned_by=alice)

    def test_admin_assignment_by_admin(self, admin, alice, roles):
        RoleService.assign_role(roles, alice, ADMIN_ROLE_ID, assigned_by=admin)
        assert RoleService.get_user_roles(roles, alice) == [ADMIN_ROLE_ID, USER_ROLE_ID]
        assert RoleService.count_active_admins(roles) == 2

    def test_user_role_cannot_be_revoked(self, alice, roles):
        with pytest.raises(RoleAssignmentError):
            RoleService.revoke_role(roles, alice, USER_ROLE_ID, revoked_by=None)

    def test_revoke_last_admin_fails(self, admin, roles):
        with pytest.raises(LastAdminError):
            RoleService.revoke_role(roles, admin, ADMIN_ROLE_ID, revoked_by=None)

    def test_admin_self_revocation_prohibited(self, admin, alice, roles):
        RoleService.assign_role(roles, alice, ADMIN_ROLE_ID, assigned_by=admin)
        with pytest.raises(RoleAssignmentError):
            RoleService.revoke_role(roles, alice, ADMIN_ROLE_ID, revoked_by=alice)

    def test_revocation_is_append_only(self, admin, alice, roles):
        RoleService.assign_role(roles, alice, ADMIN_ROLE_ID, assigned_by=admin)
        revoked = RoleService.revoke_role(roles, alice, ADMIN_ROLE_ID, revoked_by=admin)
        assert revoked is not None and revoked.revoked_at is not None
        assert RoleService.get_user_roles(roles, alice) == [USER_ROLE_ID]
        # History keeps the revoked row
        history = RoleService.get_role_history(roles, alice)
        assert len(history) == 2
        assert any(not h.is_active and h.role_id == ADMIN_ROLE_ID for h in history)
        # Re-assignment after revocation is allowed (partial unique index only covers active rows)
        RoleService.assign_role(roles, alice, ADMIN_ROLE_ID, assigned_by=admin)
        assert RoleService.has_role(roles, alice, ADMIN_ROLE_ID)
        assert len(RoleService.get_role_history(roles, alice)) == 3

    def test_revoke_missing_assignment_returns_none(self, admin, alice, roles):
        assert RoleService.revoke_role(roles, alice, ADMIN_ROLE_ID, revoked_by=admin) is None

    def test_roles_isolated_between_users(self, alice, bob, roles):
        assert RoleService.get_user_roles(roles, alice) == [USER_ROLE_ID]
        assert RoleService.get_user_roles(roles, bob) == [USER_ROLE_ID]
        assert RoleService.get_role_history(roles, alice)[0].user_id == alice


# ---------------------------------------------------------------------------
# Decision engine (pure)
# ---------------------------------------------------------------------------
USER_PERMS = PermissionService.get_role_permissions(USER_ROLE_ID)
ADMIN_PERMS = PermissionService.get_role_permissions(ADMIN_ROLE_ID)
SYSTEM_PERMS = PermissionService.get_system_permissions()


class TestDecisionEngine:
    def test_anonymous_denied_401(self):
        d = AuthorizationService.decide(ActorContext.anonymous(), resource("user", "u1"), Action.READ, set())
        assert not d.allowed and d.denial_reason == DenialReason.NOT_AUTHENTICATED and d.http_status == 401

    @pytest.mark.parametrize("account_status,session_status", [
        ("suspended", "active"), ("inactive", "active"), ("closed", "active"),
        ("active", "expired"), ("active", "revoked"),
    ])
    def test_inactive_actor_denied_401(self, account_status, session_status):
        a = actor("u1", account_status=account_status, session_status=session_status)
        d = AuthorizationService.decide(a, resource("user", "u1"), Action.READ, USER_PERMS)
        assert d.denial_reason == DenialReason.ACTOR_STATE_INVALID and d.http_status == 401

    def test_inactive_resource_denied_404(self):
        d = AuthorizationService.decide(actor("u1"), resource("user", "u1", state="deleted"), Action.READ, USER_PERMS)
        assert d.denial_reason == DenialReason.RESOURCE_STATE_INVALID and d.http_status == 404

    def test_user_reads_own_user(self):
        d = AuthorizationService.decide(actor("u1"), resource("user", "u1"), Action.READ, USER_PERMS)
        assert d.allowed and d.matched_permission == "user:read_own" and d.http_status == 200

    def test_user_updates_own_user(self):
        d = AuthorizationService.decide(actor("u1"), resource("user", "u1"), Action.UPDATE, USER_PERMS)
        assert d.allowed and d.matched_permission == "user:update_own"

    def test_idor_other_user_is_404_not_403(self):
        d = AuthorizationService.decide(actor("u1"), resource("user", "u2"), Action.READ, USER_PERMS)
        assert not d.allowed
        assert d.denial_reason == DenialReason.OWNERSHIP_VIOLATION
        assert d.http_status == 404

    def test_idor_other_users_reward_grant_is_404(self):
        d = AuthorizationService.decide(actor("u1"), resource("reward_grant", "u2"), Action.READ, USER_PERMS)
        assert d.denial_reason == DenialReason.OWNERSHIP_VIOLATION and d.http_status == 404

    def test_user_lacking_permission_on_own_resource_403(self):
        # DELETE on own user is not a registered permission -> default deny 403
        d = AuthorizationService.decide(actor("u1"), resource("user", "u1"), Action.DELETE, USER_PERMS)
        assert d.denial_reason == DenialReason.PERMISSION_DENIED and d.http_status == 403

    def test_user_cannot_touch_unowned_system_resource(self):
        d = AuthorizationService.decide(actor("u1"), resource("reward_definition", None), Action.CREATE, USER_PERMS)
        assert d.denial_reason == DenialReason.PERMISSION_DENIED and d.http_status == 403

    def test_admin_reads_any_user(self):
        d = AuthorizationService.decide(actor("adm"), resource("user", "u2"), Action.READ, ADMIN_PERMS)
        assert d.allowed and d.matched_permission == "user:read_any"

    def test_admin_reads_own_user_prefers_any(self):
        d = AuthorizationService.decide(actor("adm"), resource("user", "adm"), Action.READ, ADMIN_PERMS)
        assert d.allowed and d.matched_permission == "user:read_any"

    def test_admin_manages_reward_definitions(self):
        for action in (Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE):
            d = AuthorizationService.decide(actor("adm"), resource("reward_definition", None), action, ADMIN_PERMS)
            assert d.allowed, action

    def test_admin_cannot_grant_rewards(self):
        d = AuthorizationService.decide(actor("adm"), resource("reward_grant", None), Action.GRANT, ADMIN_PERMS)
        assert d.denial_reason == DenialReason.PERMISSION_DENIED

    def test_admin_cannot_manage_other_users_credentials(self):
        # No credential:*_any permission exists -> ownership violation (404)
        d = AuthorizationService.decide(actor("adm"), resource("credential", "u2"), Action.MANAGE, ADMIN_PERMS)
        assert d.denial_reason == DenialReason.OWNERSHIP_VIOLATION

    def test_system_grants_rewards(self):
        d = AuthorizationService.decide(actor("sys", ActorType.SYSTEM), resource("reward_grant", "u2"), Action.GRANT, SYSTEM_PERMS)
        assert d.allowed and d.matched_permission == "reward_grant:grant"

    def test_system_has_no_global_bypass(self):
        d = AuthorizationService.decide(actor("sys", ActorType.SYSTEM), resource("reward_definition", None), Action.DELETE, SYSTEM_PERMS)
        assert not d.allowed and d.denial_reason == DenialReason.PERMISSION_DENIED

    def test_system_subject_to_state_checks(self):
        a = actor("sys", ActorType.SYSTEM, session_status="revoked")
        d = AuthorizationService.decide(a, resource("reward_grant", None), Action.GRANT, SYSTEM_PERMS)
        assert d.denial_reason == DenialReason.ACTOR_STATE_INVALID

    def test_system_permissions_not_usable_by_user_actor(self):
        """A USER actor that somehow holds a scope=system permission on an owned resource still fails ownership."""
        perms = USER_PERMS | {"reward_grant:grant"}
        d = AuthorizationService.decide(actor("u1"), resource("reward_grant", "u2"), Action.GRANT, perms)
        assert not d.allowed and d.denial_reason == DenialReason.OWNERSHIP_VIOLATION

    def test_empty_permissions_default_deny(self):
        d = AuthorizationService.decide(actor("u1"), resource("user", "u1"), Action.READ, set())
        assert d.denial_reason == DenialReason.PERMISSION_DENIED

    def test_decision_is_deterministic(self):
        args = (actor("u1"), resource("user", "u2"), Action.READ, USER_PERMS)
        assert AuthorizationService.decide(*args) == AuthorizationService.decide(*args)


# ---------------------------------------------------------------------------
# Integration: roles from DB + audit
# ---------------------------------------------------------------------------
class TestAuthorizationIntegration:
    def test_authorize_user_own_resource(self, alice, roles):
        d = AuthorizationService.authorize(roles, actor(alice), resource("user", alice), Action.READ)
        assert d.allowed

    def test_authorize_user_other_resource_404(self, alice, bob, roles):
        d = AuthorizationService.authorize(roles, actor(alice), resource("user", bob), Action.READ)
        assert d.http_status == 404

    def test_authorize_admin_other_resource(self, admin, bob, roles):
        d = AuthorizationService.authorize(roles, actor(admin), resource("user", bob), Action.READ)
        assert d.allowed and d.matched_permission == "user:read_any"

    def test_revoked_admin_loses_access_immediately(self, admin, alice, bob, roles):
        RoleService.assign_role(roles, alice, ADMIN_ROLE_ID, assigned_by=admin)
        assert AuthorizationService.authorize(roles, actor(alice), resource("user", bob), Action.READ).allowed
        RoleService.revoke_role(roles, alice, ADMIN_ROLE_ID, revoked_by=admin)
        d = AuthorizationService.authorize(roles, actor(alice), resource("user", bob), Action.READ)
        assert d.http_status == 404

    def test_user_without_roles_is_denied(self, roles):
        user_id = _make_user(roles, "noroles@example.com")
        d = AuthorizationService.authorize(roles, actor(user_id), resource("user", user_id), Action.READ)
        assert d.denial_reason == DenialReason.PERMISSION_DENIED

    def test_require_raises_on_deny(self, alice, bob, roles):
        with pytest.raises(AccessDeniedError) as exc:
            AuthorizationService.require(roles, actor(alice), resource("user", bob), Action.READ)
        assert exc.value.decision.http_status == 404

    def test_audit_entry_written_without_secrets(self, alice, bob, roles):
        AuthorizationService.authorize(roles, actor(alice), resource("user", bob), Action.READ)
        entries = roles.execute(select(AuditEntry).where(AuditEntry.event_type == "authorization.decision")).scalars().all()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.actor_id == alice
        assert entry.result == "FAILURE"
        assert entry.resource_type == "user"
        assert '"denial_reason": "ownership_violation"' in entry.details
        # No token/password material can appear in an authorization audit
        for forbidden in ("token", "password", "hash"):
            assert forbidden not in entry.details.lower()

    def test_audit_can_be_disabled(self, alice, roles):
        AuthorizationService.authorize(roles, actor(alice), resource("user", alice), Action.READ, audit=False)
        count = len(roles.execute(select(AuditEntry)).scalars().all())
        assert count == 0
