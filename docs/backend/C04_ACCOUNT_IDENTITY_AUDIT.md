# C4 - ACCOUNT / IDENTITY - REPOSITORY AUDIT

**Date**: 2026-09-09  
**Phase**: C4 - ACCOUNT / IDENTITY  
**Audit Purpose**: Repository inspection before account/identity implementation

---

## C4.1 REPOSITORY AUDIT FINDINGS

### Existing Database Models (C2 - JUST IMPLEMENTED)

#### Account Model Analysis
**Location**: `backend/database/models.py` (lines 92-131)

**Structure**:
```python
class Account(Base):
    __tablename__ = "accounts"
    
    id: Mapped[str]  # UUID string, primary key
    user_id: Mapped[str]  # ForeignKey("users.id", ondelete="CASCADE")
    account_type: Mapped[str]  # default="standard", constrained to ('standard', 'premium', 'admin')
    status: Mapped[AccountStatus]  # ACTIVE, INACTIVE, SUSPENDED, CLOSED
    created_at: Mapped[datetime]  # server_default=func.now()
    updated_at: Mapped[datetime]  # server_default=func.now(), onupdate=func.now()
    
    # Relationships
    user: Mapped["User"]  # back_populates="accounts"
```

**Analysis**:
- ✅ Account is linked to User (not Identity)
- ✅ Uses CASCADE DELETE on user deletion
- ✅ Has account_type constraint
- ✅ Status enum exists with 4 states
- ❌ **CRITICAL**: Does not have provider/external identity fields
- ❌ **CRITICAL**: Identity model is separate but lacks provider abstraction

#### Identity Model Analysis
**Location**: `backend/database/models.py` (lines 133-176)

**Structure**:
```python
class Identity(Base):
    __tablename__ = "identities"
    
    id: Mapped[str]  # UUID string, primary key
    user_id: Mapped[str]  # ForeignKey("users.id", ondelete="CASCADE")
    display_name: Mapped[Optional[str]]
    first_name: Mapped[Optional[str]]
    last_name: Mapped[Optional[str]]
    locale: Mapped[str]  # default="en"
    timezone: Mapped[str]  # default="UTC"
    created_at: Mapped[datetime]  # server_default=func.now()
    updated_at: Mapped[datetime]  # server_default=func.now(), onupdate=func.now()
    
    # Relationships
    user: Mapped["User"]  # back_populates="identities"
```

**Analysis**:
- ✅ Identity is linked to User (not Account)
- ✅ Uses CASCADE DELETE on user deletion
- ✅ Has personal information fields (display_name, first_name, last_name)
- ✅ Has localization fields (locale, timezone)
- ❌ **CRITICAL**: No provider field (e.g., "google", "github", "email")
- ❌ **CRITICAL**: No provider_subject field (external identifier)
- ❌ **CRITICAL**: No uniqueness constraint on provider + provider_subject
- ❌ **ARCHITECTURAL ISSUE**: Identity is currently a "profile" model, not an "authentication identity" model

#### Session Model Analysis
**Location**: `backend/database/models.py` (lines 178-220)

**Structure**:
```python
class Session(Base):
    __tablename__ = "sessions"
    
    id: Mapped[str]  # UUID string, primary key
    user_id: Mapped[str]  # ForeignKey("users.id", ondelete="CASCADE")
    token_hash: Mapped[str]
    device_id: Mapped[Optional[str]]
    ip_address: Mapped[Optional[str]]
    user_agent: Mapped[Optional[str]]
    status: Mapped[SessionStatus]  # ACTIVE, EXPIRED, REVOKED
    expires_at: Mapped[datetime]
    created_at: Mapped[datetime]
    
    # Relationships
    user: Mapped["User"]  # back_populates="sessions"
```

**Analysis**:
- ✅ Session is linked to User (not Account or Identity)
- ✅ Uses CASCADE DELETE on user deletion
- ✅ Has authentication fields (token_hash, device_id, ip_address)
- ✅ Has status enum (ACTIVE, EXPIRED, REVOKED)
- ✅ Has expiration handling
- ✅ Correct separation from User/Account/Identity

