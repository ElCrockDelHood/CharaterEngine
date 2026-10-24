"""Authorization package for CHARACTER ENGINE backend (C6).

- ``authorization_domain``: pure domain models (ActorContext, Role, Permission,
  Resource, AuthorizationDecision, exceptions)
- ``permission_service``: static permission registry and role -> permission map
- ``role_service``: role bootstrap and append-only assignment history
- ``authorization_service``: deterministic decision engine + audit
"""

from backend.authorization.authorization_domain import (
    AccessDeniedError,
    Action,
    ActorContext,
    ActorType,
    AuthorizationDecision,
    AuthorizationError,
    DenialReason,
    LastAdminError,
    Permission,
    Resource,
    Role,
    RoleAlreadyExistsError,
    RoleAssignment,
    RoleAssignmentError,
    RoleNotFoundError,
    Scope,
)
from backend.authorization.authorization_service import UNOWNED_RESOURCES, AuthorizationService
from backend.authorization.permission_service import PermissionService
from backend.authorization.role_service import (
    ADMIN_ROLE_ID,
    USER_ROLE_ID,
    VALID_ROLE_IDS,
    RoleService,
)

__all__ = [
    # Domain
    "ActorContext",
    "ActorType",
    "Action",
    "Scope",
    "DenialReason",
    "Role",
    "RoleAssignment",
    "Permission",
    "Resource",
    "AuthorizationDecision",
    # Exceptions
    "AuthorizationError",
    "AccessDeniedError",
    "RoleNotFoundError",
    "RoleAlreadyExistsError",
    "RoleAssignmentError",
    "LastAdminError",
    # Services
    "PermissionService",
    "RoleService",
    "AuthorizationService",
    # Constants
    "USER_ROLE_ID",
    "ADMIN_ROLE_ID",
    "VALID_ROLE_IDS",
    "UNOWNED_RESOURCES",
]
