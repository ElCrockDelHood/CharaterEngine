"""Database models and connection management for CHARACTER ENGINE backend."""

from .models import (
    Base,
    User,
    Account,
    Identity,
    Session,
    Event,
    RewardDefinition,
    RewardGrant,
    AuditEntry,
    IdempotencyRecord,
    UserStatus,
    AccountStatus,
    SessionStatus,
    RewardGrantStatus
)
from .connection import (
    DatabaseManager,
    get_db_manager,
    get_session
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