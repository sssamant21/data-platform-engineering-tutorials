# Chapter 056 — Connection Management and PgBouncer Fundamentals Lab

**PostgreSQL 18 · PgBouncer lab instance · Runtime validation pending**

## 1. Preconditions

Use a disposable PostgreSQL instance and a separate PgBouncer installation configured with secure authentication and TLS appropriate to the lab. Do not expose PgBouncer to public networks. Capture PostgreSQL and PgBouncer versions and preserve a direct admin connection to PostgreSQL.

## 2. Baseline PostgreSQL connections

```powershell
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f postgresql/labs/sql/056-connections.sql
```

Record max_connections, reserved slots, session states, long transactions, wait events and application names.

## 3. Inspect PgBouncer

Connect to PgBouncer's **admin database** (`pgbouncer`) using an authorized administrative identity:

```powershell
psql -X -h localhost -p 6432 -U pgbouncer_admin -d pgbouncer -c "SHOW POOLS;"
psql -X -h localhost -p 6432 -U pgbouncer_admin -d pgbouncer -c "SHOW STATS;"
psql -X -h localhost -p 6432 -U pgbouncer_admin -d pgbouncer -c "SHOW SERVERS;"
```

Use secure credential handling. PgBouncer SHOW commands are its administrative protocol, not ordinary PostgreSQL SQL.

## 4. Connection budget exercise

Record:
- PostgreSQL max_connections and reserved headroom.
- PgBouncer replicas, number of pools and per-pool default/reserve sizes.
- Other clients connecting directly (admin, monitoring, migration, replicas).
- Peak `cl_active`, `cl_waiting`, `sv_active`, `sv_idle` and waiting duration.

Compute worst-case aggregate server connections and compare with the application budget.

## 5. Controlled load comparison

From a disposable load generator, create a small number of concurrent short transactions first directly against PostgreSQL, then through PgBouncer. Gradually increase concurrency while staying below approved limits. Compare application latency, PostgreSQL backend count, PgBouncer waiting clients and throughput. Stop on sustained queue growth, errors or resource pressure. Do not run unbounded connection storms.

## 6. Compatibility test

Within a dedicated test database, test a temporary table or session-level `SET` across separate transactions. Compare session pooling and transaction pooling; do not assume state persists in transaction pooling. Test driver prepared-statement behavior using the installed PgBouncer version and `max_prepared_statements` configuration.

## 7. Acceptance worksheet

| Test | Expected | Evidence |
|---|---|---|
| Direct connection baseline | Known backend count | |
| Pooling mode documented | App compatible | |
| Server connection budget | Within approved limit | |
| Pool queue | Bounded wait | |
| TLS and SCRAM | Verified both hops | |
| Session-state test | Expected behavior | |
| Recovery/rollback | Direct path available | |

**Runtime:** pending.
