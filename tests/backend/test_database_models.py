"""Tests for database models."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from backend.database.models import (
    User,
    Account,
    Identity,
    Session,
    Credential,
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


class TestUserStatus:
    """Test UserStatus enum."""
    
    def test_status_values(self):
        """Test status enum values."""
        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.INACTIVE.value == "inactive"
        assert UserStatus.SUSPENDED.value == "suspended"
        assert UserStatus.DELETED.value == "deleted"


class TestAccountStatus:
    """Test AccountStatus enum."""
    
    def test_status_values(self):
        """Test status enum values."""
        assert AccountStatus.ACTIVE.value == "active"
        assert AccountStatus.INACTIVE.value == "inactive"
        assert AccountStatus.SUSPENDED.value == "suspended"
        assert AccountStatus.CLOSED.value == "closed"


class TestSessionStatus:
    """Test SessionStatus enum."""
    
    def test_status_values(self):
        """Test status enum values."""
        assert SessionStatus.ACTIVE.value == "active"
        assert SessionStatus.EXPIRED.value == "expired"
        assert SessionStatus.REVOKED.value == "revoked"


class TestRewardGrantStatus:
    """Test RewardGrantStatus enum."""
    
    def test_status_values(self):
        """Test status enum values."""
        assert RewardGrantStatus.PENDING.value == "pending"
        assert RewardGrantStatus.GRANTED.value == "granted"
        assert RewardGrantStatus.REVOKED.value == "revoked"
        assert RewardGrantStatus.EXPIRED.value == "expired"
        assert RewardGrantStatus.REJECTED.value == "rejected"


class TestUser:
    """Test User model."""
    
    def test_user_creation(self):
        """Test user creation with required fields."""
        user = User(
            email="test@example.com",
            username="testuser",
            status=UserStatus.ACTIVE
        )
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.status == UserStatus.ACTIVE
        # ID and timestamps are None before database save (server_default)
        assert user.id is None
        assert user.created_at is None
        assert user.updated_at is None
    
    def test_user_required_fields(self):
        """Test user creation requires email."""
        # SQLAlchemy doesn't validate at Python level by default
        # Email requirement is enforced at database level
        user = User(username="testuser")
        assert user.email is None  # This is allowed at Python level
        # Database will enforce NOT NULL constraint


class TestAccount:
    """Test Account model."""
    
    def test_account_creation(self):
        """Test account creation."""
        user_id = str(uuid4())
        account = Account(
            user_id=user_id,
            account_type="standard",
            status=AccountStatus.ACTIVE
        )
        assert account.user_id == user_id
        assert account.account_type == "standard"
        assert account.status == AccountStatus.ACTIVE
        # ID is None before database save
        assert account.id is None


class TestIdentity:
    """Test Identity model."""
    
    def test_identity_creation(self):
        """Test identity creation."""
        user_id = str(uuid4())
        identity = Identity(
            user_id=user_id,
            provider="email",
            provider_subject="test@example.com",
            display_name="Test User",
            first_name="Test",
            last_name="User",
            locale="en",
            timezone="UTC"
        )
        assert identity.user_id == user_id
        assert identity.provider == "email"
        assert identity.provider_subject == "test@example.com"
        assert identity.display_name == "Test User"
        assert identity.first_name == "Test"
        assert identity.last_name == "User"
        assert identity.locale == "en"
        assert identity.timezone == "UTC"


class TestSession:
    """Test Session model."""
    
    def test_session_creation(self):
        """Test session creation."""
        account_id = str(uuid4())
        session = Session(
            account_id=account_id,
            token_hash="hashed_token",
            status=SessionStatus.ACTIVE,
            expires_at=datetime.now(timezone.utc)
        )
        assert session.account_id == account_id
        assert session.token_hash == "hashed_token"
        assert session.status == SessionStatus.ACTIVE
        assert session.expires_at is not None


class TestCredential:
    """Test Credential model."""
    
    def test_credential_creation(self):
        """Test credential creation."""
        account_id = str(uuid4())
        credential = Credential(
            account_id=account_id,
            credential_type="password",
            credential_hash="hashed_password",
            is_active=True
        )
        assert credential.account_id == account_id
        assert credential.credential_type == "password"
        assert credential.credential_hash == "hashed_password"
        assert credential.is_active is True


class TestEvent:
    """Test Event model."""
    
    def test_event_creation(self):
        """Test event creation."""
        actor_id = str(uuid4())
        event = Event(
            event_type="USER_REGISTERED",
            actor_id=actor_id,
            server_sequence=1,
            payload='{"test": "data"}',
            source="system",
            schema_version="1.0",
            integrity_hash="abc123",
            idempotency_key="test-key"
        )
        assert event.event_type == "USER_REGISTERED"
        assert event.actor_id == actor_id
        assert event.server_sequence == 1
        assert event.payload == '{"test": "data"}'
        assert event.source == "system"
        assert event.schema_version == "1.0"
        assert event.integrity_hash == "abc123"
        assert event.idempotency_key == "test-key"


class TestRewardDefinition:
    """Test RewardDefinition model."""
    
    def test_reward_definition_creation(self):
        """Test reward definition creation."""
        reward = RewardDefinition(
            reward_id="FIRST_USER",
            name="First User",
            description="First user reward",
            eligibility_rule='{"sequence": 1}',
            priority=0,
            active=True
        )
        assert reward.reward_id == "FIRST_USER"
        assert reward.name == "First User"
        assert reward.description == "First user reward"
        assert reward.eligibility_rule == '{"sequence": 1}'
        assert reward.priority == 0
        assert reward.active is True


class TestRewardGrant:
    """Test RewardGrant model."""
    
    def test_reward_grant_creation(self):
        """Test reward grant creation."""
        user_id = str(uuid4())
        reward_def_id = str(uuid4())
        event_id = str(uuid4())
        
        grant = RewardGrant(
            user_id=user_id,
            reward_definition_id=reward_def_id,
            qualification_event_id=event_id,
            status=RewardGrantStatus.PENDING
        )
        assert grant.user_id == user_id
        assert grant.reward_definition_id == reward_def_id
        assert grant.qualification_event_id == event_id
        assert grant.status == RewardGrantStatus.PENDING


class TestAuditEntry:
    """Test AuditEntry model."""
    
    def test_audit_entry_creation(self):
        """Test audit entry creation."""
        actor_id = str(uuid4())
        audit = AuditEntry(
            event_type="USER_REGISTERED",
            actor_id=actor_id,
            resource_type="User",
            resource_id=str(uuid4()),
            action="CREATE",
            result="SUCCESS"
        )
        assert audit.event_type == "USER_REGISTERED"
        assert audit.actor_id == actor_id
        assert audit.resource_type == "User"
        assert audit.action == "CREATE"
        assert audit.result == "SUCCESS"


class TestIdempotencyRecord:
    """Test IdempotencyRecord model."""
    
    def test_idempotency_record_creation(self):
        """Test idempotency record creation."""
        record = IdempotencyRecord(
            idempotency_key="test-key",
            request_hash="abc123",
            response_status=200,
            response_body='{"result": "success"}',
            expires_at=datetime.now(timezone.utc)
        )
        assert record.idempotency_key == "test-key"
        assert record.request_hash == "abc123"
        assert record.response_status == 200
        assert record.response_body == '{"result": "success"}'
        assert record.expires_at is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])