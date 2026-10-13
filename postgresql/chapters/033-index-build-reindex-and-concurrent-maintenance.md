# Chapter 033 — Index Build, Reindex and Concurrent Maintenance

**Audience:** DBRE/SRE. **Baseline:** PostgreSQL 18. **Outcome:** select, execute, observe and recover index maintenance with explicit lock, capacity and rollback controls.

## 1. Decide why maintenance is needed

Identify the specific query regression, index corruption indication, excessive index size, invalid index or change requirement. Collect baseline query plans, relation and index sizes, write rates, replica lag, available disk, WAL volume and transaction age. An index with low scan counts is not automatically redundant. REINDEX is not a routine substitute for VACUUM or a cure for every slow query.

Read-only inventory:

```sql
SELECT n.nspname, t.relname AS table_name, i.relname AS index_name,
       pg_size_pretty(pg_relation_size(i.oid)) AS index_size,
       x.indisvalid, x.indisready, x.indislive,
       pg_get_indexdef(i.oid) AS definition
FROM pg_index x
JOIN pg_class i ON i.oid = x.indexrelid
JOIN pg_class t ON t.oid = x.indrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname = 'public'
ORDER BY pg_relation_size(i.oid) DESC;
```

Check index ownership, constraints, partitioning, dependencies and whether an invalid index still imposes write overhead. Treat catalog state as evidence, not authorization to drop.

## 2. Regular CREATE INDEX versus CONCURRENTLY

`CREATE INDEX` normally blocks writes to the target table while building (reads continue). `CREATE INDEX CONCURRENTLY` permits normal INSERT/UPDATE/DELETE activity but typically takes longer, performs multiple scans, and waits for transactions/snapshots at different stages. It can increase CPU, I/O, WAL, disk use and replication lag.

```sql
-- Maintenance window only, with approved write blocking:
CREATE INDEX ch033_orders_customer_idx ON ch033.orders (customer_id);

-- Low-write-blocking approach, executed as a standalone statement:
CREATE INDEX CONCURRENTLY ch033_orders_created_idx
ON ch033.orders (created_at);
```

`CREATE INDEX CONCURRENTLY` cannot run inside an explicit transaction block or a multi-command transaction wrapper. Concurrent builds cannot be run simultaneously on the same table. A unique concurrent index can begin enforcing uniqueness before the index becomes valid; failures may leave an invalid index that continues enforcing uniqueness. Never assume a failed command means no side effects.

## 3. REINDEX choices

```sql
-- Blocks writes; use an approved maintenance window:
REINDEX INDEX ch033.orders_created_idx;

-- Lower-write-blocking replacement, standalone statement:
REINDEX INDEX CONCURRENTLY ch033.orders_created_idx;
```

`REINDEX` rebuilds existing index contents and can help when an index is bloated or must be rebuilt for supported operational reasons. `REINDEX CONCURRENTLY` uses a replacement-and-swap workflow with additional resource and waiting costs; not all index types or contexts support concurrent reindexing. Check PostgreSQL 18 restrictions before applying to system catalogs, partitioned relations, exclusion constraints or specialized index definitions. Reindexing does not rewrite heap tuples or automatically reclaim table bloat.

Prefer the narrowest object scope. `REINDEX TABLE`, `REINDEX SCHEMA` and `REINDEX DATABASE` have broader impact than a single index; assess each target and mode separately. A constraint-backed index needs special care: do not casually DROP it to repair a uniqueness or primary-key problem.

## 4. Progress and blocking visibility

```sql
SELECT p.pid, p.command, p.phase, p.relid::regclass AS table_name,
       p.index_relid::regclass AS index_name,
       p.blocks_done, p.blocks_total, p.tuples_done, p.tuples_total,
       p.lockers_done, p.lockers_total, p.current_locker_pid,
       a.wait_event_type, a.wait_event
FROM pg_stat_progress_create_index p
LEFT JOIN pg_stat_activity a USING (pid);
```

