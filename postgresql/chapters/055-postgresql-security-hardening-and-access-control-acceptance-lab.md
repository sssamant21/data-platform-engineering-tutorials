# Chapter 055 — PostgreSQL Security Hardening and Access Control Acceptance Lab

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Authored; runtime acceptance pending

## 1. Mission and scope

This capstone integrates [Chapter 051 — Roles and Privileges](051-postgresql-security-architecture-roles-and-privilege-boundaries.md), [Chapter 052 — Authentication and TLS](052-postgresql-authentication-pg-hba-conf-and-tls-security.md), [Chapter 053 — RLS](053-postgresql-row-level-security-and-secure-application-access.md) and [Chapter 054 — Audit Monitoring](054-postgresql-auditing-logging-and-security-monitoring.md). Prove that an application database is configured and **behaves** according to its security design, with repeatable evidence and safe rollback.

This project is for a **disposable PostgreSQL 18 lab environment**. Never execute role, HBA, TLS or RLS changes from this capstone on production without separate approved procedures.

## 2. Target architecture

```text
Trusted app clients / operators
         |
  firewall + DNS + TLS verify-full
         |
    pg_hba.conf + SCRAM
         |
   least-privilege LOGIN roles
         |
   schema / table ACL + RLS
         |
   application data and tenant rows
         |
   native logs + optional pgAudit
         |
  protected central audit store / alerts
```

Separate the database owner/migration identity, application writer, application reader, replication identity, monitoring identity and security auditor. Application identities must not be superusers, object owners or BYPASSRLS roles.

## 3. Security acceptance contract

Before execution, record system owner, PostgreSQL version, environment, maintenance window, approved client CIDRs, tenant isolation model, recovery contacts, secrets manager, backup snapshot and security requirements. Define required evidence, thresholds and exceptions with explicit approvers.

| Gate | Required evidence | Mandatory |
|---|---|---|
| Network exposure | Approved listeners/firewall/CIDRs | Yes |
| Authentication | SCRAM verifier rotation plan and successful login | Yes |
| Transport | TLS `verify-full` with valid CA and hostname | Yes |
| HBA deny tests | Non-TLS/unapproved source rejected | Yes |
| Least privilege | Application DML allowed; unauthorized DDL denied | Yes |
| Tenant isolation | Cross-tenant reads/writes denied | Yes |
| Owner and bypass | No runtime SUPERUSER/BYPASSRLS/ownership | Yes |
| Auditing | Authentication, ROLE and DDL events attributable | Yes |
| Detection and retention | Central delivery, retention and alert tests | Yes |
| Rollback | Known-good config restored and revalidated | Yes |

An untested mandatory gate is **NOT VERIFIED**, not PASS.

## 4. Phase A — Inventory and preflight

1. Confirm the lab is disposable and isolated. Capture cluster system identifier, version, databases and active sessions.
2. Export current role membership, object ownership, schema/table ACLs, default privileges and RLS policies.
3. Inspect `listen_addresses`, `ssl`, `password_encryption`, `hba_file`, `pg_hba_file_rules`, `pg_stat_ssl` and server log settings.
4. Record `pg_hba.conf` and TLS certificate backups, break-glass access and a working admin session.
5. Verify central log collector capacity, time synchronization, access controls and evidence retention.

Use [read-only acceptance inspection SQL](../labs/sql/055-inspect.sql).

## 5. Phase B — Identity and least privilege

- Provision dedicated test identities following Chapter 051; inspect role membership `INHERIT`, `SET`, `ADMIN` options.
- Test reader SELECT success and INSERT/UPDATE/DELETE failure.
- Test writer approved DML success and CREATE/DROP failure.
- Verify application identities cannot read protected mappings, modify policies or grant themselves privilege.
- Validate default privileges on tables created **after** the grant policy was configured.

Do not use a superuser query as proof of application access. Perform tests under the actual restricted identity or an equivalent authorized session-authorization test.

## 6. Phase C — Authentication and TLS

- Require `scram-sha-256` for designated application HBA rules; rotate old MD5 verifiers rather than assuming a configuration change converts them.
- Test an approved source with `sslmode=verify-full`, a trusted CA and certificate-matching DNS name.
- Test wrong hostname, untrusted CA, non-TLS and unapproved source; each must fail for the expected reason.
- Confirm HBA first-match behavior and that include order does not unintentionally allow broader access.
- Verify fresh sessions, replication and monitoring after any approved reload.

