# Page 05 — PostgreSQL Capacity Planning, Database Growth & Cost Optimization

**Document ID:** PG-DBRE-OPS-005 | **Owner:** PostgreSQL DBRE + PLT/FIN | **Status:** DRAFT — no resizing authorized

## 1. Objectives

Forecast database/table/index/WAL/storage growth; assess PostgreSQL engine compute, connection pools, caching, read replicas and I/O; right-size self-managed or managed instances while protecting transaction SLO, peak workload, HA and backup/PITR objectives.

**Cost is subordinate to availability, data integrity and recovery headroom.** Data deletion and aggressive retention reductions are not approved cost levers.

## 2. Inventory and ownership

| Area | Required information |
|---|---|
| Server/cluster | DB provider, account, region, version, tier, primary/replicas |
| Compute | vCPU, RAM, CPU saturation, memory pressure, provider class |
| Storage | Allocated GB, used GB, free GB, WAL/temp/log/backup volumes, IOPS/throughput |
| App profile | Transactions/s, read/write mix, query p95/p99, peak/batch windows |
| Connections | max_connections, real pool usage, PgBouncer mode and saturation |
| Relations | Database, schema, table/index bytes, owner, partition strategy |
| WAL/replication | Bytes/time, archive age, slot retention, lag and catch-up speed |
| Maintenance | Dead tuples, vacuum/freeze age, checkpoint/IO impacts |
| Recovery | Backup size, archive chain, restore time, target RPO/RTO |
| Costs | Compute, disk, provisioned IO, backup/object storage, network and licensing |
| Governance | Data retention/legal holds, change approvers, budget owners |

## 3. Read-only size, workload and growth SQL

~~~~sql
-- Per-database sizes (one snapshot; no time series)
SELECT datname, pg_database_size(datname) AS database_bytes,
       pg_size_pretty(pg_database_size(datname)) AS pretty
FROM pg_database
WHERE datallowconn
ORDER BY database_bytes DESC;

-- Table + dependent index/TOAST footprint in current database
SELECT n.nspname AS schema_name,
       c.relname AS relation_name,
       pg_total_relation_size(c.oid) AS total_bytes,
       pg_table_size(c.oid) AS table_bytes,
       pg_indexes_size(c.oid) AS index_bytes
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE c.relkind='r'
  AND n.nspname NOT IN ('pg_catalog','information_schema')
ORDER BY total_bytes DESC LIMIT 50;

-- Relation index inventory
SELECT schemaname, tablename, indexname,
       pg_relation_size(indexrelid) AS index_bytes,
       idx_scan
FROM pg_stat_user_indexes
ORDER BY index_bytes DESC LIMIT 50;
~~~~

**Important:** pg_database_size and relation size metrics **exclude** WAL archives, external backups and other filesystem/provider overhead. Partition parent tables often have little own storage; sum child partitions carefully to avoid double counting. idx_scan can reset and does not prove unused indexes. Size functions on large catalogs have overhead, so sample at an approved cadence.

### CPU and transaction workload

~~~~sql
SELECT datname, numbackends, xact_commit, xact_rollback,
       blks_hit, blks_read, temp_bytes, deadlocks, stats_reset
FROM pg_stat_database WHERE datname IS NOT NULL;

SELECT state, count(*) AS sessions
FROM pg_stat_activity WHERE backend_type = 'client backend'
GROUP BY state;

SELECT slot_name, slot_type, active, restart_lsn
FROM pg_replication_slots;
~~~~

Use OS node exporter/provider CloudWatch/Azure Monitor/Cloud Monitoring for CPU, actual free disk, storage latency, throughput and hardware resource metrics. SQL counters are not host disk metrics.

## 4. Snapshot-based growth schema

Persist **daily UTC** rows keyed by provider/cluster ID, database OID/name, schema/rel OID and object creation identity where possible, timestamp, owner and collection quality.

| Field | Description |
|---|---|
| sample_time_utc | Stable daily collection point |
| cluster/provider/region | Source identity |
| database_name / database_oid | Logical DB identity |
| schema_name / relation_oid / relation_name | Table/index identity; track DROP/CREATE/RENAME |
| table_bytes, index_bytes, toast_bytes, total_bytes | Storage footprint |
| partition_parent / leaf metadata | Avoid aggregation double counting |
| wal_bytes, slot_retained_bytes | Separate WAL footprint / retention exposure |
| storage_allocated/free_bytes | Cloud/host capacity from provider |
| business_owner, retention, source | Cost and governance mapping |
| sample_quality | Complete, missing, partial, reset or failover |

### Reporting periods

Daily, weekly, calendar monthly, quarterly, semiannual and annual comparisons, each calculated from retained time-series snapshots with a consistent UTC cutoff. Report net growth, new objects, dropped/archived objects and non-table WAL/backup usage independently.

### Projection formulas

- Net logical relation growth/day = (current bytes − earlier bytes) / elapsed days.
- Baseline 30/60/90 days = current footprint + (median recent net growth/day × days).
- Physical capacity projection = logical DB footprint + index/TOAST, WAL, temp, logs, backup headroom, filesystem overhead and failover/reindex/maintenance reserve.
- Storage runway = usable free disk / conservative positive physical growth rate. Assess **primary and every replica**; do not average away one nearly full node.

