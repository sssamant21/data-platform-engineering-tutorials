# Chapter 036 — Autovacuum Tuning, Freeze and Wraparound Incident Response

**Audience:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Authored; runtime verification pending

## 1. Operational mission

Prevent vacuum starvation and transaction-ID/multixact wraparound while preserving query latency, write throughput and replication health. Learn to calculate vacuum triggers, diagnose workers and cleanup horizons, tune per-table settings, monitor freeze age, and respond safely to anti-wraparound emergencies.

**Critical:** Wraparound protection is a data-integrity safeguard, not a tuning option. Never disable anti-wraparound protection or deliberately age a production database to test it.

## 2. Vacuum triggers and statistics

Ordinary dead-tuple autovacuum thresholds are influenced by `autovacuum_vacuum_threshold`, `autovacuum_vacuum_scale_factor`, and `autovacuum_vacuum_max_threshold` (when applicable). The trigger uses estimated relation size and change counters; actual behavior also includes insert-triggered vacuum and freeze-driven work. `ANALYZE` has its own thresholds. Read effective settings and table reloptions before calculating a candidate trigger.

```sql
SELECT name, setting, unit, source
FROM pg_settings
WHERE name LIKE 'autovacuum%' OR name IN
('vacuum_freeze_min_age','vacuum_freeze_table_age',
 'vacuum_multixact_freeze_min_age','vacuum_multixact_freeze_table_age')
ORDER BY name;

SELECT n.nspname, c.relname, c.reltuples::bigint AS estimated_rows, c.reloptions,
       s.n_dead_tup, s.n_ins_since_vacuum, s.n_mod_since_analyze,
       s.last_autovacuum, s.autovacuum_count
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
LEFT JOIN pg_stat_all_tables s ON s.relid=c.oid
WHERE c.relkind='r' AND n.nspname NOT IN ('pg_catalog','information_schema')
ORDER BY s.n_dead_tup DESC NULLS LAST LIMIT 30;
```

A simple **illustrative** threshold for a table with 10 million estimated rows, fixed threshold 1,000 and scale factor 0.02 is approximately 201,000 dead tuples, subject to configured maximums and other triggers. Do not equate this estimate with exact scheduling or worker start time.

## 3. Worker concurrency and I/O

Autovacuum workers share server resources with application queries. Review `autovacuum_max_workers`, `autovacuum_worker_slots` where available, `autovacuum_naptime`, cost delay/limit, per-table storage parameters, CPU and disk headroom. PostgreSQL 18 has version-specific worker controls; verify settings against the running server.

Tuning matrix:

| Signal | Potential issue | Investigation |
|---|---|---|
| Dead tuples rise across many tables | Worker saturation or slow vacuum | Active workers, I/O, autovacuum logs |
| One high-churn table grows | Per-table threshold too high | Estimate trigger, update rate, duration |
| Workers run but make little progress | Old snapshots or I/O bottleneck | Backend xmin, replication slots, standby feedback |
| Replication lag increases during vacuum | WAL/IO contention | WAL generation, replay lag, slots |
| Freeze age grows steadily | Vacuum cannot keep up or is blocked | Database and relation ages, anti-wraparound status |

Do not globally increase concurrency or remove cost delays without testing; higher worker counts can amplify storage contention.

## 4. Per-table change with rollback

```sql
-- Example only: approve based on observed churn and capacity
ALTER TABLE app.events SET (
  autovacuum_vacuum_threshold = 1000,
  autovacuum_vacuum_scale_factor = 0.02,
  autovacuum_analyze_scale_factor = 0.01
);

-- Explicit rollback
ALTER TABLE app.events RESET (
  autovacuum_vacuum_threshold,
  autovacuum_vacuum_scale_factor,
  autovacuum_analyze_scale_factor
);
```

Record the original `reloptions` **before** changing them. RESET removes the override; it is not necessarily an exact restoration if a preexisting override was present. For a production rollback, restore the captured original values individually.

## 5. Freeze and wraparound mechanics

PostgreSQL uses 32-bit transaction IDs with wraparound-safe comparisons and freezing to preserve visibility. The database `datfrozenxid` and table `relfrozenxid` summarize old XID horizons; multixact IDs have a separate lifecycle. `autovacuum_freeze_max_age` and `autovacuum_multixact_freeze_max_age` govern anti-wraparound activity; they are not targets to approach.

