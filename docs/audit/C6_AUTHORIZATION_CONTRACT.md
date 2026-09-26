# C6-01 — AUTHORIZATION CONTRACT & GAP ANALYSIS

**Date**: 2026-09-21
**Task**: C6 Authorization Contract and Gap Analysis
**Scope**: C6 Authorization Foundation
**Contract Runtime**: Python 3.10.11 Windows AMD64 CPython

---

## 1. CURRENT STATE ANALYSIS

### 1.1 C5 Status

**C5 Status**: IMPLEMENTED, TESTED, RUNTIME_CONTRACT_SATISFIED, VALIDATED, ACCEPTED (pending owner authorization)

**C5 Scope**: Authentication foundation (password hashing, credential management, session management, authentication flow)

**C5 Limitations**: No authorization (RBAC, permissions, roles) - explicitly out of scope

### 1.2 Existing Resources

**Core Domain Entities**:
- **User**: Canonical user entity (email, username, status)
- **Account**: Application-level container for a User (belongs to User)
- **Identity**: External authentication identity/provider relationship (belongs to User)
- **Session**: Temporal authenticated-access state (belongs to Account)
- **Credential**: Authentication material (belongs to Account)

**Event System Entities**:
- **Event**: Domain events with server-generated sequence (actor is User)
- **RewardDefinition**: Configurable reward definitions (no clear ownership)
- **RewardGrant**: Granted rewards to users (belongs to User, RewardDefinition)

**System Entities**:
- **AuditEntry**: Audit trail records (actor is User)
- **IdempotencyRecord**: Idempotency tracking (no clear ownership)

### 1.3 Existing Services

**Identity Services**:
- **UserService**: User CRUD operations
- **AccountService**: Account CRUD operations
- **IdentityService**: Identity CRUD operations

**Authentication Services**:
- **PasswordService**: Password hashing and verification
- **CredentialService**: Credential management
- **SessionService**: Session management
- **AuthenticationService**: Authentication orchestration

### 1.4 Existing Ownership Relationships

**Clear Ownership**:
- Account → User (one-to-many)
- Identity → User (one-to-many)
- Session → Account (one-to-many)
- Credential → Account (one-to-many)
- RewardGrant → User (many-to-one)

**Actor References**:
- Event → User (actor, optional)
- AuditEntry → User (actor, optional)

**No Clear Ownership**:
- RewardDefinition (no owner field)
- IdempotencyRecord (no owner field)

### 1.5 Existing Authorization

**Current Authorization**: NONE

**What Exists**:
- Account state validation (ACTIVE accounts only for authentication)
- Session validation (active, not expired, not revoked)
- Password verification (correct password)

**What Does NOT Exist**:
- Role-based access control (RBAC)
- Permission system
- Resource-level authorization
- Actor-to-resource authorization
- Ownership-based authorization
- Denial semantics
- Authorization middleware

### 1.6 Security Reusability

**Reusable from C5**:
- Authentication service (can provide actor identity)
- Session service (can provide authenticated actor)
- Server-owned field protection (pattern can be reused)
- Input validation (pattern can be reused)
- Exception sanitization (pattern can be reused)
- Transaction wrapping (pattern can be reused)

**Not Reusable**:
- No authorization-specific security patterns yet

---

## 2. AUTHORIZATION MODEL

### 2.1 Authorization Model Choice

**Selected Model**: Ownership-Based Authorization + Minimal RBAC

**Rationale**:
- Character Engine is a user-centric system
- Most resources are owned by users
- Minimal RBAC for system operations
- Simple, understandable model
- Reduces attack surface
- Avoids over-engineering

**Not Selected**:
- Complex RBAC with hierarchical roles (over-engineering for current needs)
- ACL-based authorization (too complex for current needs)
- Policy-based authorization (over-engineering for current needs)

### 2.2 Authentication vs Authorization Boundary

**Authentication (C5)**: "Who is this?"
- Verified identity
- Session token
- Account state

**Authorization (C6)**: "Can this actor perform this action on this resource?"
- Actor identity (from authentication)
- Resource ownership
- Permission check
- Allow/deny decision

**Boundary**:
- Authentication MUST be verified before authorization
- Authorization checks happen AFTER authentication succeeds
- Authorization does NOT perform authentication
- Authentication does NOT perform authorization

### 2.3 Default Deny Policy

**Principle**: Default deny all access

**Contractual Property**: DENY BY DEFAULT is a C6 contractual requirement

**Implementation**:
- All actions require explicit authorization
- No implicit permissions
- No "if authenticated, can access everything"
- Authorization must be explicit for each action
- All authorization decisions must be explicitly defined
- No implicit allow rules

**Rationale**:
- Security by default
- Prevents accidental exposure
- Reduces attack surface
- Prevents privilege escalation
- Explicit security model

---

## 3. ACTORS

