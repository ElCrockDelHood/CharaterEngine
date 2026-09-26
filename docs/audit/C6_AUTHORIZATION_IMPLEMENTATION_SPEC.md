# C6-03 — AUTHORIZATION IMPLEMENTATION SPECIFICATION

**Date**: 2026-09-21
**Task**: C6 Authorization Implementation Specification
**Reference**: C6_AUTHORIZATION_CONTRACT.md, C6_AUTHORIZATION_CONTRACT_RECONCILIATION.md
**Status**: C6-CONTRACT-LOCKED = YES, C5 ACCEPTED = YES
**Scope**: C6 Authorization Foundation Implementation Specification

---

## 1. CURRENT REPOSITORY MAPPING

### 1.1 Current Domain Entities

**User Domain**:
- **Location**: `backend/identity/user_domain.py`
- **Current Responsibility**: User CRUD operations, validation, normalization
- **Existing Interfaces**: User, CreateUserRequest, UserDTO, UserStatus enum
- **Current State**: IMPLEMENTED, TESTED, VALIDATED

**Account/Identity Domain**:
- **Location**: `backend/identity/account_identity_domain.py`
- **Current Responsibility**: Account/Identity CRUD operations, validation, ownership
- **Existing Interfaces**: Account, Identity, CreateAccountRequest, CreateIdentityRequest, AccountDTO, IdentityDTO, AccountStatus enum
- **Current State**: IMPLEMENTED, TESTED, VALIDATED

**Authentication Domain**:
- **Location**: `backend/authentication/authentication_domain.py`
- **Current Responsibility**: Credential management, session management, authentication flow
- **Existing Interfaces**: Credential, Session, CreateCredentialRequest, AuthenticateRequest, AuthenticationResponse, CredentialDTO, SessionDTO, CredentialType enum, SessionStatus enum, AuthenticationResult enum
- **Current State**: IMPLEMENTED, TESTED, VALIDATED

### 1.2 Current Service Layer

**UserService**:
- **Location**: `backend/identity/user_service.py`
- **Current Responsibility**: User business logic, validation, CRUD operations
- **Dependencies**: database models, user domain

**AccountService**:
- **Location**: `backend/identity/account_identity_service.py`
- **Current Responsibility**: Account/Identity business logic, validation, CRUD operations
- **Dependencies**: database models, account/identity domain

**AuthenticationService**:
- **Location**: `backend/authentication/authentication_service.py`
- **Current Responsibility**: Authentication orchestration, credential verification, session management
- **Dependencies**: database models, authentication domain, password service, account service

**PasswordService**:
- **Location**: `backend/authentication/password_service.py`
- **Current Responsibility**: Argon2id password hashing and verification
- **Dependencies**: argon2-cffi

### 1.3 Current Database Models

**User Model**:
- **Location**: `backend/database/models.py`
- **Current Fields**: id, email, username, status, created_at, updated_at
- **Current Relationships**: accounts, identities, events, reward_grants, audit_entries
- **Current Status**: IMPLEMENTED, TESTED, VALIDATED

**Account Model**:
- **Location**: `backend/database/models.py`
- **Current Fields**: id, user_id, account_type, status, created_at, updated_at
- **Current Relationships**: user, credentials, sessions
- **Current Status**: IMPLEMENTED, TESTED, VALIDATED

**Identity Model**:
- **Location**: `backend/database/models.py`
- **Current Fields**: id, user_id, provider, provider_subject, display_name, first_name, last_name, locale, timezone, created_at, updated_at
- **Current Relationships**: user
- **Current Status**: IMPLEMENTED, TESTED, VALIDATED

**Session Model**:
- **Location**: `backend/database/models.py`
- **Current Fields**: id, account_id, token_hash, device_id, ip_address, user_agent, status, expires_at, created_at
- **Current Relationships**: account
- **Current Status**: IMPLEMENTED, TESTED, VALIDATED

**Credential Model**:
- **Location**: `backend/database/models.py`
- **Current Fields**: id, account_id, credential_type, credential_hash, is_active, created_at, expires_at, invalidated_at
- **Current Relationships**: account
- **Current Status**: IMPLEMENTED, TESTED, VALIDATED

**Event Model**:
- **Location**: `backend/database/models.py`
- **Current Fields**: id, event_type, actor_id, server_sequence, payload, source, schema_version, integrity_hash, previous_hash, idempotency_key, timestamp
- **Current Relationships**: actor (User)
- **Current Status**: IMPLEMENTED, TESTED, VALIDATED

**RewardDefinition Model**:
- **Location**: `backend/database/models.py`
- **Current Fields**: id, reward_id, name, description, eligibility_rule, priority, active, valid_from, valid_until, meta_data, created_at, updated_at
- **Current Relationships**: grants
- **Current Status**: IMPLEMENTED, TESTED, VALIDATED

**RewardGrant Model**:
- **Location**: `backend/database/models.py`
- **Current Fields**: id, user_id, reward_definition_id, qualification_event_id, status, meta_data, granted_at, revoked_at, created_at, updated_at
- **Current Relationships**: user, reward_definition, qualification_event
- **Current Status**: IMPLEMENTED, TESTED, VALIDATED

**AuditEntry Model**:
- **Location**: `backend/database/models.py`
- **Current Fields**: id, event_type, actor_id, resource_type, resource_id, action, result, details, ip_address, timestamp
- **Current Relationships**: actor (User)
- **Current Status**: IMPLEMENTED, TESTED, VALIDATED

**IdempotencyRecord Model**:
- **Location**: `backend/database/models.py`
- **Current Fields**: id, idempotency_key, request_hash, response_status, response_body, processed_at, expires_at
- **Current Relationships**: None
- **Current Status**: IMPLEMENTED, TESTED, VALIDATED

---

## 2. AUTHORIZATION DOMAIN DESIGN

### 2.1 Authorization Domain Entities

**ActorContext**:
- **Purpose**: Encapsulates actor identity and context for authorization decisions
- **Fields**:
  - actor_id: str (user_id from session)
  - account_id: str (account_id from session)
  - session_id: str (session_id from session)
  - actor_type: ActorType (USER, SYSTEM, ANONYMOUS)
  - authenticated: bool
  - authentication_timestamp: datetime
  - ip_address: Optional[str]
  - user_agent: Optional[str]
  - account_status: AccountStatus (from C4 Account model)
  - session_status: SessionStatus (from C5 Session model)
- **Responsibility**: Provides authenticated actor context to authorization layer
- **Source**: Extracted from C5 AuthenticationService (Session) and C4 AccountService (Account)
- **C5 Integration**: actor_id, account_id, session_id from C5 Session; account_status from C4 Account
- **Information Required for Authorization Decision**: actor_id, account_id, actor_type, authenticated, account_status, session_status

**ActorType**:
- **Purpose**: Enumeration of actor types
- **Values**: USER, SYSTEM, ANONYMOUS
- **Responsibility**: Distinguishes between user, system, and anonymous actors
- **Derivation**: USER from authenticated session, SYSTEM from system account, ANONYMOUS from no session

