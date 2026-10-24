"""Identity module for CHARACTER ENGINE backend.

This module contains user, account, and identity domain logic.
"""

from backend.identity.account_identity_domain import (
    Account,
    AccountDTO,
    AccountError,
    AccountNotFoundError,
    AccountOwnershipError,
    AccountPersistenceError,
    AccountStatus,
    AccountValidationError,
    CreateAccountRequest,
    CreateIdentityRequest,
    Identity,
    IdentityDTO,
    IdentityDuplicateError,
    IdentityError,
    IdentityNotFoundError,
    IdentityPersistenceError,
    IdentityStatus,
    IdentityValidationError,
)
from backend.identity.account_identity_service import AccountService, IdentityService
from backend.identity.user_domain import (
    CreateUserRequest,
    User,
    UserDTO,
    UserDuplicateError,
    UserError,
    UserNotFoundError,
    UserPersistenceError,
    UserStatus,
    UserValidationError,
)
from backend.identity.user_service import UserService

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