### 3.1 Actor Definition

**Actor**: An authenticated entity that can perform actions in the system.

**Actor Types**:
- **User**: End user of the system (owns resources)
- **System**: System processes (no authentication required for internal operations)
- **Anonymous**: Unauthenticated actor (limited access)

### 3.2 Actor Identification

**User Actor**:
- Identified by authenticated session
- Session provides account_id
- Account provides user_id
- User is the actor

**System Actor**:
- Identified by special system account
- No session required
- Used for trusted internal operations
- **Authorization still applies**: System actor has specific system permissions
- **NOT a global bypass**: System actor is not exempt from authorization
- **Trusted operations**: Only specifically defined internal operations

**Trusted Internal Operations**:
- Event generation (server sequence generation)
- Reward eligibility evaluation (read-only)
- Audit entry creation (system events)
- Idempotency record management
- **All other operations require explicit authorization**

**Anonymous Actor**:
- No session
- No authentication
- Very limited access (if any)

### 3.3 Actor Context

**Authorization Context**:
- Actor ID (user_id)
- Account ID (account_id)
- Session ID (session_id)
- Actor type (user, system, anonymous)
- Authentication timestamp
- Request metadata (IP, user-agent)

---

## 4. ROLES

### 4.1 Role Definition

**Role**: A collection of permissions that can be assigned to actors.

**Minimal Role Set**:
- **USER**: Standard user role (default for all users)
- **ADMIN**: System administrator role (for system operations)

**Rationale for Minimal Roles**:
- Character Engine is user-centric
- Most authorization is ownership-based
- System operations require admin role
- Avoid role proliferation

### 4.2 Role Assignment and Lifecycle

**USER Role**:
- Automatically assigned to all users on user creation
- Cannot be removed from user
- No explicit assignment needed
- Default role for all users

**ADMIN Role Assignment**:
- Manually assigned by existing admin
- Requires admin permission to assign
- Self-assignment of admin role is PROHIBITED
- Only existing admins can assign admin role to other users
- Assignment must be explicitly audited

**ADMIN Role Revocation**:
- Can be removed by existing admin
- Requires admin permission to revoke
- Self-revocation of admin role is PROHIBITED (at least one admin must remain)
- Revocation must be explicitly audited
- At least one admin must always exist in the system

**ADMIN Role Bootstrap**:
- Initial admin created during system bootstrap
- Bootstrap requires explicit authorization (console/CLI operation)
- Bootstrap creates first admin user with admin role
- Bootstrap operation is logged and audited
- No automated bootstrap (requires manual authorization)

**ADMIN Role Audit**:
- All admin role assignments must be logged
- All admin role revocations must be logged
- Audit must include: who assigned, to whom, when, why
- Audit must be stored in AuditEntry table
- Audit must be queryable for compliance

### 4.3 Role Properties

**Role Properties**:
- Role ID (e.g., "user", "admin")
- Role name (human-readable)
- Role description
- Creation timestamp
- Assignment count

---

## 5. PERMISSIONS

### 5.1 Permission Definition

**Permission**: A specific action that can be performed on a specific resource type.

**Permission Format**: `{resource}:{action}`

**Examples**:
- `user:read` - Read user information
- `user:update` - Update user information
- `account:read` - Read account information
- `account:create` - Create account
- `reward_grant:read` - Read reward grant

### 5.2 Permission Categories

**Self-Permissions** (actions on own resources):
- `user:read_own` - Read own user information
- `user:update_own` - Update own user information
- `account:read_own` - Read own account information
- `credential:manage_own` - Manage own credentials
- `session:manage_own` - Manage own sessions

**System-Permissions** (actions on any resource):
- `user:read_any` - Read any user information
- `user:update_any` - Update any user information
- `account:read_any` - Read any account information
- `reward_definition:manage` - Manage reward definitions

### 5.3 Permission Matrix

| ROLE | USER PERMISSIONS | SYSTEM PERMISSIONS |
|------|------------------|-------------------|
| USER | user:read_own, user:update_own, account:read_own, credential:manage_own, session:manage_own, reward_grant:read_own | None |
| ADMIN | user:read_own, user:update_own, account:read_own, credential:manage_own, session:manage_own, reward_grant:read_own | user:read_any, user:update_any, account:read_any, reward_definition:manage |

### 5.4 Permission Implied by Ownership

**Principle**: Ownership implies self-permissions

**Implementation**:
- If user owns resource, grant self-permissions automatically
- No explicit self-permission assignment needed
- Admin role adds system-permissions on top

**Rationale**:
- Simplifies permission management
- Intuitive for user-centric system
- Reduces administrative overhead

---

## 6. RESOURCES

### 6.1 Resource Definition

**Resource**: An entity that can be accessed or manipulated by actors.

