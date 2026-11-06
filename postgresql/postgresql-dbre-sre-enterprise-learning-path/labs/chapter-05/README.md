# Chapter 05 Lab — Index Design, EXPLAIN and Performance Evidence

**Duration:** ~22 minutes of a 60-minute lesson · **Reference:** PostgreSQL 17, Docker Desktop/Engine  
**State:** Instructions authored. **No commands have been run or runtime evidence collected.**

[Chapter 05 lesson](../../chapters/05-indexes-query-plans-and-performance.md) · [Course home](../../README.md)

## Scope and safety

This lab creates **only** a disposable database named `training_ch05` in the `pg-fleet-lab` Docker container established in Chapter 01. It does not touch Chapter 01–04 databases, production data, server configuration, or real credentials.

- Requires Docker in Linux-container mode, PostgreSQL 17 image, and enough disk space for ~200,000 synthetic event rows and indexes. Actual footprint varies.
- The `postgres` superuser is used **only** inside the local teaching container; never model this as an application credential.
- Do not copy commands to a production system. In particular, `CREATE INDEX` can use locks and resources; production indexing needs change review.
- All `EXPLAIN (ANALYZE, BUFFERS)` commands here are read-only `SELECT` statements; the `ANALYZE` option **executes** the query.
- No cleanup is performed automatically. Inspect names and ownership before any future deletion.

## Step 0 — Verify the disposable target (2 minutes)

In PowerShell:

```powershell
$ErrorActionPreference = 'Stop'
$context = docker context show
if ($LASTEXITCODE -ne 0 -or -not $context) { throw 'Cannot determine Docker context' }
docker context inspect $context
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect Docker endpoint' }
# Compare the context AND endpoint with the retained Chapter 01 creation record.
# Stop unless this is the same approved, local, disposable Docker engine.
$engine = docker info --format '{{.OSType}}'
if ($LASTEXITCODE -ne 0 -or $engine -ne 'linux') { throw 'Requires Linux Docker engine' }
$names = @(docker ps --filter 'name=^/pg-fleet-lab

Check whether this lab database already exists:

```powershell
docker exec pg-fleet-lab psql -U postgres -d postgres -tAc "SELECT datname FROM pg_database WHERE datname = 'training_ch05';"
```

For a fresh lab, expect no output. If it exists, **stop and inspect it**; do not drop or overwrite it.

## Step 1 — Create and connect (2 minutes)

Run **only when the database does not exist**:

```powershell
docker exec pg-fleet-lab createdb -U postgres training_ch05
docker exec -it pg-fleet-lab psql -U postgres -d training_ch05
```

The following statements run **inside the psql prompt** unless otherwise specified.

```sql
SELECT current_database(), current_user, current_setting('server_version');
CREATE SCHEMA perf_lab;
```

Expected: `training_ch05`, `postgres`, PostgreSQL 17, and `CREATE SCHEMA`.

## Step 2 — Create a deterministic synthetic workload (4 minutes)

```sql
CREATE TABLE perf_lab.events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'completed')),
    amount NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
    created_at TIMESTAMPTZ NOT NULL
);

INSERT INTO perf_lab.events (customer_id, status, amount, created_at)
SELECT
    ((g - 1) % 2000) + 1,
    CASE WHEN g % 10 = 0 THEN 'pending' ELSE 'completed' END,
    (g % 10000)::numeric / 100,
    TIMESTAMPTZ '2026-01-01 00:00:00+00' + g * INTERVAL '1 second'
FROM generate_series(1, 200000) AS g;

ANALYZE perf_lab.events;

SELECT count(*) AS total_events,
       count(*) FILTER (WHERE status = 'pending') AS pending_events,
       count(DISTINCT customer_id) AS customers
FROM perf_lab.events;
```

Expected row counts:

```text
 total_events | pending_events | customers
--------------+----------------+----------
       200000 |          20000 |     2000
