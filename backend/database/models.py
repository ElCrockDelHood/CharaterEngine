"""Database models for CHARACTER ENGINE backend.

This module defines all database models using SQLAlchemy ORM.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class UserStatus(str, Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class AccountStatus(str, Enum):
    """Account status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class SessionStatus(str, Enum):
    """Session status enumeration."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class RewardGrantStatus(str, Enum):
    """Reward grant status enumeration."""
    PENDING = "pending"
    GRANTED = "granted"
    REVOKED = "revoked"
    EXPIRED = "expired"
    REJECTED = "rejected"


class User(Base):
    """User model.

    Represents a user in the system. User ID is stable and independent
    of mutable data like email.
    """
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, index=True)
    status: Mapped[UserStatus] = mapped_column(String(20), default=UserStatus.ACTIVE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    accounts: Mapped[list["Account"]] = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    identities: Mapped[list["Identity"]] = relationship("Identity", back_populates="user", cascade="all, delete-orphan")
    events: Mapped[list["Event"]] = relationship("Event", back_populates="actor", cascade="all, delete-orphan")
    reward_grants: Mapped[list["RewardGrant"]] = relationship("RewardGrant", back_populates="user", cascade="all, delete-orphan")
    audit_entries: Mapped[list["AuditEntry"]] = relationship("AuditEntry", back_populates="actor", cascade="all, delete-orphan")
    user_roles: Mapped[list["UserRole"]] = relationship("UserRole", foreign_keys="UserRole.user_id", back_populates="user", cascade="all, delete-orphan")

    @property
    def uuid(self) -> str:
        """Get UUID as string."""
        return self.id

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, status={self.status})>"


class Account(Base):
    """Account model.

    Represents an account in the system. One identity can have multiple accounts.
    """
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    account_type: Mapped[str] = mapped_column(String(50), default="standard", nullable=False)
    status: Mapped[AccountStatus] = mapped_column(String(20), default=AccountStatus.ACTIVE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="accounts")
    credentials: Mapped[list["Credential"]] = relationship("Credential", back_populates="account", cascade="all, delete-orphan")
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="account", cascade="all, delete-orphan")

    @property
    def uuid(self) -> str:
        """Get UUID as string."""
        return self.id

    # Constraints
    __table_args__ = (
        CheckConstraint("account_type IN ('standard', 'premium', 'admin')", name="check_account_type"),
    )

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, user_id={self.user_id}, type={self.account_type}, status={self.status})>"


class Identity(Base):
    """Identity model.

    Represents identity information for a user. Separate from user for
    flexibility and to avoid mixing concepts. Includes provider abstraction
    for external authentication providers.
    """
    __tablename__ = "identities"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    provider_subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    locale: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="identities")

    @property
    def uuid(self) -> str:
        """Get UUID as string."""
        return self.id

    # Constraints
    __table_args__ = (
        UniqueConstraint("provider", "provider_subject", name="uq_identity_provider_subject"),
    )

    def __repr__(self) -> str:
        return f"<Identity(id={self.id}, user_id={self.user_id}, provider={self.provider}, display_name={self.display_name})>"


class Session(Base):
    """Session model.

    Represents an account session for authentication.
    Linked to Account, not User, as per C5 architectural decision.
    """
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True
    )
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    device_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[SessionStatus] = mapped_column(String(20), default=SessionStatus.ACTIVE, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="sessions")

    @property
    def uuid(self) -> str:
        """Get UUID as string."""
        return self.id

    # Constraints
    __table_args__ = (
        Index("idx_session_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, account_id={self.account_id}, status={self.status}, expires_at={self.expires_at})>"


class Credential(Base):
    """Credential model.

    Represents authentication credentials for an account.
    Supports multiple credential types (password, OAuth tokens, etc.).
    """
    __tablename__ = "credentials"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True
    )
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    credential_type: Mapped[str] = mapped_column(String(50), default="password", nullable=False, index=True)
    credential_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    invalidated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="credentials")

    @property
    def uuid(self) -> str:
        """Get UUID as string."""
        return self.id

    # Constraints
    __table_args__ = (
        CheckConstraint("credential_type IN ('password', 'oauth', 'api_key')", name="check_credential_type"),
        UniqueConstraint("account_id", "credential_type", "is_active", name="uq_credential_account_type_active"),
    )

    def __repr__(self) -> str:
        return f"<Credential(id={self.id}, account_id={self.account_id}, type={self.credential_type}, active={self.is_active})>"


class Event(Base):
    """Event model.

    Represents domain events in the system with server-generated sequence
    and integrity verification.
    """
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    server_sequence: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    source: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    schema_version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)
    integrity_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    previous_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)

    # Relationships
    actor: Mapped[Optional["User"]] = relationship("User", back_populates="events")

    @property
    def uuid(self) -> str:
        """Get UUID as string."""
        return self.id

    # Constraints
    __table_args__ = (
        Index("idx_event_server_sequence", "server_sequence"),
        Index("idx_event_timestamp", "timestamp"),
        Index("idx_event_integrity_hash", "integrity_hash"),
    )

    def __repr__(self) -> str:
        return f"<Event(id={self.id}, type={self.event_type}, sequence={self.server_sequence})>"


class RewardDefinition(Base):
    """Reward definition model.

    Defines available rewards with eligibility rules. Configurable,
    not hardcoded.
    """
    __tablename__ = "reward_definitions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True
    )
    reward_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    eligibility_rule: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    valid_from: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    meta_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    grants: Mapped[list["RewardGrant"]] = relationship("RewardGrant", back_populates="reward_definition", cascade="all, delete-orphan")

    @property
    def uuid(self) -> str:
        """Get UUID as string."""
        return self.id

    # Constraints
    __table_args__ = (
        CheckConstraint("priority >= 0", name="check_reward_priority"),
        Index("idx_reward_active", "active"),
    )

    def __repr__(self) -> str:
        return f"<RewardDefinition(id={self.id}, reward_id={self.reward_id}, name={self.name}, active={self.active})>"


class RewardGrant(Base):
    """Reward grant model.

    Represents granted rewards to users with audit trail.
    """
    __tablename__ = "reward_grants"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    reward_definition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("reward_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    qualification_event_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    status: Mapped[RewardGrantStatus] = mapped_column(String(20), default=RewardGrantStatus.PENDING, nullable=False)
    meta_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    granted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="reward_grants")
    reward_definition: Mapped["RewardDefinition"] = relationship("RewardDefinition", back_populates="grants")
    qualification_event: Mapped["Event"] = relationship("Event")

    @property
    def uuid(self) -> str:
        """Get UUID as string."""
        return self.id

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "reward_definition_id", name="uq_user_reward"),
        Index("idx_reward_grant_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<RewardGrant(id={self.id}, user_id={self.user_id}, reward_id={self.reward_definition_id}, status={self.status})>"


class AuditEntry(Base):
    """Audit entry model.

    Records important operations for audit trail. Does not store secrets.
    """
    __tablename__ = "audit_entries"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    result: Mapped[str] = mapped_column(String(20), nullable=False)  # SUCCESS, FAILURE, ERROR
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)

    # Relationships
    actor: Mapped[Optional["User"]] = relationship("User", back_populates="audit_entries")

    @property
    def uuid(self) -> str:
        """Get UUID as string."""
        return self.id

    # Constraints
    __table_args__ = (
        Index("idx_audit_event_type", "event_type"),
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_actor", "actor_id"),
    )

    def __repr__(self) -> str:
        return f"<AuditEntry(id={self.id}, event_type={self.event_type}, action={self.action}, result={self.result})>"


class IdempotencyRecord(Base):
    """Idempotency record model.

    Ensures idempotency by tracking processed requests.
    """
    __tablename__ = "idempotency_records"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    processed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    @property
    def uuid(self) -> str:
        """Get UUID as string."""
        return self.id

    # Constraints
    __table_args__ = (
        Index("idx_idempotency_expires", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<IdempotencyRecord(id={self.id}, idempotency_key={self.idempotency_key})>"


class Role(Base):
    """Role model.

    Represents a role in the authorization system.
    """
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True
    )
    role_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    role_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint("role_id IN ('user', 'admin')", name="check_role_id"),
        Index("idx_role_id", "role_id"),
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, role_id={self.role_id}, role_name={self.role_name})>"


class UserRole(Base):
    """UserRole model.

    Represents role assignments to users with append-only history.
    """
    __tablename__ = "user_roles"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    assigned_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="user_roles")
    role: Mapped["Role"] = relationship("Role", foreign_keys=[role_id])

    # Constraints
    # Constraints
    # Partial unique index: only one ACTIVE (revoked_at IS NULL) assignment per (user, role).
    # Revoked rows are kept as append-only history and are excluded from the uniqueness check.
    __table_args__ = (
        Index(
            "uq_user_role_active",
            "user_id",
            "role_id",
            unique=True,
            sqlite_where=text("revoked_at IS NULL"),
            postgresql_where=text("revoked_at IS NULL"),
        ),
        Index("idx_user_role_user", "user_id"),
        Index("idx_user_role_role", "role_id"),
        Index("idx_user_role_assigned_by", "assigned_by"),
        Index("idx_user_role_revoked_at", "revoked_at"),
    )

    def __repr__(self) -> str:
        return f"<UserRole(id={self.id}, user_id={self.user_id}, role_id={self.role_id}, revoked_at={self.revoked_at})>"
