# Chapter 13 — VACUUM, Autovacuum, Bloat and Maintenance

**Audience:** DBRE/SRE beginners and operators · **Duration:** 60 minutes · **Reference runtime:** PostgreSQL 17 on local Docker Desktop · **Status:** Authored; runtime validation and independent review pending.

[Learning path](../README.md) · [Master TOC](../MASTER-TOC.md) · [Chapter 13 lab](../labs/chapter-13/README.md) · [Progress](../STATUS-TRACKER.md)

## Learning objectives

After this lesson, explain why PostgreSQL creates dead row versions, what VACUUM/ANALYZE do, how autovacuum is triggered, why space is not necessarily returned to the operating system, and how to assess transaction-ID wraparound risk. Use safe, evidence-based diagnostics before proposing maintenance.

## 60-minute instructor outline

| Minutes | Topic | Outcome |
|---|---|---|
| 0–10 | MVCC, updates/deletes and dead tuples | Describe why old versions exist |
| 10–20 | VACUUM vs ANALYZE vs VACUUM FULL | Distinguish purposes and risks |
| 20–30 | Autovacuum, freezing and wraparound | Interpret thresholds and XID ages |
| 30–50 | [Isolated Chapter 13 lab](../labs/chapter-13/README.md) | Generate churn, inspect stats, run ordinary VACUUM |
| 50–60 | Incident triage and acceptance | Draft a safe maintenance recommendation |

## 1. Architecture: MVCC and row-version lifecycle

PostgreSQL's multi-version concurrency control (MVCC) lets readers see suitable row versions while writers change data. An UPDATE normally creates a new tuple version; DELETE marks an old version as no longer live once its deletion is visible. Old versions cannot be removed while they remain visible to a transaction snapshot.

~~~text
INSERT row v1 → UPDATE creates v2 → v1 becomes removable when safe
                     |
             snapshot/transaction horizon
                     |
             VACUUM reclaims reusable space
                     |
             subsequent INSERT/UPDATE may reuse it
~~~

**Important distinction:** a *dead tuple* is not a deleted application record that can always be removed immediately. Visibility and transaction horizons determine whether a row version is safe to prune. HOT (heap-only tuple) updates and page pruning may reduce index churn; their behavior depends on indexed columns, page space and workload.

## 2. VACUUM, ANALYZE and space reclamation