```

**Why this workload?** Each customer has 100 events. The query below asks for the latest 20 events for one customer, so a well-chosen composite index may avoid scanning most rows and sorting the matches.

## Step 3 — Capture the baseline plan (3 minutes)

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT event_id, customer_id, created_at, amount
FROM perf_lab.events
WHERE customer_id = 42
ORDER BY created_at DESC
LIMIT 20;
```

Record:

- Scan method: often `Seq Scan` before the new index.
- Whether there is a `Sort` node.
- Estimated and actual rows.
- `Rows Removed by Filter`, if shown.
- `Buffers: shared hit` and `shared read`.
- Planning and execution times.

**Expected observation, not a guarantee:** the pre-index plan commonly scans the table and sorts matching rows. The exact plan and timing depend on statistics and environment.

Do not use `SET enable_seqscan = off` to force a result. That would hide the planner's actual decision.

## Step 4 — Add a targeted composite B-tree index (3 minutes)

```sql
CREATE INDEX idx_events_customer_created
ON perf_lab.events (customer_id, created_at DESC);

ANALYZE perf_lab.events;
```

This ordinary `CREATE INDEX` is allowed only because the target is a disposable lab. For production, evaluate `CREATE INDEX CONCURRENTLY`, capacity, write load, failure behavior, and change controls separately.

Repeat **exactly the same query**:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT event_id, customer_id, created_at, amount
FROM perf_lab.events
WHERE customer_id = 42
ORDER BY created_at DESC
LIMIT 20;
```

**Possible expected observation:** `Index Scan using idx_events_customer_created` with `Index Cond: (customer_id = 42)` and no explicit sort. It can stop after retrieving 20 rows. PostgreSQL is free to choose another plan if it estimates a lower cost.

Compare both plans:

| Evidence | Before index | After index |
|---|---|---|
| Scan method | Record actual | Record actual |
| Sort present? | Record actual | Record actual |
| Estimated rows | Record actual | Record actual |
| Actual rows and loops | Record actual | Record actual |
| Shared hits/reads | Record actual | Record actual |
| Execution time (ms) | Record actual | Record actual |

**Do not claim an exact speedup** from a single run. Buffer cache warming and measurement overhead can distort comparisons. For a stronger result, repeat each read-only query several times in a controlled environment and report median plus variability; application p95 requires separate workload testing.

## Step 5 — Test a partial index (optional, 3 minutes)

A small subset of events is `pending`. A partial index can be attractive for a frequent query that only reads this subset.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT event_id, status, created_at
FROM perf_lab.events
WHERE status = 'pending'
ORDER BY created_at DESC
LIMIT 20;

CREATE INDEX idx_events_pending_recent
ON perf_lab.events (created_at DESC)
WHERE status = 'pending';

ANALYZE perf_lab.events;

EXPLAIN (ANALYZE, BUFFERS)
SELECT event_id, status, created_at
FROM perf_lab.events
WHERE status = 'pending'
ORDER BY created_at DESC
LIMIT 20;
```

**Possible observation:** the partial index supports the second query with an ordered index scan. Its actual use is planner-dependent. Note that `status = 'pending'` is a literal matching the partial-index predicate; generic parameterized plans may not prove a matching predicate.

Do not create a partial index with a volatile time-based predicate such as `WHERE created_at > now() - interval '1 day'`; index predicates require immutable expressions.

## Step 6 — Inspect size and usage (3 minutes)

```sql
SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'perf_lab'
ORDER BY tablename, indexname;

SELECT
    c.relname AS index_name,
    pg_size_pretty(pg_relation_size(c.oid)) AS index_size
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'perf_lab'
  AND c.relkind = 'i'
ORDER BY pg_relation_size(c.oid) DESC;

SELECT
    relname, indexrelname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'perf_lab'
ORDER BY relname, indexrelname;

SELECT
    pg_size_pretty(pg_relation_size('perf_lab.events')) AS table_heap,
    pg_size_pretty(pg_indexes_size('perf_lab.events')) AS all_indexes,
    pg_size_pretty(pg_total_relation_size('perf_lab.events')) AS total_relation;
```