**Role**:
- **Purpose**: Collection of permissions assigned to actors
- **Fields**:
  - role_id: str (e.g., "user", "admin")
  - role_name: str (human-readable)
  - description: str
  - created_at: datetime
- **Responsibility**: Defines role-based permissions
- **Default Roles**: USER (default for all users), ADMIN (system administrator)

**Permission**:
- **Purpose**: Specific action on specific resource type
- **Format**: `{resource}:{action}:{scope}`
- **Fields**:
  - permission_id: str (e.g., "user:read_own")
  - resource: str (e.g., "user")
  - action: str (e.g., "read")
  - scope: str (e.g., "own", "any", "system")
- **Responsibility**: Defines fine-grained permissions
- **Examples**: user:read_own, account:read_own, user:read_any, reward_definition:manage

**Resource**:
- **Purpose**: Entity that can be accessed or manipulated
- **Fields**:
  - resource_type: str (e.g., "user", "account")
  - resource_id: str (UUID)
  - owner_id: Optional[str] (user_id if owned)
  - state: str (e.g., "active", "disabled")
- **Responsibility**: Represents resource for authorization check
- **Derivation**: From database models

**Action**:
- **Purpose**: Operation performed on resource
- **Values**: create, read, update, delete, list, manage, grant, revoke
- **Responsibility**: Defines operation type for permission check

**Scope**:
- **Purpose**: Scope of permission (self vs any vs system)
- **Values**: own, any, system
- **Responsibility**: Distinguishes self-permissions from system-permissions

**Ownership Evaluation**:
- **Purpose**: Determine if actor owns resource
- **Input**: actor.user_id, resource.owner_id
- **Output**: owned, not_owned, unowned
- **Responsibility**: Validate resource ownership

**Resource State Evaluation**:
- **Purpose**: Determine if resource is in accessible state
- **Input**: resource.state
- **Output**: accessible, not_accessible
- **Responsibility**: Validate resource state before authorization

**Authorization Decision**:
- **Purpose**: Allow/deny decision for actor action on resource
- **Input**: ActorContext, Action, Resource, Permissions
- **Output**: ALLOW, DENY
- **Responsibility**: Make authorization decision based on rules

**Denial Reason**:
- **Purpose**: Explanation for authorization denial
- **Values**: NOT_AUTHENTICATED, PERMISSION_DENIED, OWNERSHIP_VIOLATION, RESOURCE_NOT_FOUND, RESOURCE_STATE_INVALID
- **Responsibility**: Provide reason for denial (internal, not exposed to client)

### 2.2 Authorization Domain Location

**New Domain File**: `backend/authorization/authorization_domain.py`

**Package Structure**:
```
backend/authorization/
├── __init__.py
├── authorization_domain.py (new)
├── authorization_service.py (new)
├── role_service.py (new)
├── permission_service.py (new)
└── authorization_middleware.py (new)
```

---

## 3. DATA MODEL IMPACT

### 3.1 New Database Models Required

**Role Model**:
- **Table**: roles
- **Fields**:
  - id: String(36) (primary key, UUID)
  - role_id: String(50) (unique, not null, e.g., "user", "admin")
  - role_name: String(100) (not null, human-readable)
  - description: Text (nullable)
  - created_at: DateTime (server_default=func.now(), not null)
- **Constraints**:
  - UniqueConstraint on role_id
  - CheckConstraint on role_id in ('user', 'admin')
- **Indexes**:
  - Index on role_id
- **Level**: APPLICATION/ORM (database-level enforcement deferred to infrastructure)
- **Audit Requirement**: Role creation must be audited

**UserRole Model**:
- **Table**: user_roles
- **Fields**:
  - id: String(36) (primary key, UUID)
  - user_id: String(36) (ForeignKey to users.id, CASCADE DELETE)
  - role_id: String(36) (ForeignKey to roles.id, CASCADE DELETE)
  - assigned_by: String(36) (ForeignKey to users.id, SET NULL, nullable)
  - assigned_at: DateTime (server_default=func.now(), not null)
  - revoked_at: DateTime (nullable, set to current timestamp on revocation)
- **Constraints**:
  - UniqueConstraint on (user_id, role_id, revoked_at) where revoked_at IS NULL (only one active assignment per user/role)
- **Indexes**:
  - Index on user_id
  - Index on role_id
  - Index on assigned_by
  - Index on revoked_at
- **Level**: APPLICATION/ORM (database-level enforcement deferred to infrastructure)
- **Audit Requirement**: Role assignment/revocation must be audited

### 3.2 Existing Database Models to Modify

**backend/database/models.py**: MODIFY REQUIRED

**Required Changes**:
- Add Role model
- Add UserRole model

**Rationale**: Authorization requires role and role assignment data to be persisted. These are new models added to the existing models.py file, not modifications to existing models.

**Existing Models Unchanged**: All existing models (User, Account, Identity, Session, Credential, Event, RewardDefinition, RewardGrant, AuditEntry, IdempotencyRecord) remain unchanged.

### 3.3 Model Relationships

**Role Model**:
- **Primary Key**: id (String(36), UUID)
- **Stable Identifier**: role_id (String(50), unique, e.g., "user", "admin")
- **Relationships**: None (standalone model)

**UserRole Model**:
- **Primary Key**: id (String(36), UUID)
- **Foreign Keys**:
  - user_id: String(36) → users.id (CASCADE DELETE)
  - role_id: String(36) → roles.id (CASCADE DELETE)
  - assigned_by: String(36) → users.id (SET NULL, nullable)
- **Uniqueness**: UniqueConstraint on (user_id, role_id)
- **Indexes**:
  - Index on user_id
  - Index on role_id
  - Index on assigned_by
- **Nullability**:
  - user_id: NOT NULL
  - role_id: NOT NULL
  - assigned_by: NULLABLE (SET NULL if assigning user deleted)
- **Delete Behavior**:
  - UserRole.user_id: CASCADE DELETE (user deleted → role assignments deleted)
  - UserRole.role_id: CASCADE DELETE (role deleted → role assignments deleted)
  - UserRole.assigned_by: SET NULL (assigning user deleted → assigned_by set to NULL)

### 3.4 Constraint Level Classification

**APPLICATION/ORM REQUIREMENTS**:
- All authorization constraints
- All role assignment constraints
- All permission checks
- All ownership validation
- All state validation

**DATABASE-ENGINE REQUIREMENTS DEFERRED TO INFRASTRUCTURE**:
- Database-level constraint enforcement
- Database-level cascade behavior
- Database-level transaction isolation
- Database-level locking

---

## 4. ROLE MODEL

### 4.1 USER Role

**Role ID**: "user"
**Role Name**: "User"
**Description**: Standard user role with self-permissions
**Assignment**: Automatic on user creation
**Removal**: Cannot be removed from user
**Permissions**:
- user:read_own
- user:update_own
- account:read_own
- credential:manage_own
- session:manage_own
- reward_grant:read_own

**Implementation**:
- Automatically assigned in UserService.create_user()
- No explicit assignment logic needed
- Cannot be removed (no removal logic)

### 4.2 ADMIN Role

