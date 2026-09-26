"""Identity module for CHARACTER ENGINE backend.

This module contains user, account, and identity domain logic.
"""

from backend.identity.user_domain import (
    User,
    CreateUserRequest,
    UserDTO,
    UserStatus,
    UserError,
    UserValidationError,
    UserDuplicateError,
    UserNotFoundError,
    UserPersistenceError
)

from backend.identity.user_service import UserService

from backend.identity.account_identity_domain import (
    Account,
    Identity,
    CreateAccountRequest,
    CreateIdentityRequest,
    AccountDTO,
    IdentityDTO,
    AccountStatus,
    IdentityStatus,
    AccountError,
    AccountValidationError,
    AccountNotFoundError,
    AccountOwnershipError,
    AccountPersistenceError,
    IdentityError,
    IdentityValidationError,
    IdentityNotFoundError,
    IdentityDuplicateError,
    IdentityPersistenceError
)

from backend.identity.account_identity_service import AccountService, IdentityService

__all__ = [
    # User domain models
    "User",
    "CreateUserRequest",
    "UserDTO",
    "UserStatus",
    # User exceptions
    "UserError",
    "UserValidationError",
    "UserDuplicateError",
    "UserNotFoundError",
    "UserPersistenceError",
    # User services
    "UserService",
    # Account/Identity domain models
    "Account",
    "Identity",
    "CreateAccountRequest",
    "CreateIdentityRequest",
    "AccountDTO",
    "IdentityDTO",
    "AccountStatus",
    "IdentityStatus",
    # Account exceptions
    "AccountError",
    "AccountValidationError",
    "AccountNotFoundError",
    "AccountOwnershipError",
    "AccountPersistenceError",
    # Identity exceptions
    "IdentityError",
    "IdentityValidationError",
    "IdentityNotFoundError",
    "IdentityDuplicateError",
    "IdentityPersistenceError",
    # Account/Identity services
    "AccountService",
    "IdentityService"
]