| Operation | Primary purpose | Locks and cost | Disk expectation |
|---|---|---|---|
| Ordinary \`VACUUM\` | Reclaim reusable space from obsolete tuples; maintain visibility map and freeze eligible XIDs | I/O and CPU; generally compatible with normal reads/writes, with some lock interactions | **Usually** makes space reusable within the relation; may truncate free tail pages |
| \`ANALYZE\` | Refresh planner statistics | Samples rows; can consume I/O | Does not reclaim dead tuple storage |
| \`VACUUM (ANALYZE)\` | Both routine cleanup and planner statistics | Combined maintenance work | Not a guaranteed filesystem shrink |
| \`VACUUM FULL\` | Rewrite and compact a relation | **ACCESS EXCLUSIVE lock**, additional temporary disk space, potentially long downtime | Can reduce relation file size; not routine maintenance |
| \`REINDEX\` / \`REINDEX CONCURRENTLY\` | Rebuild indexes for selected index problems | Different locking and resource costs | Not a substitute for heap vacuuming |

**Never schedule VACUUM FULL simply because \`n_dead_tup\` is high.** Confirm physical bloat, available disk, lock/SLO impact, table size, application workload, and a reviewed maintenance window. Routine VACUUM can also create substantial I/O and must be capacity-aware.

### Why space may not fall after VACUUM

PostgreSQL generally reuses freed pages inside tables and indexes. \`pg_total_relation_size\` includes table, indexes and TOAST storage, so a single number is not a reliable bloat percentage. Size may remain flat after successful cleanup. A true bloat estimate requires suitable evidence (for example, reviewed \`pgstattuple\` use, page-level analysis, or observed sustained growth relative to live data).

## 3. Autovacuum mechanics

The autovacuum launcher schedules workers to vacuum/analyze eligible tables. It is a core safety mechanism, **not an optional housekeeping convenience**.

A simplified UPDATE/DELETE vacuum trigger in PostgreSQL 17 is:

\`\`\`text
estimated_dead_tuple_trigger =
    autovacuum_vacuum_threshold
    + autovacuum_vacuum_scale_factor × estimated_table_rows
\`\`\`

Insert-driven vacuuming has separate thresholds. The table-specific reloptions can override cluster defaults; statistics are approximate and asynchronous. Workers and I/O budgets can limit throughput. A high-churn large table may require a smaller *per-table* scale factor after measurement, but never copy a tuning value blindly to the whole fleet.

Example: if the base threshold is 50, scale factor is 0.2 and estimated table rows are 1,000,000, the simple dead-tuple trigger is approximately **200,050** obsolete tuples. Confirm actual settings with \`SHOW\` and \`pg_class.reloptions\`; this is an illustration, not a recommendation.

### Critical failure modes

- Long-running transactions, idle-in-transaction sessions and retained snapshots can delay tuple removal.
- Replication slots, standby feedback and prepared transactions can retain horizons; assess separately before changing any of them.
- Autovacuum workers can be saturated across large/high-churn tables.
- Frequent conflicting DDL can interrupt ordinary autovacuum work.
- Poor planner statistics may cause bad plans even after dead tuples are reclaimed.
- Partitioned parents need special attention: autovacuum operates on leaf partitions, and parent-level \`ANALYZE\` may require an explicit plan.

**Do not disable autovacuum globally or on a production table as an incident workaround.** Anti-wraparound autovacuum can still be forced despite ordinary autovacuum being disabled.

## 4. XID freezing and wraparound

PostgreSQL transaction IDs are finite. VACUUM freezes sufficiently old row versions and advances table/database freeze horizons to avoid transaction ID wraparound.

- \`age(relfrozenxid)\`: approximate age of oldest remaining unfrozen XID horizon for a relation.
- \`age(datfrozenxid)\`: database-wide lower-bound age across relations.
- \`autovacuum_freeze_max_age\`: anti-wraparound maintenance threshold (not the absolute database shutdown threshold).
- \`relminmxid\` and \`datminmxid\`: separate multixact horizons; monitor where row locking is heavy.

A high or increasing XID age is a **reliability risk**, not a reason to run arbitrary aggressive commands. Capture evidence and escalate early. PostgreSQL can eventually refuse writes to protect data from wraparound.

## 5. Read-only DBRE/SRE diagnostic queries

Run only after confirming environment and privileges. These queries do not change user data.

### Table-level dead tuples, vacuum/analyze history

\`\`\`sql
SELECT schemaname, relname, n_live_tup, n_dead_tup,
       n_tup_upd, n_tup_del, n_tup_hot_upd,
       last_vacuum, last_autovacuum, vacuum_count, autovacuum_count,
       last_analyze, last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC LIMIT 20;
\`\`\`

\`n_dead_tup\` and \`n_live_tup\` are **estimates**; counters can lag and reset. Interpret with \`stats_reset\`, activity, and actual storage trends.

### Current VACUUM progress

\`\`\`sql
SELECT pid, datname, relid::regclass AS relation,
       phase, heap_blks_total, heap_blks_scanned,
       heap_blks_vacuumed
FROM pg_stat_progress_vacuum
WHERE datname = current_database();
\`\`\`

An empty result means no ordinary VACUUM is currently visible, not that maintenance is healthy or broken.

### Database XID horizon

\`\`\`sql
SELECT datname, age(datfrozenxid) AS xid_age,
       current_setting('autovacuum_freeze_max_age')::bigint AS anti_wraparound_trigger
FROM pg_database
ORDER BY age(datfrozenxid) DESC;
\`\`\`

Do not interpret this one trigger as a complete alert threshold; include age trends, multixact age, worker progress, and safety margin.

### Active transactions holding horizons

\`\`\`sql
SELECT pid, usename, datname, state,
       now() - xact_start AS xact_age,
       age(backend_xmin) AS xmin_age
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
ORDER BY xact_start;
\`\`\`

\`age(backend_xmin)\` is NULL when no xmin horizon is held. Do not terminate a backend based solely on age. Review ownership and impact first.

## 6. Practical maintenance decision tree

1. **Confirm identity and impact:** database, environment, table, business owner, symptoms, and SLO.
2. **Gather baseline:** table/index/TOAST size, row churn, \`n_dead_tup\`, vacuum history, XID age, storage growth, long transactions, replication/slots.
3. **Determine the cause:** high write churn, worker capacity, long snapshots, missing statistics, storage pressure, or actual bloat.
4. **Choose the least disruptive response:** allow autovacuum, tune a specific table after review, schedule ordinary \`VACUUM (ANALYZE)\`, or design a separate index/table rebuild if genuinely necessary.
5. **Protect production:** estimate I/O, WAL, lock duration, backup/recovery readiness, stop conditions, change window and owner approvals.
6. **Verify outcome:** maintenance completion, XID trend, live/dead estimates, query latency, application errors, disk headroom and future recurrence.
7. **Document prevention:** dashboard, actionable alerts, per-table tuning rationale, ownership and follow-up.

### Anti-patterns

- Blindly using \`VACUUM FULL\` to reclaim storage during an outage.
- Disabling autovacuum to improve latency.
- Running \`VACUUM\` inside a transaction block (PostgreSQL rejects it).
- Treating estimated dead tuples as an exact bloat percentage.
- Dropping replication slots or terminating transactions without owner approval.
- Assuming a single vacuum reduces the physical database size.

## 7. Lab and acceptance

Complete [Chapter 13 lab](../labs/chapter-13/README.md) in a dedicated PostgreSQL 17 container. The lab uses only synthetic data, generates UPDATE/DELETE churn, compares before/after statistics, executes ordinary \`VACUUM (VERBOSE, ANALYZE)\`, and examines XID horizons and maintenance settings.

**Acceptance checklist**

- [ ] Explain how MVCC creates obsolete tuple versions.
- [ ] Contrast VACUUM, ANALYZE and VACUUM FULL, including locks and space behavior.
- [ ] Interpret \`n_dead_tup\` as an estimate and explain delayed statistics.
- [ ] Explain autovacuum base threshold + scale factor and table-specific overrides.
- [ ] Inspect XID age and distinguish anti-wraparound threshold from emergency exhaustion.
- [ ] Demonstrate ordinary VACUUM in a disposable database, outside a transaction.
- [ ] Explain why filesystem storage may not decrease.
- [ ] Record sanitized execution evidence if lab was actually run.
- [ ] Write an incident-safe recommendation with owner approval and stop conditions.

**Validation boundary:** Written examples and expected outputs are not runtime evidence. No production certification is implied.

## Official PostgreSQL 17 references

- [Routine Vacuuming](https://www.postgresql.org/docs/17/routine-vacuuming.html)
- [VACUUM command](https://www.postgresql.org/docs/17/sql-vacuum.html)
- [Autovacuum configuration](https://www.postgresql.org/docs/17/runtime-config-autovacuum.html)
- [Cumulative statistics views](https://www.postgresql.org/docs/17/monitoring-stats.html)
- [Progress reporting](https://www.postgresql.org/docs/17/progress-reporting.html)
- [Storage parameters](https://www.postgresql.org/docs/17/sql-createtable.html#SQL-CREATETABLE-STORAGE-PARAMETERS)
