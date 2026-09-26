# C6-02 — AUTHORIZATION CONTRACT RECONCILIATION

**Date**: 2026-09-21
**Task**: C6 Authorization Contract Reconciliation
**Reference**: C6_AUTHORIZATION_CONTRACT.md
**Scope**: C6 Authorization Contract Ambiguity Resolution

---

## 1. RECONCILIATION OBJECTIVE

Resolve contractual ambiguities detected in C6_AUTHORIZATION_CONTRACT.md to achieve C6-CONTRACT-LOCKED status.

---

## 2. AMBIGUITY RESOLUTION

### 2.1 SYSTEM Actor Ambiguity

**Original Ambiguity**: "System bypasses authorization" as global authorization bypass

**Resolution**:
- System actor is NOT a global authorization bypass
- System actor requires explicit system permissions
- System actor is subject to authorization checks
- System actor bypasses ONLY for explicitly defined trusted internal operations

**Trusted Internal Operations**:
- Event generation (server sequence generation)
- Reward eligibility evaluation (read-only)
- Audit entry creation (system events)
- Idempotency record management
- **All other operations require explicit authorization**

**Contractual Update**: System actor must have explicit system permissions; no global bypass

### 2.2 ADMIN Lifecycle Ambiguity

**Original Ambiguity**: ADMIN role assignment/revocation not fully defined

**Resolution**:

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

**Contractual Update**: ADMIN lifecycle fully defined with security controls and audit requirements

### 2.3 Authorization Decision Model Ambiguity

**Original Ambiguity**: Authorization decision process not formally defined

**Resolution**:

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

**Decision Priority**:
1. Authentication check (if fails → DENY)
2. Resource state check (if not active → DENY)
3. System permission check (if system actor and has system permission → ALLOW)
4. Ownership check (if not owned → DENY unless has any permission)
5. Permission check (if permission missing → DENY)
6. Default deny (if no explicit allow → DENY)

**Contractual Update**: Authorization decision model formally defined with explicit logic

### 2.4 Identity/Account State Ambiguity

**Original Ambiguity**: Identity/account state behavior not defined for authorization

**Resolution**:

**Account State Behavior**:
- **ACTIVE**: Normal authorization (allow/deny based on permissions/ownership)
- **INACTIVE**: DENY all actions (except possibly account reactivation by admin)
- **SUSPENDED**: DENY all actions (except possibly account reactivation by admin)
- **CLOSED**: DENY all actions (closed accounts cannot be reactivated)

**Identity State Behavior**:
- **ACTIVE**: Normal authorization (allow/deny based on permissions/ownership)
- **DISABLED**: DENY all actions (identity cannot be used for authentication)
- **REVOKED**: DENY all actions (revoked identity cannot be used for authentication)

**Session State Behavior**:
- **ACTIVE**: Normal authorization (allow/deny based on permissions/ownership)
- **EXPIRED**: DENY all actions (session must be re-authenticated)
- **REVOKED**: DENY all actions (session must be re-authenticated)

**Implementation**:
- Check account state before authorization
- Check identity state before authorization (if used for authentication)
- Check session state before authorization
- State check happens AFTER authentication, BEFORE authorization

**Contractual Update**: Identity/account/session state behavior fully defined for authorization

### 2.5 HTTP Denial Semantics Ambiguity

**Original Ambiguity**: HTTP status codes not fully defined with anti-enumeration policy

**Resolution**:

**HTTP Status Codes**:
- **401 Unauthorized**: Actor not authenticated, session invalid/expired/revoked, account/identity/session state not ACTIVE
- **403 Forbidden**: Actor authenticated but not authorized, actor lacks permission, actor lacks system-permission
- **404 Not Found**: Resource does not exist, resource ID invalid, ownership violation (use 404 instead of 403 to prevent IDOR)

**Anti-Enumeration Policy**:
- **Contractual Property**: Anti-enumeration is a C6 contractual requirement
- Use 404 for ownership violations (do not reveal resource existence)
- Use 403 for permission violations (reveal capability denial, not resource existence)
- Generic error messages (no specific permission revealed)
- No enumeration of resources actor cannot access
- No enumeration of permissions actor lacks