**Role ID**: "admin"
**Role Name**: "Administrator"
**Description**: System administrator with system-permissions
**Assignment**: Manual by existing admin
**Removal**: Manual by existing admin (at least one admin must remain)
**Permissions**:
- All USER permissions
- user:read_any
- user:update_any
- account:read_any
- reward_definition:manage

**Assignment Rules**:
- Requires admin permission to assign
- Self-assignment of admin role is PROHIBITED
- Only existing admins can assign admin role to other users
- Assignment must be explicitly audited

**Revocation Rules**:
- Requires admin permission to revoke
- Self-revocation of admin role is PROHIBITED (at least one admin must remain)
- Revocation must be explicitly audited
- Cannot revoke last admin in system

**Bootstrap**:
- Initial admin created during system bootstrap
- Bootstrap requires explicit authorization (console/CLI operation)
- Bootstrap creates first admin user with admin role
- Bootstrap operation is logged and audited
- No automated bootstrap (requires manual authorization)

**Audit Requirements**:
- All admin role assignments must be logged
- All admin role revocations must be logged
- Audit must include: who assigned, to whom, when, why
- Audit must be stored in AuditEntry table
- Audit must be queryable for compliance

### 4.3 SYSTEM Process Authorization

**System Actor**: Identified by special system account
**Authorization**: Still applies (not a global bypass)
**System Permissions**: Explicit system permissions for specific operations
**Trusted Internal Operations**:
- Event generation (server sequence generation)
- Reward eligibility evaluation (read-only)
- Audit entry creation (system events)
- Idempotency record management
- **All other operations require explicit authorization**

**Implementation**:
- System actor identified by special system account
- System actor has explicit system permissions
- System actor is subject to authorization checks
- System actor bypasses ONLY for explicitly defined trusted internal operations

### 4.4 UserRole Revocation Model

**Contract Requirement**: Role assignment/revocation must be supported

**Selected Model**: Append-only assignment history with current state query

**Rationale**:
- Append-only history provides complete audit trail
- Current state can be derived from latest assignment
- Simpler than temporal validity with complex date ranges
- More auditable than simple active/revoked flag

**Implementation**:
- UserRole records are append-only (never deleted, never modified)
- To revoke a role: Create a new UserRole record with revoked_at timestamp
- To check current role: Query UserRole where user_id=X AND role_id=Y AND revoked_at IS NULL
- To check role history: Query all UserRole records for user_id=X AND role_id=Y
- Revocation timestamp: revoked_at (DateTime, nullable, set to current timestamp on revocation)

**Revocation Logic**:
- Active role: UserRole where revoked_at IS NULL
- Revoked role: UserRole where revoked_at IS NOT NULL
- Current roles: All UserRole records where revoked_at IS NULL for user
- Role history: All UserRole records for user (including revoked)

**Query Examples**:
- Get current roles: SELECT * FROM user_roles WHERE user_id = ? AND revoked_at IS NULL
- Revoke role: UPDATE user_roles SET revoked_at = NOW() WHERE user_id = ? AND role_id = ? AND revoked_at IS NULL
- Check if user has role: SELECT * FROM user_roles WHERE user_id = ? AND role_id = ? AND revoked_at IS NULL

**Audit**: Role revocation must be audited (who revoked, from whom, when, why)

---

## 5. PERMISSION MODEL

### 5.1 Permission Registry

**User Permissions**:

| permission_id | resource | action | scope | actor/role | ownership requirement | resource-state requirement | audit requirement |
|---------------|----------|--------|-------|------------|----------------------|--------------------------|------------------|
| user:read_own | user | read | own | USER, ADMIN | owned | ACTIVE | success/failure |
| user:update_own | user | update | own | USER, ADMIN | owned | ACTIVE | success/failure |
| account:read_own | account | read | own | USER, ADMIN | owned | ACTIVE | success/failure |
| credential:manage_own | credential | manage | own | USER, ADMIN | owned | ACTIVE | success/failure |
| session:manage_own | session | manage | own | USER, ADMIN | owned | ACTIVE | success/failure |
| reward_grant:read_own | reward_grant | read | own | USER, ADMIN | owned | ACTIVE | success/failure |

**System Permissions**:

| permission_id | resource | action | scope | actor/role | ownership requirement | resource-state requirement | audit requirement |
|---------------|----------|--------|-------|------------|----------------------|--------------------------|------------------|
| user:read_any | user | read | any | ADMIN | any | ACTIVE | success/failure |
| user:update_any | user | update | any | ADMIN | any | ACTIVE | success/failure |
| account:read_any | account | read | any | ADMIN | any | ACTIVE | success/failure |
| reward_definition:create | reward_definition | create | system | ADMIN | unowned | ACTIVE | success/failure |
| reward_definition:read | reward_definition | read | system | ADMIN, SYSTEM | unowned | ACTIVE | success/failure |
| reward_definition:update | reward_definition | update | system | ADMIN | unowned | ACTIVE | success/failure |
| reward_definition:delete | reward_definition | delete | system | ADMIN | unowned | ACTIVE | success/failure |

**Reward Engine System Permissions**:

| permission_id | resource | action | scope | actor/role | ownership requirement | resource-state requirement | audit requirement |
|---------------|----------|--------|-------|------------|----------------------|--------------------------|------------------|
| reward_grant:grant | reward_grant | grant | system | SYSTEM | unowned | ACTIVE | success/failure |
| reward_grant:revoke | reward_grant | revoke | system | SYSTEM | unowned | ACTIVE | success/failure |
| reward_definition:read | reward_definition | read | system | SYSTEM | unowned | ACTIVE | success/failure |
| user:read_any | user | read | any | SYSTEM | any | ACTIVE | success/failure |

### 5.2 Permission Implementation

**Permission Check**:
- Permission format: `{resource}:{action}:{scope}`
- Check: Does actor have permission for resource:action:scope?
- If scope == "own": Check ownership
- If scope == "any": Bypass ownership check
- If scope == "system": Check system permission

**Permission Assignment**:
- USER role has all self-permissions
- ADMIN role has all self-permissions + system-permissions
- SYSTEM actor has explicit system permissions

---

## 6. AUTHORIZATION DECISION

### 6.1 Decision Flow

```
Authentication (C5)
  ↓
Session validated
  ↓
ActorContext extracted (user_id, account_id, session_id, actor_type)
  ↓
Actor state check (account status, identity status, session status)
  ↓
Resource identified (resource_type, resource_id)
  ↓
Action identified (action_type)
  ↓
Actor roles loaded (from UserRole where revoked_at IS NULL)
  ↓
Actor permissions loaded (from roles)
  ↓
Resource state check (resource.status == ACTIVE)
  ↓
Ownership check (actor.user_id == resource.owner_id OR has any permission)
  ↓
Permission check (actor.permissions includes resource:action:scope)
  ↓
Authorization decision (ALLOW or DENY)
  ↓
Denial reason (if DENY)
  ↓
Audit/security behavior (log decision)
  ↓
Response (200 OK or 401/403/404)
```

### 6.2 Decision Logic

