# Chapter 055 — Security Hardening and Access Control Acceptance Lab

**PostgreSQL 18 · Disposable lab only · Runtime acceptance pending.**

## Prerequisites

Use a dedicated PostgreSQL 18 test instance with administrator access and an isolated database. Complete Chapter 051–054 labs first. Preserve HBA and TLS backups, a working break-glass admin session, trusted CA, secret-manager credentials and centralized log access. No destructive security changes are automated by this capstone.

## Step 1 — Capture read-only baseline

```powershell
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f postgresql/labs/sql/055-inspect.sql
```

Review active logging settings, HBA parse errors, roles, privilege escalation attributes, policies, and TLS session state.

## Step 2 — Role and privilege acceptance

Run Chapter 051 provisioning/verification in its dedicated lab database. Record successful reader SELECT, denied reader writes, successful writer DML, denied writer DDL, and post-default-grant table checks.

## Step 3 — TLS and HBA acceptance

Run Chapter 052 tests from approved and unapproved networks. Verify `sslmode=verify-full` success for correct hostname/CA, failure for wrong hostname/CA, denial of non-TLS access, and continued replication/monitoring access. Capture logs and HBA first-match review.

## Step 4 — Tenant isolation acceptance

Run Chapter 053 tests using the actual tenant identity simulation in its dedicated lab database. Confirm that tenant A/B cannot read or modify each other's rows. Inspect bypass attributes and object ownership.

## Step 5 — Audit acceptance

Run Chapter 054 audit-event lab. Correlate failed login, DDL, GRANT/REVOKE and security-alert events with the central store. Measure delivery lag and verify retention.

## Step 6 — Metadata assertions

Run the [assertions SQL](sql/055-assertions.sql) against the PostgreSQL server **after** all labs are provisioned. It checks for unexpectedly privileged lab identities and HBA parsing errors. Note that it cannot replace end-to-end TLS, RLS or audit tests.

```powershell
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f postgresql/labs/sql/055-assertions.sql
```

## Acceptance worksheet

| Control | Test result | Evidence | Owner |
|---|---|---|---|
| Role least privilege | Pending | | |
| Default privileges | Pending | | |
| SCRAM and HBA first match | Pending | | |
| TLS verify-full | Pending | | |
| Unapproved source denied | Pending | | |
| Tenant isolation | Pending | | |
| No privileged runtime role | Pending | | |
| Audited DDL/ROLE events | Pending | | |
| Alerting and retention | Pending | | |
| Rollback tested | Pending | | |

Any mandatory gate untested or failed means **NOT ACCEPTED**. Record residual risks, incident response contacts and retest schedule.

## Cleanup

Follow each chapter's dedicated lab cleanup after confirming no shared dependencies. Retain audit evidence according to policy. Do not perform broad `DROP OWNED` or remove shared roles.

**Runtime:** pending.
