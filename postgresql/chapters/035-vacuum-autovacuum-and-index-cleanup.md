# Chapter 035 — VACUUM, Autovacuum and Index Cleanup

**Audience:** DBRE/SRE. **Baseline:** PostgreSQL 18. **Outcome:** diagnose dead-tuple accumulation and autovacuum lag, perform bounded maintenance, and preserve transaction-ID safety.

## 1. Why VACUUM exists

PostgreSQL MVCC leaves obsolete row versions after UPDATE and DELETE. Plain `VACUUM` makes reclaimable space available for reuse, updates visibility-map information and may clean dead index entries. It does **not** generally return heap or index space to the filesystem. `VACUUM FULL` rewrites a table, needs an ACCESS EXCLUSIVE lock and extra disk, and is unsuitable as a routine online cleanup.

`VACUUM (ANALYZE)` combines dead-tuple cleanup with planner-statistics refresh. `ANALYZE` alone updates planner statistics but does not remove dead tuples.

VACUUM can be prevented from removing still-visible-to-old-snapshots row versions by long transactions, prepared transactions, replication slots and standby feedback. Distinguish slow vacuum from vacuum that cannot advance its cleanup horizon.

## 2. Read-only triage

```sql
SELECT now() AS sampled_at, datname, age(datfrozenxid) AS xid_age,
       mxid_age(datminmxid) AS multixact_age
FROM pg_database WHERE datallowconn ORDER BY age(datfrozenxid) DESC;

SELECT schemaname, relname, n_live_tup, n_dead_tup,
       last_vacuum, last_autovacuum, vacuum_count, autovacuum_count,
       last_analyze, last_autoanalyze
FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 30;

SELECT pid, datname, usename, state, xact_start, backend_xmin,
       wait_event_type, wait_event
FROM pg_stat_activity
WHERE xact_start IS NOT NULL ORDER BY xact_start LIMIT 30;
```

`n_dead_tup` and `n_live_tup` are estimates; `last_autovacuum` being NULL does not prove autovacuum is disabled. Look at table creation, workload, resets, thresholds, partitions and statistics timing. For large partitioned structures inspect each leaf partition, not just the parent.

## 3. Autovacuum trigger and tuning

The usual dead-tuple trigger combines a fixed threshold and a scale factor applied to estimated relation tuples. PostgreSQL 18 also provides insert-triggered vacuum and max-threshold controls. Check actual values with `pg_settings` and table `reloptions` rather than assuming defaults.

```sql
SELECT name, setting, unit, source
FROM pg_settings
WHERE name IN ('autovacuum', 'autovacuum_vacuum_threshold',
'autovacuum_vacuum_scale_factor', 'autovacuum_vacuum_max_threshold',
'autovacuum_analyze_threshold', 'autovacuum_analyze_scale_factor',
'autovacuum_max_workers', 'autovacuum_naptime',
'autovacuum_vacuum_cost_limit', 'autovacuum_vacuum_cost_delay',
'autovacuum_freeze_max_age')
ORDER BY name;
```

For a large, high-churn table, a table-specific threshold can improve maintenance responsiveness:

```sql
ALTER TABLE app.orders SET (
  autovacuum_vacuum_scale_factor = 0.02,
  autovacuum_vacuum_threshold = 1000
);
-- Rollback after approval: ALTER TABLE app.orders RESET
-- (autovacuum_vacuum_scale_factor, autovacuum_vacuum_threshold);
```

These are illustrative, **not universal recommendations**. Model actual update/delete rates, relation size, I/O headroom, vacuum duration and worker concurrency. Too-aggressive settings can overload disks; too-relaxed settings can increase dead tuples and wraparound risk. Autovacuum can launch anti-wraparound work even if ordinary autovacuum is disabled; do not attempt to disable anti-wraparound protection.

## 4. Index cleanup and VACUUM options

VACUUM may remove dead entries from indexes and reclaim reusable index pages. Index vacuuming can dominate maintenance time on heavily indexed tables. PostgreSQL exposes `INDEX_CLEANUP` choices such as AUTO, ON and OFF. `INDEX_CLEANUP OFF` can be useful for carefully justified emergency maintenance, but repeatedly skipping index cleanup allows index garbage to accumulate; PostgreSQL can override this for wraparound protection. It is not a routine performance optimization.