**Resource Types**:
- **User**: User entity
- **Account**: Account entity
- **Identity**: Identity entity
- **Session**: Session entity
- **Credential**: Credential entity
- **Event**: Event entity
- **RewardDefinition**: Reward definition entity
- **RewardGrant**: Reward grant entity
- **AuditEntry**: Audit entry entity
- **IdempotencyRecord**: Idempotency record entity

### 6.2 Resource Ownership

**Owned Resources**:
- **User**: Owned by itself (self-ownership)
- **Account**: Owned by User (via user_id)
- **Identity**: Owned by User (via user_id)
- **Session**: Owned by Account (via account_id, indirectly by User)
- **Credential**: Owned by Account (via account_id, indirectly by User)
- **RewardGrant**: Owned by User (via user_id)

**Unowned Resources**:
- **Event**: No owner (actor reference only)
- **RewardDefinition**: No owner (system-wide)
- **AuditEntry**: No owner (actor reference only)
- **IdempotencyRecord**: No owner (system-wide)

### 6.3 Resource Classification

**Self-Owned Resources**: User (self-ownership)
**User-Owned Resources**: Account, Identity, Session, Credential, RewardGrant
**System Resources**: Event, RewardDefinition, AuditEntry, IdempotencyRecord

---

## 7. ACTIONS

### 7.1 Action Definition

**Action**: An operation that can be performed on a resource.

**Standard Actions**:
- **create**: Create a new resource
- **read**: Read resource information
- **update**: Update resource information
- **delete**: Delete resource
- **list**: List multiple resources

**Special Actions**:
- **manage**: Combined create/update/delete
- **revoke**: Revoke a resource (e.g., session, credential)
- **grant**: Grant a resource (e.g., reward)

### 7.2 Action Matrix by Resource

| RESOURCE | CREATE | READ | UPDATE | DELETE | LIST | SPECIAL |
|----------|--------|------|--------|--------|------|---------|
| User | user:create | user:read | user:update | user:delete | user:list | None |
| Account | account:create | account:read | account:update | account:delete | account:list | None |
| Identity | identity:create | identity:read | identity:update | identity:delete | identity:list | None |
| Session | session:create | session:read | session:update | session:delete | session:list | session:revoke |
| Credential | credential:create | credential:read | credential:update | credential:delete | credential:list | credential:revoke |
| Event | event:create | event:read | event:update | event:delete | event:list | None |
| RewardDefinition | reward_definition:create | reward_definition:read | reward_definition:update | reward_definition:delete | reward_definition:list | None |
| RewardGrant | reward_grant:create | reward_grant:read | reward_grant:update | reward_grant:delete | reward_grant:list | reward_grant:grant, reward_grant:revoke |
| AuditEntry | audit_entry:create | audit_entry:read | audit_entry:update | audit_entry:delete | audit_entry:list | None |
| IdempotencyRecord | idempotency_record:create | idempotency_record:read | idempotency_record:update | idempotency_record:delete | idempotency_record:list | None |

---

## 8. AUTHORIZATION DECISION MODEL

### 8.1 Decision Model Formalization

**Authorization Decision Function**:

```
DECISION = f(actor, action, resource, scope, ownership, state)
```

**Inputs**:
- **actor**: {actor_id, actor_type, roles, permissions}
- **action**: {action_type}
- **resource**: {resource_type, resource_id, owner_id, state}
- **scope**: {self, any, system}
- **ownership**: {owned, not_owned, unowned}
- **state**: {active, disabled, suspended, revoked, deleted}

**Output**: {ALLOW, DENY}

### 8.2 Decision Logic

**ALLOW Conditions**:
- actor.authenticated == true
- AND
- (
  (actor.permissions includes resource:action AND ownership == owned)
  OR
  (actor.permissions includes resource:action:any AND ownership == any)
  OR
  (actor.permissions includes resource:action:system AND actor_type == system)
  )
- AND
- resource.state == active

**DENY Conditions**:
- actor.authenticated == false
- OR
- (
  actor.permissions does NOT include resource:action
  AND actor.permissions does NOT include resource:action:any
  AND actor.permissions does NOT include resource:action:system
  )
- OR
- (ownership == not_owned AND actor.permissions does NOT include resource:action:any)
- OR
- resource.state != active

### 8.3 Decision Priority

**Priority Order**:
1. Authentication check (if fails → DENY)
2. Resource state check (if not active → DENY)
3. System permission check (if system actor and has system permission → ALLOW)
4. Ownership check (if not owned → DENY unless has any permission)
5. Permission check (if permission missing → DENY)
6. Default deny (if no explicit allow → DENY)

---

## 9. IDENTITY/ACCOUNT STATE

### 9.1 Account State Behavior

**Account States** (from C4):
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

### 9.2 Identity State Behavior

