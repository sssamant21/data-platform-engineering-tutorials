# Chapter 060 — Connection Pooling and Availability Acceptance Project Lab

**PostgreSQL 18 · PgBouncer lab · Runtime validation pending**

## 1. Prerequisites and safety

Use disposable PostgreSQL and PgBouncer instances with a dedicated `ch060_lab` database. Record versions, config snapshots, admin break-glass connection, backup, recovery plan, client/driver version and expected SLOs. Do not run restart/failover or load injection against production. Keep all generated workload bounded.

## 2. Preflight diagnostics

```powershell
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f postgresql/labs/sql/060-preflight.sql
```

For PgBouncer administrative snapshots:

```powershell
psql -X -h localhost -p 6432 -U pgbouncer_admin -d pgbouncer -c "SHOW VERSION;"
psql -X -h localhost -p 6432 -U pgbouncer_admin -d pgbouncer -c "SHOW CONFIG;"
psql -X -h localhost -p 6432 -U pgbouncer_admin -d pgbouncer -c "SHOW POOLS;"
psql -X -h localhost -p 6432 -U pgbouncer_admin -d pgbouncer -c "SHOW STATS;"
```

## 3. Create an idempotency fixture

Create a dedicated `ch060_lab` database, then execute:

```powershell
psql -X -v ON_ERROR_STOP=1 -U postgres -d ch060_lab -f postgresql/labs/sql/060-fixture.sql
```

The SQL refuses execution outside `ch060_lab`. Use distinct request IDs for each write. Verify that repeating a request ID cannot create duplicate committed rows.

## 4. Baseline and burst

With a bounded test client, record 10–15 minutes of baseline and a brief, controlled increase in concurrent clients. Measure request rate, p95/p99 latency, connection acquisition time, PostgreSQL backend count, PgBouncer waiting clients and maximum wait. Abort on persistent errors or exceeded resource limits.

## 5. Compatibility acceptance

Run Chapter 057's session-state, transaction-local setting and driver prepared-statement tests under the intended pool mode. Record incompatible features and application mitigations.

## 6. Failure injection

In an approved disposable environment, test one PgBouncer instance restart, PostgreSQL restart and a bounded lock wait. Preserve before/during/after metrics and logs. Stop if the service cannot recover within the lab's agreed objective. Do not promote a standby without an established HA test plan.

## 7. Reconcile transaction correctness

For each submitted request ID, classify success, explicit failure or ambiguous outcome. Query `ch060.requests` to determine which IDs committed. Validate no duplicate IDs and that expected committed operations are present. Do not infer that a timeout means a transaction rolled back.

## 8. Recovery and rollback

Restore previous pooler routing/configuration, verify secure connectivity and compare error rate, queue age and backend count against baseline. Document any unavailable tests as NOT VERIFIED.

## 9. Acceptance worksheet

| Gate | Threshold | Observed | Result |
|---|---|---|---|
| Backend budget | Preapproved | | Pending |
| Baseline p95/p99 | Preapproved | | Pending |
| Burst queue age | Preapproved | | Pending |
| Transaction correctness | No duplicate/lost confirmed writes | | Pending |
| Pooler recovery | Preapproved RTO | | Pending |
| PostgreSQL recovery | Preapproved RTO | | Pending |
| TLS/SCRAM | Verified | | Pending |
| Alert delivery | Verified | | Pending |
| Rollback | Verified | | Pending |

**Runtime:** pending. Cleanup only after preserving evidence and verifying the database is dedicated.
