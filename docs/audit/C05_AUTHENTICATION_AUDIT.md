# C5 - AUTHENTICATION FOUNDATION - FORENSIC AUDIT

**Date**: 2026-09-14  
**Phase**: C5 - Authentication Foundation  
**Audit Purpose**: Repository inspection before authentication implementation

---

## C5.1 FORENSIC AUDIT FINDINGS

### Existing Database Models (C2 - ALREADY IMPLEMENTED)

#### Session Model Analysis
**Location**: `backend/database/models.py` (lines 181-222)

**Current Structure**:
```python
class Session(Base):
    __tablename__ = "sessions"
    
    id: Mapped[str]  # UUID string, primary key
    user_id: Mapped[str]  # ForeignKey("users.id", ondelete="CASCADE")
    token_hash: Mapped[str]  # String(255), indexed
    device_id: Mapped[Optional[str]]  # String(100), indexed
    ip_address: Mapped[Optional[str]]  # String(45)
    user_agent: Mapped[Optional[str]]  # String(500)
    status: Mapped[SessionStatus]  # ACTIVE, EXPIRED, REVOKED
    expires_at: Mapped[datetime]
    created_at: Mapped[datetime]  # server_default=func.now()
    
    # Relationships
    user: Mapped["User"]  # back_populates="sessions"
```

**Analysis**:
- ✅ Session is linked to User (not Account or Identity)
- ✅ Has token_hash field (already designed for hashed tokens)
- ✅ Has device_id, ip_address, user_agent for metadata
- ✅ Has status enum (ACTIVE, EXPIRED, REVOKED)
- ✅ Has expiration handling (expires_at)
- ✅ Proper index on expires_at
- ❌ **CRITICAL**: Linked to User, not Account (C5 architectural decision required)
- ❌ **CRITICAL**: No credential relationship
- ❌ **CRITICAL**: No Credential model exists

#### Account Model Analysis
**Location**: `backend/database/models.py` (lines 92-131)

**Analysis**:
- ✅ Account model exists with account_type and status
- ✅ AccountStatus enum: ACTIVE, INACTIVE, SUSPENDED, CLOSED
- ❌ **CRITICAL**: No credential relationship
- ❌ **CRITICAL**: No password/credential fields

#### Credential Model Analysis
**Status**: DOES NOT EXIST
**Gap**: No credential model for password storage
**Requirement**: Must create Credential model for C5

---

### Existing Configuration (C1 - ALREADY IMPLEMENTED)

#### Security Configuration
**Location**: `backend/config/config.py` (lines 32-53)

**Current Structure**:
```python
@dataclass
class SecurityConfig:
    secret_key: str = "dev-secret-key-change-in-production"
    password_min_length: int = 8
    password_max_length: int = 128
    session_timeout_minutes: int = 60
    max_sessions_per_user: int = 5
```

**Analysis**:
- ✅ Security configuration exists
- ✅ Password length limits defined
- ✅ Session timeout defined
- ✅ Max sessions per user defined
- ❌ **CRITICAL**: No password hashing algorithm specified
- ❌ **CRITICAL**: No password complexity requirements

---

### Existing Dependencies

#### Password Handling
**Passlib**: Already installed (from C2 requirements)
- `passlib[bcrypt]>=1.7.4`
- Supports bcrypt, argon2, and other algorithms
- **Gap**: Argon2 may require additional dependency

#### Cryptographic Support
**python-jose**: Already installed (from C2 requirements)
- `python-jose[cryptography]>=3.3.0`
- JWT support (if needed later)
- Cryptographic operations

---

### Existing Authentication Logic
**Status**: NO AUTHENTICATION LOGIC EXISTS
**Gap**: No authentication service, no password hashing, no session management logic
**Requirement**: Must implement complete authentication foundation in C5

---

## C5.2 CLASSIFICATION DECISIONS

### Database Models (backend/database/models.py)
**Decision**: MODIFY
**Reason**: Session model exists but needs Account relationship; Credential model must be created
**Status**: REQUIRES MODIFICATION
**Action**: 
1. Create Credential model
2. Modify Session model to link to Account (architectural decision required)
3. Add missing Session fields if required

### Configuration (backend/config/config.py)
**Decision**: MODIFY
**Reason**: Security configuration exists but lacks password hashing algorithm
**Status**: REQUIRES MODIFICATION
**Action**: Add password hashing algorithm to SecurityConfig

### Dependencies (requirements.txt)
**Decision**: MODIFY
**Reason**: Passlib installed but may need argon2 dependency
**Status**: REQUIRES MODIFICATION
**Action**: Add argon2-cffi dependency if using Argon2id

### No Code to DEPRECATE
- No existing authentication implementations to deprecate

---

## C5.3 ARCHITECTURAL DECISIONS

