"""Authentication domain models for CHARACTER ENGINE backend.

This module defines the domain layer for authentication, separate from
the database persistence layer.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class CredentialType(str, Enum):
    """Credential type enumeration - domain level."""
    PASSWORD = "password"
    OAUTH = "oauth"
    API_KEY = "api_key"


class SessionStatus(str, Enum):
    """Session status enumeration - domain level."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class AuthenticationResult(str, Enum):
    """Authentication result enumeration."""
    SUCCESS = "success"
    FAILURE = "failure"
    ACCOUNT_DISABLED = "account_disabled"
    ACCOUNT_SUSPENDED = "account_suspended"
    INVALID_CREDENTIALS = "invalid_credentials"


@dataclass(frozen=True)
class Credential:
    """Credential domain entity.

    Represents authentication credentials for an account.

    Invariants:
    - credential_id is a valid UUID string
    - account_id is a valid UUID string
    - credential_type is valid
    - credential_hash is stored (never plaintext)
    - is_active is boolean
    - created_at and updated_at are server-generated
    """
    credential_id: str
    account_id: str
    credential_type: CredentialType
    credential_hash: str
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]
    invalidated_at: Optional[datetime]

    def __post_init__(self):
        """Validate credential invariants."""
        if not self.credential_id or not isinstance(self.credential_id, str):
            raise ValueError("credential_id must be a non-empty string")

        if not self.account_id or not isinstance(self.account_id, str):
            raise ValueError("account_id must be a non-empty string")

        if not isinstance(self.credential_type, CredentialType):
            raise ValueError(f"credential_type must be CredentialType, got {type(self.credential_type)}")

        if not self.credential_hash or not isinstance(self.credential_hash, str):
            raise ValueError("credential_hash must be a non-empty string")

        if not isinstance(self.is_active, bool):
            raise ValueError("is_active must be boolean")

        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at must be datetime")


@dataclass(frozen=True)
class Session:
    """Session domain entity.

    Represents an authenticated session for an account.

    Invariants:
    - session_id is a valid UUID string
    - account_id is a valid UUID string
    - token_hash is stored (never plaintext token)
    - status is valid SessionStatus
    - expires_at is in the future for active sessions
    - created_at is server-generated
    """
    session_id: str
    account_id: str
    token_hash: str
    device_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    status: SessionStatus
    expires_at: datetime
    created_at: datetime

    def __post_init__(self):
        """Validate session invariants."""
        if not self.session_id or not isinstance(self.session_id, str):
            raise ValueError("session_id must be a non-empty string")

        if not self.account_id or not isinstance(self.account_id, str):
            raise ValueError("account_id must be a non-empty string")

        if not self.token_hash or not isinstance(self.token_hash, str):
            raise ValueError("token_hash must be a non-empty string")

        if not isinstance(self.status, SessionStatus):
            raise ValueError(f"status must be SessionStatus, got {type(self.status)}")

        if not isinstance(self.expires_at, datetime):
            raise ValueError("expires_at must be datetime")

        if not isinstance(self.created_at, datetime):
            raise ValueError("created_at must be datetime")


@dataclass
class CreateCredentialRequest:
    """Credential creation request schema.

    This schema defines the contract for credential creation.

    Security:
    - credential_id is NOT accepted from client (server-generated)
    - credential_hash is NOT accepted from client (server-generated from password)
    - is_active is NOT accepted from client (server-defaulted)
    - created_at/updated_at are NOT accepted from client (server-generated)
    """
    account_id: str
    credential_type: CredentialType = CredentialType.PASSWORD
    password: Optional[str] = None  # Plain text password (will be hashed)

    def __post_init__(self):
        """Validate request invariants."""
        if not self.account_id or not isinstance(self.account_id, str):
            raise ValueError("account_id must be a non-empty string")

        if not isinstance(self.credential_type, CredentialType):
            raise ValueError(f"credential_type must be CredentialType, got {type(self.credential_type)}")

        if self.credential_type == CredentialType.PASSWORD and not self.password:
            raise ValueError("password is required for password credentials")


@dataclass
class AuthenticateRequest:
    """Authentication request schema.

    This schema defines the contract for authentication.

    Security:
    - account_id is accepted (identifier)
    - password is accepted (plain text, will be hashed for verification)
    - No session control fields accepted
    """
    account_id: str
    password: str
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    def __post_init__(self):
        """Validate request invariants."""
        if not self.account_id or not isinstance(self.account_id, str):
            raise ValueError("account_id must be a non-empty string")

        if not self.password or not isinstance(self.password, str):
            raise ValueError("password must be a non-empty string")


@dataclass
class AuthenticationResponse:
    """Authentication response schema.

    This schema defines the contract for authentication response.

    Security:
    - token is the plain text session token (returned only on success)
    - session_id is server-generated
    - expires_at is server-generated
    """
    success: bool
    result: AuthenticationResult
    session_id: Optional[str] = None
    token: Optional[str] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass(frozen=True)
class CredentialDTO:
    """Credential data transfer object.

    Safe representation of credential data for external systems.
    """
    credential_id: str
    account_id: str
    credential_type: str
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]
    invalidated_at: Optional[datetime]


@dataclass(frozen=True)
class SessionDTO:
    """Session data transfer object.

    Safe representation of session data for external systems.
    """
    session_id: str
    account_id: str
    device_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    status: str
    expires_at: datetime
    created_at: datetime


class AuthenticationError(Exception):
    """Base exception for authentication-related errors."""

    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class CredentialError(AuthenticationError):
    """Exception raised when credential operations fail."""

    def __init__(self, message: str):
        super().__init__(message, error_code="CREDENTIAL_ERROR")


class CredentialNotFoundError(AuthenticationError):
    """Exception raised when credential is not found."""

    def __init__(self, message: str, credential_id: Optional[str] = None):
        self.credential_id = credential_id
        super().__init__(message, error_code="CREDENTIAL_NOT_FOUND_ERROR")


class AuthenticationFailedError(AuthenticationError):
    """Exception raised when authentication fails."""

    def __init__(self, message: str, result: AuthenticationResult):
        self.result = result
        super().__init__(message, error_code="AUTHENTICATION_FAILED_ERROR")


class SessionError(AuthenticationError):
    """Exception raised when session operations fail."""

    def __init__(self, message: str):
        super().__init__(message, error_code="SESSION_ERROR")


class SessionNotFoundError(AuthenticationError):
    """Exception raised when session is not found."""

    def __init__(self, message: str, session_id: Optional[str] = None):
        self.session_id = session_id
        super().__init__(message, error_code="SESSION_NOT_FOUND_ERROR")


class SessionExpiredError(AuthenticationError):
    """Exception raised when session is expired."""

    def __init__(self, message: str):
        super().__init__(message, error_code="SESSION_EXPIRED_ERROR")


class SessionRevokedError(AuthenticationError):
    """Exception raised when session is revoked."""

    def __init__(self, message: str):
        super().__init__(message, error_code="SESSION_REVOKED_ERROR")