**ALLOW Conditions**:
- actor.authenticated == true
- AND
- actor.state == ACTIVE (account/identity/session state)
- AND
- resource.state == ACTIVE
- AND
- (
  (actor.permissions includes resource:action:own AND ownership == owned)
  OR
  (actor.permissions includes resource:action:any AND ownership == any)
  OR
  (actor.permissions includes resource:action:system AND actor_type == system)
  )

**DENY Conditions**:
- actor.authenticated == false
- OR
- actor.state != ACTIVE (account/identity/session state not ACTIVE)
- OR
- resource.state != ACTIVE
- OR
- (
  actor.permissions does NOT include resource:action:own
  AND actor.permissions does NOT include resource:action:any
  AND actor.permissions does NOT include resource:action:system
  )
- OR
- (ownership == not_owned AND actor.permissions does NOT include resource:action:any)

### 6.3 Decision Priority (Deterministic for All Actor Types)

**Priority Order**:
1. Authentication check (if fails → DENY, 401)
2. Actor state check (if not ACTIVE → DENY, 401)
3. Resource state check (if not ACTIVE → DENY, 404)
4. System permission check (if system actor and has system permission → check)
5. Ownership check (if not owned → DENY unless has any permission, 404)
6. Permission check (if permission missing → DENY, 403)
7. Default deny (if no explicit allow → DENY, 403)

**SYSTEM Actor Does NOT Have Global Bypass**:
- SYSTEM actor is subject to all checks (authentication, state, resource state, ownership, permission)
- SYSTEM actor bypasses ONLY step 4 (system permission check) if it has explicit system permission
- SYSTEM actor cannot bypass step 5 (ownership check) unless it has resource:action:any permission
- SYSTEM actor cannot bypass step 6 (permission check) unless it has explicit permission
- SYSTEM actor cannot bypass step 7 (default deny)

**USER Actor Evaluation**:
- Step 1: Authentication check (must be authenticated)
- Step 2: Actor state check (must be ACTIVE)
- Step 3: Resource state check (must be ACTIVE)
- Step 4: System permission check (USER never has system permissions → skip)
- Step 5: Ownership check (must own resource OR have any permission)
- Step 6: Permission check (must have resource:action:own permission)
- Step 7: Default deny (if no explicit allow)

**ADMIN Actor Evaluation**:
- Step 1: Authentication check (must be authenticated)
- Step 2: Actor state check (must be ACTIVE)
- Step 3: Resource state check (must be ACTIVE)
- Step 4: System permission check (ADMIN has system permissions → check)
- Step 5: Ownership check (bypassed if has any permission)
- Step 6: Permission check (has self-permissions and system-permissions)
- Step 7: Default deny (if no explicit allow)

**SYSTEM Actor Evaluation**:
- Step 1: Authentication check (system actor is authenticated via system account)
- Step 2: Actor state check (system account is ACTIVE)
- Step 3: Resource state check (must be ACTIVE)
- Step 4: System permission check (SYSTEM has system permissions → check)
- Step 5: Ownership check (bypassed if has any permission)
- Step 6: Permission check (has system permissions)
- Step 7: Default deny (if no explicit allow)

---

## 7. OWNERSHIP GRAPH

### 7.1 Ownership Relationships

```
User (self-ownership)
├── Account (owned by User)
│   ├── Credential (owned by Account, indirectly by User)
│   └── Session (owned by Account, indirectly by User)
├── Identity (owned by User)
└── RewardGrant (owned by User)
```

### 7.2 Unowned Resources

**Event**: No owner (actor reference only)
**RewardDefinition**: No owner (system-wide)
**AuditEntry**: No owner (actor reference only)
**IdempotencyRecord**: No owner (system-wide)

### 7.3 Ownership Paths

**User Self-Ownership**:
- Resource: User
- Owner: User itself
- Path: direct (user_id == actor.user_id)

**Account Ownership**:
- Resource: Account
- Owner: User
- Path: Account.user_id == actor.user_id

**Identity Ownership**:
- Resource: Identity
- Owner: User
- Path: Identity.user_id == actor.user_id

**Session Ownership**:
- Resource: Session
- Owner: User (via Account)
- Path: Session.account.user_id == actor.user_id

**Credential Ownership**:
- Resource: Credential
- Owner: User (via Account)
- Path: Credential.account.user_id == actor.user_id

**RewardGrant Ownership**:
- Resource: RewardGrant
- Owner: User
- Path: RewardGrant.user_id == actor.user_id

---

## 8. IDOR PROTECTION

### 8.1 IDOR Protection Mapping

**User Resource**:
- **Actor Identity**: user_id from session
- **Resource Owner**: user_id from User model
- **Comparison Rule**: actor.user_id == resource.user_id
- **Allowed Operation**: User can read/update own user information
- **Denied Operation**: User cannot read/update another user's user information
- **Expected Denial Semantics**: 404 (not 403) to prevent resource existence revelation

**Account Resource**:
- **Actor Identity**: user_id from session
- **Resource Owner**: user_id from Account model
- **Comparison Rule**: actor.user_id == resource.user_id
- **Allowed Operation**: User can read own account information
- **Denied Operation**: User cannot read another user's account information
- **Expected Denial Semantics**: 404 (not 403) to prevent resource existence revelation

**Identity Resource**:
- **Actor Identity**: user_id from session
- **Resource Owner**: user_id from Identity model
- **Comparison Rule**: actor.user_id == resource.user_id
- **Allowed Operation**: User can read/update own identity information
- **Denied Operation**: User cannot read/update another user's identity information
- **Expected Denial Semantics**: 404 (not 403) to prevent resource existence revelation

**Session Resource**:
- **Actor Identity**: user_id from session
- **Resource Owner**: user_id from Session.account model
- **Comparison Rule**: actor.user_id == resource.account.user_id
- **Allowed Operation**: User can manage own sessions
- **Denied Operation**: User cannot manage another user's sessions
- **Expected Denial Semantics**: 404 (not 403) to prevent resource existence revelation

**Credential Resource**:
- **Actor Identity**: user_id from session
- **Resource Owner**: user_id from Credential.account model
- **Comparison Rule**: actor.user_id == resource.account.user_id
- **Allowed Operation**: User can manage own credentials
- **Denied Operation**: User cannot manage another user's credentials
- **Expected Denial Semantics**: 404 (not 403) to prevent resource existence revelation

**RewardGrant Resource**:
- **Actor Identity**: user_id from session
- **Resource Owner**: user_id from RewardGrant model
- **Comparison Rule**: actor.user_id == resource.user_id
- **Allowed Operation**: User can read own reward grants
- **Denied Operation**: User cannot read another user's reward grants
- **Expected Denial Semantics**: 404 (not 403) to prevent resource existence revelation

### 8.2 IDOR Implementation

**Implementation**:
- Extract actor identity from session (not from request)
- Never trust user_id/account_id from request
- Validate ownership against session actor
- Use 404 for ownership violations (not 403)
- Do not reveal resource existence

---

## 9. HTTP/API BOUNDARY

### 9.1 HTTP Status Codes

**HTTP Decision Table**:

| Condition | Actor State | Resource State | Ownership | Permission | Response | Error Message | Anti-Enumeration |
|-----------|-------------|----------------|-----------|------------|----------|---------------|------------------|
| Unauthenticated | N/A | N/A | N/A | N/A | 401 | "Authentication required" | Generic error message |
| Invalid/revoked authentication | Not ACTIVE | N/A | N/A | N/A | 401 | "Authentication required" | Generic error message |
| Resource absent | ACTIVE | N/A | N/A | N/A | 404 | "Resource not found" | Generic error message |
| Resource exists but hidden (ownership violation) | ACTIVE | ACTIVE | not_owned | N/A | 404 | "Resource not found" | Anti-enumeration (do not reveal resource existence) |
| Authenticated but unauthorized (permission violation) | ACTIVE | ACTIVE | owned | missing | 403 | "Access denied" | Generic error message (do not reveal specific permission) |
| Authenticated but unauthorized (state violation) | ACTIVE | not ACTIVE | owned | present | 404 | "Resource not found" | Generic error message (do not reveal state) |

**401 Unauthorized**:
- **When**: Actor not authenticated, session invalid/expired/revoked, account/identity/session state not ACTIVE
- **Response**: "Authentication required"
- **Anti-Enumeration**: Generic error message, no specific state revealed

**403 Forbidden**:
- **When**: Actor authenticated but not authorized, actor lacks permission, actor lacks system-permission
- **Response**: "Access denied"
- **Anti-Enumeration**: Generic error message, no specific permission revealed

**404 Not Found**:
- **When**: Resource does not exist, resource ID invalid, ownership violation, resource state not ACTIVE
- **Response**: "Resource not found"
- **Anti-Enumeration**: Use 404 instead of 403 for ownership violations to prevent resource existence revelation

### 9.2 Future API Endpoints

**Note**: No API endpoints currently exist in the repository. Authorization will apply to future API endpoints.

**Example Endpoints** (future):
- GET /users/{user_id} - Read user
- PUT /users/{user_id} - Update user
- GET /accounts/{account_id} - Read account
- POST /accounts - Create account
- GET /sessions/{session_id} - Read session
- DELETE /sessions/{session_id} - Delete session
- POST /credentials - Create credential
- DELETE /credentials/{credential_id} - Delete credential

**Authorization Applied**:
- All endpoints will require authentication (C5)
- All endpoints will require authorization (C6)
- Ownership validation for resource access
- Permission check for action

---

## 10. REWARD AUTHORIZATION

### 10.1 RewardDefinition Authorization

**RewardDefinition Ownership**: System resource (no owner)

**Actor Permissions**:
- **USER Role**: No permissions (read-only public access if applicable)
- **ADMIN Role**: reward_definition:create, reward_definition:read, reward_definition:update, reward_definition:delete

**Authorization Rules**:
- Admins can create reward definitions
- Admins can read reward definitions
- Admins can update reward definitions
- Admins can delete reward definitions
- Users cannot modify reward definitions
- Reward definitions are system-wide configuration

**Explicit Actions**:
- CREATE: reward_definition:create (ADMIN only)
- READ: reward_definition:read (ADMIN only, or public read-only if applicable)
- UPDATE: reward_definition:update (ADMIN only)
- DELETE: reward_definition:delete (ADMIN only)
- ENABLE/DISABLE: reward_definition:update (ADMIN only, via active field)
- **No "manage" permission**: Replaced with explicit CREATE/READ/UPDATE/DELETE permissions

**Implementation**:
- Check admin permission for reward definition operations
- No ownership check (system resource)
- Audit all reward definition changes

### 10.2 RewardGrant Authorization

**RewardGrant Ownership**: User resource (owned by user)

**USER Role Permissions**:
- reward_grant:read_own (read own reward grants)

