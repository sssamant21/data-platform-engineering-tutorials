# Chapter 088 — PostgreSQL Storage Growth, Retention and Lifecycle Optimization

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Forecast, control and safely reclaim PostgreSQL storage while preserving application correctness, retention obligations, backups and disaster recovery. Build on [Chapter 086 — Capacity and FinOps](086-postgresql-capacity-forecasting-cost-optimization-and-finops.md) and [Chapter 087 — Workload and Stress Testing](087-postgresql-workload-forecasting-performance-baselines-and-capacity-stress-testing.md).

**Key distinction:** ordinary `VACUUM` makes dead tuple space reusable within relations; it generally does not return relation-file space to the filesystem. `VACUUM FULL` rewrites the relation, requires an ACCESS EXCLUSIVE lock and temporary free space.

## 2. Storage components

```text
Database storage
  ├─ heap tables + free space/dead tuples
  ├─ indexes (including bloat)
  ├─ TOAST tables and their indexes
  ├─ temporary files
  ├─ WAL and replication-slot retention
  ├─ system catalogs and auxiliary forks
  └─ tablespaces / filesystem allocation
Outside data files: backups, WAL archive, snapshots and replicas
```

`pg_total_relation_size` includes a relation's indexes and TOAST; `pg_relation_size` measures a selected relation fork (main by default). Avoid summing overlapping size functions as if they were independent components.

## 3. Read-only inventory

Use [088 storage inspection SQL](../labs/sql/088-storage-lifecycle-inspect.sql). Key queries:

```sql
SELECT schemaname,relname,
       pg_size_pretty(pg_table_size(relid)) AS table_including_toast,
       pg_size_pretty(pg_indexes_size(relid)) AS indexes,
       pg_size_pretty(pg_total_relation_size(relid)) AS total,
       n_live_tup,n_dead_tup,last_autovacuum
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC LIMIT 20;
```

`n_live_tup` and `n_dead_tup` are estimates, not exact counts. Collect timestamped samples, including relation size, filesystem free space, WAL size, archive/slot health and statistics resets.

## 4. Growth forecasting

Track data growth by tenant, partition, table, index and TOAST. Separate net new business data from churn and maintenance overhead.

```text
Net growth = new data + new indexes + retained versions - genuinely reclaimed disk
Forecast used(t) = current used + measured net growth per period × t
Safe usable capacity = provisioned capacity - reserved maintenance/WAL/restore headroom
```

Model linear, compound and step-change scenarios. Reindex, table rewrites and logical migrations can require substantial temporary disk, often before any space is reclaimed. Forecast based on measured growth and the storage tier's scaling lead time.

## 5. MVCC, autovacuum and bloat

UPDATE/DELETE create obsolete row versions. Autovacuum removes dead tuples when safe and advances transaction ID freeze horizons. Long transactions, idle-in-transaction sessions, replication feedback and other retention horizons can delay cleanup.

**Do not disable autovacuum as a storage optimization.** Inspect XID age, table-level vacuum statistics, long-running transactions and `pg_stat_progress_vacuum`. Tune per-table autovacuum thresholds only after measuring write churn and capacity.

## 6. Reclaim methods and tradeoffs

| Method | What it does | Key risk |
|---|---|---|
| Regular VACUUM | Marks dead tuple space reusable; updates visibility map | I/O and WAL; limited filesystem shrink |
| VACUUM (ANALYZE) | VACUUM plus planner statistics | I/O and lock interaction |
| VACUUM FULL | Rewrites relation, can shrink file | ACCESS EXCLUSIVE lock, large scratch space |
| REINDEX CONCURRENTLY | Rebuilds eligible indexes with reduced write blocking | Additional disk, long runtime, invalid artifacts on failure |
| CLUSTER | Physically rewrites table by index order | Heavy locks and rewrite |
| Partition DROP after retention approval | Removes whole partition files | Destructive; backup/legal hold concerns |
| pg_repack (third-party) | Online-ish rewrite using extension tooling | Extension support, triggers, disk, operational risk |