### D5.1 - Session Ownership
**Current State**: Session linked to User
**Question**: Should Session be linked to User or Account?
**Decision**: ACCOUNT
**Rationale**: 
- C5 architectural boundary requires Account ownership
- Authentication operates on Account level, not User level
- Future external authentication will use Account → Identity → Session
- Consistent with security best practices

**Action Required**: Modify Session model to link to Account instead of User

### D5.2 - Credential Model Structure
**Current State**: No Credential model exists
**Question**: What should the Credential model contain?
**Decision**: Account-level credential model
**Rationale**:
- Credentials belong to Account, not User
- Support multiple credential types (password, future OAuth tokens)
- Enable credential rotation and invalidation

**Proposed Structure**:
```python
class Credential(Base):
    __tablename__ = "credentials"
    
    id: Mapped[str]  # UUID
    account_id: Mapped[str]  # ForeignKey("accounts.id")
    credential_type: Mapped[str]  # "password", "oauth", etc.
    credential_hash: Mapped[str]  # Password hash or token hash
    is_active: Mapped[bool]  # Credential active/inactive
    created_at: Mapped[datetime]
    expires_at: Mapped[Optional[datetime]]  # Credential expiration
    invalidated_at: Mapped[Optional[datetime]]  # Credential invalidation
```

### D5.3 - Password Hashing Algorithm
**Current State**: Passlib installed, no algorithm specified
**Question**: Which password hashing algorithm to use?
**Decision**: Argon2id
**Rationale**:
- Industry best practice
- Memory-hard, resistant to GPU/ASIC attacks
- Salted by default
- Recommended by OWASP

**Action Required**: Add argon2-cffi dependency and implement Argon2id hashing

### D5.4 - Token Strategy
**Current State**: Session model has token_hash field
**Question**: Opaque server-side tokens vs JWT?
**Decision**: Opaque server-side tokens
**Rationale**:
- Revocation support
- Auditability
- Server-side control
- Simpler lifecycle
- Smaller attack surface
- Session model already designed for token_hash

**Implementation**: Cryptographically secure random tokens, hashed before storage

### D5.5 - Account State Behavior
**Current State**: AccountStatus enum has ACTIVE, INACTIVE, SUSPENDED, CLOSED
**Question**: How should authentication handle different account states?
**Decision**: 
- ACTIVE: Allow authentication
- INACTIVE: Fail authentication
- SUSPENDED: Fail authentication
- CLOSED: Fail authentication

**Rationale**: Security best practice - only active accounts can authenticate

---

## C5.4 OPEN DECISIONS (Preserved from C4)

### D4.1 - Deletion Policy
**Status**: OPEN
**Decision**: CASCADE DELETE vs SET NULL for User deletion?
**Impact**: RewardGrants history lost on User deletion
**Future Phase**: Production review

### D4.2 - Account Deletion Logic
**Status**: DEFERRED
**Decision**: How to delete Accounts?
**Future Phase**: C4+ (Account management phase)

### D4.3 - Identity Deletion Logic
**Status**: DEFERRED
**Decision**: How to delete Identities?
**Future Phase**: C4+ (Identity management phase)

### D4.4 - Account Status Transitions
**Status**: DEFERRED
**Decision**: What are valid Account status transitions?
**Future Phase**: C4+ (Account management phase)

### D4.5 - Identity Status
**Status**: DEFERRED
**Decision**: Should Identity have status field?
**Future Phase**: C4+ (Identity management phase)

---

## C5.5 FORENSIC AUDIT CONCLUSION

### Existing Code to REUSE
- `backend/database/models.py` (Session model, Account model - need modification)
- `backend/config/config.py` (SecurityConfig - need modification)
- `backend/database/connection.py` (DatabaseManager, session management)
- `backend/identity/account_identity_domain.py` (Account domain layer)
- `backend/identity/account_identity_service.py` (Account service layer)

### New Code Required
- Credential model (database)
- Credential domain layer
- Credential service layer
- Authentication service layer
- Password hashing service
- Session management service
- Session domain layer (if needed)
- Authentication exceptions

### Code to MODIFY
- `backend/database/models.py` (Session model - change User relationship to Account, add Credential model)
- `backend/config/config.py` (SecurityConfig - add password hashing algorithm)
- `requirements.txt` (add argon2-cffi dependency)

### Repository Audit Conclusion
**Status**: REQUIRES MODIFICATION + NEW IMPLEMENTATION
**Approach**: 
1. Create Credential model
2. Modify Session model to link to Account
3. Implement password hashing with Argon2id
4. Implement authentication service
5. Implement session management
6. Add comprehensive security tests
**Complexity**: MEDIUM - Solid foundation exists, but requires significant new implementation
**Risk**: LOW - Architectural decisions are clear, security best practices are well-established