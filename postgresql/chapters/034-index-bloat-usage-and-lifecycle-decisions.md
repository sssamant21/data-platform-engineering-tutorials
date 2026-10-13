# Chapter 034 — Index Bloat, Usage and Lifecycle Decisions

**Audience:** DBRE/SRE. **Baseline:** PostgreSQL 18. **Outcome:** distinguish legitimate index growth from waste, interpret usage evidence, and make safe retain/rebuild/consolidate/retire decisions.

## 1. Operational decision framework

Index storage is not automatically bloat. An index can be large because it supports a large table, wide keys, INCLUDE payload, low deduplication opportunities, fillfactor or workload history. Dead entries, page splits and free space may increase size; PostgreSQL's B-tree bottom-up deletion and deduplication can mitigate some churn. **Do not derive a precise bloat percentage from `pg_relation_size` or dead-tuple counts alone.**

A decision requires: (1) query/constraint purpose, (2) usage across a representative window, (3) physical size and growth, (4) write/maintenance cost, (5) dependency and rollback feasibility, and (6) business SLO impact.

| Observation | Interpretation | Next action |
|---|---|---|
| Large index, high-value selective access | Could be healthy | Retain; investigate actual plan and size trend |
| Low `idx_scan` since recent stats reset | Inconclusive | Extend measurement window and inspect constraints |
| Index size rising faster than live rows | Possible churn or wider keys | Inspect workload, page density, updates, vacuum history |
| Duplicative prefix index | Potential consolidation | Compare plans and ORDER BY needs before removing |
| Invalid index | May consume writes/storage without planner use | Inspect constraint/dependency and Chapter 033 recovery |
| Sustained space pressure with verified waste | Candidate for rebuild | Budget temporary disk/WAL, choose safe maintenance mode |

## 2. Read-only inventory and reset-aware usage

```sql
SELECT current_database() AS db, stats_reset
FROM pg_stat_database WHERE datname = current_database();

SELECT s.schemaname, s.relname AS table_name, s.indexrelname AS index_name,
       s.idx_scan, s.idx_tup_read, s.idx_tup_fetch,
       pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size,
       i.indisvalid, i.indisready, i.indisunique, i.indisprimary,
       pg_get_indexdef(s.indexrelid) AS definition
FROM pg_stat_user_indexes s
JOIN pg_index i ON i.indexrelid = s.indexrelid
ORDER BY pg_relation_size(s.indexrelid) DESC;
```

`idx_scan` is an accumulated counter since the relevant statistics reset, **not** a count of application requests. One SQL statement may initiate multiple index scans. `idx_tup_read` and `idx_tup_fetch` are different metrics; index-only scans and bitmap scans complicate interpretation. `pg_stat_user_indexes` excludes system indexes. Never label a zero-scan index unused without examining window, constraints, query patterns, seasonal jobs and standby reads (which are not captured as usage on the primary).

Capture two samples and compare deltas; account for restarts, statistics reset, index replacement (new OID), role and monitoring coverage. `pg_stat_all_tables.n_dead_tup` is an estimate of **table** dead tuples, not an index bloat measurement.

## 3. Physical evidence and bloat diagnostics

```sql
SELECT c.oid::regclass AS relation, pg_size_pretty(pg_relation_size(c.oid)) AS bytes,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total_relation_bytes
FROM pg_class c
WHERE c.oid = 'ch034.events'::regclass;
```

`pg_relation_size(index)` measures the index's main fork size; `pg_total_relation_size(table)` includes indexes and auxiliary storage. Do not add them together as though they were independent.

For an approved deeper investigation, `pgstattuple` extension functions such as `pgstatindex` (B-tree only) can expose page density, deleted and empty pages. Installation may require privileges and a change process; scans consume I/O and can be expensive. Low leaf density alone is not definitive proof of actionable bloat, particularly with recent splits or configured fillfactor. Review PostgreSQL 18 documentation and measure repeatedly.

Example (only if extension is installed and approved):

```sql
SELECT * FROM pgstatindex('ch034.events_customer_idx'::regclass);
```

