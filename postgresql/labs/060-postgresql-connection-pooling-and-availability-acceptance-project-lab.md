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
psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 55432 -U lab_admin -d ch060_lab -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID -v confirm_stage=060-CREATE-IDEMPOTENCY -f postgresql/labs/sql/060-fixture.sql
```

Use the **Chapter 004 disposable PostgreSQL 18 primary** (127.0.0.1:55432, `lab_admin`) and its verified `PG_LAB_ROOT/primary` data directory, original cluster marker and private `PGPASSFILE`. Independently record the source system identifier via `pg_control_system()` before replacing `REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID`. Check the target database and `ch060` schema do not already exist before creation; never reuse a populated fixture. The SQL refuses any other database, cluster, role or repeated invocation, and creates the fixture atomically. It intentionally performs the *same* request ID twice within that new fixture to demonstrate `PRIMARY KEY`/`ON CONFLICT DO NOTHING`. It fails with a nonzero status if the expected single row is absent or altered. Use distinct request IDs for later simulated writes and verify actual committed rows.

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