**Illustrative only:** database logical footprint 2 TiB and net growth 20 GiB/day → 30-day added 600 GiB, 90-day added 1800 GiB before any WAL/archive/replica/headroom. Do not interpret as an actual current cluster forecast.

## 5. Autovacuum, index and partition capacity tradeoffs

- Track largest high-churn tables, n_dead_tup, vacuum cadence and transaction freeze age.
- Indexes improve reads but consume storage, CPU, write I/O and WAL; validate new/drop candidates with workload and business dependencies.
- Bloat estimates can be noisy and may require optional extension or offline techniques; never automatically VACUUM FULL based on n_dead_tup alone.
- Prefer safe targeted regular VACUUM (ANALYZE), workload-adjusted autovacuum and index lifecycle maintenance when justified; staging test lock/IO and WAL effects.
- Use partitions for time-based lifecycle and pruning where query patterns justify them. Dropping/detaching partitions is a data-retention change requiring owner approval.
- pg_repack or external tooling may be unavailable on managed services and requires compatibility, extensions and security review.

## 6. Right-sizing and cost model

| Lever | Intended benefit | Major risk |
|---|---|---|
| Instance downsize | Lower CPU/memory price | P95/P99, cache misses, vacuum/recovery slower |
| Storage/IOPS optimization | Right provisioned performance | Saturation, WAL and checkpoint delays |
| Connection pooling | Fewer backend sessions | Transaction/session semantics, prepared statements |
| Read replicas | Offload read queries | Lag and data-staleness; extra cost |
| Query/index optimization | Less CPU/IO per operation | Extra index storage/write cost, plan regression |
| Partition/retention design | More predictable cleanup | Data deletion and application query correctness |
| Cloud tier/backup options | Lower service price | HA/RPO/RTO, SLA, encryption and restore differences |

**Managed service specifics:**
- RDS/Aurora pricing and IO/backup policies differ; instance or DB cluster classes are not interchangeable.
- Azure Flexible Server HA/backup, disk auto-growth and tier constraints must be checked before downsize.
- Cloud SQL flags, instance class, HA/SSD sizing, storage auto-increase and backup tier impact recovery.
- Self-managed optimizations must include OS, disk, network and operator labor.

### Staging benchmark matrix

| Test | Measurement | Pass condition |
|---|---|---|
| Normal business load | APP latency, errors and DB CPU/IO | All approved SLOs |
| Peak/batch load | p95/p99, contention, CPU and disk throughput | Headroom and freshness |
| Connection burst | Pool wait/rejections and max_connections | No workload outage |
| Vacuum during writes | Progress, IO, write latency | Maintenance without major regression |
| Index build | Lock behavior, WAL, extra storage | Capacity and rollback |
| Replica catch-up | WAL generation/lag/recovery rate | Meets approved lag/RTO |
| Failover | Single-writer, restart times, app endpoint | Data integrity and recovery target |
| PITR restore | Valid base+WAL/new managed instance | RPO/RTO and APP data verification |
| Rollback | Return to known-safe capacity/topology | No data loss, SLO recovered |

### Change gates

Baseline 14–30 days including weekends and peak data; application and data owners sign expected workload; PLT/FIN price estimate; DBRE recovery and freeze/slot safety review; approved change window; documented revert and stop triggers.

Never downsize with unresolved WAL space risk, high freeze age, incomplete backups, exhausted connections, fragile replicas or untested rollback.

## 7. Monthly reporting template

| Measure | Observed / projected |
|---|---|
| Total database logical footprint / change | |
| 10 largest/growing tables and indexes | |
| WAL/day, archive failures, slot-retained bytes | |
| Primary/replica free disk, IOPS and latency | |
| CPU/IO peak, cache/wait trends | |
| Vacuum/bloat/transaction-age risks | |
| 30/60/90-day forecast with peak scenario | |
| RPO/RTO and restore evidence | |
| Cost by compute/IO/storage/backup/network | |
| Candidate initiatives, owners and approvals | |

**Realized savings** should compare actual billed costs in equivalent workload periods minus incremental backup/storage/network and one-time transition costs. The fraction of vCPUs removed does not automatically equal the same fraction of invoice savings.

## 8. Acceptance

- [ ] Logical sizes, WAL, physical disk and backups all measured separately.
- [ ] Owner-attributed daily to annual growth data and object lineage available.
- [ ] 30/60/90-day forecasts include primary and standby capacity/failure headroom.
- [ ] Query, connection, autovacuum and WAL pressure correlated with peak load.
- [ ] Provider-specific pricing and limits verified.
- [ ] Right-sizing staged with performance, recovery, capacity and rollback tests.
- [ ] APP/DATA, DBRE, PLT, FIN and SM approve production proposal.
- [ ] Post-change SLO and actual spend are documented.

## References
- [PostgreSQL relation sizes](https://www.postgresql.org/docs/current/functions-admin.html)
- [PostgreSQL vacuum/autovacuum](https://www.postgresql.org/docs/current/routine-vacuuming.html)
- [PostgreSQL monitoring stats](https://www.postgresql.org/docs/current/monitoring-stats.html)
- [PostgreSQL resource settings](https://www.postgresql.org/docs/current/runtime-config-resource.html)