---

## C4.2 CASCADE DELETE ANALYSIS

### Foreign Key Relationships with CASCADE DELETE

**Accounts**:
- `user_id` → `users.id` (CASCADE DELETE)
- **Consequence**: Deleting a User deletes all associated Accounts

**Identities**:
- `user_id` → `users.id` (CASCADE DELETE)
- **Consequence**: Deleting a User deletes all associated Identities

**Sessions**:
- `user_id` → `users.id` (CASCADE DELETE)
- **Consequence**: Deleting a User deletes all associated Sessions

**RewardGrants**:
- `user_id` → `users.id` (CASCADE DELETE)
- **Consequence**: Deleting a User deletes all associated RewardGrants

**RewardGrants**:
- `reward_definition_id` → `reward_definitions.id` (CASCADE DELETE)
- **Consequence**: Deleting a RewardDefinition deletes all associated RewardGrants

### Foreign Key Relationships with SET NULL

**Events**:
- `actor_id` → `users.id` (SET NULL)
- **Consequence**: Deleting a User sets actor_id to NULL in Events
- **Implication**: Audit trail preserved, but actor reference lost

**RewardGrants**:
- `qualification_event_id` → `events.id` (SET NULL)
- **Consequence**: Deleting an Event sets qualification_event_id to NULL
- **Implication**: Reward grant loses qualification reference

**AuditEntries**:
- `actor_id` → `users.id` (SET NULL)
- **Consequence**: Deleting a User sets actor_id to NULL in AuditEntries
- **Implication**: Audit trail preserved, but actor reference lost

---

## C4.3 C4.6 C4.7 ARCHITECTURAL GAPS

### C4.6 - Identity Uniqueness Gap
**Current State**: Identity model has no provider or provider_subject fields
**Missing**: No uniqueness constraint on provider + provider_subject
**Consequence**: Cannot enforce unique external identity mapping
**Decision**: REQUIRED - Need to add provider/subject fields to support external authentication

### C4.7 - Identity Model Gap
**Current State**: Identity model is a "profile" model, not an "authentication identity" model
**Missing**: No provider abstraction for OAuth/OIDC/social login
**Consequence**: Cannot support external authentication providers
**Decision**: REQUIRED - Need to restructure Identity model or create separate ExternalIdentity model

---

## C4.4 CLASSIFICATION DECISIONS

### Database Models (backend/database/models.py)
**Decision**: KEEP BUT MODIFY
**Reason**: Account and Identity models exist but lack provider abstraction
**Status**: NEEDS MODIFICATION
**Action**: Add provider/subject fields to Identity model for C4 scope

### Account Model
**Decision**: KEEP
**Reason**: Correct structure, proper User relationship
**Status**: PRODUCTION-READY FOUNDATION
**Action**: Add domain layer only

### Identity Model
**Decision**: MODIFY
**Reason**: Lacks provider/subject fields for external authentication
**Status**: NEEDS MODIFICATION
**Action**: Add provider and provider_subject fields

### Session Model
**Decision**: KEEP
**Reason**: Correct structure, proper User relationship
**Status**: PRODUCTION-READY FOUNDATION
**Action**: No changes in C4 (deferred to C5 authentication)

---

## C4.5 EXISTING CODE AUDIT

### Legacy/Character Engine Source
**Location**: `src/character_engine/`
**Status**: NO ACCOUNT/IDENTITY IMPLEMENTATIONS FOUND
**Result**: No existing account/identity implementations in character_engine source

### C3 User Implementation
**Location**: `backend/identity/user_domain.py`, `backend/identity/user_service.py`
**Status**: COMPLETE
**Result**: User domain layer is solid and ready for Account/Identity layer

---

## C4.6 CANONICAL CONCEPTS ANALYSIS

### USER (C3 - COMPLETE)
**Definition**: Canonical user entity established by C3
**Relationships**: Has many Accounts, Identities, Sessions
**Scope**: User identity and authentication base

