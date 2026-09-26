"""Account and Identity domain models for CHARACTER ENGINE backend.

This module defines the domain layer for account and identity management,
separate from the database persistence layer.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class AccountStatus(str, Enum):
    """Account status enumeration - domain level."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class IdentityStatus(str, Enum):
    """Identity status enumeration - domain level."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"


@dataclass(frozen=True)
class Account:
    """Account domain entity.
    
    Represents a product/application-level container associated with a User.
    This is the canonical domain contract, separate from the database persistence layer.
    
    Invariants:
    - account_id is a valid UUID string
    - user_id is a valid UUID string
    - account_type is one of the allowed types
    - status is a valid AccountStatus
    - created_at and updated_at are server-generated
    """
    account_id: str
    user_id: str
    account_type: str
    status: AccountStatus
    created_at: datetime
    updated_at: datetime
    
    def __post_init__(self):
        """Validate account invariants."""
        # Validate account_id is not empty
        if not self.account_id or not isinstance(self.account_id, str):
            raise ValueError("account_id must be a non-empty string")
        
        # Validate user_id is not empty
        if not self.user_id or not isinstance(self.user_id, str):
            raise ValueError("user_id must be a non-empty string")
        
        # Validate account_type
        if not self.account_type or not isinstance(self.account_type, str):
            raise ValueError("account_type must be a non-empty string")
        
        # Validate status
        if not isinstance(self.status, AccountStatus):
            raise ValueError(f"status must be AccountStatus, got {type(self.status)}")
        
        # Validate timestamps
        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at must be datetime")
        if not isinstance(self.updated_at, datetime):
            raise ValueError("updated_at must be datetime")


@dataclass(frozen=True)
class Identity:
    """Identity domain entity.
    
    Represents an authentication identity/provider relationship. This includes
    both profile information and provider abstraction for external authentication.
    
    Invariants:
    - identity_id is a valid UUID string
    - user_id is a valid UUID string
    - provider is optional but valid if present
    - provider_subject is optional but valid if present
    - status is a valid IdentityStatus
    - created_at and updated_at are server-generated
    """
    identity_id: str
    user_id: str
    provider: Optional[str]
    provider_subject: Optional[str]
    display_name: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    locale: str
    timezone: str
    created_at: datetime
    updated_at: datetime
    
    def __post_init__(self):
        """Validate identity invariants."""
        # Validate identity_id is not empty
        if not self.identity_id or not isinstance(self.identity_id, str):
            raise ValueError("identity_id must be a non-empty string")
        
        # Validate user_id is not empty
        if not self.user_id or not isinstance(self.user_id, str):
            raise ValueError("user_id must be a non-empty string")
        
        # Validate locale
        if not self.locale or not isinstance(self.locale, str):
            raise ValueError("locale must be a non-empty string")
        
        # Validate timezone
        if not self.timezone or not isinstance(self.timezone, str):
            raise ValueError("timezone must be a non-empty string")
        
        # Validate timestamps
        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at must be datetime")
        if not isinstance(self.updated_at, datetime):
            raise ValueError("updated_at must be datetime")


@dataclass
class CreateAccountRequest:
    """Account creation request schema.
    
    This schema defines the contract for account creation. All fields are
    server-controlled except user_id and account_type.
    
    Security:
    - account_id is NOT accepted from client (server-generated)
    - status is NOT accepted from client (server-defaulted)
    - created_at/updated_at are NOT accepted from client (server-generated)
    - No privilege/role fields accepted
    """
    user_id: str
    account_type: str = "standard"
    
    def __post_init__(self):
        """Validate request invariants."""
        if not self.user_id or not isinstance(self.user_id, str):
            raise ValueError("user_id must be a non-empty string")
        
        if not self.account_type or not isinstance(self.account_type, str):
            raise ValueError("account_type must be a non-empty string")


@dataclass
class CreateIdentityRequest:
    """Identity creation request schema.
    
    This schema defines the contract for identity creation. All fields are
    server-controlled except the profile information.
    
    Security:
    - identity_id is NOT accepted from client (server-generated)
    - status is NOT accepted from client (server-defaulted)
    - created_at/updated_at are NOT accepted from client (server-generated)
    """
    user_id: str
    provider: Optional[str] = None
    provider_subject: Optional[str] = None
    display_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    locale: str = "en"
    timezone: str = "UTC"
    
    def __post_init__(self):
        """Validate request invariants."""
        if not self.user_id or not isinstance(self.user_id, str):
            raise ValueError("user_id must be a non-empty string")
        
        if not self.locale or not isinstance(self.locale, str):
            raise ValueError("locale must be a non-empty string")
        
        if not self.timezone or not isinstance(self.timezone, str):
            raise ValueError("timezone must be a non-empty string")


@dataclass(frozen=True)
class AccountDTO:
    """Account data transfer object.
    
    Safe representation of account data for external systems.
    """
    account_id: str
    user_id: str
    account_type: str
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class IdentityDTO:
    """Identity data transfer object.
    
    Safe representation of identity data for external systems.
    """
    identity_id: str
    user_id: str
    provider: Optional[str]
    provider_subject: Optional[str]
    display_name: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    locale: str
    timezone: str
    created_at: datetime
    updated_at: datetime


class AccountError(Exception):
    """Base exception for account-related errors."""
    
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class AccountValidationError(AccountError):
    """Exception raised when account validation fails."""
    
    def __init__(self, message: str, field: str):
        self.field = field
        super().__init__(message, error_code="ACCOUNT_VALIDATION_ERROR")


class AccountNotFoundError(AccountError):
    """Exception raised when account is not found."""
    
    def __init__(self, message: str, account_id: Optional[str] = None):
        self.account_id = account_id
        super().__init__(message, error_code="ACCOUNT_NOT_FOUND_ERROR")


class AccountOwnershipError(AccountError):
    """Exception raised when account ownership validation fails."""
    
    def __init__(self, message: str, account_id: str, user_id: str):
        self.account_id = account_id
        self.user_id = user_id
        super().__init__(message, error_code="ACCOUNT_OWNERSHIP_ERROR")


class AccountPersistenceError(AccountError):
    """Exception raised when account persistence fails."""
    
    def __init__(self, message: str):
        super().__init__(message, error_code="ACCOUNT_PERSISTENCE_ERROR")


class IdentityError(Exception):
    """Base exception for identity-related errors."""
    
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class IdentityValidationError(IdentityError):
    """Exception raised when identity validation fails."""
    
    def __init__(self, message: str, field: str):
        self.field = field
        super().__init__(message, error_code="IDENTITY_VALIDATION_ERROR")


class IdentityNotFoundError(IdentityError):
    """Exception raised when identity is not found."""
    
    def __init__(self, message: str, identity_id: Optional[str] = None):
        self.identity_id = identity_id
        super().__init__(message, error_code="IDENTITY_NOT_FOUND_ERROR")


class IdentityDuplicateError(IdentityError):
    """Exception raised when duplicate identity is detected."""
    
    def __init__(self, message: str, provider: Optional[str] = None, provider_subject: Optional[str] = None):
        self.provider = provider
        self.provider_subject = provider_subject
        super().__init__(message, error_code="IDENTITY_DUPLICATE_ERROR")


class IdentityPersistenceError(IdentityError):
    """Exception raised when identity persistence fails."""
    
    def __init__(self, message: str):
        super().__init__(message, error_code="IDENTITY_PERSISTENCE_ERROR")