"""Authorization domain models for CHARACTER ENGINE backend.

This module defines the domain layer for authorization, separate from
the database persistence layer.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class ActorType(str, Enum):
    """Actor type enumeration - domain level."""
    USER = "user"
    SYSTEM = "system"
    ANONYMOUS = "anonymous"


class Scope(str, Enum):
    """Permission scope enumeration - domain level."""
    OWN = "own"
    ANY = "any"
    SYSTEM = "system"


class Action(str, Enum):
    """Action enumeration - domain level."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"
    MANAGE = "manage"
    GRANT = "grant"
    REVOKE = "revoke"


class DenialReason(str, Enum):
    """Denial reason enumeration - domain level."""
    NOT_AUTHENTICATED = "not_authenticated"
    PERMISSION_DENIED = "permission_denied"
    OWNERSHIP_VIOLATION = "ownership_violation"
    RESOURCE_NOT_FOUND = "resource_not_found"
    RESOURCE_STATE_INVALID = "resource_state_invalid"
    ACTOR_STATE_INVALID = "actor_state_invalid"

    @property
    def http_status(self) -> int:
        """HTTP status mapped by the C6 spec (section 9.1).

        Ownership violations and inactive resources return 404 (not 403) so the
        existence of another user's resource is never revealed (IDOR protection).
        """
        return _HTTP_STATUS_BY_REASON[self]


_HTTP_STATUS_BY_REASON = {
    DenialReason.NOT_AUTHENTICATED: 401,
    DenialReason.ACTOR_STATE_INVALID: 401,
    DenialReason.PERMISSION_DENIED: 403,
    DenialReason.OWNERSHIP_VIOLATION: 404,
    DenialReason.RESOURCE_NOT_FOUND: 404,
    DenialReason.RESOURCE_STATE_INVALID: 404,
}


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------
class AuthorizationError(Exception):
    """Base exception for the authorization domain."""


class RoleNotFoundError(AuthorizationError):
    """Requested role does not exist (bootstrap not executed)."""


class RoleAlreadyExistsError(AuthorizationError):
    """Role already exists."""


class RoleAssignmentError(AuthorizationError):
    """Invalid assignment/revocation request (duplicate, self-assignment, invalid role...)."""


class LastAdminError(RoleAssignmentError):
    """Attempt to revoke the last active administrator."""


class AccessDeniedError(AuthorizationError):
    """Raised by ``AuthorizationService.require`` when a decision is DENY."""

    def __init__(self, decision: "AuthorizationDecision"):
        self.decision = decision
        super().__init__(f"Access denied: {decision.denial_reason.value}")