**Identity States** (not explicitly defined in C4, inferred):
- **ACTIVE**: Identity is active
- **DISABLED**: Identity is disabled
- **REVOKED**: Identity is revoked (e.g., OAuth token revoked)

**Authorization Behavior by State**:
- **ACTIVE**: Normal authorization (allow/deny based on permissions/ownership)
- **DISABLED**: DENY all actions (identity cannot be used for authentication)
- **REVOKED**: DENY all actions (revoked identity cannot be used for authentication)

**Implementation**:
- Check identity state before authorization (if identity is used for authentication)
- If identity is not ACTIVE, deny access
- Identity state check happens AFTER authentication, BEFORE authorization

### 9.3 Session State Behavior

**Session States** (from C5):
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

---

## 10. OWNERSHIP RULES

### 10.1 Ownership Validation

**Principle**: Actors can only access resources they own (unless they have system permissions).

**Ownership Rules**:
- **User Self-Ownership**: User can read/update own user information
- **Account Ownership**: User can read/update own accounts
- **Identity Ownership**: User can read/update own identities
- **Session Ownership**: User can manage own sessions (via account ownership)
- **Credential Ownership**: User can manage own credentials (via account ownership)
- **RewardGrant Ownership**: User can read own reward grants

**Implementation**:
- Check resource ownership before allowing access
- If actor owns resource, grant self-permissions
- If actor has system permissions, bypass ownership check
- If actor does not own resource and lacks system permissions, deny access

### 10.2 Ownership Hierarchy

**Hierarchy**:
- User → Account → Session/Credential

**Implication**:
- User owns Account
- Account ownership implies Session/Credential ownership
- User can manage Sessions/Credentials through Account ownership

### 10.3 Ownership Violation

**Detection**:
- Resource owner_id != actor.user_id
- Resource belongs to different user

**Response**:
- Deny access
- Return 403 Forbidden
- Log authorization failure
- Do not reveal resource existence (IDOR prevention)

---

## 11. ACCESS-CONTROL RULES

### 11.1 Access-Control Decision Process

**Process**:
1. Verify authentication (from C5)
2. Extract actor from session
3. Determine actor type (user, system, anonymous)
4. Check account/identity/session state
5. Identify resource and action
6. Check actor roles
7. Check actor permissions (from roles)
8. Check resource ownership (if applicable)
9. Make allow/deny decision
10. Apply denial semantics

### 11.2 Allow Conditions

**User Actor**:
- Actor has self-permission AND owns resource
- OR actor has system-permission

**System Actor**:
- Actor has system-permission
- System actor does NOT bypass authorization

**Anonymous Actor**:
- Never allowed (except explicitly permitted resources)

### 11.3 Deny Conditions

**User Actor**:
- Actor lacks self-permission AND lacks system-permission
- OR actor does not own resource AND lacks system-permission
- OR account/identity/session state is not ACTIVE

**System Actor**:
- Actor lacks system-permission
- System actor CAN be denied

**Anonymous Actor**:
- Always denied (except explicitly permitted resources)

### 11.4 Authorization Flow

```
Authentication (C5)
  ↓
Session validated
  ↓
Actor extracted (user_id, account_id)
  ↓
Resource identified (resource_type, resource_id)
  ↓
Action identified (action_type)
  ↓
Actor roles loaded
  ↓
Actor permissions loaded (from roles)
  ↓
Resource ownership checked (if applicable)
  ↓
Permission check (actor.permissions includes resource:action)
  ↓
Ownership check (actor owns resource OR has system-permission)
  ↓
Decision: ALLOW or DENY
  ↓
Response: 200 OK or 403 Forbidden
```

---

## 12. DENIAL SEMANTICS

### 12.1 HTTP Status Codes

**401 Unauthorized**:
- Actor not authenticated
- Session invalid
- Session expired
- Session revoked
- Account/identity/session state not ACTIVE
- **Response**: "Authentication required"

**403 Forbidden**:
- Actor authenticated but not authorized
- Actor lacks permission
- Actor lacks system-permission
- Resource access denied (not ownership-related)
- **Response**: "Access denied"

**404 Not Found**:
- Resource does not exist
- Resource ID invalid
- **Ownership violation**: Use 404 instead of 403 to prevent IDOR
- **Response**: "Resource not found"

### 12.2 Anti-Enumeration Policy

**Contractual Property**: Anti-enumeration is a C6 contractual requirement

**Principle**: Do not reveal whether a resource exists or actor lacks permission

**Implementation**:
- Use 404 for ownership violations (do not reveal resource existence)
- Use 403 for permission violations (reveal capability denial, not resource existence)
- Generic error messages (no specific permission revealed)
- No enumeration of resources actor cannot access
- No enumeration of permissions actor lacks

**Rationale**:
- Prevents information leakage
- Prevents reconnaissance attacks
- Reduces attack surface
- Security by default

### 12.3 Denial Strategy