**ADMIN Role Permissions**:
- reward_grant:read_any (read any user's reward grants)

**SYSTEM/Reward Engine Permissions**:
- reward_grant:grant (grant rewards to users)
- reward_grant:revoke (revoke rewards from users)
- **Scope**: These permissions are scoped to SYSTEM actor only (not global for all actors)
- **Not Global**: SYSTEM cannot grant arbitrary permissions; SYSTEM has only explicitly defined reward permissions

**Authorization Rules**:
- Users can read own reward grants
- Admins can read any user's reward grants
- SYSTEM actor can grant rewards to users (explicit reward_grant:grant permission)
- SYSTEM actor can revoke rewards from users (explicit reward_grant:revoke permission)
- SYSTEM actor cannot grant arbitrary permissions
- SYSTEM actor has no other reward permissions beyond grant/revoke

**Explicit Actions**:
- READ (USER): reward_grant:read_own (own reward grants only)
- READ (ADMIN): reward_grant:read_any (any user's reward grants)
- GRANT (SYSTEM): reward_grant:grant (SYSTEM only, scoped permission)
- REVOKE (SYSTEM): reward_grant:revoke (SYSTEM only, scoped permission)

### 10.3 Reward Engine Authorization

**Reward Engine as System Actor**:
- Reward Engine operates as system actor
- System actor has specific system permissions for reward operations
- System actor does NOT bypass authorization
- System actor must have explicit system permissions

**System Permissions for Reward Engine**:
- reward_grant:grant (grant rewards to users)
- reward_grant:revoke (revoke rewards from users)
- reward_definition:read (read reward definitions for eligibility)
- user:read_any (read user information for eligibility)

**Implementation**:
- Reward Engine authenticates as system actor
- Reward Engine checks system permissions before operations
- Reward Engine operations are audited
- Reward Engine cannot grant arbitrary permissions

---

## 11. STATE HANDLING

### 11.1 Account State Behavior

**Account States** (from C4 models):
- **ACTIVE**: Account is active and can authenticate/authorize
- **INACTIVE**: Account is disabled and cannot authenticate/authorize
- **SUSPENDED**: Account is suspended and cannot authenticate/authorize
- **CLOSED**: Account is closed and cannot authenticate/authorize

**Authorization Behavior by State**:
- **ACTIVE**: Normal authorization (allow/deny based on permissions/ownership)
- **INACTIVE**: DENY all actions (except possibly account reactivation by admin)
- **SUSPENDED**: DENY all actions (except possibly account reactivation by admin)
- **CLOSED**: DENY all actions (closed accounts cannot be reactivated)

**Implementation**:
- Check account state before authorization
- If account is not ACTIVE, deny access (except admin operations)
- Account state check happens AFTER authentication, BEFORE authorization

### 11.2 Identity State Behavior

**Identity States** (NOT PRESENT IN CURRENT IMPLEMENTATION):
- **ACTIVE**: Identity is active (inferred)
- **DISABLED**: Identity is disabled (inferred)
- **REVOKED**: Identity is revoked (inferred)

**Authorization Behavior by State**:
- **ACTIVE**: Normal authorization (allow/deny based on permissions/ownership)
- **DISABLED**: DENY all actions (identity cannot be used for authentication)
- **REVOKED**: DENY all actions (revoked identity cannot be used for authentication)

**Implementation**:
- Check identity state before authorization (if identity is used for authentication)
- If identity is not ACTIVE, deny access
- Identity state check happens AFTER authentication, BEFORE authorization
- **Note**: Identity state not currently defined in models, defer identity state to future phase

### 11.3 Session State Behavior

**Session States** (from C5 models):
- **ACTIVE**: Session is active and valid
- **EXPIRED**: Session has expired
- **REVOKED**: Session has been revoked

**Authorization Behavior by State**:
- **ACTIVE**: Normal authorization (allow/deny based on permissions/ownership)
- **EXPIRED**: DENY all actions (session must be re-authenticated)
- **REVOKED**: DENY all actions (session must be re-authenticated)

**Implementation**:
- Check session state before authorization
- If session is not ACTIVE, deny access (401)
- Session state check happens in authentication (C5), not authorization (C6)

### 11.4 User State Behavior

**User States** (from C3 models):
- **ACTIVE**: User is active
- **INACTIVE**: User is disabled
- **SUSPENDED**: User is suspended
- **DELETED**: User is deleted

**Authorization Behavior by State**:
- **ACTIVE**: Normal authorization (allow/deny based on permissions/ownership)
- **INACTIVE**: DENY all actions (user cannot authenticate/authorize)
- **SUSPENDED**: DENY all actions (user cannot authenticate/authorize)
- **DELETED**: DENY all actions (user cannot authenticate/authorize)

**Implementation**:
- Check user state before authorization
- If user is not ACTIVE, deny access (401)
- User state check happens in authentication (C5), not authorization (C6)

---

## 12. AUDIT REQUIREMENTS

### 12.1 Authorization Audit Events

**Successful Privileged Operation**:
- Admin role assignment
- Admin role revocation
- Reward definition modification
- Reward grant (system operation)
- Reward revoke (system operation)

**Denied Privileged Operation**:
- Unauthorized role assignment attempt
- Unauthorized role revocation attempt
- Unauthorized reward definition modification attempt
- IDOR attempt
- Privilege escalation attempt

**Ownership Denial**:
- Actor accessing another user's resources
- Ownership violation detected

**Role Assignment/Revocation**:
- Who assigned/revoked
- To whom
- When
- Why (if provided)

**Authorization-Sensitive Security Event**:
- IDOR attempt
- Privilege escalation attempt
- Forged resource identifier attempt
- Unauthorized system operation attempt

### 12.2 Audit Data

**Required Audit Data**:
- Actor ID (user_id)
- Resource type
- Resource ID
- Action attempted
- Permission required
- Decision (ALLOW/DENY)
- Reason for denial
- Timestamp
- IP address
- User agent

### 12.3 Audit Storage

**Storage Location**: AuditEntry table (already exists in models.py)

**Implementation**:
- Log all authorization decisions
- Log authorization failures
- Log security events (IDOR, privilege escalation)
- Retain audit trail for investigation

### 12.4 Sensitive Data (Never Log)

**Never Log**:
- Passwords
- Credential hashes
- Session tokens
- API secrets
- Sensitive authentication material

---

## 13. FILE-LEVEL IMPLEMENTATION PLAN

### 13.1 New Files to Create

**Total New Files**: 9

**backend/authorization/__init__.py**:
- **Current Responsibility**: None (new file)
- **Required Change**: Create package initialization
- **Why**: Required for authorization package
- **Dependencies**: None
- **Risk**: Low
- **Test Coverage**: Module import tests

**backend/authorization/authorization_domain.py**:
- **Current Responsibility**: None (new file)
- **Required Change**: Create authorization domain models
- **Why**: Define authorization domain entities (ActorContext, ActorType, Role, Permission, Resource, Action, Scope, DenialReason)
- **Dependencies**: None (pure domain models)
- **Risk**: Low
- **Test Coverage**: Domain model validation tests

**backend/authorization/authorization_service.py**:
- **Current Responsibility**: None (new file)
- **Required Change**: Create authorization service
- **Why**: Implement authorization decision logic, ownership validation, permission checking
- **Dependencies**: authorization_domain, database models, C5 AuthenticationService
- **Risk**: Medium (critical security logic)
- **Test Coverage**: Unit tests, integration tests, security tests

**backend/authorization/role_service.py**:
- **Current Responsibility**: None (new file)
- **Required Change**: Create role service
- **Why**: Implement role CRUD, role assignment, role revocation, bootstrap
- **Dependencies**: authorization_domain, database models
- **Risk**: Medium (critical security logic)
- **Test Coverage**: Unit tests, integration tests, security tests

**backend/authorization/permission_service.py**:
- **Current Responsibility**: None (new file)
- **Required Change**: Create permission service
- **Why**: Implement permission definition, permission assignment, permission checking
- **Dependencies**: authorization_domain, database models
- **Risk**: Low (permission lookup logic)
- **Test Coverage**: Unit tests

**backend/authorization/authorization_middleware.py**:
- **Current Responsibility**: None (new file)
- **Required Change**: Create authorization middleware
- **Why**: Extract actor from session, check authorization, apply denial semantics
- **Dependencies**: authorization_service, C5 AuthenticationService
- **Risk**: Medium (critical security logic)
- **Test Coverage**: Unit tests, integration tests, security tests

**tests/backend/test_c6_authorization.py**:
- **Current Responsibility**: None (new file)
- **Required Change**: Create authorization tests
- **Why**: Validate authorization implementation
- **Dependencies**: authorization services, domain models
- **Risk**: Low (test code)
- **Test Coverage**: Unit tests, integration tests, security tests

**docs/backend/C06_AUTHORIZATION.md**:
- **Current Responsibility**: None (new file)
- **Required Change**: Create C6 documentation
- **Why**: Document C6 implementation
- **Dependencies**: None
- **Risk**: Low
- **Test Coverage**: Documentation review

**docs/audit/C06_AUTHORIZATION_AUDIT.md**:
- **Current Responsibility**: None (new file)
- **Required Change**: Create C6 audit documentation
- **Why**: Document C6 forensic audit
- **Dependencies**: None
- **Risk**: Low
- **Test Coverage**: Documentation review

### 13.2 Existing Files to Modify

**backend/database/models.py**:
- **Current Responsibility**: Database models definition
- **Required Change**: Add Role model, UserRole model
- **Why**: Store role and role assignment data
- **Dependencies**: None
- **Risk**: Medium (database schema change)
- **Test Coverage**: Database model tests, migration tests

**backend/config/config.py**:
- **Current Responsibility**: Configuration management
- **Required Change**: Add authorization configuration
- **Why**: Configure authorization settings (if any)
- **Dependencies**: None
- **Risk**: Low
- **Test Coverage**: Configuration tests

**tests/backend/test_database_models.py**:
- **Current Responsibility**: Database model tests
- **Required Change**: Add Role, UserRole model tests
- **Why**: Validate new database models
- **Dependencies**: database models
- **Risk**: Low
- **Test Coverage**: Database model tests

---

## 14. TEST IMPLEMENTATION PLAN

### 14.1 Unit Tests

**Permission Evaluation Tests**:
- Test role assignment
- Test permission inheritance
- Test self-permission vs system-permission
- Test permission check logic
- Test permission format validation

**Ownership Tests**:
- Test ownership validation
- Test ownership hierarchy
- Test ownership bypass prevention
- Test forged identifier prevention
- Test ownership path resolution

**Authorization Flow Tests**:
- Test authorization decision process
- Test allow conditions
- Test deny conditions
- Test default deny policy
- Test decision priority order

**Decision Logic Tests**:
- Test decision function inputs
- Test decision function outputs
- Test decision function edge cases
- Test decision function state handling

### 14.2 Integration Tests

**User Ownership Tests**:
- Test user can read own user information
- Test user cannot read another user's user information
- Test user can update own user information
- Test user cannot update another user's user information
- Test 404 returned for ownership violations

**Account Ownership Tests**:
- Test user can read own account information
- Test user cannot read another user's account information
- Test 404 returned for ownership violations

**Identity Ownership Tests**:
- Test user can read own identity information
- Test user cannot read another user's identity information
- Test 404 returned for ownership violations

**Session Ownership Tests**:
- Test user can manage own sessions
- Test user cannot manage another user's sessions
- Test 404 returned for ownership violations

**Credential Ownership Tests**:
- Test user can manage own credentials
- Test user cannot manage another user's credentials
- Test 404 returned for ownership violations

**RewardGrant Ownership Tests**:
- Test user can read own reward grants
- Test user cannot read another user's reward grants
- Test 404 returned for ownership violations

### 14.3 Security Tests

**IDOR Tests**:
- Test actor cannot access another user's resources
- Test 404 returned for ownership violations
- Test resource existence not revealed
- Test all owned resources (User, Account, Identity, Session, Credential, RewardGrant)

**Horizontal Privilege Escalation Tests**:
- Test actor cannot access same-role actor's resources
- Test ownership validation prevents horizontal escalation
- Test 404 returned for ownership violations

**Vertical Privilege Escalation Tests**:
- Test actor cannot elevate privileges
- Test role assignment requires admin permission
- Test self-assignment of admin role prevented
- Test 403 returned for permission violations

**Forged Resource Identifier Tests**:
- Test actor identity from session, not request
- Test user_id/account_id from request ignored
- Test ownership validation against session actor
- Test 404 returned for ownership violations

**ADMIN Boundary Tests**:
- Test admin role assignment requires admin permission
- Test admin role revocation requires admin permission
- Test self-assignment of admin role prevented
- Test at least one admin must remain

**SYSTEM Boundary Tests**:
- Test system actor requires system permissions
- Test system actor does NOT bypass authorization
- Test system actor can perform trusted internal operations
- Test system actor cannot perform arbitrary operations

**Revoked/Disabled Actor Tests**:
- Test revoked session rejected
- Test disabled account rejected
- Test revoked identity rejected (if implemented)
- Test suspended user rejected
- Test 401 returned for authentication failures

**Anti-Enumeration Tests**:
- Test 404 for ownership violations
- Test 403 for permission violations
- Test generic error messages
- Test no resource existence revelation
- Test no permission revelation

**HTTP Semantics Tests**:
- Test 401 for authentication failures
- Test 403 for permission failures
- Test 404 for ownership failures
- Test generic error messages

### 14.4 Concurrency Tests

**Status**: NOT REQUIRED by C6 contract

**Rationale**: C6 contract does not require concurrent authorization testing. Concurrency testing deferred to infrastructure phase.

---

## 15. DEPENDENCY ANALYSIS

### 15.1 Dependency Graph

```
C6 Authorization
  ↓ depends on
C5 Authentication (AuthenticationService, SessionService)
  ↓ depends on
C4 Account/Identity (AccountService, Account/Identity models)
  ↓ depends on
C3 User (UserService, User models)
  ↓ depends on
C2 Database (DatabaseManager, models)
  ↓ depends on
C1 Configuration (Config)
```

### 15.2 Dependency Direction

**Authorization → Authentication**: One-way dependency
- Authorization depends on Authentication for actor identity
- Authentication does NOT depend on Authorization
- No circular dependency

**Authorization → Database**: One-way dependency
- Authorization depends on Database for models
- Database does NOT depend on Authorization
- No circular dependency

**Authorization → Reward Engine**: One-way dependency
- Authorization depends on Reward Engine for system permissions
- Reward Engine does NOT depend on Authorization
- No circular dependency

**Authorization → Event System**: One-way dependency
- Authorization depends on Event System for audit
- Event System does NOT depend on Authorization
- No circular dependency

**Authorization → Audit System**: One-way dependency
- Authorization depends on Audit System for audit
- Audit System does NOT depend on Authorization
- No circular dependency

### 15.3 Dependency Safety

**Circular Dependencies**: None detected
**Circular Risk**: Low (clear one-way dependencies)
**Isolation**: Authorization is isolated from implementation details of dependencies

---

## 16. FAILURE MODES

### 16.1 Failure Mode Analysis

**Missing Actor Context**:
- **Failure**: Actor context not available (no session)
- **Expected Behavior**: DENY, 401, "Authentication required"
- **Implementation**: Return 401 before authorization

**Invalid Role**:
- **Failure**: Role not found in database
- **Expected Behavior**: DENY, 403, "Access denied"
- **Implementation**: Return 403 for permission violation

**Unknown Permission**:
- **Failure**: Permission not defined in permission registry
- **Expected Behavior**: DENY, 403, "Access denied"
- **Implementation**: Return 403 for permission violation

**Missing Resource**:
- **Failure**: Resource not found in database
- **Expected Behavior**: DENY, 404, "Resource not found"
- **Implementation**: Return 404 for resource not found

**Ownership Mismatch**:
- **Failure**: Actor does not own resource
- **Expected Behavior**: DENY, 404, "Resource not found"
- **Implementation**: Return 404 for ownership violation (IDOR prevention)

**Disabled Actor**:
- **Failure**: Actor account/identity/session state not ACTIVE
- **Expected Behavior**: DENY, 401, "Authentication required"
- **Implementation**: Return 401 for authentication failure

**Revoked Session**:
- **Failure**: Session state is REVOKED
- **Expected Behavior**: DENY, 401, "Authentication required"
- **Implementation**: Return 401 for authentication failure

**Forged Resource ID**:
- **Failure**: Actor provides forged user_id/account_id in request
- **Expected Behavior**: DENY, 404, "Resource not found"
- **Implementation**: Return 404 for ownership violation (IDOR prevention)

**Malformed Authorization Request**:
- **Failure**: Authorization request is malformed
- **Expected Behavior**: DENY, 403, "Access denied"
- **Implementation**: Return 403 for authorization failure

**Internal Authorization Failure**:
- **Failure**: Authorization service internal error
- **Expected Behavior**: DENY, 500, "Internal server error"
- **Implementation**: Return 500 for internal error (fail-safe deny)

### 16.2 Fail-Safe Behavior

**Principle**: Fail-safe deny on all failures

**Implementation**:
- All failure modes result in DENY
- All failures are logged for investigation
- No failures result in ALLOW
- Internal errors result in 500, not 200

---

## 17. MIGRATION IMPACT

### 17.1 New Tables

**roles**:
- Purpose: Store role definitions
- Columns: id, role_id, role_name, description, created_at
- Constraints: UniqueConstraint on role_id, CheckConstraint on role_id
- Indexes: Index on role_id
- Migration ordering: Before user_roles

**user_roles**:
- Purpose: Store role assignments
- Columns: id, user_id, role_id, assigned_by, assigned_at
- Constraints: UniqueConstraint on (user_id, role_id)
- Foreign Keys: user_id → users.id (CASCADE DELETE), role_id → roles.id (CASCADE DELETE), assigned_by → users.id (SET NULL)
- Indexes: Index on user_id, Index on role_id, Index on assigned_by
- Migration ordering: After roles

### 17.2 Altered Tables

**None**: No existing tables require alteration

### 17.3 Migration Ordering

**Order**:
1. Create roles table
2. Create user_roles table
3. Create initial roles (USER, ADMIN)
4. Assign USER role to all existing users (if any)
5. Create initial admin user (bootstrap)

### 17.4 Rollback Considerations

**Rollback Strategy**:
- Drop user_roles table (CASCADE DELETE will clean up)
- Drop roles table (CASCADE DELETE will clean up)
- No data loss if rollback before role assignments
- If role assignments exist, manual cleanup may be required

---

## 18. SECURITY REVIEW BEFORE CODING

### 18.1 Threat Review

**IDOR (Insecure Direct Object Reference)**:
- **Threat**: Actor accesses another user's resources by guessing resource IDs
- **Required Implementation Controls**: Ownership validation for all resource access, 404 for ownership violations, actor identity from session not request

**Privilege Escalation (Vertical)**:
- **Threat**: Actor elevates privileges to admin role
- **Required Implementation Controls**: Role assignment only by existing admin, self-assignment prohibited, audit all role changes

**Privilege Escalation (Horizontal)**:
- **Threat**: Actor accesses another user's resources (same role, different user)
- **Required Implementation Controls**: Ownership validation for all resource access, 404 for ownership violations

**Confused Deputy**:
- **Threat**: System actor performs unintended operations
- **Required Implementation Controls**: System actor has explicit system permissions, no global bypass, trusted internal operations explicitly defined

**Role Escalation**:
- **Threat**: Actor escalates roles without authorization
- **Required Implementation Controls**: Role assignment requires admin permission, self-assignment prohibited, audit all role changes

**Authorization Bypass**:
- **Threat**: Actor bypasses authorization checks
- **Required Implementation Controls**: Default deny policy, explicit allow rules, no implicit permissions, all actions require authorization

**Stale Authorization State**:
- **Threat**: Actor uses stale session or revoked privileges
- **Required Implementation Controls**: Session validation (C5), account/identity state validation, role validation

**Enumeration**:
- **Threat**: Attacker enumerates resources or permissions
- **Required Implementation Controls**: 404 for ownership violations, 403 for permission violations, generic error messages, no resource existence revelation

**Fail-Open Behavior**:
- **Threat**: Authorization failure results in allow
- **Required Implementation Controls**: Fail-safe deny on all failures, internal errors result in 500 not 200

**Internal SYSTEM Privilege Abuse**:
- **Threat**: System actor abuses system privileges
- **Required Implementation Controls**: System actor has explicit system permissions, no global bypass, trusted internal operations explicitly defined

### 18.2 Implementation Controls

**Ownership Validation**:
- Extract actor identity from session (not from request)
- Validate ownership against session actor
- Use 404 for ownership violations
- Never trust user_id/account_id from request

**Permission Validation**:
- Default deny policy
- Explicit allow rules only
- No implicit permissions
- All actions require authorization

**State Validation**:
- Validate account state before authorization
- Validate identity state before authorization (if used)
- Validate session state before authorization
- Validate resource state before authorization

**Audit**:
- Log all authorization decisions
- Log all authorization failures
- Log all security events
- Never log sensitive data

**Anti-Enumeration**:
- 404 for ownership violations
- 403 for permission violations
- Generic error messages
- No resource existence revelation
- No permission revelation

---

## 19. IMPLEMENTATION READINESS

### 19.1 Repository Reality

**Current Repository State**:
- C5 Authentication: IMPLEMENTED, TESTED, VALIDATED, ACCEPTED
- C3 User: IMPLEMENTED, TESTED, VALIDATED
- C4 Account/Identity: IMPLEMENTED, TESTED, VALIDATED
- C2 Database: IMPLEMENTED, TESTED, VALIDATED
- C1 Configuration: IMPLEMENTED, TESTED, VALIDATED

**Authorization Foundation**: NOT IMPLEMENTED

### 19.2 Specification Completeness

**Authorization Domain Design**: COMPLETE ✅
**Data Model Impact**: COMPLETE ✅
**Role Model**: COMPLETE ✅
**Permission Model**: COMPLETE ✅
**Authorization Decision**: COMPLETE ✅
**Ownership Graph**: COMPLETE ✅
**IDOR Protection**: COMPLETE ✅
**HTTP/API Boundary**: COMPLETE ✅
**Reward Authorization**: COMPLETE ✅
**State Handling**: COMPLETE ✅
**Audit Requirements**: COMPLETE ✅
**File-Level Implementation Plan**: COMPLETE ✅
**Test Implementation Plan**: COMPLETE ✅
**Dependency Analysis**: COMPLETE ✅
**Failure Modes**: COMPLETE ✅
**Migration Impact**: COMPLETE ✅
**Security Review**: COMPLETE ✅

### 19.3 Unresolved Questions

**None**: All requirements are resolved in the specification

---

## 20. SUMMARY

**Repository Reality**: Current repository has C1-C5 implemented and validated, C6 not implemented
**Exact Files Affected**: 9 new files, 3 existing files to modify
**Exact Models Affected**: 2 new models (Role, UserRole) added to models.py, no existing models modified
**Authorization Domain Design**: Complete with ActorContext, ActorType, Role, Permission, Resource, Action, Scope, DenialReason
**Permission Registry**: Complete with 14 permissions defined (6 user, 8 system/admin)
**Ownership Graph**: Complete with User → Account → Session/Credential, User → Identity, User → RewardGrant
**Decision Flow**: Complete with 7-step decision process, deterministic for USER/ADMIN/SYSTEM actors
**API Semantics**: Complete with HTTP decision table and anti-enumeration policy
**Reward Authorization**: Complete with explicit CREATE/READ/UPDATE/DELETE for RewardDefinition, explicit GRANT/REVOKE for RewardGrant (SYSTEM scoped)
**Audit Requirements**: Complete with 6 audit event types
**Test Plan**: Complete with unit, integration, and security tests
**Migration Plan**: Complete with 2 new tables, no existing table alterations, append-only UserRole with revoked_at
**Dependency Graph**: Complete with one-way dependencies, no circular dependencies
**Security Review**: Complete with 10 threat analyses and required implementation controls
**Unresolved Questions**: None

---

C6-IMPLEMENTATION-SPEC-LOCKED