Expected: the primary-key index, composite index, and (if optional step completed) partial index. Sizes and cumulative counters vary by runtime. `idx_scan` can lag or be reset; do not interpret it as an authoritative inventory of application dependencies.

## Step 7 — Explain why the optimizer might not use an index (2 minutes)

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*)
FROM perf_lab.events
WHERE customer_id BETWEEN 1 AND 2000;
```

The predicate covers all rows. A sequential or parallel sequential scan can be reasonable even though the table has an index on `customer_id`. The exact plan is not guaranteed.

Discuss:

1. Why might the planner prefer a sequential scan for this query?
2. Why do `shared read` counts not prove physical disk I/O?
3. Why is `cost=100` not equivalent to 100 milliseconds?
4. Why can adding indexes make high-ingest systems slower?
5. Why should an unused-index cleanup job not delete a low-scan index automatically?

## Step 8 — Production design exercise (3 minutes)

Prepare a short change proposal for an application query that frequently retrieves the latest customer events.

Include:
- **Before:** representative plan, parameter pattern, row counts, query rate, latency baseline.
- **Change:** composite index definition, justification for column order, expected size and write impact.
- **Safety:** staging test, lock/DDL review, storage/WAL headroom, replication lag, deployment owner, change window or online-indexing approach.
- **Validation:** after-plan, application p95, CPU/I/O, write throughput, errors, replication lag.
- **Rollback:** preapproved plan to remove only the newly introduced index if needed, after verifying its name, ownership, and dependencies. No automatic destructive SQL is included.

Do not treat a successful local lab as production approval.

## Step 9 — Close the session, retain evidence

At the `psql` prompt:

```text
\q
```

Do not delete the `training_ch05` database as part of the lab; retain it for follow-up learning. If decommissioning the disposable environment later, verify its identity and follow a separate, approved cleanup procedure.

### Acceptance checklist

- [ ] PostgreSQL 17 and disposable target verified.
- [ ] 200,000 synthetic rows loaded; 20,000 pending; 2,000 distinct customers.
- [ ] Baseline `EXPLAIN (ANALYZE, BUFFERS)` captured.
- [ ] Composite index created and second plan captured.
- [ ] Difference in scan, sort, buffers, and time explained without promising a fixed speedup.
- [ ] Optional partial index exercise performed or explicitly marked skipped.
- [ ] Index inventory, size, and usage queries captured.
- [ ] Broad-selectivity query discussed.
- [ ] Production change and rollback plan drafted.
- [ ] Sanitized evidence retained **only if the commands were actually run**.

**Publication status:** Authored, not executed. Independent technical review and operational certification remain pending.

## Troubleshooting

| Symptom | Safe response |
|---|---|
| `pg-fleet-lab` is absent | Follow Chapter 01 Docker setup; never redirect to a production server |
| `training_ch05` already exists | Inspect first; do not overwrite or drop automatically |
| `CREATE SCHEMA` or `CREATE TABLE` says already exists | A previous run left objects; verify their contents rather than rerunning blindly |
| `INSERT` reports 0 or unexpected count | Check whether the lab was already populated and confirm current database |
| Planner still uses Seq Scan | Compare row estimates, selectivity, and statistics; planner may be correct |
| Index build seems slow | Check container resources and storage headroom; do not kill unrelated processes |
| Plan shows many `shared hit` buffers | Shared-memory activity is not necessarily a storage problem |
| SQL output differs from examples | Treat examples as illustrative; record actual observations and version |

## Official PostgreSQL 17 references

- [EXPLAIN](https://www.postgresql.org/docs/17/sql-explain.html)
- [Using EXPLAIN](https://www.postgresql.org/docs/17/using-explain.html)
- [Index Types](https://www.postgresql.org/docs/17/indexes-types.html)
- [Multicolumn Indexes](https://www.postgresql.org/docs/17/indexes-multicolumn.html)
- [Partial Indexes](https://www.postgresql.org/docs/17/indexes-partial.html)
- [CREATE INDEX](https://www.postgresql.org/docs/17/sql-createindex.html)
- [Examining Index Usage](https://www.postgresql.org/docs/17/indexes-examine.html)
 --format '{{.Names}}')
if ($LASTEXITCODE -ne 0 -or $names.Count -ne 1 -or $names[0] -ne 'pg-fleet-lab') {
    throw 'Expected disposable container is not uniquely running'
}
$labId = docker inspect --format '{{.Id}}' pg-fleet-lab
if ($LASTEXITCODE -ne 0 -or -not $labId) { throw 'Cannot inspect container ID' }
$label = docker inspect --format '{{index .Config.Labels "dbre.training"}}' $labId
if ($LASTEXITCODE -ne 0 -or $label -ne 'postgresql-enterprise-ch01') { throw 'Training ownership label mismatch' }
$image = docker inspect --format '{{.Config.Image}}' $labId
if ($LASTEXITCODE -ne 0 -or $image -ne 'postgres:17') { throw 'Unexpected image; verify PostgreSQL 17 lab provenance' }
$volume = docker inspect --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}' $labId
if ($LASTEXITCODE -ne 0 -or $volume -ne 'pg_fleet_data') { throw 'Unexpected data volume' }
# Independently compare $labId with the full ID recorded when Chapter 01 created the container.
# Do not continue if that record is missing or differs. Names/labels alone do not prove ownership.
docker exec $labId pg_isready -U postgres
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL is not ready' }
docker exec $labId psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -tAc 'SHOW server_version;'
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL version check failed' }
```

