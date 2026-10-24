"""Database models and connection management for CHARACTER ENGINE backend."""

from .connection import DatabaseManager, get_db_manager, get_session
from .models import (
    Account,
    AccountStatus,
    AuditEntry,
    Base,
    Credential,
    Event,
    IdempotencyRecord,
    Identity,
    RewardDefinition,
    RewardGrant,
    RewardGrantStatus,
    Role,
    Session,
    SessionStatus,
    User,
    UserRole,
    UserStatus,
)

__all__ = [
    # Models
    "Base",
    "User",
    "Account",
    "Identity",
    "Session",
    "Event",
    "RewardDefinition",
    "RewardGrant",
    "AuditEntry",
    "IdempotencyRecord",
    "Credential",
    "Role",
    "UserRole",
    # Enums
    "UserStatus",
    "AccountStatus",
    "SessionStatus",
    "RewardGrantStatus",
    # Connection
    "DatabaseManager",
    "get_db_manager",
    "get_session"
]
