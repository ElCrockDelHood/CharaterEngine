"""Role service for CHARACTER ENGINE backend.

This module implements role management including assignment, revocation, and bootstrap.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from uuid import uuid4

from backend.database.models import Role as RoleModel, UserRole as UserRoleModel, User as UserModel
from backend.authorization.authorization_domain import Role
from backend.authorization.permission_service import PermissionService


class RoleService:
    """Role service for role management."""
    
    @staticmethod
    def create_role(
        db: Session,
        role_id: str,
        role_name: str,
        description: Optional[str] = None
    ) -> Role:
        """Create a new role.
        
        Args:
            db: Database session
            role_id: Role identifier (e.g., "user", "admin")
            role_name: Human-readable role name
            description: Role description
            
        Returns:
            Created role domain entity
            
        Raises:
            ValueError: If role_id is invalid
        """
        # Validate role_id
        if role_id not in ["user", "admin"]:
            raise ValueError(f"Invalid role_id: {role_id}. Must be 'user' or 'admin'.")
        
        # Check if role already exists
        existing_role = db.execute(
            select(RoleModel).where(RoleModel.role_id == role_id)
        ).scalar_one_or_none()
        
        if existing_role:
            raise ValueError(f"Role with role_id '{role_id}' already exists")
        
        # Create role
        role_model = RoleModel(
            id=str(uuid4()),
            role_id=role_id,
            role_name=role_name,
            description=description,
            created_at=datetime.utcnow()
        )
        
        db.add(role_model)
        db.commit()
        db.refresh(role_model)
        
        return Role(
            role_id=role_model.role_id,
            role_name=role_model.role_name,
            description=role_model.description,
            created_at=role_model.created_at
        )
    
    @staticmethod
    def get_role(db: Session, role_id: str) -> Optional[Role]:
        """Get role by ID.
        
        Args:
            db: Database session
            role_id: Role identifier
            
        Returns:
            Role domain entity or None if not found
        """
        role_model = db.execute(
            select(RoleModel).where(RoleModel.role_id == role_id)
        ).scalar_one_or_none()
        
        if not role_model:
            return None
        
        return Role(
            role_id=role_model.role_id,
            role_name=role_model.role_name,
            description=role_model.description,
            created_at=role_model.created_at
        )
    
    @staticmethod
    def assign_role(
        db: Session,
        user_id: str,
        role_id: str,
        assigned_by: str
    ) -> UserRoleModel:
        """Assign a role to a user.
        
        Args:
            db: Database session
            user_id: User ID
            role_id: Role identifier
            assigned_by: User ID of the user assigning the role
            
        Returns:
            Created UserRole model
            
        Raises:
            ValueError: If role_id is invalid or user already has active role
        """
        # Validate role_id
        if role_id not in ["user", "admin"]:
            raise ValueError(f"Invalid role_id: {role_id}. Must be 'user' or 'admin'.")
        
        # Check if user already has active role
        existing_assignment = db.execute(
            select(UserRoleModel).where(
                UserRoleModel.user_id == user_id,
                UserRoleModel.role_id == role_id,
                UserRoleModel.revoked_at.is_(None)
            )
        ).scalar_one_or_none()
        
        if existing_assignment:
            raise ValueError(f"User already has active role '{role_id}'")
        
        # Assign role
        user_role = UserRoleModel(
            id=str(uuid4()),
            user_id=user_id,
            role_id=role_id,
            assigned_by=assigned_by,
            assigned_at=datetime.utcnow(),
            revoked_at=None
        )
        
        db.add(user_role)
        db.commit()
        db.refresh(user_role)
        
        return user_role
    
    @staticmethod
    def revoke_role(
        db: Session,
        user_id: str,
        role_id: str,
        revoked_by: str
    ) -> Optional[UserRoleModel]:
        """Revoke a role from a user.
        
        Args:
            db: Database session
            user_id: User ID
            role_id: Role identifier
            revoked_by: User ID of the user revoking the role
            
        Returns:
            Updated UserRole model or None if no active assignment found
            
        Raises:
            ValueError: If attempting to revoke last admin role
        """
        # Check if user has active role
        user_role = db.execute(
            select(UserRoleModel).where(
                UserRoleModel.user_id == user_id,
                UserRoleModel.role_id == role_id,
                UserRoleModel.revoked_at.is_(None)
            )
        ).scalar_one_or_none()
        
        if not user_role:
            return None
        
        # Check if this is the last admin role
        if role_id == "admin":
            admin_count = db.execute(
                select(UserRoleModel).where(
                    UserRoleModel.role_id == "admin",
                    UserRoleModel.revoked_at.is_(None)
                )
            ).count()
            
            if admin_count <= 1:
                raise ValueError("Cannot revoke last admin role in system")
        
        # Revoke role (append-only: set revoked_at)
        user_role.revoked_at = datetime.utcnow()
        db.commit()
        db.refresh(user_role)
        
        return user_role
    
    @staticmethod
    def get_user_roles(db: Session, user_id: str) -> List[str]:
        """Get active roles for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            List of role IDs for the user
        """
        user_roles = db.execute(
            select(UserRoleModel).where(
                UserRoleModel.user_id == user_id,
                UserRoleModel.revoked_at.is_(None)
            )
        ).scalars().all()
        
        role_ids = []
        for user_role in user_roles:
            role = db.execute(
                select(RoleModel).where(RoleModel.id == user_role.role_id)
            ).scalar_one_or_none()
            if role:
                role_ids.append(role.role_id)
        
        return role_ids
    
    @staticmethod
    def bootstrap_roles(db: Session) -> None:
        """Bootstrap initial roles (USER and ADMIN).
        
        Args:
            db: Database session
            
        Raises:
            ValueError: If roles already exist
        """
        # Check if roles already exist
        existing_user_role = db.execute(
            select(RoleModel).where(RoleModel.role_id == "user")
        ).scalar_one_or_none()
        
        existing_admin_role = db.execute(
            select(RoleModel).where(RoleModel.role_id == "admin")
        ).scalar_one_or_none()
        
        if existing_user_role or existing_admin_role:
            raise ValueError("Roles already exist. Bootstrap can only be run once.")
        
        # Create USER role
        RoleService.create_role(
            db=db,
            role_id="user",
            role_name="User",
            description="Standard user role with self-permissions"
        )
        
        # Create ADMIN role
        RoleService.create_role(
            db=db,
            role_id="admin",
            role_name="Administrator",
            description="System administrator with system-permissions"
        )
    
    @staticmethod
    def assign_user_role_on_creation(db: Session, user_id: str) -> None:
        """Assign USER role to a user on user creation.
        
        Args:
            db: Database session
            user_id: User ID
        """
        # Get USER role
        user_role = RoleService.get_role(db, "user")
        
        if not user_role:
            raise ValueError("USER role not found. Run bootstrap first.")
        
        # Assign USER role (system assignment, no assigned_by)
        # Use None for system assignments
        user_role_assignment = UserRoleModel(
            id=str(uuid4()),
            user_id=user_id,
            role_id=user_role.role_id,
            assigned_by=None,  # System assignment
            assigned_at=datetime.utcnow(),
            revoked_at=None
        )
        
        db.add(user_role_assignment)
        db.commit()