Do not weaken TLS verification to make a failed test pass.

## 7. Phase D — RLS and secure application access

- Run Chapter 053's two-tenant isolation lab.
- Verify tenant A sees only A rows and tenant B sees only B rows.
- Assert cross-tenant INSERT/UPDATE/DELETE attempts are rejected or affect zero rows as appropriate.
- Inspect table ownership, `BYPASSRLS`, `FORCE ROW LEVEL SECURITY`, permissive policy composition and definer function `search_path`.
- Test application pool reuse; session variables alone are not a trusted tenant identity boundary.

## 8. Phase E — Audit and detection

- Generate a known failed login, an authorized DDL change and a lab GRANT/REVOKE.
- Confirm event capture by native logging or installed/configured pgAudit as applicable.
- Validate source, role, DB, timestamp and session correlation in the central log store.
- Trigger a test alert for an unauthorized-like role change and confirm responder ownership.
- Verify audit retention, access control, integrity, log rotation and disk-pressure monitoring.

Native logs may not capture all ROLE/DDL changes unless appropriate statement logging or pgAudit was configured **before** the events. A missing event is a failed audit coverage test, not a reason to infer success.

## 9. Failure injection matrix

| Scenario | Expected result | Abort / response |
|---|---|---|
| Broad `PUBLIC` grant | Excessive access detected | Revoke in lab, retest |
| Application role is owner | Privilege-boundary failure | Separate owner, retest |
| `host` rule shadows `hostssl` | TLS policy violation | Correct HBA order and deny rules |
| Expired/untrusted TLS cert | `verify-full` fails | Rotate cert/CA safely |
| Tenant context swapped | Cross-tenant denial | Stop and fix trust boundary |
| RLS policy removed | Isolation test fails | Restore tested policy |
| pgAudit unavailable | Audit gate not verified | Use approved native coverage or install/test |
| Log delivery interrupted | Alert on missing telemetry | Restore pipeline, preserve local evidence |
| Admin access lost | Change abort | Use documented break-glass rollback |

## 10. Acceptance rubric

| Category | Points |
|---|---:|
| Identity, roles and object privilege isolation | 20 |
| Authentication, HBA and TLS | 20 |
| Tenant RLS enforcement | 20 |
| Audit logging and detection | 20 |
| Operational runbooks, rollback and evidence | 20 |

**PASS requires all mandatory gates, 100/100 evidence points, and no unresolved critical/high exposure.** Exceptions require explicit documented risk acceptance and cannot be labeled a clean PASS. A lab PASS does not authorize a production deployment.

## 11. Evidence and handoff

Deliver a signed acceptance pack containing sanitized topology, role and ACL inventory, TLS certificate verification, HBA review, positive/negative test results, RLS isolation results, audit events and ingestion timestamps, incident response playbook, rollback proof, residual risks, owners and retest date.

## 12. Troubleshooting and rollback

If a critical control fails, stop further change, preserve evidence and restore the last known-good configuration through the authorized admin path. Roll back specific grants or policy changes using captured ACLs; do **not** disable RLS, use `trust`, weaken TLS or grant SUPERUSER to restore functionality. Re-run every affected gate after remediation.

## 13. Lab

See [Chapter 055 acceptance lab](../labs/055-postgresql-security-hardening-and-access-control-acceptance-lab.md) and its read-only [inspection SQL](../labs/sql/055-inspect.sql) and [acceptance assertions](../labs/sql/055-assertions.sql).

**Runtime status:** not executed; evidence and scores remain pending.

## References

- [Role privileges](https://www.postgresql.org/docs/18/ddl-priv.html)
- [Client authentication](https://www.postgresql.org/docs/18/client-authentication.html)
- [SSL support](https://www.postgresql.org/docs/18/ssl-tcp.html)
- [Row security](https://www.postgresql.org/docs/18/ddl-rowsecurity.html)
- [Logging](https://www.postgresql.org/docs/18/runtime-config-logging.html)

**Next:** Chapter 056 — PostgreSQL Connection Management and PgBouncer Fundamentals.
