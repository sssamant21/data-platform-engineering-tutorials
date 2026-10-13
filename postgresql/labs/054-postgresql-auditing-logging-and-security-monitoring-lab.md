# Chapter 054 — Auditing, Logging and Security Monitoring Lab

**PostgreSQL 18 · Disposable instance · Runtime validation pending.**

## 1. Safety

Use a dedicated PostgreSQL 18 lab instance and an isolated `ch054_lab` database. The exercise creates test objects and roles only in the lab. Preserve server log files and keep passwords out of shell history. No automatic pgAudit installation or server logging reconfiguration is performed.

## 2. Inspect logging configuration

```powershell
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f postgresql/labs/sql/054-inspect.sql
```

Record logging collector status, destinations, log prefix, connection logging, statement/error logging, log timezone, pending restarts and pgAudit availability.

## 3. Generate controlled audit events

Create a new disposable `ch054_lab` database using a lab administrator:

```powershell
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -c "CREATE DATABASE ch054_lab"
psql -X -v ON_ERROR_STOP=1 -U postgres -d ch054_lab -f postgresql/labs/sql/054-events.sql
```

The script refuses to run outside `ch054_lab` and refuses role collisions. It generates a lab role, GRANT/REVOKE, CREATE TABLE and ALTER TABLE events.

**Important:** events appear in server logs only if the relevant native/pgAudit logging settings were enabled before execution. Re-run events after enabling a documented, approved lab configuration if needed.

## 4. Negative and correlation tests

- Attempt one login with a deliberately incorrect lab credential; verify server log capture and source attribution.
- Execute one known lab DDL change; verify its timestamp, role, database and session ID.
- If pgAudit is installed, validate configured ROLE and DDL audit classes and their event records.
- Verify log collection reaches the central store; record ingestion delay.
- Confirm authorized lab DDL does not create a high-severity unauthorized-change incident.

## 5. Evidence worksheet

| Event | Expected evidence | Observed | Pass/Fail |
|---|---|---|---|
| Failed login | SQLSTATE, user, source, time | | |
| CREATE ROLE | Role change audit | | |
| GRANT/REVOKE | Privilege change audit | | |
| CREATE/ALTER TABLE | DDL audit | | |
| TLS session | pg_stat_ssl and connection metadata | | |
| Collector delivery | Central event and timestamp | | |
| Audit retention | Policy and access controls | | |

## 6. Cleanup

After verifying `ch054_lab` is dedicated and all sessions are closed, drop the lab database from `postgres`, then drop `ch054_auditor` if it has no dependencies. Do not run blanket `DROP OWNED` on shared databases. Retain audit evidence according to policy.

**Acceptance:** traceable security events and a verified pipeline. **Runtime:** pending.