Progress counters are phase-dependent and are not a universal percent-complete indicator. Investigate waits with `pg_blocking_pids(pid)`, `pg_stat_activity`, `pg_locks` and oldest transactions. Avoid killing application backends automatically. Coordinate cancellation with the change owner, then inspect index validity and replacement artifacts.

## 5. Preflight, execution and acceptance

| Stage | DBRE/SRE checkpoint |
|---|---|
| Preflight | Confirm index definition, target table, dependencies, free space, WAL/replica headroom and long transactions |
| Safety | Approved window, query/load baseline, timeouts, operator identity, monitoring and rollback owner |
| Execution | Run one standalone DDL at a time; capture start/end, PID, progress, waits and replica lag |
| Postflight | Check `indisvalid`, `indisready`, plans, write latency, disk/WAL, replication and application errors |
| Recovery | If invalid artifacts remain, inspect exact object identity/dependencies; choose approved retry or removal |

**Capacity:** A rebuild can temporarily require space for the new index while the old one remains; budget additional WAL, temporary files and replication retention. Exact requirements depend on index size, workload, access method and concurrent operations. Do not treat available table free space as sufficient evidence.

**Timeouts:** Set an appropriate `lock_timeout` and `statement_timeout` per change plan. A short `lock_timeout` can intentionally fail a concurrent build while it waits; do not confuse that with a harmless no-op. Confirm `idle_in_transaction_session_timeout` and connection-pool behavior.

## 6. Failure and rollback runbook

1. Stop initiating additional DDL. Record SQLSTATE, PID, logs, target definition and current phase.
2. Check `pg_index.indisvalid/indisready`, `pg_class`, constraint dependencies, `pg_stat_progress_create_index`, and any `_ccnew`/`_ccold` artifacts before acting.
3. For a failed *non-constraint* `CREATE INDEX CONCURRENTLY`, a verified invalid index may be removed with `DROP INDEX CONCURRENTLY` in a standalone statement, then retried after addressing the root cause. Do not drop an index backing a constraint or one still serving a valid access path without approval.
4. For failed `REINDEX CONCURRENTLY`, follow the PostgreSQL-documented cleanup path appropriate to the specific surviving old/new indexes. Do not blindly drop names based on suffix alone.
5. Recheck application writes, plans, disk, WAL and replicas. Record rollback outcome and whether the original index remains valid.

**Cancellation:** `pg_cancel_backend` can interrupt a running build, but cancellation does not guarantee automatic cleanup of all invalid artifacts. Avoid `pg_terminate_backend` unless escalation is approved and session identity is verified.

## 7. Hands-on lab and acceptance

Run [Chapter 033 lab](../labs/033-index-build-reindex-and-concurrent-maintenance-lab.md) on a disposable PostgreSQL 18 database. It exercises ordinary and concurrent builds, progress observation, concurrent reindex, a deliberately failed unique concurrent build, safe invalid-index cleanup and final schema removal.

Acceptance evidence: baseline and final definitions, progress observations, exact failure SQLSTATE, invalid-index inspection, verified cleanup, correct query results and recorded operational risk assessment. Timing and blocking vary with host workload; a short lab may complete before progress polling catches it.

**Validation:** Content and scripts authored; actual PostgreSQL 18 runtime execution pending.

## Official PostgreSQL 18 references

- [CREATE INDEX](https://www.postgresql.org/docs/18/sql-createindex.html)
- [REINDEX](https://www.postgresql.org/docs/18/sql-reindex.html)
- [DROP INDEX](https://www.postgresql.org/docs/18/sql-dropindex.html)
- [Index build progress](https://www.postgresql.org/docs/18/progress-reporting.html#CREATE-INDEX-PROGRESS-REPORTING)
- [Monitoring statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)

**Next:** Chapter 034 — Index Bloat, Usage and Lifecycle Decisions.