Reclaim choice must be justified by a measurable storage or performance benefit. Never blanket-reindex or force VACUUM FULL in production as routine cleanup.

## 7. Partitioning and retention

Partition large time-series tables when pruning and lifecycle operations justify the complexity. Design partition keys, indexes, constraints, future partition creation, and retention automation before ingest.

A safe retention pipeline:
1. Identify partitions beyond retention and check actual bounds.
2. Verify policy, legal holds, application dependencies and downstream CDC/ETL consumers.
3. Validate backup/archive export and restore ability.
4. Prepare an immutable manifest of approved partitions.
5. Detach/drop only through reviewed DDL with lock and timeout controls.
6. Verify catalog, row visibility, application queries, backups and metrics.

**Partition removal is data deletion.** A dry-run candidate list is not authorization to drop data. `DETACH PARTITION CONCURRENTLY` has PostgreSQL restrictions and cannot be treated as universally supported for all partition layouts.

## 8. WAL, archive and replication slots

WAL storage can grow independently of relation data. Monitor `pg_stat_wal`, `pg_stat_archiver`, replication slots, `pg_wal` filesystem utilization and replica replay/receive lag. A stalled logical slot can retain WAL indefinitely when no effective limit applies; `max_slot_wal_keep_size` can limit retention but risks making the slot unusable and requiring consumer recovery.

Never delete WAL files manually or drop a production slot solely to recover disk without evaluating replication, CDC and PITR impact. Archival retention and backup retention are separate policies.

## 9. TOAST, indexes and temporary files

Wide rows can move values to TOAST storage. Measure table size, index size and TOAST contribution before changing schema or compression. Monitor `temp_bytes` deltas and disk headroom; large sorts/hashes may spill under load. Indexes accelerate reads but increase writes, WAL and storage. Remove unused indexes only after workload-wide analysis and dependency checks.

## 10. Capacity and FinOps controls

Track GiB-month of provisioned storage, IOPS/throughput tier, backup/archive/snapshot storage, replica duplication and network transfer. Rightsizing a volume can be difficult or impossible without migration depending on provider. Do not assume logical free space inside PostgreSQL reduces cloud provisioned-storage charges.

Use alert thresholds based on **time-to-full**, peak growth, WAL/slot exposure and maintenance scratch requirements rather than a single fixed percentage.

## 11. Incident response

**Disk nearing full:** capture mount/volume, PostgreSQL relation growth, WAL/slot/archiver, temp files and free space. Stop optional bulk jobs, protect backup/replication, add capacity through approved scaling and resolve the cause. Avoid emergency `VACUUM FULL` when disk is already exhausted.

**Retention failure:** halt destructive steps, preserve manifests, verify affected partitions/backup, notify data owners and initiate restore if needed.

**Unexpected bloat:** inspect autovacuum, long transactions, update churn and indexes; choose a bounded remediation after checking locks and disk.

## 12. Lab and acceptance

Use [Chapter 088 lab](../labs/088-postgresql-storage-growth-retention-and-lifecycle-optimization-lab.md), [inspection SQL](../labs/sql/088-storage-lifecycle-inspect.sql), [retention manifest](../labs/retention/088-partition-retention-manifest.csv), and [acceptance scorecard](../labs/acceptance/088-storage-lifecycle-scorecard.csv).

**PASS requires:** complete size inventory, measured growth, validated reclaim method, approved retention and archive proof, WAL/slot safety, capacity headroom, postchange application tests and rollback/restore evidence. Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/diskusage.html
- https://www.postgresql.org/docs/18/routine-vacuuming.html
- https://www.postgresql.org/docs/18/sql-vacuum.html
- https://www.postgresql.org/docs/18/ddl-partitioning.html
- https://www.postgresql.org/docs/18/monitoring-stats.html

**Next:** Chapter 089 — PostgreSQL Cloud Cost Governance, Rightsizing and FinOps Acceptance Project.
