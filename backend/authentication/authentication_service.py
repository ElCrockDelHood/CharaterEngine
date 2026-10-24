"""Authentication service for CHARACTER ENGINE backend.

This module implements the authentication business logic layer, including
password verification, session management, and account state validation.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from backend.authentication.authentication_domain import (
    AuthenticateRequest,
    AuthenticationResponse,
    AuthenticationResult,
    CreateCredentialRequest,
    Credential,
    CredentialDTO,
    CredentialError,
    CredentialNotFoundError,
    CredentialType,
    Session,
    SessionDTO,
    SessionError,
    SessionExpiredError,
    SessionNotFoundError,
    SessionRevokedError,
    SessionStatus,
)
from backend.authentication.password_service import PasswordService
from backend.config.config import get_config
from backend.database.models import Credential as CredentialModel
from backend.database.models import Session as SessionModel
from backend.identity.account_identity_domain import AccountStatus
from backend.identity.account_identity_service import AccountService


class CredentialService:
    """Credential service for credential business logic."""

    @staticmethod
    def validate_password(password: str) -> None:
        """Validate password against security requirements.

        Args:
            password: Password to validate

        Raises:
            ValueError: If password is invalid
        """
        config = get_config()

        if not password:
            raise ValueError("Password cannot be empty")

        if len(password) < config.security.password_min_length:
            raise ValueError(
                f"Password must be at least {config.security.password_min_length} characters"
            )

        if len(password) > config.security.password_max_length:
            raise ValueError(
                f"Password cannot exceed {config.security.password_max_length} characters"
            )

    @staticmethod
    def map_credential_type(domain_type: CredentialType) -> str:
        """Map domain credential type to database string.

        Args:
            domain_type: Domain credential type

        Returns:
            Database credential type string
        """
        return domain_type.value

    @staticmethod
    def credential_model_to_domain(credential_model: CredentialModel) -> Credential:
        """Convert database model to domain entity.

        Args:
            credential_model: Database credential model

        Returns:
            Domain credential entity
        """
        return Credential(
            credential_id=credential_model.id,
            account_id=credential_model.account_id,
            credential_type=CredentialType(credential_model.credential_type),
            credential_hash=credential_model.credential_hash,
            is_active=credential_model.is_active,
            created_at=credential_model.created_at,
            expires_at=credential_model.expires_at,
            invalidated_at=credential_model.invalidated_at
        )

    @staticmethod
    def credential_model_to_dto(credential_model: CredentialModel) -> CredentialDTO:
        """Convert database model to DTO.

        Args:
            credential_model: Database credential model

        Returns:
            Credential DTO
        """
        return CredentialDTO(
            credential_id=credential_model.id,
            account_id=credential_model.account_id,
            credential_type=credential_model.credential_type,
            is_active=credential_model.is_active,
            created_at=credential_model.created_at,
            expires_at=credential_model.expires_at,
            invalidated_at=credential_model.invalidated_at
        )

    @staticmethod
    def create_credential(session: DbSession, request: CreateCredentialRequest) -> Credential:
        """Create a new credential.

        Args:
            session: Database session
            request: Credential creation request

        Returns:
            Created credential domain entity

        Raises:
            CredentialError: If validation fails or database operation fails
        """
        # Validate password if password credential
        if request.credential_type == CredentialType.PASSWORD:
            CredentialService.validate_password(request.password)
            # Hash password
            credential_hash = PasswordService.hash_password(request.password)
        else:
            # For non-password credentials, use provided hash (future OAuth implementation)
            credential_hash = request.password  # In this case, password is the hash

        # Create credential model
        credential_model = CredentialModel(
            id=str(uuid4()),  # Server-generated UUID
            account_id=request.account_id,
            credential_type=CredentialService.map_credential_type(request.credential_type),
            credential_hash=credential_hash,
            is_active=True,  # Server-defaulted
            created_at=datetime.now(timezone.utc)  # Will be overridden by server_default
        )

        try:
            session.add(credential_model)
            session.flush()  # Flush to trigger database constraints
            session.commit()
        except IntegrityError as e:
            session.rollback()

            # Parse integrity error to determine field
            error_str = str(e).lower()
            if "account_id" in error_str or "accounts" in error_str:
                raise CredentialError(
                    f"Account with ID '{request.account_id}' does not exist"
                )
            else:
                raise CredentialError("Failed to create credential due to database constraint")
        except Exception as e:
            session.rollback()
            raise CredentialError(f"Failed to create credential: {str(e)}")

        # Convert to domain entity
        return CredentialService.credential_model_to_domain(credential_model)

    @staticmethod
    def get_active_credential(session: DbSession, account_id: str) -> Optional[Credential]:
        """Get active credential for an account.

        Args:
            session: Database session
            account_id: Account ID

        Returns:
            Credential domain entity or None if not found

        Raises:
            CredentialError: If database operation fails
        """
        try:
            credential_model = session.query(CredentialModel).filter(
                CredentialModel.account_id == account_id,
                CredentialModel.is_active == True,
                CredentialModel.invalidated_at.is_(None)
            ).first()

            if not credential_model:
                return None

            return CredentialService.credential_model_to_domain(credential_model)
        except Exception as e:
            raise CredentialError(f"Failed to get active credential: {str(e)}")

    @staticmethod
    def invalidate_credential(session: DbSession, credential_id: str) -> Credential:
        """Invalidate a credential.

        Args:
            session: Database session
            credential_id: Credential ID

        Returns:
            Updated credential domain entity

        Raises:
            CredentialNotFoundError: If credential not found
            CredentialError: If database operation fails
        """
        try:
            credential_model = session.query(CredentialModel).filter(
                CredentialModel.id == credential_id
            ).first()

            if not credential_model:
                raise CredentialNotFoundError(f"Credential with ID '{credential_id}' not found", credential_id)

            # Mark as invalidated
            credential_model.invalidated_at = datetime.now(timezone.utc)
            credential_model.is_active = False

            session.commit()

            return CredentialService.credential_model_to_domain(credential_model)
        except CredentialNotFoundError:
            raise
        except Exception as e:
            session.rollback()
            raise CredentialError(f"Failed to invalidate credential: {str(e)}")


class SessionService:
    """Session service for session business logic."""

    @staticmethod
    def generate_token() -> str:
        """Generate a cryptographically secure random token.

        Returns:
            Secure random token string
        """
        # Generate 32-byte random token (256 bits of entropy)
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a session token.

        Args:
            token: Plain text token

        Returns:
            Hashed token string
        """
        return PasswordService.hash_password(token)

    @staticmethod
    def verify_token(token: str, token_hash: str) -> bool:
        """Verify a token against a hash.

        Args:
            token: Plain text token
            token_hash: Hashed token

        Returns:
            True if token matches hash, False otherwise
        """
        return PasswordService.verify_password(token, token_hash)

    @staticmethod
    def calculate_expiration() -> datetime:
        """Calculate session expiration time.

        Returns:
            Expiration datetime
        """
        config = get_config()
        timeout_minutes = config.security.session_timeout_minutes
        return datetime.now(timezone.utc) + timedelta(minutes=timeout_minutes)

    @staticmethod
    def map_status(db_status: str) -> SessionStatus:
        """Map database status to domain status.

        Args:
            db_status: Database session status

        Returns:
            Domain session status
        """
        return SessionStatus(db_status)

    @staticmethod
    def session_model_to_domain(session_model: SessionModel) -> Session:
        """Convert database model to domain entity.

        Args:
            session_model: Database session model

        Returns:
            Domain session entity
        """
        return Session(
            session_id=session_model.id,
            account_id=session_model.account_id,
            token_hash=session_model.token_hash,
            device_id=session_model.device_id,
            ip_address=session_model.ip_address,
            user_agent=session_model.user_agent,
            status=SessionService.map_status(session_model.status),
            expires_at=session_model.expires_at,
            created_at=session_model.created_at
        )

    @staticmethod
    def session_model_to_dto(session_model: SessionModel) -> SessionDTO:
        """Convert database model to DTO.

        Args:
            session_model: Database session model

        Returns:
            Session DTO
        """
        return SessionDTO(
            session_id=session_model.id,
            account_id=session_model.account_id,
            device_id=session_model.device_id,
            ip_address=session_model.ip_address,
            user_agent=session_model.user_agent,
            status=session_model.status.value,
            expires_at=session_model.expires_at,
            created_at=session_model.created_at
        )

    @staticmethod
    def create_session(session: DbSession, account_id: str, device_id: Optional[str] = None,
                      ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> tuple[Session, str]:
        """Create a new session.

        Args:
            session: Database session
            account_id: Account ID
            device_id: Optional device identifier
            ip_address: Optional IP address
            user_agent: Optional user agent string

        Returns:
            Tuple of (session domain entity, plain text token)

        Raises:
            SessionError: If database operation fails
        """
        # Generate token
        token = SessionService.generate_token()
        token_hash = SessionService.hash_token(token)

        # Calculate expiration
        expires_at = SessionService.calculate_expiration()

        # Create session model
        session_model = SessionModel(
            id=str(uuid4()),  # Server-generated UUID
            account_id=account_id,
            token_hash=token_hash,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status="active",  # Server-defaulted
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc)  # Will be overridden by server_default
        )

        try:
            session.add(session_model)
            session.flush()  # Flush to trigger database constraints
            session.commit()
        except IntegrityError as e:
            session.rollback()

            # Parse integrity error to determine field
            error_str = str(e).lower()
            if "account_id" in error_str or "accounts" in error_str:
                raise SessionError(
                    f"Account with ID '{account_id}' does not exist"
                )
            else:
                raise SessionError("Failed to create session due to database constraint")
        except Exception as e:
            session.rollback()
            raise SessionError(f"Failed to create session: {str(e)}")

        # Convert to domain entity
        domain_session = SessionService.session_model_to_domain(session_model)

        return domain_session, token

    @staticmethod
    def get_session_by_id(session: DbSession, session_id: str) -> Session:
        """Get session by ID.

        Args:
            session: Database session
            session_id: Session ID

        Returns:
            Session domain entity

        Raises:
            SessionNotFoundError: If session not found
            SessionError: If database operation fails
        """
        try:
            session_model = session.query(SessionModel).filter(
                SessionModel.id == session_id
            ).first()

            if not session_model:
                raise SessionNotFoundError(f"Session with ID '{session_id}' not found", session_id)

            return SessionService.session_model_to_domain(session_model)
        except SessionNotFoundError:
            raise
        except Exception as e:
            raise SessionError(f"Failed to get session by ID: {str(e)}")

    @staticmethod
    def validate_session(session: DbSession, session_id: str, token: str) -> Session:
        """Validate a session by ID and token.

        Args:
            session: Database session
            session_id: Session ID
            token: Plain text token

        Returns:
            Session domain entity

        Raises:
            SessionNotFoundError: If session not found
            SessionExpiredError: If session is expired
            SessionRevokedError: If session is revoked
            SessionError: If validation fails
        """
        # Get session
        domain_session = SessionService.get_session_by_id(session, session_id)

        # Check if session is active
        if domain_session.status != SessionStatus.ACTIVE:
            if domain_session.status == SessionStatus.EXPIRED:
                raise SessionExpiredError("Session has expired")
            elif domain_session.status == SessionStatus.REVOKED:
                raise SessionRevokedError("Session has been revoked")
            else:
                raise SessionError(f"Session has invalid status: {domain_session.status}")

        # Check if session is expired
        # Handle both timezone-aware and timezone-naive timestamps
        expires_at = domain_session.expires_at
        if expires_at.tzinfo is not None:
            now = datetime.now(timezone.utc)
        else:
            now = datetime.now(timezone.utc).replace(tzinfo=None)

        if expires_at < now:
            raise SessionExpiredError("Session has expired")

        # Verify token
        if not SessionService.verify_token(token, domain_session.token_hash):
            raise SessionError("Invalid session token")

        return domain_session

    @staticmethod
    def revoke_session(session: DbSession, session_id: str) -> Session:
        """Revoke a session.

        Args:
            session: Database session
            session_id: Session ID

        Returns:
            Updated session domain entity

        Raises:
            SessionNotFoundError: If session not found
            SessionError: If database operation fails
        """
        try:
            session_model = session.query(SessionModel).filter(
                SessionModel.id == session_id
            ).first()

            if not session_model:
                raise SessionNotFoundError(f"Session with ID '{session_id}' not found", session_id)

            # Mark as revoked
            session_model.status = "revoked"

            session.commit()

            return SessionService.session_model_to_domain(session_model)
        except SessionNotFoundError:
            raise
        except Exception as e:
            session.rollback()
            raise SessionError(f"Failed to revoke session: {str(e)}")