```sql
SELECT datname, age(datfrozenxid) AS xid_age,
       mxid_age(datminmxid) AS multixact_age
FROM pg_database
WHERE datallowconn
ORDER BY age(datfrozenxid) DESC;

SELECT n.nspname, c.relname, age(c.relfrozenxid) AS xid_age,
       mxid_age(c.relminmxid) AS multixact_age,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE c.relkind IN ('r','m','t')
  AND n.nspname NOT IN ('pg_catalog','information_schema')
ORDER BY age(c.relfrozenxid) DESC LIMIT 30;
```

Watch both XID and multixact ages, especially during sustained write workloads. Freeze thresholds and age values require interpretation with the server's actual configuration and the PostgreSQL version. Database age can reflect a different relation than the current largest table.

## 6. Cleanup horizon blockers

```sql
SELECT pid, datname, usename, state, xact_start, backend_xmin,
       wait_event_type, wait_event
FROM pg_stat_activity
WHERE xact_start IS NOT NULL OR backend_xmin IS NOT NULL
ORDER BY xact_start NULLS LAST LIMIT 40;

SELECT slot_name, slot_type, active, xmin, catalog_xmin,
       restart_lsn, confirmed_flush_lsn
FROM pg_replication_slots;
```

Long-running transactions, prepared transactions, logical slots and hot-standby feedback can retain old row versions or horizons. Inspect `pg_prepared_xacts` and `pg_stat_replication` when relevant. Not every slot blocks vacuum; interpret non-null `xmin`/`catalog_xmin` and retention behavior. Do not drop replication slots, cancel business transactions or disable `hot_standby_feedback` without understanding replication and data-loss consequences.

## 7. Vacuum progress and anti-wraparound evidence

```sql
SELECT p.pid, p.relid::regclass AS relation, p.phase,
       p.heap_blks_total, p.heap_blks_scanned,
       p.heap_blks_vacuumed, p.index_vacuum_count,
       a.query, a.wait_event_type, a.wait_event
FROM pg_stat_progress_vacuum p
LEFT JOIN pg_stat_activity a USING (pid);
```

Check autovacuum log messages for wraparound-prevention activity and stalls. A high phase-specific progress count is not proof that freezing has advanced. Correlate age changes after completion and across all at-risk relations.

## 8. Incident severity and runbook

**Warning:** age is trending toward configured freeze thresholds, or autovacuum backlog is rising. **Critical:** anti-wraparound work repeatedly fails, XID/multixact age approaches safety limits, or writes are threatened. Set site-specific thresholds with substantial headroom, not a hardcoded universal percentage.

1. Capture time, server version, `pg_settings`, ages, affected relations, vacuum workers, logs, free disk/WAL, replica health and application symptoms.
2. Identify long snapshots, prepared transactions, replication feedback, slots, resource saturation, locks and vacuum cancellation history.
3. Escalate early. Preserve backups and replication recovery options; prioritize maintaining the ability to write safely.
4. Resolve blockers only with verified session/slot ownership and approval. Prefer bounded targeted maintenance when safe. Anti-wraparound vacuum may ignore some normal cost limits; do not interrupt it casually.
5. If database writes have already been restricted due to wraparound safeguards, follow PostgreSQL's documented emergency procedure and involve experienced operators. Do not suggest resetting XIDs, changing system catalogs or bypassing safety controls.
6. Confirm age reduction and healthy vacuum completion, plus query/write latency, disk, WAL, replicas and recurring worker capacity. Write an RCA with preventive alerts and ownership.

## 9. Lab and acceptance

[Chapter 036 hands-on lab](../labs/036-autovacuum-tuning-freeze-and-wraparound-incident-response-lab.md) uses safe synthetic churn, a per-table tuning/rollback exercise, XID-age inspection and an incident decision worksheet. It **does not** simulate actual wraparound.

**Acceptance:** calculate approximate trigger, capture age baselines, identify cleanup blockers, verify per-table rollback and explain safe escalation. **Validation:** authored; PostgreSQL 18 runtime execution pending.

## Official references

- [Routine vacuuming and wraparound](https://www.postgresql.org/docs/18/routine-vacuuming.html)
- [Autovacuum settings](https://www.postgresql.org/docs/18/runtime-config-autovacuum.html)
- [VACUUM](https://www.postgresql.org/docs/18/sql-vacuum.html)
- [Progress reporting](https://www.postgresql.org/docs/18/progress-reporting.html)
- [Monitoring statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)

**Next:** Chapter 037 — Table and Index Maintenance Strategy.