@dataclass(frozen=True)
class ActorContext:
    """Actor context for authorization decisions.

    Encapsulates actor identity and context for authorization decisions.

    Invariants:
    - actor_id is a valid UUID string if authenticated
    - account_id is a valid UUID string if authenticated
    - session_id is a valid UUID string if authenticated
    - actor_type is valid ActorType
    - authenticated is boolean
    - account_status is valid AccountStatus if authenticated
    - session_status is valid SessionStatus if authenticated
    """
    actor_id: Optional[str]  # user_id from session
    account_id: Optional[str]  # account_id from session
    session_id: Optional[str]  # session_id from session
    actor_type: ActorType
    authenticated: bool
    authentication_timestamp: Optional[datetime]
    ip_address: Optional[str]
    user_agent: Optional[str]
    account_status: Optional[str]  # AccountStatus from C4
    session_status: Optional[str]  # SessionStatus from C5

    def __post_init__(self):
        """Validate actor context invariants."""
        if self.authenticated:
            if not self.actor_id or not isinstance(self.actor_id, str):
                raise ValueError("actor_id must be a non-empty string when authenticated")
            if not self.account_id or not isinstance(self.account_id, str):
                raise ValueError("account_id must be a non-empty string when authenticated")
            if not self.session_id or not isinstance(self.session_id, str):
                raise ValueError("session_id must be a non-empty string when authenticated")
            if not isinstance(self.actor_type, ActorType):
                raise ValueError(f"actor_type must be ActorType, got {type(self.actor_type)}")
        else:
            if self.actor_type != ActorType.ANONYMOUS:
                raise ValueError("actor_type must be ANONYMOUS when not authenticated")

    @property
    def is_system(self) -> bool:
        return self.actor_type == ActorType.SYSTEM

    @staticmethod
    def anonymous(ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> "ActorContext":
        """Unauthenticated actor."""
        return ActorContext(
            actor_id=None, account_id=None, session_id=None,
            actor_type=ActorType.ANONYMOUS, authenticated=False,
            authentication_timestamp=None, ip_address=ip_address, user_agent=user_agent,
            account_status=None, session_status=None,
        )

    @staticmethod
    def from_session(
        actor_id: str,
        account_id: str,
        session_id: str,
        account_status: str,
        session_status: str,
        actor_type: ActorType = ActorType.USER,
        authentication_timestamp: Optional[datetime] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> "ActorContext":
        """Authenticated actor built from a validated C5 session."""
        return ActorContext(
            actor_id=actor_id, account_id=account_id, session_id=session_id,
            actor_type=actor_type, authenticated=True,
            authentication_timestamp=authentication_timestamp,
            ip_address=ip_address, user_agent=user_agent,
            account_status=account_status, session_status=session_status,
        )


@dataclass(frozen=True)
class Role:
    """Role domain entity.

    Represents a role in the authorization system.

    Invariants:
    - role_id is a valid role identifier (e.g., "user", "admin")
    - role_name is a non-empty string
    - created_at is server-generated
    """
    role_id: str
    role_name: str
    description: Optional[str]
    created_at: datetime

    def __post_init__(self):
        """Validate role invariants."""
        if not self.role_id or not isinstance(self.role_id, str):
            raise ValueError("role_id must be a non-empty string")
        if not self.role_name or not isinstance(self.role_name, str):
            raise ValueError("role_name must be a non-empty string")
        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at must be datetime")


@dataclass(frozen=True)
class RoleAssignment:
    """A single row of the append-only role assignment history.

    Invariants:
    - assignment_id, user_id and role_id are non-empty strings
    - assigned_by is None only for SYSTEM assignments
    - revoked_at is None while the assignment is active
    """
    assignment_id: str
    user_id: str
    role_id: str
    assigned_by: Optional[str]
    assigned_at: datetime
    revoked_at: Optional[datetime] = None

    def __post_init__(self):
        for name in ("assignment_id", "user_id", "role_id"):
            value = getattr(self, name)
            if not value or not isinstance(value, str):
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(self.assigned_at, datetime):
            raise ValueError("assigned_at must be datetime")

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    @property
    def is_system_assignment(self) -> bool:
        return self.assigned_by is None


@dataclass(frozen=True)
class Permission:
    """Permission domain entity.

    Represents a specific action on a specific resource type.

    Invariants:
    - permission_id is a valid permission identifier (e.g., "user:read_own")
    - resource is a non-empty string
    - action is a valid Action
    - scope is a valid Scope
    """
    permission_id: str
    resource: str
    action: Action
    scope: Scope

    def __post_init__(self):
        """Validate permission invariants."""
        if not self.permission_id or not isinstance(self.permission_id, str):
            raise ValueError("permission_id must be a non-empty string")
        if not self.resource or not isinstance(self.resource, str):
            raise ValueError("resource must be a non-empty string")
        if not isinstance(self.action, Action):
            raise ValueError(f"action must be Action, got {type(self.action)}")
        if not isinstance(self.scope, Scope):
            raise ValueError(f"scope must be Scope, got {type(self.scope)}")


@dataclass(frozen=True)
class Resource:
    """Resource domain entity.

    Represents a resource for authorization check.

    Invariants:
    - resource_type is a non-empty string
    - resource_id is a valid UUID string
    - owner_id is a valid UUID string if owned
    - state is a valid state string
    """
    resource_type: str
    resource_id: str
    owner_id: Optional[str]
    state: str

    def __post_init__(self):
        """Validate resource invariants."""
        if not self.resource_type or not isinstance(self.resource_type, str):
            raise ValueError("resource_type must be a non-empty string")
        if not self.resource_id or not isinstance(self.resource_id, str):
            raise ValueError("resource_id must be a non-empty string")
        if not isinstance(self.state, str):
            raise ValueError("state must be a string")


@dataclass(frozen=True)
class AuthorizationDecision:
    """Authorization decision domain entity.

    Represents the result of an authorization decision.

    Invariants:
    - allowed is boolean
    - denial_reason is valid DenialReason if denied
    """
    allowed: bool
    denial_reason: Optional[DenialReason]
    matched_permission: Optional[str] = None  # permission_id that granted access (audit)

    def __post_init__(self):
        """Validate authorization decision invariants."""
        if not isinstance(self.allowed, bool):
            raise ValueError("allowed must be boolean")
        if not self.allowed and self.denial_reason is None:
            raise ValueError("denial_reason must be provided when not allowed")
        if self.allowed and self.denial_reason is not None:
            raise ValueError("denial_reason must be None when allowed")
        if self.denial_reason is not None and not isinstance(self.denial_reason, DenialReason):
            raise ValueError(f"denial_reason must be DenialReason, got {type(self.denial_reason)}")

    @property
    def http_status(self) -> int:
        """200 when allowed, otherwise the status mapped from the denial reason."""
        return 200 if self.allowed else self.denial_reason.http_status

    @staticmethod
    def allow(matched_permission: str) -> "AuthorizationDecision":
        return AuthorizationDecision(allowed=True, denial_reason=None, matched_permission=matched_permission)

    @staticmethod
    def deny(reason: DenialReason) -> "AuthorizationDecision":
        return AuthorizationDecision(allowed=False, denial_reason=reason)