Treat index-size trend and page-density diagnostics as supporting evidence, not an automatic REINDEX trigger.

## 4. Why index count affects writes

Every applicable index can add INSERT cost, WAL, storage, checkpoint work, backup volume and maintenance overhead. UPDATEs may need index changes when indexed values change or when HOT update is unavailable; DELETEs leave cleanup work. Excessive indexes can increase vacuum and replication cost. A larger index is not always slower; buffer residency and access patterns matter.

Use `pg_stat_user_tables.n_tup_hot_upd`, `n_tup_upd`, `n_dead_tup`, vacuum timestamps, WAL rate, write latency and representative plans as a correlated picture. A HOT ratio can change for reasons other than index count, including page free space and which columns are updated.

## 5. Safe index retirement

Before removal:

1. Confirm exact index definition, access method, columns, expressions, predicate, INCLUDE payload, ordering and collation.
2. Check `pg_constraint.conindid`, uniqueness, primary key, exclusion and other dependencies. A constraint-backed index must not be treated as an optional performance index.
3. Compare all candidate query shapes, including background jobs, rarely used paths, prepared statements and replica workloads. Query statistics are supporting evidence, not a complete workload inventory.
4. Validate that an alternative index really supports the needed filters and ordering; a composite prefix is not automatically interchangeable in both directions.
5. Agree on a rollback plan, saved DDL, disk/WAL budget, observation window and deployment owner.

`DROP INDEX CONCURRENTLY` can reduce write blocking but must be a standalone command; it has restrictions (including no CASCADE and no constraint-backed index removal). It is **not a reversible toggle**: recreating an index takes time and resources. Production removal requires an approved change, with a validated restore definition and realistic recovery time.

## 6. Rebuild versus retain versus redesign

- **Retain:** access path is important, size is proportionate and write costs acceptable.
- **Rebuild:** evidence of reclaimable index waste or index repair need; assess `REINDEX INDEX CONCURRENTLY` restrictions and temporary resource headroom (Chapter 033).
- **Redesign:** wrong key order, over-wide INCLUDE columns, ineffective partial predicate, poor partitioning alignment or redundant indexes; benchmark replacement before removal.
- **Retire:** proven no dependency and low value across a representative workload, with approved rollback.
- **Defer:** insufficient statistics window, unclear standby usage, unknown application owner or inadequate free space.

Avoid automatic thresholds such as “reindex at 20% bloat” or “drop after 30 days without scans.” Choose workload-specific evidence and SLOs.

## 7. Incident runbook and acceptance

**Incident:** disk pressure and index growth. First check disk/replication safety, long transactions, autovacuum progress, index sizes and growth. Do not launch concurrent reindex when free space or WAL retention is insufficient. Escalate to capacity mitigation and controlled maintenance planning.

**Lab:** [Chapter 034 — Index Bloat, Usage and Lifecycle Lab](../labs/034-index-bloat-usage-and-lifecycle-decisions-lab.md) uses a disposable schema to compare index inventory and workload changes, capture statistics and test reversible index replacement logic. It intentionally does **not** claim a measured bloat percentage.

**Acceptance:** evidence includes sample timestamps and reset identity, definitions/dependencies, plan comparisons, storage deltas, a justified decision per index, and a rollback record. Runtime performance results must be measured on a real PostgreSQL 18 instance.

**Validation:** Authored and structurally reviewed; PostgreSQL 18 runtime execution pending.

## Official PostgreSQL 18 references

- [Monitoring statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [Index maintenance](https://www.postgresql.org/docs/18/routine-reindex.html)
- [REINDEX](https://www.postgresql.org/docs/18/sql-reindex.html)
- [DROP INDEX](https://www.postgresql.org/docs/18/sql-dropindex.html)
- [pgstattuple](https://www.postgresql.org/docs/18/pgstattuple.html)
- [Index-only scans and HOT considerations](https://www.postgresql.org/docs/18/storage-hot.html)

**Next:** Chapter 035 — VACUUM, Autovacuum and Index Cleanup.
