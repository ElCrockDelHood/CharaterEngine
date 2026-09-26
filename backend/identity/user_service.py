"""User service for CHARACTER ENGINE backend.

This module implements the user business logic layer, including validation,
normalization, creation, and queries.
"""

import re
from typing import Optional
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.database.models import User as UserModel, UserStatus as DBUserStatus
from backend.identity.user_domain import (
    User,
    CreateUserRequest,
    UserDTO,
    UserStatus,
    UserValidationError,
    UserDuplicateError,
    UserNotFoundError,
    UserPersistenceError
)


class UserService:
    """User service for user business logic."""
    
    # Validation policies
    EMAIL_MIN_LENGTH = 5
    EMAIL_MAX_LENGTH = 255
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    USERNAME_MIN_LENGTH = 3
    USERNAME_MAX_LENGTH = 100
    USERNAME_PATTERN = r'^[a-zA-Z0-9_-]+$'
    
    @staticmethod
    def validate_email(email: str) -> None:
        """Validate email address.
        
        Args:
            email: Email address to validate
            
        Raises:
            UserValidationError: If email is invalid
        """
        if not email:
            raise UserValidationError("Email cannot be empty", "email")
        
        if len(email) < UserService.EMAIL_MIN_LENGTH:
            raise UserValidationError(
                f"Email must be at least {UserService.EMAIL_MIN_LENGTH} characters",
                "email"
            )
        
        if len(email) > UserService.EMAIL_MAX_LENGTH:
            raise UserValidationError(
                f"Email cannot exceed {UserService.EMAIL_MAX_LENGTH} characters",
                "email"
            )
        
        if not re.match(UserService.EMAIL_PATTERN, email):
            raise UserValidationError("Email format is invalid", "email")
    
    @staticmethod
    def validate_username(username: str) -> None:
        """Validate username.
        
        Args:
            username: Username to validate
            
        Raises:
            UserValidationError: If username is invalid
        """
        if not username:
            raise UserValidationError("Username cannot be empty", "username")
        
        if len(username) < UserService.USERNAME_MIN_LENGTH:
            raise UserValidationError(
                f"Username must be at least {UserService.USERNAME_MIN_LENGTH} characters",
                "username"
            )
        
        if len(username) > UserService.USERNAME_MAX_LENGTH:
            raise UserValidationError(
                f"Username cannot exceed {UserService.USERNAME_MAX_LENGTH} characters",
                "username"
            )
        
        if not re.match(UserService.USERNAME_PATTERN, username):
            raise UserValidationError(
                "Username can only contain letters, numbers, underscores, and hyphens",
                "username"
            )
    
    @staticmethod
    def normalize_email(email: str) -> str:
        """Normalize email address.
        
        Policy: Convert to lowercase and trim whitespace.
        
        Args:
            email: Email address to normalize
            
        Returns:
            Normalized email address
        """
        return email.strip().lower()
    
    @staticmethod
    def normalize_username(username: str) -> str:
        """Normalize username.
        
        Policy: Convert to lowercase and trim whitespace.
        
        Args:
            username: Username to normalize
            
        Returns:
            Normalized username
        """
        return username.strip().lower()
    
    @staticmethod
    def map_status(db_status: DBUserStatus) -> UserStatus:
        """Map database status to domain status.
        
        Args:
            db_status: Database user status
            
        Returns:
            Domain user status
        """
        # Handle both enum and string values
        if isinstance(db_status, str):
            return UserStatus(db_status)
        return UserStatus(db_status.value)
    
    @staticmethod
    def map_status_to_db(domain_status: UserStatus) -> DBUserStatus:
        """Map domain status to database status.
        
        Args:
            domain_status: Domain user status
            
        Returns:
            Database user status
        """
        return DBUserStatus(domain_status.value)
    
    @staticmethod
    def user_model_to_domain(user_model: UserModel) -> User:
        """Convert database model to domain entity.
        
        Args:
            user_model: Database user model
            
        Returns:
            Domain user entity
        """
        return User(
            user_id=user_model.id,
            email=user_model.email,
            username=user_model.username,
            status=UserService.map_status(user_model.status),
            created_at=user_model.created_at,
            updated_at=user_model.updated_at
        )
    
    @staticmethod
    def user_model_to_dto(user_model: UserModel) -> UserDTO:
        """Convert database model to DTO.
        
        Args:
            user_model: Database user model
            
        Returns:
            User DTO
        """
        return UserDTO(
            user_id=user_model.id,
            email=user_model.email,
            username=user_model.username,
            status=user_model.status.value,
            created_at=user_model.created_at,
            updated_at=user_model.updated_at
        )
    
    @staticmethod
    def create_user(session: Session, request: CreateUserRequest) -> User:
        """Create a new user.
        
        Args:
            session: Database session
            request: User creation request
            
        Returns:
            Created user domain entity
            
        Raises:
            UserValidationError: If validation fails
            UserDuplicateError: If email or username already exists
            UserPersistenceError: If database operation fails
        """
        # Validate and normalize email
        UserService.validate_email(request.email)
        normalized_email = UserService.normalize_email(request.email)
        
        # Validate and normalize username if provided
        normalized_username = None
        if request.username:
            UserService.validate_username(request.username)
            normalized_username = UserService.normalize_username(request.username)
            # Ensure we don't store empty string as username
            if not normalized_username:
                normalized_username = None
        
        # Create user model
        user_model = UserModel(
            id=str(uuid4()),  # Server-generated UUID
            email=normalized_email,
            username=normalized_username,
            status=DBUserStatus.ACTIVE  # Server-defaulted status
        )
        
        try:
            session.add(user_model)
            session.flush()  # Flush to trigger database constraints
            session.commit()
        except IntegrityError as e:
            session.rollback()
            
            # Parse integrity error to determine field
            error_str = str(e).lower()
            # Check which unique constraint was violated
            if normalized_username and "username" in error_str:
                raise UserDuplicateError(
                    f"Username '{normalized_username}' already exists",
                    "username",
                    normalized_username
                )
            elif "email" in error_str:
                raise UserDuplicateError(
                    f"Email '{normalized_email}' already exists",
                    "email",
                    normalized_email
                )
            else:
                raise UserPersistenceError("Failed to create user due to database constraint")
        except Exception as e:
            session.rollback()
            raise UserPersistenceError(f"Failed to create user: {str(e)}")
        
        # Convert to domain entity
        return UserService.user_model_to_domain(user_model)
    
    @staticmethod
    def get_user_by_id(session: Session, user_id: str) -> User:
        """Get user by ID.
        
        Args:
            session: Database session
            user_id: User ID
            
        Returns:
            User domain entity
            
        Raises:
            UserNotFoundError: If user not found
            UserPersistenceError: If database operation fails
        """
        try:
            user_model = session.query(UserModel).filter(UserModel.id == user_id).first()
            
            if not user_model:
                raise UserNotFoundError(f"User with ID '{user_id}' not found", user_id)
            
            return UserService.user_model_to_domain(user_model)
        except UserNotFoundError:
            raise
        except Exception as e:
            raise UserPersistenceError(f"Failed to get user by ID: {str(e)}")
    
    @staticmethod
    def get_user_by_email(session: Session, email: str) -> User:
        """Get user by email.
        
        Args:
            session: Database session
            email: User email
            
        Returns:
            User domain entity
            
        Raises:
            UserNotFoundError: If user not found
            UserPersistenceError: If database operation fails
        """
        # Normalize email for lookup
        normalized_email = UserService.normalize_email(email)
        
        try:
            user_model = session.query(UserModel).filter(
                UserModel.email == normalized_email
            ).first()
            
            if not user_model:
                raise UserNotFoundError(
                    f"User with email '{normalized_email}' not found"
                )
            
            return UserService.user_model_to_domain(user_model)
        except UserNotFoundError:
            raise
        except Exception as e:
            raise UserPersistenceError(f"Failed to get user by email: {str(e)}")
    
    @staticmethod
    def get_user_by_username(session: Session, username: str) -> User:
        """Get user by username.
        
        Args:
            session: Database session
            username: Username
            
        Returns:
            User domain entity
            
        Raises:
            UserNotFoundError: If user not found
            UserPersistenceError: If database operation fails
        """
        # Normalize username for lookup
        normalized_username = UserService.normalize_username(username)
        
        try:
            user_model = session.query(UserModel).filter(
                UserModel.username == normalized_username
            ).first()
            
            if not user_model:
                raise UserNotFoundError(
                    f"User with username '{normalized_username}' not found"
                )
            
            return UserService.user_model_to_domain(user_model)
        except UserNotFoundError:
            raise
        except Exception as e:
            raise UserPersistenceError(f"Failed to get user by username: {str(e)}")
    
    @staticmethod
    def user_exists_by_email(session: Session, email: str) -> bool:
        """Check if user exists by email.
        
        Args:
            session: Database session
            email: User email
            
        Returns:
            True if user exists, False otherwise
            
        Raises:
            UserPersistenceError: If database operation fails
        """
        # Normalize email for lookup
        normalized_email = UserService.normalize_email(email)
        
        try:
            count = session.query(UserModel).filter(
                UserModel.email == normalized_email
            ).count()
            return count > 0
        except Exception as e:
            raise UserPersistenceError(f"Failed to check user existence by email: {str(e)}")
    
    @staticmethod
    def user_exists_by_username(session: Session, username: str) -> bool:
        """Check if user exists by username.
        
        Args:
            session: Database session
            username: Username
            
        Returns:
            True if user exists, False otherwise
            
        Raises:
            UserPersistenceError: If database operation fails
        """
        # Normalize username for lookup
        normalized_username = UserService.normalize_username(username)
        
        try:
            count = session.query(UserModel).filter(
                UserModel.username == normalized_username
            ).count()
            return count > 0
        except Exception as e:
            raise UserPersistenceError(f"Failed to check user existence by username: {str(e)}")