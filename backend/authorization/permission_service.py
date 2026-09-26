"""Permission service for CHARACTER ENGINE backend.

This module implements permission management and checking.
"""

from typing import Set, Optional
from backend.authorization.authorization_domain import (
    Permission,
    Action,
    Scope
)


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
    
    @staticmethod
    def get_permission(permission_id: str) -> Optional[Permission]:
        """Get permission by ID.
        
        Args:
            permission_id: Permission identifier
            
        Returns:
            Permission object or None if not found
        """
        return PermissionService.PERMISSION_REGISTRY.get(permission_id)
    
    @staticmethod
    def get_role_permissions(role_id: str) -> Set[str]:
        """Get permissions for a role.
        
        Args:
            role_id: Role identifier
            
        Returns:
            Set of permission IDs for the role
        """
        return set(PermissionService.ROLE_PERMISSIONS.get(role_id, set()))
    
    @staticmethod
    def get_system_permissions() -> Set[str]:
        """Get system actor permissions.
        
        Returns:
            Set of permission IDs for system actor
        """
        return set(PermissionService.SYSTEM_PERMISSIONS)
    
    @staticmethod
    def has_permission(
        actor_permissions: Set[str],
        resource: str,
        action: Action,
        scope: Scope
    ) -> bool:
        """Check if actor has permission for resource:action:scope.
        
        Args:
            actor_permissions: Set of permission IDs the actor has
            resource: Resource type
            action: Action type
            scope: Permission scope
            
        Returns:
            True if actor has permission, False otherwise
        """
        # Construct permission ID
        permission_id = f"{resource}:{action.value}:{scope.value}"
        
        # Check if actor has the permission
        return permission_id in actor_permissions
    
    @staticmethod
    def format_permission_id(resource: str, action: Action, scope: Scope) -> str:
        """Format permission ID from components.
        
        Args:
            resource: Resource type
            action: Action type
            scope: Permission scope
            
        Returns:
            Formatted permission ID
        """
        return f"{resource}:{action.value}:{scope.value}"
