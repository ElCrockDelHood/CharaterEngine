"""Account and Identity service for CHARACTER ENGINE backend.

This module implements the account and identity business logic layer, including
validation, creation, queries, and ownership validation.
"""

from typing import List, Optional
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database.models import Account as AccountModel
from backend.database.models import AccountStatus as DBAccountStatus
from backend.database.models import Identity as IdentityModel
from backend.identity.account_identity_domain import (
    Account,
    AccountDTO,
    AccountNotFoundError,
    AccountPersistenceError,
    AccountStatus,
    AccountValidationError,
    CreateAccountRequest,
    CreateIdentityRequest,
    Identity,
    IdentityDTO,
    IdentityDuplicateError,
    IdentityNotFoundError,
    IdentityPersistenceError,
    IdentityValidationError,
)


class AccountService:
    """Account service for account business logic."""

    # Validation policies
    ACCOUNT_TYPE_VALUES = {"standard", "premium", "admin"}

    @staticmethod
    def validate_account_type(account_type: str) -> None:
        """Validate account type.

        Args:
            account_type: Account type to validate

        Raises:
            AccountValidationError: If account type is invalid
        """
        if not account_type:
            raise AccountValidationError("Account type cannot be empty", "account_type")

        if account_type not in AccountService.ACCOUNT_TYPE_VALUES:
            raise AccountValidationError(
                f"Account type must be one of {AccountService.ACCOUNT_TYPE_VALUES}",
                "account_type"
            )

    @staticmethod
    def validate_user_id(user_id: str) -> None:
        """Validate user ID.

        Args:
            user_id: User ID to validate

        Raises:
            AccountValidationError: If user ID is invalid
        """
        if not user_id or not isinstance(user_id, str):
            raise AccountValidationError("User ID cannot be empty", "user_id")

    @staticmethod
    def map_status(db_status: DBAccountStatus) -> AccountStatus:
        """Map database status to domain status.

        Args:
            db_status: Database account status

        Returns:
            Domain account status
        """
        # Handle both enum and string values
        if isinstance(db_status, str):
            return AccountStatus(db_status)
        return AccountStatus(db_status.value)

    @staticmethod
    def map_status_to_db(domain_status: AccountStatus) -> DBAccountStatus:
        """Map domain status to database status.

        Args:
            domain_status: Domain account status

        Returns:
            Database account status
        """
        return DBAccountStatus(domain_status.value)

    @staticmethod
    def account_model_to_domain(account_model: AccountModel) -> Account:
        """Convert database model to domain entity.

        Args:
            account_model: Database account model

        Returns:
            Domain account entity
        """
        return Account(
            account_id=account_model.id,
            user_id=account_model.user_id,
            account_type=account_model.account_type,
            status=AccountService.map_status(account_model.status),
            created_at=account_model.created_at,
            updated_at=account_model.updated_at
        )

    @staticmethod
    def account_model_to_dto(account_model: AccountModel) -> AccountDTO:
        """Convert database model to DTO.

        Args:
            account_model: Database account model

        Returns:
            Account DTO
        """
        return AccountDTO(
            account_id=account_model.id,
            user_id=account_model.user_id,
            account_type=account_model.account_type,
            status=account_model.status.value,
            created_at=account_model.created_at,
            updated_at=account_model.updated_at
        )

    @staticmethod
    def create_account(session: Session, request: CreateAccountRequest) -> Account:
        """Create a new account.

        Args:
            session: Database session
            request: Account creation request

        Returns:
            Created account domain entity

        Raises:
            AccountValidationError: If validation fails
            AccountPersistenceError: If database operation fails
        """
        # Validate user_id
        AccountService.validate_user_id(request.user_id)

        # Validate account_type
        AccountService.validate_account_type(request.account_type)

        # Create account model
        account_model = AccountModel(
            id=str(uuid4()),  # Server-generated UUID
            user_id=request.user_id,
            account_type=request.account_type,
            status=DBAccountStatus.ACTIVE  # Server-defaulted status
        )

        try:
            session.add(account_model)
            session.flush()  # Flush to trigger database constraints
            session.commit()
        except IntegrityError as e:
            session.rollback()

            # Parse integrity error to determine field
            error_str = str(e).lower()
            if "user_id" in error_str or "users" in error_str:
                raise AccountPersistenceError(
                    f"User with ID '{request.user_id}' does not exist"
                )
            else:
                raise AccountPersistenceError("Failed to create account due to database constraint")
        except Exception as e:
            session.rollback()
            raise AccountPersistenceError(f"Failed to create account: {str(e)}")

        # Convert to domain entity
        return AccountService.account_model_to_domain(account_model)

    @staticmethod
    def get_account_by_id(session: Session, account_id: str) -> Account:
        """Get account by ID.

        Args:
            session: Database session
            account_id: Account ID

        Returns:
            Account domain entity

        Raises:
            AccountNotFoundError: If account not found
            AccountPersistenceError: If database operation fails
        """
        try:
            account_model = session.query(AccountModel).filter(
                AccountModel.id == account_id
            ).first()

            if not account_model:
                raise AccountNotFoundError(f"Account with ID '{account_id}' not found", account_id)

            return AccountService.account_model_to_domain(account_model)
        except AccountNotFoundError:
            raise
        except Exception as e:
            raise AccountPersistenceError(f"Failed to get account by ID: {str(e)}")

    @staticmethod
    def get_accounts_by_user_id(session: Session, user_id: str) -> List[Account]:
        """Get accounts by user ID.

        Args:
            session: Database session
            user_id: User ID

        Returns:
            List of account domain entities

        Raises:
            AccountPersistenceError: If database operation fails
        """
        try:
            account_models = session.query(AccountModel).filter(
                AccountModel.user_id == user_id
            ).all()

            return [AccountService.account_model_to_domain(model) for model in account_models]
        except Exception as e:
            raise AccountPersistenceError(f"Failed to get accounts by user ID: {str(e)}")

    @staticmethod
    def account_exists(session: Session, account_id: str) -> bool:
        """Check if account exists.

        Args:
            session: Database session
            account_id: Account ID

        Returns:
            True if account exists, False otherwise

        Raises:
            AccountPersistenceError: If database operation fails
        """
        try:
            count = session.query(AccountModel).filter(
                AccountModel.id == account_id
            ).count()
            return count > 0
        except Exception as e:
            raise AccountPersistenceError(f"Failed to check account existence: {str(e)}")

    @staticmethod
    def validate_account_ownership(session: Session, account_id: str, user_id: str) -> bool:
        """Validate account ownership.

        Args:
            session: Database session
            account_id: Account ID
            user_id: User ID

        Returns:
            True if user owns the account, False otherwise

        Raises:
            AccountPersistenceError: If database operation fails
        """
        try:
            count = session.query(AccountModel).filter(
                AccountModel.id == account_id,
                AccountModel.user_id == user_id
            ).count()
            return count > 0
        except Exception as e:
            raise AccountPersistenceError(f"Failed to validate account ownership: {str(e)}")


