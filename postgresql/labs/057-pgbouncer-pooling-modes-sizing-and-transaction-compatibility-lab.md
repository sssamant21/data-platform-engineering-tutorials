# Chapter 057 — PgBouncer Pooling Modes, Sizing and Transaction Compatibility Lab

**PostgreSQL 18 · Versioned PgBouncer installation · Runtime validation pending**

## 1. Safety and prerequisites

Use a disposable PostgreSQL instance, dedicated `ch057_lab` database and a PgBouncer instance reachable only from the lab. Preserve direct administrator access. Record exact PgBouncer version, pool mode and driver/ORM versions. Do not run high-concurrency tests on production.

## 2. Baseline PostgreSQL capacity

```powershell
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f postgresql/labs/sql/057-capacity.sql
```

Record max connections, reserved slots, application backend counts and long transactions.

## 3. PgBouncer admin snapshots

```powershell
psql -X -h localhost -p 6432 -U pgbouncer_admin -d pgbouncer -c "SHOW VERSION;"
psql -X -h localhost -p 6432 -U pgbouncer_admin -d pgbouncer -c "SHOW CONFIG;"
psql -X -h localhost -p 6432 -U pgbouncer_admin -d pgbouncer -c "SHOW POOLS;"
psql -X -h localhost -p 6432 -U pgbouncer_admin -d pgbouncer -c "SHOW STATS;"
```

PgBouncer administrative SHOW commands must run against the `pgbouncer` administrative database, not PostgreSQL.

## 4. Aggregate sizing worksheet

| Parameter | Measured |
|---|---|
| PgBouncer instances | |
| Active database/user pools per instance | |
| Default pool size | |
| Reserve pool size | |
| Maximum potential pooled backends | |
| Direct and operational connections | |
| PostgreSQL usable connection budget | |
| Headroom after worst-case allocation | |

Calculate aggregate pool ceiling and ensure operational and break-glass headroom remain available.

## 5. Transaction compatibility

In a dedicated test database, connect via PgBouncer and execute:

```sql
BEGIN;
SET LOCAL application_name = 'ch057-local-test';
SELECT current_setting('application_name');
COMMIT;
```

This proves transaction-local state works **within the transaction**, not that session state persists across transactions. Compare with a session-level `SET` across separate transactions and note that transaction pooling may reassign the server connection. A single successful persistence observation does **not** establish compatibility; repeat with multiple concurrent clients and inspect backend PID changes.

For an isolated temporary-table experiment:

```sql
BEGIN;
CREATE TEMP TABLE ch057_tmp(x integer) ON COMMIT DROP;
INSERT INTO ch057_tmp VALUES (1);
SELECT * FROM ch057_tmp;
COMMIT;
```

This demonstrates transaction-scoped temporary table use; a temp table that must survive commit is not transaction-pool safe without an explicit compatible design.

## 6. Prepared statements and advisory locks

Test your actual driver with named protocol prepared statements and PgBouncer's configured `max_prepared_statements`; do not infer compatibility from SQL `PREPARE`. Test transaction-scoped `pg_advisory_xact_lock` rather than session-level advisory locks.

## 7. Controlled saturation test

Increase disposable load gradually within a defined client limit. Capture `cl_waiting`, `sv_active`, `sv_idle`, queue age, application p95/p99 and backend count. Stop on sustained queue growth or timeouts. Never create an unbounded connection storm.

## 8. Acceptance

| Gate | Expected | Evidence |
|---|---|---|
| Backend ceiling | Below approved budget | |
| Transaction-local state | Correct within transaction | |
| Session-affine features | Compatible or excluded | |
| Prepared statements | Driver verified | |
| Queue time | Within SLO | |
| Authentication and TLS | Both hops verified | |
| Rollback | Tested | |

**Runtime:** pending.
