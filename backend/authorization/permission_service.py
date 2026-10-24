"""Permission service for CHARACTER ENGINE backend.

This module implements permission management and checking.
"""

from typing import Dict, Iterable, Optional, Set, Tuple

from backend.authorization.authorization_domain import Action, Permission, Scope


class PermissionService:
    """Permission service for permission management and checking."""

    # Permission registry (14 permissions as per specification)
    PERMISSION_REGISTRY = {
        # User permissions (self-permissions)
        "user:read_own": Permission(
            permission_id="user:read_own",
            resource="user",
            action=Action.READ,
            scope=Scope.OWN
        ),
        "user:update_own": Permission(
            permission_id="user:update_own",
            resource="user",
            action=Action.UPDATE,
            scope=Scope.OWN
        ),
        "account:read_own": Permission(
            permission_id="account:read_own",
            resource="account",
            action=Action.READ,
            scope=Scope.OWN
        ),
        "credential:manage_own": Permission(
            permission_id="credential:manage_own",
            resource="credential",
            action=Action.MANAGE,
            scope=Scope.OWN
        ),
        "session:manage_own": Permission(
            permission_id="session:manage_own",
            resource="session",
            action=Action.MANAGE,
            scope=Scope.OWN
        ),
        "reward_grant:read_own": Permission(
            permission_id="reward_grant:read_own",
            resource="reward_grant",
            action=Action.READ,
            scope=Scope.OWN
        ),
        # System/admin permissions
        "user:read_any": Permission(
            permission_id="user:read_any",
            resource="user",
            action=Action.READ,
            scope=Scope.ANY
        ),
        "user:update_any": Permission(
            permission_id="user:update_any",
            resource="user",
            action=Action.UPDATE,
            scope=Scope.ANY
        ),
        "account:read_any": Permission(
            permission_id="account:read_any",
            resource="account",
            action=Action.READ,
            scope=Scope.ANY
        ),
        "reward_definition:create": Permission(
            permission_id="reward_definition:create",
            resource="reward_definition",
            action=Action.CREATE,
            scope=Scope.SYSTEM
        ),
        "reward_definition:read": Permission(
            permission_id="reward_definition:read",
            resource="reward_definition",
            action=Action.READ,
            scope=Scope.SYSTEM
        ),
        "reward_definition:update": Permission(
            permission_id="reward_definition:update",
            resource="reward_definition",
            action=Action.UPDATE,
            scope=Scope.SYSTEM
        ),
        "reward_definition:delete": Permission(
            permission_id="reward_definition:delete",
            resource="reward_definition",
            action=Action.DELETE,
            scope=Scope.SYSTEM
        ),
        "reward_grant:grant": Permission(
            permission_id="reward_grant:grant",
            resource="reward_grant",
            action=Action.GRANT,
            scope=Scope.SYSTEM
        ),
        "reward_grant:revoke": Permission(
            permission_id="reward_grant:revoke",
            resource="reward_grant",
            action=Action.REVOKE,
            scope=Scope.SYSTEM
        ),
    }

    # Role permissions mapping
    ROLE_PERMISSIONS = {
        "user": {
            "user:read_own",
            "user:update_own",
            "account:read_own",
            "credential:manage_own",
            "session:manage_own",
            "reward_grant:read_own",
        },
        "admin": {
            # User permissions (self-permissions)
            "user:read_own",
            "user:update_own",
            "account:read_own",
            "credential:manage_own",
            "session:manage_own",
            "reward_grant:read_own",
            # System permissions
            "user:read_any",
            "user:update_any",
            "account:read_any",
            "reward_definition:create",
            "reward_definition:read",
            "reward_definition:update",
            "reward_definition:delete",
        },
    }

    # System actor permissions (explicit system permissions)
    SYSTEM_PERMISSIONS = {
        "reward_definition:read",
        "reward_grant:grant",
        "reward_grant:revoke",
        "user:read_any",
    }

    # Reverse index (resource, action, scope) -> permission_id. Built once from the
    # registry so lookups never depend on string formatting conventions.
    _LOOKUP: Dict[Tuple[str, Action, Scope], str] = {
        (p.resource, p.action, p.scope): pid for pid, p in PERMISSION_REGISTRY.items()
    }

    @staticmethod
    def get_permission(permission_id: str) -> Optional[Permission]:
        """Get permission by ID, or None if not registered."""
        return PermissionService.PERMISSION_REGISTRY.get(permission_id)

    @staticmethod
    def all_permission_ids() -> Set[str]:
        """All registered permission identifiers."""
        return set(PermissionService.PERMISSION_REGISTRY)

    @staticmethod
    def get_role_permissions(role_id: str) -> Set[str]:
        """Get permission IDs for a role (empty set for unknown roles)."""
        return set(PermissionService.ROLE_PERMISSIONS.get(role_id, set()))

    @staticmethod
    def get_permissions_for_roles(role_ids: Iterable[str]) -> Set[str]:
        """Union of the permissions granted by a collection of roles."""
        permissions: Set[str] = set()
        for role_id in role_ids:
            permissions |= PermissionService.get_role_permissions(role_id)
        return permissions

    @staticmethod
    def get_system_permissions() -> Set[str]:
        """Get explicit SYSTEM actor permissions (no global bypass)."""
        return set(PermissionService.SYSTEM_PERMISSIONS)

    @staticmethod
    def find_permission_id(resource: str, action: Action, scope: Scope) -> Optional[str]:
        """Resolve the registered permission_id for resource/action/scope, or None."""
        return PermissionService._LOOKUP.get((resource, action, scope))

    @staticmethod
    def has_permission(
        actor_permissions: Set[str],
        resource: str,
        action: Action,
        scope: Scope
    ) -> bool:
        """Check if the actor holds the registered permission for resource/action/scope.

        Unregistered combinations always return False (default deny).
        """
        permission_id = PermissionService.find_permission_id(resource, action, scope)
        return permission_id is not None and permission_id in actor_permissions

    @staticmethod
    def format_permission_id(resource: str, action: Action, scope: Scope) -> str:
        """Canonical permission_id for resource/action/scope.

        Returns the registered identifier when it exists; otherwise the
        conventional form (``resource:action_scope`` for own/any,
        ``resource:action`` for system) used to name new permissions.
        """
        registered = PermissionService.find_permission_id(resource, action, scope)
        if registered:
            return registered
        if scope == Scope.SYSTEM:
            return f"{resource}:{action.value}"
        return f"{resource}:{action.value}_{scope.value}"