class IdentityService:
    """Identity service for identity business logic."""

    # Validation policies
    LOCALE_VALUES = {"en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko"}
    TIMEZONE_VALUES = {"UTC", "America/New_York", "America/Los_Angeles", "Europe/London", "Asia/Tokyo"}

    @staticmethod
    def validate_locale(locale: str) -> None:
        """Validate locale.

        Args:
            locale: Locale to validate

        Raises:
            IdentityValidationError: If locale is invalid
        """
        if not locale:
            raise IdentityValidationError("Locale cannot be empty", "locale")

        # Allow any valid locale format (simplified validation)
        if len(locale) < 2 or len(locale) > 10:
            raise IdentityValidationError("Locale must be 2-10 characters", "locale")

    @staticmethod
    def validate_timezone(timezone: str) -> None:
        """Validate timezone.

        Args:
            timezone: Timezone to validate

        Raises:
            IdentityValidationError: If timezone is invalid
        """
        if not timezone:
            raise IdentityValidationError("Timezone cannot be empty", "timezone")

        # Allow any valid timezone format (simplified validation)
        if len(timezone) < 3 or len(timezone) > 50:
            raise IdentityValidationError("Timezone must be 3-50 characters", "timezone")

    @staticmethod
    def validate_provider_uniqueness(provider: Optional[str], provider_subject: Optional[str]) -> None:
        """Validate provider uniqueness rule.

        Args:
            provider: Provider name
            provider_subject: Provider subject

        Raises:
            IdentityValidationError: If provider uniqueness rule is violated
        """
        # If both provider and provider_subject are provided, they must both be valid
        if provider and not provider_subject:
            raise IdentityValidationError("Provider subject required when provider is provided", "provider_subject")

        if provider_subject and not provider:
            raise IdentityValidationError("Provider required when provider subject is provided", "provider")

    @staticmethod
    def identity_model_to_domain(identity_model: IdentityModel) -> Identity:
        """Convert database model to domain entity.

        Args:
            identity_model: Database identity model

        Returns:
            Domain identity entity
        """
        return Identity(
            identity_id=identity_model.id,
            user_id=identity_model.user_id,
            provider=identity_model.provider,
            provider_subject=identity_model.provider_subject,
            display_name=identity_model.display_name,
            first_name=identity_model.first_name,
            last_name=identity_model.last_name,
            locale=identity_model.locale,
            timezone=identity_model.timezone,
            created_at=identity_model.created_at,
            updated_at=identity_model.updated_at
        )

    @staticmethod
    def identity_model_to_dto(identity_model: IdentityModel) -> IdentityDTO:
        """Convert database model to DTO.

        Args:
            identity_model: Database identity model

        Returns:
            Identity DTO
        """
        return IdentityDTO(
            identity_id=identity_model.id,
            user_id=identity_model.user_id,
            provider=identity_model.provider,
            provider_subject=identity_model.provider_subject,
            display_name=identity_model.display_name,
            first_name=identity_model.first_name,
            last_name=identity_model.last_name,
            locale=identity_model.locale,
            timezone=identity_model.timezone,
            created_at=identity_model.created_at,
            updated_at=identity_model.updated_at
        )

    @staticmethod
    def create_identity(session: Session, request: CreateIdentityRequest) -> Identity:
        """Create a new identity.

        Args:
            session: Database session
            request: Identity creation request

        Returns:
            Created identity domain entity

        Raises:
            IdentityValidationError: If validation fails
            IdentityDuplicateError: If identity already exists
            IdentityPersistenceError: If database operation fails
        """
        # Validate user_id
        if not request.user_id or not isinstance(request.user_id, str):
            raise IdentityValidationError("User ID cannot be empty", "user_id")

        # Validate locale
        IdentityService.validate_locale(request.locale)

        # Validate timezone
        IdentityService.validate_timezone(request.timezone)

        # Validate provider uniqueness
        IdentityService.validate_provider_uniqueness(request.provider, request.provider_subject)

        # Create identity model
        identity_model = IdentityModel(
            id=str(uuid4()),  # Server-generated UUID
            user_id=request.user_id,
            provider=request.provider,
            provider_subject=request.provider_subject,
            display_name=request.display_name,
            first_name=request.first_name,
            last_name=request.last_name,
            locale=request.locale,
            timezone=request.timezone
        )

        try:
            session.add(identity_model)
            session.flush()  # Flush to trigger database constraints
            session.commit()
        except IntegrityError as e:
            session.rollback()

            # Parse integrity error to determine field
            error_str = str(e).lower()
            # Check for provider/subject uniqueness constraint first
            if "provider" in error_str and "provider_subject" in error_str:
                raise IdentityDuplicateError(
                    f"Identity with provider '{request.provider}' and subject '{request.provider_subject}' already exists",
                    request.provider,
                    request.provider_subject
                )
            elif "user_id" in error_str or "users" in error_str:
                raise IdentityPersistenceError(
                    f"User with ID '{request.user_id}' does not exist"
                )
            else:
                raise IdentityPersistenceError("Failed to create identity due to database constraint")
        except Exception as e:
            session.rollback()
            raise IdentityPersistenceError(f"Failed to create identity: {str(e)}")

        # Convert to domain entity
        return IdentityService.identity_model_to_domain(identity_model)

    @staticmethod
    def get_identity_by_id(session: Session, identity_id: str) -> Identity:
        """Get identity by ID.

        Args:
            session: Database session
            identity_id: Identity ID

        Returns:
            Identity domain entity

        Raises:
            IdentityNotFoundError: If identity not found
            IdentityPersistenceError: If database operation fails
        """
        try:
            identity_model = session.query(IdentityModel).filter(
                IdentityModel.id == identity_id
            ).first()

            if not identity_model:
                raise IdentityNotFoundError(f"Identity with ID '{identity_id}' not found", identity_id)

            return IdentityService.identity_model_to_domain(identity_model)
        except IdentityNotFoundError:
            raise
        except Exception as e:
            raise IdentityPersistenceError(f"Failed to get identity by ID: {str(e)}")

    @staticmethod
    def get_identity_by_provider_subject(session: Session, provider: str, provider_subject: str) -> Identity:
        """Get identity by provider and subject.

        Args:
            session: Database session
            provider: Provider name
            provider_subject: Provider subject

        Returns:
            Identity domain entity

        Raises:
            IdentityNotFoundError: If identity not found
            IdentityPersistenceError: If database operation fails
        """
        try:
            identity_model = session.query(IdentityModel).filter(
                IdentityModel.provider == provider,
                IdentityModel.provider_subject == provider_subject
            ).first()

            if not identity_model:
                raise IdentityNotFoundError(
                    f"Identity with provider '{provider}' and subject '{provider_subject}' not found"
                )

            return IdentityService.identity_model_to_domain(identity_model)
        except IdentityNotFoundError:
            raise
        except Exception as e:
            raise IdentityPersistenceError(f"Failed to get identity by provider/subject: {str(e)}")

    @staticmethod
    def get_identities_by_user_id(session: Session, user_id: str) -> List[Identity]:
        """Get identities by user ID.

        Args:
            session: Database session
            user_id: User ID

        Returns:
            List of identity domain entities

        Raises:
            IdentityPersistenceError: If database operation fails
        """
        try:
            identity_models = session.query(IdentityModel).filter(
                IdentityModel.user_id == user_id
            ).all()

            return [IdentityService.identity_model_to_domain(model) for model in identity_models]
        except Exception as e:
            raise IdentityPersistenceError(f"Failed to get identities by user ID: {str(e)}")

    @staticmethod
    def identity_exists(session: Session, identity_id: str) -> bool:
        """Check if identity exists.

        Args:
            session: Database session
            identity_id: Identity ID

        Returns:
            True if identity exists, False otherwise

        Raises:
            IdentityPersistenceError: If database operation fails
        """
        try:
            count = session.query(IdentityModel).filter(
                IdentityModel.id == identity_id
            ).count()
            return count > 0
        except Exception as e:
            raise IdentityPersistenceError(f"Failed to check identity existence: {str(e)}")

    @staticmethod
    def identity_exists_by_provider_subject(session: Session, provider: str, provider_subject: str) -> bool:
        """Check if identity exists by provider and subject.

        Args:
            session: Database session
            provider: Provider name
            provider_subject: Provider subject

        Returns:
            True if identity exists, False otherwise

        Raises:
            IdentityPersistenceError: If database operation fails
        """
        try:
            count = session.query(IdentityModel).filter(
                IdentityModel.provider == provider,
                IdentityModel.provider_subject == provider_subject
            ).count()
            return count > 0
        except Exception as e:
            raise IdentityPersistenceError(f"Failed to check identity existence by provider/subject: {str(e)}")