**Error Messages**:
- 401: "Authentication required"
- 403: "Access denied"
- 404: "Resource not found"

**Contractual Update**: HTTP denial semantics fully defined with anti-enumeration policy

### 2.6 Reward Authorization Ambiguity

**Original Ambiguity**: Reward authorization not fully defined

**Resolution**:

**RewardDefinition Authorization**:
- System resource (no owner)
- Admins can manage reward definitions
- Users cannot modify reward definitions
- Reward definitions are system-wide configuration

**RewardGrant Authorization**:
- User resource (owned by user)
- Users can read own reward grants
- Admins can read any user's reward grants
- System actor can grant/revoke rewards (system operation)
- System actor can evaluate eligibility (system operation)

**Reward Engine Authorization**:
- Reward Engine operates as system actor
- System actor has specific system permissions for reward operations
- System actor does NOT bypass authorization
- System actor must have explicit system permissions

**System Permissions for Reward Engine**:
- reward_grant:grant (grant rewards to users)
- reward_grant:revoke (revoke rewards from users)
- reward_definition:read (read reward definitions for eligibility)
- user:read_any (read user information for eligibility)

**Contractual Update**: Reward authorization fully defined for RewardDefinition and RewardGrant

### 2.7 Default Deny Ambiguity

**Original Ambiguity**: Default deny not explicitly defined as contractual property

**Resolution**:

**Contractual Property**: DENY BY DEFAULT is a C6 contractual requirement

**Implementation**:
- All actions require explicit authorization
- No implicit permissions
- No "if authenticated, can access everything"
- Authorization must be explicit for each action
- All authorization decisions must be explicitly defined
- No implicit allow rules

**Contractual Update**: Default deny explicitly defined as contractual property

### 2.8 IDOR Ambiguity

**Original Ambiguity**: IDOR prevention not defined with verifiable properties

**Resolution**:

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

**Contractual Update**: IDOR prevention defined with verifiable properties for all owned resources

### 2.9 Authorization Matrix Ambiguity

**Original Ambiguity**: Authorization matrix not provided

**Resolution**:

**Authorization Matrix**: Actor × Resource × Action × Scope × Decision

**Complete Matrix**: Provided in C6_AUTHORIZATION_CONTRACT.md (Section 21)

**Matrix Format**:
- ACTOR: User, Admin, System, Anonymous
- RESOURCE: User, Account, Identity, Session, Credential, RewardGrant, RewardDefinition
- ACTION: read, update, manage, grant, revoke
- SCOPE: self, any, system
- OWNERSHIP: owned, not_owned, unowned
- STATE: ACTIVE
- DECISION: ALLOW, DENY
- DENIAL REASON: Ownership violation, Permission violation, Not authenticated

**Contractual Update**: Complete authorization matrix provided with all decisions

### 2.10 Performance Ambiguity

**Original Ambiguity**: Performance mitigation claimed as risk mitigation without explicit requirement

**Resolution**:

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

**Contractual Update**: Performance explicitly out of C6 scope (deferred to later phase)

---

## 3. CONTRACT STATUS

### 3.1 Contract Completeness

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

### 3.2 Contract Readiness

**C6-CONTRACT-LOCKED**: YES ✅

**Rationale**:
- Authorization model fully defined
- Security requirements fully specified
- Test requirements fully specified
- Implementation dependencies identified
- Risks identified and mitigated
- Gap analysis complete
- All ambiguities resolved:
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

## 4. SUMMARY

**Ambiguities Resolved**: 10
- System actor global bypass
- ADMIN lifecycle
- Authorization decision model
- Identity/account state
- HTTP denial semantics
- Reward authorization
- Default deny policy
- IDOR verifiable properties
- Authorization matrix
- Performance scope

**Contract Status**: C6-CONTRACT-LOCKED

**Next Step**: Awaiting explicit C5 acceptance and project owner authorization to proceed with C6 implementation

---

## 5. FILES MODIFIED

**Modified**:
- `docs/audit/C6_AUTHORIZATION_CONTRACT.md` - Updated with all reconciliations (1300+ lines)

**Created**:
- `docs/audit/C6_AUTHORIZATION_CONTRACT_RECONCILIATION.md` - This file (200+ lines)

---

C6-CONTRACT-LOCKED