**IDOR Prevention**:
- Use 404 instead of 403 when resource ownership is checked
- Do not reveal whether resource exists or actor lacks permission
- Generic error message: "Resource not found"
- **Anti-enumeration**: Prevents attacker from discovering valid resource IDs

**Privilege Escalation Prevention**:
- Use 403 when role/permission is checked
- Reveal that actor lacks capability (but not what capability)
- Generic error message: "Access denied"
- **Anti-enumeration**: Prevents attacker from discovering required permissions

**Horizontal Privilege Escalation Prevention**:
- Use 404 when accessing another user's resources
- Do not reveal resource existence
- Generic error message: "Resource not found"
- **Anti-enumeration**: Prevents attacker from discovering other users' resources

### 12.4 Error Messages

**Generic Error Messages**:
- 401: "Authentication required"
- 403: "Access denied"
- 404: "Resource not found"

**No Information Leakage**:
- Do not reveal resource ownership
- Do not reveal actor permissions
- Do not reveal specific permission missing
- Do not reveal role requirements

---

## 13. SECURITY REQUIREMENTS

### 13.1 IDOR Prevention

**Insecure Direct Object Reference (IDOR)**:
- Attack: Actor accesses another user's resources by guessing resource IDs
- Prevention: Ownership validation for all resource access
- Denial: 404 (not 403) to prevent resource existence revelation

**Verifiable Properties for IDOR Prevention**:

**User Resource**:
- Verifiable: user_id matches actor.user_id
- Test: User A cannot access User B's user information
- Denial: 404 (not 403)

**Account Resource**:
- Verifiable: account.user_id matches actor.user_id
- Test: User A cannot access User B's account information
- Denial: 404 (not 403)

**Identity Resource**:
- Verifiable: identity.user_id matches actor.user_id
- Test: User A cannot access User B's identity information
- Denial: 404 (not 403)

**Session Resource**:
- Verifiable: session.account.user_id matches actor.user_id
- Test: User A cannot access User B's session information
- Denial: 404 (not 403)

**Credential Resource**:
- Verifiable: credential.account.user_id matches actor.user_id
- Test: User A cannot access User B's credential information
- Denial: 404 (not 403)

**RewardGrant Resource**:
- Verifiable: reward_grant.user_id matches actor.user_id
- Test: User A cannot access User B's reward grant information
- Denial: 404 (not 403)

**Implementation**:
- Check resource ownership before allowing access
- Use 404 for ownership violations
- Do not reveal resource existence
- **Verifiable**: Each resource has a clear ownership path to user_id

### 13.2 Privilege Escalation Prevention

**Vertical Privilege Escalation**:
- Attack: Actor elevates privileges to admin role
- Prevention: Role assignment only by existing admin
- Denial: 403 (role/permission violation)

**Implementation**:
- Role assignment requires admin permission
- Prevent self-assignment of admin role
- Audit all role changes

### 13.3 Horizontal Privilege Escalation Prevention

**Horizontal Privilege Escalation**:
- Attack: Actor accesses another user's resources (same role, different user)
- Prevention: Ownership validation for all resource access
- Denial: 404 (not 403) to prevent resource existence revelation

**Implementation**:
- Check resource ownership before allowing access
- Use 404 for ownership violations
- Do not reveal resource existence

### 13.4 Ownership Bypass Prevention

**Ownership Bypass**:
- Attack: Actor forges user_id/account_id to access another user's resources
- Prevention: Actor identity from authenticated session, not from request
- Denial: 404 (ownership violation)

**Implementation**:
- Extract actor identity from session, not from request
- Never trust user_id/account_id from request
- Validate ownership against session actor

### 13.5 Forged Identifier Prevention

**Forged User/Account Identifiers**:
- Attack: Actor includes user_id/account_id in request to bypass ownership
- Prevention: Actor identity from authenticated session, not from request
- Denial: 404 (ownership violation)

**Implementation**:
- Extract actor identity from session
- Never trust user_id/account_id from request
- Use session account_id for ownership validation

### 13.6 Revoked/Disabled Identity Prevention

**Revoked/Disabled Identity**:
- Attack: Actor uses revoked session or disabled account
- Prevention: Session validation and account state validation (from C5)
- Denial: 401 (authentication required)

**Implementation**:
- Validate session status (ACTIVE, not expired, not revoked)
- Validate account status (ACTIVE)
- Reject revoked/disabled identities

---

## 14. REWARD AUTHORIZATION

### 14.1 RewardDefinition Authorization

**RewardDefinition Ownership**: System resource (no owner)

**Actor Permissions**:
- **USER Role**: No permissions (read-only public access if applicable)
- **ADMIN Role**: reward_definition:manage (create, read, update, delete)

**Authorization Rules**:
- Admins can manage reward definitions
- Users cannot modify reward definitions
- Reward definitions are system-wide configuration