class AuthenticationService:
    """Authentication service for authentication business logic."""

    @staticmethod
    def check_account_status(account_status: AccountStatus) -> bool:
        """Check if account can authenticate based on status.

        Args:
            account_status: Account status

        Returns:
            True if account can authenticate, False otherwise
        """
        return account_status == AccountStatus.ACTIVE

    @staticmethod
    def authenticate(session: DbSession, request: AuthenticateRequest) -> AuthenticationResponse:
        """Authenticate an account with credentials.

        Args:
            session: Database session
            request: Authentication request

        Returns:
            Authentication response

        Raises:
            AuthenticationFailedError: If authentication fails
        """
        # Get account
        try:
            account = AccountService.get_account_by_id(session, request.account_id)
        except Exception:
            # Account not found - return generic error to prevent enumeration
            return AuthenticationResponse(
                success=False,
                result=AuthenticationResult.INVALID_CREDENTIALS,
                error_message="Invalid credentials"
            )

        # Check account status
        if not AuthenticationService.check_account_status(account.status):
            if account.status == AccountStatus.INACTIVE:
                return AuthenticationResponse(
                    success=False,
                    result=AuthenticationResult.ACCOUNT_DISABLED,
                    error_message="Account is disabled"
                )
            elif account.status == AccountStatus.SUSPENDED:
                return AuthenticationResponse(
                    success=False,
                    result=AuthenticationResult.ACCOUNT_SUSPENDED,
                    error_message="Account is suspended"
                )
            else:
                return AuthenticationResponse(
                    success=False,
                    result=AuthenticationResult.ACCOUNT_DISABLED,
                    error_message="Account is not active"
                )

        # Get active credential
        try:
            credential = CredentialService.get_active_credential(session, request.account_id)
        except CredentialError:
            # Credential error - return generic error to prevent enumeration
            return AuthenticationResponse(
                success=False,
                result=AuthenticationResult.INVALID_CREDENTIALS,
                error_message="Invalid credentials"
            )

        if not credential:
            # No active credential - return generic error to prevent enumeration
            return AuthenticationResponse(
                success=False,
                result=AuthenticationResult.INVALID_CREDENTIALS,
                error_message="Invalid credentials"
            )

        # Only create session if credential exists and password is valid
        # Verify password first to avoid creating orphan sessions
        if not PasswordService.verify_password(request.password, credential.credential_hash):
            # Wrong password - return generic error to prevent enumeration
            return AuthenticationResponse(
                success=False,
                result=AuthenticationResult.INVALID_CREDENTIALS,
                error_message="Invalid credentials"
            )

        # Authentication successful - create session
        try:
            domain_session, token = SessionService.create_session(
                session,
                request.account_id,
                request.device_id,
                request.ip_address,
                request.user_agent
            )

            return AuthenticationResponse(
                success=True,
                result=AuthenticationResult.SUCCESS,
                session_id=domain_session.session_id,
                token=token,
                expires_at=domain_session.expires_at
            )
        except SessionError:
            # Session creation failed
            return AuthenticationResponse(
                success=False,
                result=AuthenticationResult.FAILURE,
                error_message="Failed to create session"
            )