```sql
VACUUM (VERBOSE, ANALYZE, INDEX_CLEANUP AUTO) app.orders;
```

Use `VACUUM (DISABLE_PAGE_SKIPPING)` only for a specific diagnostic or recovery reason, not as a default. `VACUUM FULL` rewrites the table and requires a separately approved outage/lock and storage budget. For index-specific rebuild decisions see Chapters 033–034.

## 5. Progress, blocking and I/O impact

```sql
SELECT p.pid, p.relid::regclass AS relation, p.phase,
       p.heap_blks_total, p.heap_blks_scanned, p.heap_blks_vacuumed,
       p.index_vacuum_count, p.num_dead_item_ids,
       a.wait_event_type, a.wait_event
FROM pg_stat_progress_vacuum p
LEFT JOIN pg_stat_activity a USING (pid);
```

Progress counters describe phases, not a universal percent complete. Also monitor WAL generation, disk latency, replica lag, oldest snapshots, autovacuum worker utilization and the visibility map. A regular VACUUM normally coexists with DML, but it still consumes resources and takes locks that can conflict with DDL.

## 6. Freeze and wraparound risk

Vacuum freezes sufficiently old transaction IDs and multixact IDs so tuple visibility remains safe. Track `age(datfrozenxid)` and `mxid_age(datminmxid)`, compare against configured thresholds, and investigate tables with old `relfrozenxid`/`relminmxid`. If approaching anti-wraparound limits, prioritize preservation of data availability, identify blockers and follow an approved incident runbook. Do not indiscriminately terminate sessions or change freeze settings.

Read-only table-age inspection:

```sql
SELECT n.nspname, c.relname, age(c.relfrozenxid) AS xid_age,
       mxid_age(c.relminmxid) AS mxid_age
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE c.relkind IN ('r','m','t') AND n.nspname NOT IN ('pg_catalog','information_schema')
ORDER BY age(c.relfrozenxid) DESC LIMIT 30;
```

## 7. Production incident runbook

1. **Observe:** capture incident window, application SLOs, table sizes, dead-tuple estimates, XID/multixact age, vacuum progress and wait events.
2. **Classify:** insufficient autovacuum cadence, resource starvation, blocked cleanup horizon, excessive indexes, large transaction bursts, or anti-wraparound urgency.
3. **Protect:** confirm free disk/WAL, replica health, backup/recovery status and maintenance window.
4. **Mitigate:** address root blockers with owner approval; use targeted plain VACUUM/ANALYZE when justified; avoid defaulting to VACUUM FULL or REINDEX.
5. **Validate:** compare dead tuples, progress, age, query plans, write latency, disk/WAL and replica lag over a meaningful window.
6. **Prevent:** document per-table threshold rationale, monitor worker saturation and long-running transactions, and establish alert thresholds with headroom.

## 8. Hands-on lab

[Chapter 035 lab](../labs/035-vacuum-autovacuum-and-index-cleanup-lab.md) creates a disposable table, generates bounded churn, inspects autovacuum configuration and progress, runs VACUUM with index cleanup, and restores its isolated schema. It cannot reliably force autovacuum to run on demand or demonstrate real wraparound risk; those require separately designed environments.

**Acceptance:** explain VACUUM versus VACUUM FULL; capture before/after dead-tuple estimates and sizes; identify long-snapshot risk; document safe per-table threshold rollback; verify cleanup. **Validation:** authored and structurally reviewed; PostgreSQL 18 runtime verification pending.

## PostgreSQL 18 references

- [Routine vacuuming](https://www.postgresql.org/docs/18/routine-vacuuming.html)
- [VACUUM](https://www.postgresql.org/docs/18/sql-vacuum.html)
- [Progress reporting](https://www.postgresql.org/docs/18/progress-reporting.html)
- [Monitoring statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [Storage HOT](https://www.postgresql.org/docs/18/storage-hot.html)

**Next:** Chapter 036 — Autovacuum Tuning, Freeze and Wraparound Incident Response.
