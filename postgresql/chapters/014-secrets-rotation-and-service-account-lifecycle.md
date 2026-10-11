# Chapter 014 — Secrets Rotation and Service Account Lifecycle

**Audience:** DBRE and SRE teams only. **Baseline:** PostgreSQL 18.
**Duration:** 90–120 minutes with the lab. **Prerequisites:** Chapters 004 and 011–013.
**Status:** Authored and statically reviewed; PostgreSQL lab execution pending.

[Master plan](../MASTER-PLAN.md) · [Previous chapter](013-tls-certificates-verification-and-rotation.md) · [Hands-on lab](../labs/014-secrets-rotation-and-service-account-lifecycle-lab.md) · [Provisioning SQL](../scripts/014-provision-lab.sql) · [Service access probe](../scripts/014-service-access-check.sql) · [Lifecycle inspection](../scripts/014-account-lifecycle-inspection.sql)

## 1. Operational problem and objectives

A password is rotated in PostgreSQL, but some service instances still use the prior secret. Their existing pooled connections work, while new connections fail. A deployment reports success because its readiness check never opened a new connection. Later, an account is marked NOLOGIN but its established sessions continue operating.

Rotation is a coordinated change across the database, secret source, consumer configuration and connection pools. This chapter teaches how to select a rotation strategy, prove credential adoption, handle rollback boundaries and retire identities without leaving sessions or object dependencies unexplained.

The lab uses isolated roles and a dedicated database. It compares same-role password replacement with a bounded overlap between two login identities sharing one least-privilege group.

## 2. Build the identity and secret inventory

| Item | Required evidence |
|---|---|
| Account | Login role, owner/team, purpose, environments and endpoint |
| Authority | Membership options, direct grants, ownership and powerful attributes |
| Secret source | Approved store, version reference, access policy and rotation owner |
| Consumers | Services, jobs, pools, probes, migration tools and recovery dependencies |
| Loading behavior | Startup-only environment, watched file, SDK/cache refresh or manual reload |
| Connection behavior | Pool lifetime, new-connection rate, retry/backoff and drain control |
| Expiry | Password/token/certificate semantics and renewal lead time |
| Recovery | Authorized administrative path, rollback conditions and emergency owner |

Do not put secret values or password verifiers in the inventory. Use version identifiers and sanitized evidence. Separate database service credentials from OS passwords, CA keys and administrator recovery credentials.

An account should have a specific owner and purpose. Shared identities across unrelated applications make adoption measurement and emergency revocation harder. Application login roles should not own durable objects; reuse a stable NOLOGIN privilege group and object owner as taught in Chapter 011.

## 3. Understand what PostgreSQL changes affect

| Action | New connections | Established sessions |
|---|---|---|
| Replace a role's password | Must use the replacement password for password auth | Continue unless independently disconnected |
| Password VALID UNTIL expires | Password authentication fails | Does not automatically terminate them |
| Set NOLOGIN | Direct new logins are denied | Does not disconnect them |
| Set PASSWORD NULL | Password authentication cannot succeed | Does not disconnect them; non-password methods need separate review |
| Revoke CONNECT | New database admission can fail | Existing connections remain |
| Revoke grants/membership | Removes that authority path | Recheck permissions; does not cancel an already running statement |
| Terminate a backend | Does not prevent another login | Ends the targeted session; client retries may create a new one |

NOLOGIN is not a universal prohibition on SET ROLE by another authorized identity. Audit assumption paths separately. External authentication, managed-service tokens, certificates and pooler authentication may have different credential lifetimes.

PostgreSQL stores one password verifier per role. Replacing the password is not a built-in two-password overlap for that role. password_encryption affects newly set passwords, not existing verifiers. Use SCRAM with compatible clients and verify the intended HBA method.

VALID UNTIL concerns password validity; it is not an account-wide expiry across all authentication methods. Password/role changes do not require a PostgreSQL configuration reload. Role changes can be transactional, but they are not atomic with an external secret manager or application deployment.

## 4. Choose a rotation strategy

### Same-role replacement

Keep the login identity and replace its password. Coordinate the database update with the consumer's adoption of the new secret, then force controlled fresh-connection tests.

Changing the database first makes stale consumers fail on new authentication. Publishing the new consumer secret first can also fail until PostgreSQL accepts it. Define the bounded transition window, retry behavior and rollout controls instead of claiming these two systems update atomically.

Existing pools can hide the mismatch. Test fresh connections from each consumer class, then drain/recycle pools deliberately. Avoid restarting every replica simultaneously and creating a connection storm.

### Two-login staged cutover

Create a replacement login with equivalent approved privileges and a distinct secret. Validate it before changing the active consumer configuration. Allow a short, measured overlap, move clients to the replacement, drain old sessions and retire the old identity.

This can reduce transition risk, but expands the set of valid identities during overlap. Time-box it and monitor adoption. Different login names can change role defaults, RLS identity checks, audit labels, tenant mappings and pooler rules. Equal membership does not automatically establish semantic equivalence.

The lab's blue/green identities only share a read-only fixture contract. It does not certify arbitrary application identity equivalence or zero-downtime rotation.

## 5. Treat rotation as an operational state machine

| State | Gate before advancing | Failure response |
|---|---|---|
| Prepared | Inventory and rollback/recovery paths reviewed | Resolve missing consumers or authority |
| Candidate available | Secret created under approved access controls | Keep current version active |
| Database ready | Actual candidate login and restricted operations pass | Repair or withdraw candidate |
| Consumer canary | Fresh canary connection uses intended role/version | Stop rollout and reconcile |
| Adoption | Every consumer class reconnects successfully | Investigate stale config/cache/pool |
| Old admission disabled | Old fresh login fails for the intended reason | Remove remaining admission path |
| Old sessions drained | No unexplained old sessions/jobs | Drain or terminate narrowly under the runbook |
| Retired | Dependencies/grants/secret copies accounted for | Preserve data; resolve remaining references |