Expected: the verified Chapter 01 container, `linux` engine, PostgreSQL accepting connections, and server version 17.x. Compare the full ID, context endpoint, and volume against Chapter 01's retained creation record **before any further `docker exec`**. A mismatched or missing record is a stop condition. The remaining commands use the name `pg-fleet-lab`; reconfirm identity if the container is recreated or the Docker context changes.

Check whether this lab database already exists:

```powershell
docker exec pg-fleet-lab psql -U postgres -d postgres -tAc "SELECT datname FROM pg_database WHERE datname = 'training_ch05';"
```

For a fresh lab, expect no output. If it exists, **stop and inspect it**; do not drop or overwrite it.

## Step 1 — Create and connect (2 minutes)

Run **only when the database does not exist**:

```powershell
docker exec pg-fleet-lab createdb -U postgres training_ch05
docker exec -it pg-fleet-lab psql -U postgres -d training_ch05
```

The following statements run **inside the psql prompt** unless otherwise specified.

```sql
SELECT current_database(), current_user, current_setting('server_version');
CREATE SCHEMA perf_lab;
```

Expected: `training_ch05`, `postgres`, PostgreSQL 17, and `CREATE SCHEMA`.

## Step 2 — Create a deterministic synthetic workload (4 minutes)

```sql
CREATE TABLE perf_lab.events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'completed')),
    amount NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
    created_at TIMESTAMPTZ NOT NULL
);

INSERT INTO perf_lab.events (customer_id, status, amount, created_at)
SELECT
    ((g - 1) % 2000) + 1,
    CASE WHEN g % 10 = 0 THEN 'pending' ELSE 'completed' END,
    (g % 10000)::numeric / 100,
    TIMESTAMPTZ '2026-01-01 00:00:00+00' + g * INTERVAL '1 second'
FROM generate_series(1, 200000) AS g;

ANALYZE perf_lab.events;

SELECT count(*) AS total_events,
       count(*) FILTER (WHERE status = 'pending') AS pending_events,
       count(DISTINCT customer_id) AS customers
FROM perf_lab.events;
```

Expected row counts:

```text
 total_events | pending_events | customers
--------------+----------------+----------
       200000 |          20000 |     2000
```

**Why this workload?** Each customer has 100 events. The query below asks for the latest 20 events for one customer, so a well-chosen composite index may avoid scanning most rows and sorting the matches.

