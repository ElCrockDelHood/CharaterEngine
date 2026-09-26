# C3 - USER - REPOSITORY AUDIT

**Date**: 2026-09-07  
**Phase**: C3 - USER  
**Audit Purpose**: Repository inspection before user implementation

---

## C3.1 REPOSITORY AUDIT FINDINGS

### Existing User Implementations

**Backend Database Models** (C2 - JUST IMPLEMENTED):
- Location: `backend/database/models.py`
- Status: EXISTS_AND_IMPLEMENTED
- Components:
  - `User` class (lines 55-90)
  - `UserStatus` enum (lines 24-28): ACTIVE, INACTIVE, SUSPENDED, DELETED
  - `Account` class (lines 93-135)
  - `AccountStatus` enum (lines 31-36): ACTIVE, INACTIVE, SUSPENDED, CLOSED
  - `Identity` class (lines 138-180)
  - `Session` class (lines 183-220)

**Legacy/Character Engine Source**:
- Location: `src/character_engine/`
- Status: NO USER IMPLEMENTATIONS FOUND
- Result: No existing user/account/identity classes in character_engine source

**Old Anatomy Directory**:
- Location: `src/character_engine/anatomy/`
- Status: DEPRECATED (marked in reorientation audit)
- Contains: Old anatomical models (human.py, male.py, female.py)
- Relevance: NONE for user identity system

---

## C3.2 CLASSIFICATION DECISIONS

### Database Models (backend/database/models.py)
**Decision**: KEEP
**Reason**: These are the canonical database models implemented in C2
**Status**: PRODUCTION-READY FOUNDATION
**Action**: Use as persistence layer for C3 domain logic

### Character Engine Source (src/character_engine/)
**Decision**: N/A
**Reason**: No user/account/identity implementations exist
**Status**: NOT APPLICABLE
**Action**: No action required

### Old Anatomy Directory (src/character_engine/anatomy/)
**Decision**: DEPRECATED
**Reason**: Pre-domain architecture, anatomical models only
**Status**: MARKED FOR DEPRECATION
**Action**: Do not use for user identity system

---

## C3.3 EXISTING USER MODEL ANALYSIS

### User Model Structure
```python
class User(Base):
    __tablename__ = "users"
    
    id: Mapped[str]  # UUID string, primary key
    email: Mapped[str]  # String(255), unique, indexed
    username: Mapped[Optional[str]]  # String(100), unique, indexed
    status: Mapped[UserStatus]  # ACTIVE, INACTIVE, SUSPENDED, DELETED
    created_at: Mapped[datetime]  # server_default=func.now()
    updated_at: Mapped[datetime]  # server_default=func.now(), onupdate=func.now()
    
    # Relationships
    accounts: Mapped[list["Account"]]
    identities: Mapped[list["Identity"]]
    sessions: Mapped[list["Session"]]
    events: Mapped[list["Event"]]
    reward_grants: Mapped[list["RewardGrant"]]
    audit_entries: Mapped[list["AuditEntry"]]
```

### Analysis
**Strengths**:
- ✅ User ID is stable UUID (server-generated)
- ✅ Email is unique and indexed
- ✅ Username is unique and indexed (optional)
- ✅ Status enum exists with 4 states
- ✅ Timestamps use server defaults
- ✅ Clear separation from Account, Identity, Session
- ✅ No password field (appropriate for C3)
- ✅ No privilege/role fields (appropriate for C3)

**Gaps for C3**:
- ❌ No domain/application layer (only persistence layer)
- ❌ No validation logic
- ❌ No normalization logic
- ❌ No duplicate handling logic
- ❌ No business logic for user creation
- ❌ No query functions (get_by_id, get_by_email, etc.)
- ❌ No transaction management
- ❌ No error handling/sanitization

### UserStatus Semantics
**Existing States**:
- ACTIVE: User is active and can use the system
- INACTIVE: User exists but cannot use the system
- SUSPENDED: User is temporarily suspended
- DELETED: User is deleted (soft delete implied)

**C3 Decision**: PRESERVE all 4 states
**Reason**: The existing enum provides a complete lifecycle without gaps
**Deletion Policy**: Based on DELETED state, soft deletion is implied

---

## C3.4 ACCOUNT/IDENTITY/SESSION SEPARATION

### Account Model
**Purpose**: Represents an account in the system
**Relationship**: One user can have multiple accounts
**Status**: SEPARATE CONCEPT
**C3 Decision**: DO NOT implement account logic in C3

### Identity Model
**Purpose**: Represents identity information (display name, first name, last name, locale, timezone)
**Relationship**: One user can have multiple identities
**Status**: SEPARATE CONCEPT
**C3 Decision**: DO NOT implement identity logic in C3

### Session Model
**Purpose**: Represents authentication session
**Relationship**: One user can have multiple sessions
**Status**: SEPARATE CONCEPT
**C3 Decision**: DO NOT implement session logic in C3

---

## C3.5 OPEN DECISIONS

### D3.1 - Deletion Policy
**Current State**: UserStatus.DELETED exists in enum
**Question**: Is this soft deletion or hard deletion?
**Decision**: OPEN
**C3 Approach**: Preserve existing DELETED state, document as soft deletion
**Implementation**: C3 will not implement deletion logic (deferred to C4+)

### D3.2 - Username Required
**Current State**: username is Optional[str] in model
**Question**: Is username required for user creation?
**Decision**: OPEN
**C3 Approach**: Treat username as optional during C3, require only email
**Implementation**: C3 will allow creation with email only, username can be added later

### D3.3 - Email Normalization
**Current State**: No normalization policy exists
**Question**: What is the email normalization policy?
**Decision**: OPEN
**C3 Approach**: Implement lowercase normalization, document as C3 policy
**Implementation**: Convert email to lowercase before storage

### D3.4 - Username Normalization
**Current State**: No normalization policy exists
**Question**: What is the username normalization policy?
**Decision**: OPEN
**C3 Approach**: Implement lowercase + trim whitespace, document as C3 policy
**Implementation**: Convert username to lowercase and trim before storage

---

## C3.6 SUMMARY

### Existing Code to REUSE
- `backend/database/models.py` (User model, UserStatus enum)
- `backend/database/connection.py` (DatabaseManager, session management)
- `backend/config/config.py` (Configuration)

### New Code Required
- User domain/application layer
- User service class
- User validation logic
- User normalization logic
- User creation logic
- User query functions
- User error handling
- User exception classes

### No Code to DEPRECATE
- No existing user implementations to deprecate

### No Code to MOVE/MERGE
- Clear separation exists in database models

### Repository Audit Conclusion
**Status**: CLEAN - No conflicts with existing code
**Approach**: Build domain/application layer on top of existing database models
**Complexity**: LOW - Foundation is solid, only need business logic layer