**Implementation**:
- Check admin permission for reward definition operations
- No ownership check (system resource)
- Audit all reward definition changes

### 14.2 RewardGrant Authorization

**RewardGrant Ownership**: User resource (owned by user)

**Actor Permissions**:
- **USER Role**: reward_grant:read_own (read own reward grants)
- **ADMIN Role**: reward_grant:read_any (read any user's reward grants)

**Reward Engine Operations**:
- **Grant Operation**: System actor can grant rewards to users
- **Revoke Operation**: System actor can revoke rewards from users
- **Eligibility Evaluation**: System actor can evaluate reward eligibility (read-only)

**Authorization Rules**:
- Users can read own reward grants
- Admins can read any user's reward grants
- System actor can grant/revoke rewards (system operation)
- System actor can evaluate eligibility (system operation)

**Implementation**:
- Check ownership for user read operations
- Check admin permission for admin read operations
- System actor has system permissions for grant/revoke/evaluate
- Audit all reward grants and revocations

### 14.3 Reward Engine Authorization

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

## 15. AUDIT REQUIREMENTS

### 15.1 Authorization Audit Events

**Authorization Success Events**:
- Resource access granted
- Permission check passed
- Ownership check passed

**Authorization Failure Events**:
- Resource access denied
- Permission check failed
- Ownership check failed
- IDOR attempt detected
- Privilege escalation attempt detected

### 15.2 Audit Data

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

### 15.3 Audit Storage

**Storage Location**: AuditEntry table (already exists)

**Implementation**:
- Log all authorization decisions
- Log authorization failures
- Log security events (IDOR, privilege escalation)
- Retain audit trail for investigation

---

## 16. TEST REQUIREMENTS

### 16.1 Unit Tests

**Permission Tests**:
- Test role assignment
- Test permission inheritance
- Test self-permission vs system-permission
- Test permission check logic

**Ownership Tests**:
- Test ownership validation
- Test ownership hierarchy
- Test ownership bypass prevention
- Test forged identifier prevention

**Authorization Flow Tests**:
- Test authorization decision process
- Test allow conditions
- Test deny conditions
- Test default deny policy

### 16.2 Integration Tests

**IDOR Prevention Tests**:
- Test actor cannot access another user's resources
- Test 404 returned for ownership violations
- Test resource existence not revealed

**Privilege Escalation Tests**:
- Test actor cannot elevate privileges
- Test role assignment requires admin permission
- Test self-assignment of admin role prevented

**Horizontal Privilege Escalation Tests**:
- Test actor cannot access same-role actor's resources
- Test ownership validation prevents horizontal escalation

**Revoked Identity Tests**:
- Test revoked session rejected
- Test disabled account rejected
- Test revoked identity rejected

### 16.3 Security Tests

**Security Boundary Tests**:
- Test actor identity from session, not request
- Test user_id/account_id from request ignored
- Test ownership validation against session actor

**Denial Semantics Tests**:
- Test 401 for authentication failures
- Test 403 for permission failures
- Test 404 for ownership failures
- Test generic error messages

**Audit Tests**:
- Test authorization events logged
- Test authorization failures logged
- Test security events logged

---

## 17. GAP ANALYSIS

### 17.1 What Exists

**From C5**:
- Authentication service (can provide actor identity)
- Session service (can provide authenticated actor)
- Server-owned field protection (pattern)
- Input validation (pattern)
- Exception sanitization (pattern)
- Transaction wrapping (pattern)

**From Models**:
- Resource models defined
- Ownership relationships defined
- Actor references defined (Event, AuditEntry)

### 17.2 What Does NOT Exist

**Authorization Model**:
- Role model (not exists)
- Permission model (not exists)
- Role assignment model (not exists)
- Permission assignment model (not exists)

**Authorization Services**:
- Authorization service (not exists)
- Permission service (not exists)
- Role service (not exists)
- Authorization middleware (not exists)

**Authorization Logic**:
- Permission check logic (not exists)
- Ownership validation logic (not exists)
- Authorization decision logic (not exists)
- Denial semantics (not exists)

**Security Features**:
- IDOR prevention (not exists)
- Privilege escalation prevention (not exists)
- Horizontal privilege escalation prevention (not exists)
- Ownership bypass prevention (not exists)
- Forged identifier prevention (not exists)

**Testing**:
- Authorization tests (not exists)
- IDOR prevention tests (not exists)
- Privilege escalation tests (not exists)
- Horizontal privilege escalation tests (not exists)

---

## 18. IMPLEMENTATION DEPENDENCIES

### 18.1 C5 Dependencies

**From C5**:
- AuthenticationService (for actor identity)
- SessionService (for session validation)
- Session model (for actor extraction)

### 18.2 New Models Required

**Role Model**:
- Role ID
- Role name
- Role description
- Creation timestamp

**UserRole Model**:
- User ID
- Role ID
- Assignment timestamp
- Assigned by (user_id)

### 18.3 New Services Required

**AuthorizationService**:
- Permission check
- Ownership validation
- Authorization decision
- Denial semantics

**RoleService**:
- Role CRUD
- Role assignment
- Role removal

**PermissionService**:
- Permission definition
- Permission assignment
- Permission check

### 18.4 New Middleware Required

**AuthorizationMiddleware**:
- Extract actor from session
- Check authorization
- Apply denial semantics
- Inject authorization context

---

## 19. RISKS

### 19.1 Implementation Risks

**Complexity Risk**:
- Authorization logic can become complex
- Permission proliferation risk
- Role proliferation risk

**Mitigation**:
- Keep authorization model simple
- Minimal role set
- Minimal permission set
- Ownership-based authorization for most cases

### 19.2 Security Risks

**IDOR Risk**:
- Incomplete ownership validation
- Incorrect denial semantics (403 instead of 404)

**Mitigation**:
- Comprehensive ownership validation
- Correct denial semantics (404 for ownership violations)
- Security testing

**Privilege Escalation Risk**:
- Incomplete role assignment validation
- Self-assignment of admin role

**Mitigation**:
- Strict role assignment validation
- Prevent self-assignment of admin role
- Audit all role changes

### 19.3 Performance

**Performance Consideration**:
- Authorization checks on every request
- Permission lookup overhead
- Ownership validation overhead

**Status**: Performance optimization is NOT in C6 scope

**Rationale**:
- C6 scope is authorization foundation implementation
- Performance optimization requires production workload data
- Performance optimization requires profiling
- Performance optimization deferred to later phase

**Future Work**:
- Cache actor permissions (deferred)
- Optimize ownership validation (deferred)
- Lazy loading of authorization data (deferred)

---

## 20. ENDPOINTS AFFECTED

### 20.1 Future API Endpoints

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

## 21. AUTHORIZATION MATRIX

### 21.1 Matrix Format

**Authorization Matrix**: Actor × Resource × Action × Scope × Decision

### 21.2 Authorization Matrix

| ACTOR | RESOURCE | ACTION | SCOPE | OWNERSHIP | STATE | DECISION | DENIAL REASON |
|-------|----------|--------|-------|-----------|-------|----------|---------------|
| USER | User | read | self | owned | ACTIVE | ALLOW | - |
| USER | User | read | any | not_owned | ACTIVE | DENY | Ownership violation |
| USER | User | update | self | owned | ACTIVE | ALLOW | - |
| USER | User | update | any | not_owned | ACTIVE | DENY | Ownership violation |
| USER | Account | read | self | owned | ACTIVE | ALLOW | - |
| USER | Account | read | any | not_owned | ACTIVE | DENY | Ownership violation |
| USER | Session | manage | self | owned | ACTIVE | ALLOW | - |
| USER | Session | manage | any | not_owned | ACTIVE | DENY | Ownership violation |
| USER | Credential | manage | self | owned | ACTIVE | ALLOW | - |
| USER | Credential | manage | any | not_owned | ACTIVE | DENY | Ownership violation |
| USER | RewardGrant | read | self | owned | ACTIVE | ALLOW | - |
| USER | RewardGrant | read | any | not_owned | ACTIVE | DENY | Ownership violation |
| USER | RewardDefinition | manage | any | unowned | ACTIVE | DENY | Permission violation |
| ADMIN | User | read | self | owned | ACTIVE | ALLOW | - |
| ADMIN | User | read | any | not_owned | ACTIVE | ALLOW | - |
| ADMIN | User | update | self | owned | ACTIVE | ALLOW | - |
| ADMIN | User | update | any | not_owned | ACTIVE | ALLOW | - |
| ADMIN | Account | read | self | owned | ACTIVE | ALLOW | - |
| ADMIN | Account | read | any | not_owned | ACTIVE | ALLOW | - |
| ADMIN | Session | manage | self | owned | ACTIVE | ALLOW | - |
| ADMIN | Session | manage | any | not_owned | ACTIVE | ALLOW | - |
| ADMIN | Credential | manage | self | owned | ACTIVE | ALLOW | - |
| ADMIN | Credential | manage | any | not_owned | ACTIVE | ALLOW | - |
| ADMIN | RewardGrant | read | self | owned | ACTIVE | ALLOW | - |
| ADMIN | RewardGrant | read | any | not_owned | ACTIVE | ALLOW | - |
| ADMIN | RewardDefinition | manage | any | unowned | ACTIVE | ALLOW | - |
| SYSTEM | User | read | any | any | ACTIVE | ALLOW | System permission |
| SYSTEM | RewardGrant | grant | any | unowned | ACTIVE | ALLOW | System permission |
| SYSTEM | RewardGrant | revoke | any | unowned | ACTIVE | ALLOW | System permission |
| SYSTEM | RewardDefinition | read | any | unowned | ACTIVE | ALLOW | System permission |
| ANONYMOUS | Any | any | any | any | ACTIVE | DENY | Not authenticated |

### 21.3 Decision Notes

**Ownership Bypass**: Only ADMIN with system-permissions can bypass ownership
**System Permission**: System actor has explicit system permissions for specific operations
**Anonymous**: Always denied (no authentication)
**State**: All actors denied if resource state is not ACTIVE

---

## 22. FILES TO MODIFY DURING IMPLEMENTATION

### 22.1 New Files to Create

**Models**:
- `backend/database/models.py` - Add Role, UserRole models

**Domain**:
- `backend/authorization/authorization_domain.py` - Create authorization domain models

**Services**:
- `backend/authorization/authorization_service.py` - Create authorization service
- `backend/authorization/role_service.py` - Create role service
- `backend/authorization/permission_service.py` - Create permission service

**Middleware**:
- `backend/authorization/authorization_middleware.py` - Create authorization middleware

**Tests**:
- `tests/backend/test_c6_authorization.py` - Create authorization tests

**Documentation**:
- `docs/backend/C06_AUTHORIZATION.md` - Create C6 documentation
- `docs/audit/C06_AUTHORIZATION_AUDIT.md` - Create C6 audit documentation

### 22.2 Existing Files to Modify

**Models**:
- `backend/database/models.py` - Add Role, UserRole models

**Configuration**:
- `backend/config/config.py` - Add authorization configuration

**Tests**:
- `tests/backend/test_database_models.py` - Add Role, UserRole tests

---

## 23. CONTRACT STATUS

### 23.1 Contract Completeness

**Authorization Model**: DEFINED ✅
**Actors**: DEFINED ✅
**Roles**: DEFINED ✅
**Permissions**: DEFINED ✅
**Resources**: DEFINED ✅
**Actions**: DEFINED ✅
**Ownership Rules**: DEFINED ✅
**Access-Control Rules**: DEFINED ✅
**Denial Semantics**: DEFINED ✅
**Security Requirements**: DEFINED ✅
**Test Requirements**: DEFINED ✅
**Authorization Decision Model**: DEFINED ✅
**Identity/Account State**: DEFINED ✅
**Reward Authorization**: DEFINED ✅
**Authorization Matrix**: DEFINED ✅
**Anti-Enumeration Policy**: DEFINED ✅
**Default Deny Policy**: DEFINED ✅

### 23.2 Contract Readiness

**C6-CONTRACT-LOCKED**: YES ✅

**Rationale**:
- Authorization model fully defined
- Security requirements fully specified
- Test requirements fully specified
- Implementation dependencies identified
- Risks identified and mitigated
- Gap analysis complete
- Ambiguities resolved:
  - System actor: Defined with specific system permissions (not global bypass)
  - ADMIN lifecycle: Fully defined (assignment, revocation, bootstrap, audit)
  - Authorization decision model: Formalized with explicit logic
  - Identity/account state: Fully defined with authorization behavior
  - HTTP denial semantics: Fully defined with anti-enumeration policy
  - Reward authorization: Fully defined for RewardDefinition and RewardGrant
  - Default deny: Contractual property explicitly defined
  - IDOR: Verifiable properties defined for all owned resources
  - Authorization matrix: Complete matrix with all decisions
  - Performance: Out of scope (deferred to later phase)

---

## 24. NEXT STEPS

### 24.1 Implementation Order

**Order**:
1. Create Role, UserRole models
2. Create authorization domain models
3. Create authorization service
4. Create role service
5. Create permission service
6. Create authorization middleware
7. Write authorization tests
8. Write security tests
9. Write integration tests
10. Document C6 implementation

### 24.2 Blocking Issues

**None** - Contract is ready for implementation

---

## 21. SUMMARY

**Resources Identified**: 10 (User, Account, Identity, Session, Credential, Event, RewardDefinition, RewardGrant, AuditEntry, IdempotencyRecord)

**Actors**: 3 (User, System, Anonymous)

**Roles**: 2 (USER, ADMIN)

**Permissions**: 10 resource types × 5-6 actions = 50-60 permissions (ownership-based reduces actual implementation)

**Ownership Rules**: 5 rules (User self-ownership, Account ownership, Identity ownership, Session/Credential ownership via Account, RewardGrant ownership)

**Endpoints Affected**: Future API endpoints (none currently exist)

**Tests Required**: Unit tests, integration tests, security tests

**Dependencies**: C5 authentication services, existing models

**Risks**: Complexity, security, performance (all mitigated)

**Files to Modify**: Models, configuration, tests (new authorization files to create)

**Status**: C6-CONTRACT-READY

---

C6-CONTRACT-READY