## Step 3 — Capture the baseline plan (3 minutes)

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT event_id, customer_id, created_at, amount
FROM perf_lab.events
WHERE customer_id = 42
ORDER BY created_at DESC
LIMIT 20;
```

Record:

- Scan method: often `Seq Scan` before the new index.
- Whether there is a `Sort` node.
- Estimated and actual rows.
- `Rows Removed by Filter`, if shown.
- `Buffers: shared hit` and `shared read`.
- Planning and execution times.

**Expected observation, not a guarantee:** the pre-index plan commonly scans the table and sorts matching rows. The exact plan and timing depend on statistics and environment.

Do not use `SET enable_seqscan = off` to force a result. That would hide the planner's actual decision.

## Step 4 — Add a targeted composite B-tree index (3 minutes)

```sql
CREATE INDEX idx_events_customer_created
ON perf_lab.events (customer_id, created_at DESC);

ANALYZE perf_lab.events;
```

This ordinary `CREATE INDEX` is allowed only because the target is a disposable lab. For production, evaluate `CREATE INDEX CONCURRENTLY`, capacity, write load, failure behavior, and change controls separately.

Repeat **exactly the same query**:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT event_id, customer_id, created_at, amount
FROM perf_lab.events
WHERE customer_id = 42
ORDER BY created_at DESC
LIMIT 20;
```

**Possible expected observation:** `Index Scan using idx_events_customer_created` with `Index Cond: (customer_id = 42)` and no explicit sort. It can stop after retrieving 20 rows. PostgreSQL is free to choose another plan if it estimates a lower cost.

Compare both plans:

| Evidence | Before index | After index |
|---|---|---|
| Scan method | Record actual | Record actual |
| Sort present? | Record actual | Record actual |
| Estimated rows | Record actual | Record actual |
| Actual rows and loops | Record actual | Record actual |
| Shared hits/reads | Record actual | Record actual |
| Execution time (ms) | Record actual | Record actual |

**Do not claim an exact speedup** from a single run. Buffer cache warming and measurement overhead can distort comparisons. For a stronger result, repeat each read-only query several times in a controlled environment and report median plus variability; application p95 requires separate workload testing.

## Step 5 — Test a partial index (optional, 3 minutes)

A small subset of events is `pending`. A partial index can be attractive for a frequent query that only reads this subset.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT event_id, status, created_at
FROM perf_lab.events
WHERE status = 'pending'
ORDER BY created_at DESC
LIMIT 20;

CREATE INDEX idx_events_pending_recent
ON perf_lab.events (created_at DESC)
WHERE status = 'pending';

ANALYZE perf_lab.events;

EXPLAIN (ANALYZE, BUFFERS)
SELECT event_id, status, created_at
FROM perf_lab.events
WHERE status = 'pending'
ORDER BY created_at DESC
LIMIT 20;
```

**Possible observation:** the partial index supports the second query with an ordered index scan. Its actual use is planner-dependent. Note that `status = 'pending'` is a literal matching the partial-index predicate; generic parameterized plans may not prove a matching predicate.

Do not create a partial index with a volatile time-based predicate such as `WHERE created_at > now() - interval '1 day'`; index predicates require immutable expressions.

## Step 6 — Inspect size and usage (3 minutes)

```sql
SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'perf_lab'
ORDER BY tablename, indexname;

SELECT
    c.relname AS index_name,
    pg_size_pretty(pg_relation_size(c.oid)) AS index_size
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'perf_lab'
  AND c.relkind = 'i'
ORDER BY pg_relation_size(c.oid) DESC;

SELECT
    relname, indexrelname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'perf_lab'
ORDER BY relname, indexrelname;

SELECT
    pg_size_pretty(pg_relation_size('perf_lab.events')) AS table_heap,
    pg_size_pretty(pg_indexes_size('perf_lab.events')) AS all_indexes,
    pg_size_pretty(pg_total_relation_size('perf_lab.events')) AS total_relation;
