"""User domain models and exceptions for CHARACTER ENGINE backend.

This module defines the domain layer for user management, separate from
the database persistence layer.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class UserStatus(str, Enum):
    """User status enumeration - domain level."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


@dataclass(frozen=True)
class User:
    """User domain entity.
    
    Represents a user in the system. This is the canonical domain contract,
    separate from the database persistence layer.
    
    Invariants:
    - user_id is a valid UUID string
    - email is normalized and valid
    - username is normalized and valid (if present)
    - status is a valid UserStatus
    - created_at and updated_at are server-generated
    """
    user_id: str
    email: str
    username: Optional[str]
    status: UserStatus
    created_at: datetime
    updated_at: datetime
    
    def __post_init__(self):
        """Validate user invariants."""
        # Validate user_id is not empty
        if not self.user_id or not isinstance(self.user_id, str):
            raise ValueError("user_id must be a non-empty string")
        
        # Validate email is not empty
        if not self.email or not isinstance(self.email, str):
            raise ValueError("email must be a non-empty string")
        
        # Validate status
        if not isinstance(self.status, UserStatus):
            raise ValueError(f"status must be UserStatus, got {type(self.status)}")
        
        # Validate timestamps
        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at must be datetime")
        if not isinstance(self.updated_at, datetime):
            raise ValueError("updated_at must be datetime")


@dataclass
class CreateUserRequest:
    """User creation request schema.
    
    This schema defines the contract for user creation. All fields are
    server-controlled except email and username.
    
    Security:
    - user_id is NOT accepted from client (server-generated)
    - status is NOT accepted from client (server-defaulted)
    - created_at/updated_at are NOT accepted from client (server-generated)
    - No privilege/role fields accepted
    - No password fields accepted (deferred to authentication)
    """
    email: str
    username: Optional[str] = None
    
    def __post_init__(self):
        """Validate request invariants."""
        if not self.email or not isinstance(self.email, str):
            raise ValueError("email must be a non-empty string")
        
        if self.username is not None:
            if not isinstance(self.username, str):
                raise ValueError("username must be a string if provided")
            if not self.username or not self.username.strip():
                raise ValueError("username must be a non-empty string if provided")


@dataclass(frozen=True)
class UserDTO:
    """User data transfer object.
    
    Safe representation of user data for external systems. Contains
    only safe fields for transmission.
    """
    user_id: str
    email: str
    username: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime


class UserError(Exception):
    """Base exception for user-related errors."""
    
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class UserValidationError(UserError):
    """Exception raised when user validation fails."""
    
    def __init__(self, message: str, field: str):
        self.field = field
        super().__init__(message, error_code="USER_VALIDATION_ERROR")


class UserDuplicateError(UserError):
    """Exception raised when duplicate user is detected."""
    
    def __init__(self, message: str, field: str, value: str):
        self.field = field
        self.value = value
        super().__init__(message, error_code="USER_DUPLICATE_ERROR")


class UserNotFoundError(UserError):
    """Exception raised when user is not found."""
    
    def __init__(self, message: str, user_id: Optional[str] = None):
        self.user_id = user_id
        super().__init__(message, error_code="USER_NOT_FOUND_ERROR")


class UserPersistenceError(UserError):
    """Exception raised when user persistence fails.
    
    This wraps database/ORM exceptions to prevent leaking internal details.
    """
    
    def __init__(self, message: str):
        super().__init__(message, error_code="USER_PERSISTENCE_ERROR")