### ACCOUNT (C4 - PARTIAL)
**Definition**: Product/application-level container associated with a User
**Current Structure**: Linked to User, has account_type and status
**Gap**: Missing domain layer and business logic
**Decision**: IMPLEMENT in C4

### IDENTITY (C4 - NEEDS MODIFICATION)
**Definition**: Representation of an authentication identity/provider relationship
**Current Structure**: Profile model (display_name, first_name, last_name, locale, timezone)
**Gap**: Missing provider/subject fields for external authentication
**Decision**: MODIFY model + IMPLEMENT domain layer in C4

### SESSION (C2 - COMPLETE, C5 - FUTURE)
**Definition**: Temporal authenticated-access state
**Current Structure**: Linked to User, has token_hash, device_id, ip_address
**Status**: Database model complete, deferred to C5 for authentication logic
**Decision**: DEFER to C5

---

## C4.7 OPEN DECISIONS

### D4.1 - Identity Model Structure
**Current State**: Identity model is a "profile" model, not an "authentication identity" model
**Question**: Should we modify existing Identity model or create separate ExternalIdentity model?
**Decision**: MODIFY existing Identity model
**Rationale**: Preserve existing profile fields while adding provider/subject fields

### D4.2 - Identity Ownership
**Current State**: Identity is linked to User (not Account)
**Question**: Should Identity be linked to User or Account?
**Decision**: User
**Rationale**: Existing model uses User, and Identity is more fundamental than Account

### D4.3 - Identity Uniqueness
**Current State**: No uniqueness constraint on provider + provider_subject
**Question**: What is the uniqueness rule for external identities?
**Decision**: UNIQUE constraint on (provider, provider_subject)
**Rationale**: Same external identity should not map to multiple users

### D4.4 - Account Ownership
**Current State**: Account is linked to User (not Identity)
**Question**: Should Account be linked to User or Identity?
**Decision**: User
**Rationale**: Existing model uses User, and Account is a product-level container

### D4.5 - Deletion Policy
**Current State**: CASCADE DELETE is used throughout
**Question**: Is CASCADE DELETE correct for production?
**Decision**: OPEN - Documented but not resolved
**Rationale**: Audit trail preservation concerns (SET NULL used in Events/AuditEntries)

---

## C4.8 CASCADE DELETE IMPLICATIONS

### High Risk (Historical Data Loss)
**CASCADE DELETE on User**:
- Deletes Accounts (acceptable)
- Deletes Identities (acceptable)
- Deletes Sessions (acceptable)
- Deletes RewardGrants (UNACCEPTABLE - rewards history lost)
- Preserves Events (SET NULL - actor reference lost)
- Preserves AuditEntries (SET NULL - actor reference lost)

### Recommendation
**Audit Trail**: Events and AuditEntries use SET NULL (preserves records, loses actor reference)
**Rewards**: RewardGrants use CASCADE DELETE (loses reward history)
**Decision**: Document as OPEN, defer deletion policy to production review

---

## C4.9 SUMMARY

### Existing Code to REUSE
- `backend/database/models.py` (Account model, Identity model needs modification)
- `backend/database/connection.py` (DatabaseManager, session management)
- `backend/config/config.py` (Configuration)
- `backend/identity/user_domain.py` (User domain layer)
- `backend/identity/user_service.py` (User service layer)

### New Code Required
- Modify Identity model (add provider, provider_subject fields)
- Account domain/application layer
- Identity domain/application layer
- Account service class
- Identity service class
- Account/Identity validation logic
- Account/Identity exception classes

### Code to MODIFY
- `backend/database/models.py` (Identity model - add provider/subject fields)

### No Code to DEPRECATE
- No existing account/identity implementations to deprecate

### Repository Audit Conclusion
**Status**: REQUIRES MODIFICATION
**Approach**: Modify Identity model to add provider/subject fields, then build domain/application layer
**Complexity**: MEDIUM - Model modification required, but foundation is solid
**Risk**: LOW - Model modification is additive, not breaking