With a same-role rotation, database readiness and publication sequencing need a specific coordinated procedure; there is no independent overlapping login identity. With two identities, candidate testing can happen before the consumer cutover.

For Kubernetes, updating a Secret object does not by itself prove environment variables in running processes changed. Mounted files and SDK-based retrieval also need consumer-specific refresh behavior. Retain the adopted version reference and an authenticated reconnect result.

For PgBouncer or another pooler, include both its client authentication state and its backend PostgreSQL credentials. A backend pool that never reconnects cannot prove secret adoption.

## 6. Secret handling and validation

Use the approved secret system for production values. For interactive lab changes, psql's password command avoids placing a cleartext password directly in SQL/history:

~~~text
SET password_encryption = 'scram-sha-256';
\password c014_single
~~~

Use an authenticated administrative path and protected transport in production. Do not pass secrets on command lines, embed them in URLs, enable shell tracing or save password-bearing SQL in repository files.

The lab uses interactive password prompts and writes no credential files. For automation, use protected driver/secret APIs and carefully controlled temporary files if needed. A private password file still contains a secret and needs lifecycle cleanup.

Acceptance combines authentication, authorization and fresh-session evidence. An auth failure alone does not identify stale credentials: correlate role state, HBA, endpoint, expiry and protected logs. A successful existing SELECT does not establish that the currently published secret works.

## 7. Retire identities and handle incidents

For planned retirement, establish replacement adoption first. Disable old admission, stop or drain old consumers, remove unnecessary authority, and inspect owned objects/grants across all databases. NOLOGIN or PASSWORD NULL alone leaves established sessions.

Collect candidate PID, login role, database, application label, backend start, transaction state and workload impact before terminating a session. Use narrowly identified targets; application_name is helpful metadata, not an authorization boundary.

pg_terminate_backend with a positive timeout waits for actual termination or reports timeout. Verify the session is gone and ensure retries do not recreate it. Termination aborts the session's active transaction; coordinate application retry/reconciliation.

DROP ROLE fails when dependencies remain. Preserve durable objects through reviewed ownership/grant remediation. REASSIGN OWNED and DROP OWNED have different effects and require per-database planning; do not use destructive cleanup to make a retirement error disappear.

For suspected credential compromise, containment may need admission disablement, session termination and secret revocation ahead of normal adoption. Do not restore a compromised password as rollback. Evaluate alternate authentication, role-assumption paths and exposed copies.

## 8. Production prechecks, rollback and diagnosis

Precheck the account's full authority, consumers, authentication method, TLS contract, secret version, expiry, pool refresh behavior, scheduled jobs and recovery identity. Define the allowed overlap/transition window and the signal that stops rollout.

| Symptom | Evidence | Next action |
|---|---|---|
| Old pools healthy, reconnect fails | Consumer version and fresh auth | Refresh stale configuration/pools |
| New password fails everywhere | Role/method/expiry and protected server logs | Reconcile database and secret source |
| Only some services fail | Deployment/cache versions and endpoints | Pause rollout; fix the stale consumer class |
| NOLOGIN account still active | Session list and consumer retries | Drain identified sessions and stop retries |
| Replacement reads different data | RLS/defaults/current_user assumptions | Investigate identity equivalence |
| DROP ROLE blocked | Cross-database ownership/ACL dependencies | Preserve required data and remove intended references |
| Rotated secret leaks in evidence | Artifact/log access and exposed copies | Contain and issue another credential |

Rollback must restore a consistent database/consumer state, not just a secret-manager label. Reverting a label alone does not revert PostgreSQL's verifier. Use an authorized compensating password change or reactivate a still-valid, approved alternate identity. Document the point after which old secret destruction or compromise makes rollback impossible.

Stop for missing adoption evidence, unknown dependencies, broader-than-approved replacement privileges, unresolved identity behavior, unexpected authentication methods or lost recovery access.

## 9. Monitoring, acceptance and references

Monitor new-authentication failures, old-identity connection counts, secret-version adoption, overdue overlap, expiring passwords/tokens and powerful-role changes. Correlate failures with rollout and connection creation, not just aggregate query health. Keep secret values out of logs/metric labels.

The lab passes when old/new same-role credentials behave correctly, retained sessions survive password/expiry/NOLOGIN changes as expected, blue/green restricted access matches, old admission is disabled, the identified old session is retired, and original lab access remains healthy. Real secret-manager publication and production pool behavior remain separate acceptance gates.

- [ALTER ROLE](https://www.postgresql.org/docs/18/sql-alterrole.html)
- [Password authentication](https://www.postgresql.org/docs/18/auth-password.html)
- [psql password handling](https://www.postgresql.org/docs/18/app-psql.html)
- [Password files](https://www.postgresql.org/docs/18/libpq-pgpass.html)
- [Backend termination](https://www.postgresql.org/docs/18/functions-admin.html)
- [Role retirement](https://www.postgresql.org/docs/18/role-removal.html)
- [DROP ROLE](https://www.postgresql.org/docs/18/sql-droprole.html)
- [Shared dependencies](https://www.postgresql.org/docs/18/catalog-pg-shdepend.html)

**Next:** Chapter 015 — Audit Logging, Network Isolation and Security Acceptance.