```

Expected: the primary-key index, composite index, and (if optional step completed) partial index. Sizes and cumulative counters vary by runtime. `idx_scan` can lag or be reset; do not interpret it as an authoritative inventory of application dependencies.

## Step 7 — Explain why the optimizer might not use an index (2 minutes)

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*)
FROM perf_lab.events
WHERE customer_id BETWEEN 1 AND 2000;
```

The predicate covers all rows. A sequential or parallel sequential scan can be reasonable even though the table has an index on `customer_id`. The exact plan is not guaranteed.

Discuss:

1. Why might the planner prefer a sequential scan for this query?
2. Why do `shared read` counts not prove physical disk I/O?
3. Why is `cost=100` not equivalent to 100 milliseconds?
4. Why can adding indexes make high-ingest systems slower?
5. Why should an unused-index cleanup job not delete a low-scan index automatically?

## Step 8 — Production design exercise (3 minutes)

Prepare a short change proposal for an application query that frequently retrieves the latest customer events.

Include:
- **Before:** representative plan, parameter pattern, row counts, query rate, latency baseline.
- **Change:** composite index definition, justification for column order, expected size and write impact.
- **Safety:** staging test, lock/DDL review, storage/WAL headroom, replication lag, deployment owner, change window or online-indexing approach.
- **Validation:** after-plan, application p95, CPU/I/O, write throughput, errors, replication lag.
- **Rollback:** preapproved plan to remove only the newly introduced index if needed, after verifying its name, ownership, and dependencies. No automatic destructive SQL is included.

Do not treat a successful local lab as production approval.

## Step 9 — Close the session, retain evidence

At the `psql` prompt:

```text
\q
```

Do not delete the `training_ch05` database as part of the lab; retain it for follow-up learning. If decommissioning the disposable environment later, verify its identity and follow a separate, approved cleanup procedure.

### Acceptance checklist

- [ ] PostgreSQL 17 and disposable target verified.
- [ ] 200,000 synthetic rows loaded; 20,000 pending; 2,000 distinct customers.
- [ ] Baseline `EXPLAIN (ANALYZE, BUFFERS)` captured.
- [ ] Composite index created and second plan captured.
- [ ] Difference in scan, sort, buffers, and time explained without promising a fixed speedup.
- [ ] Optional partial index exercise performed or explicitly marked skipped.
- [ ] Index inventory, size, and usage queries captured.
- [ ] Broad-selectivity query discussed.
- [ ] Production change and rollback plan drafted.
- [ ] Sanitized evidence retained **only if the commands were actually run**.

**Publication status:** Authored, not executed. Independent technical review and operational certification remain pending.

## Troubleshooting

| Symptom | Safe response |
|---|---|
| `pg-fleet-lab` is absent | Follow Chapter 01 Docker setup; never redirect to a production server |
| `training_ch05` already exists | Inspect first; do not overwrite or drop automatically |
| `CREATE SCHEMA` or `CREATE TABLE` says already exists | A previous run left objects; verify their contents rather than rerunning blindly |
| `INSERT` reports 0 or unexpected count | Check whether the lab was already populated and confirm current database |
| Planner still uses Seq Scan | Compare row estimates, selectivity, and statistics; planner may be correct |
| Index build seems slow | Check container resources and storage headroom; do not kill unrelated processes |
| Plan shows many `shared hit` buffers | Shared-memory activity is not necessarily a storage problem |
| SQL output differs from examples | Treat examples as illustrative; record actual observations and version |

## Official PostgreSQL 17 references

- [EXPLAIN](https://www.postgresql.org/docs/17/sql-explain.html)
- [Using EXPLAIN](https://www.postgresql.org/docs/17/using-explain.html)
- [Index Types](https://www.postgresql.org/docs/17/indexes-types.html)
- [Multicolumn Indexes](https://www.postgresql.org/docs/17/indexes-multicolumn.html)
- [Partial Indexes](https://www.postgresql.org/docs/17/indexes-partial.html)
- [CREATE INDEX](https://www.postgresql.org/docs/17/sql-createindex.html)
- [Examining Index Usage](https://www.postgresql.org/docs/17/indexes-examine.html)
