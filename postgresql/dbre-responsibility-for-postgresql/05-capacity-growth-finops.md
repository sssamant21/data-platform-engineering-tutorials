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
       pg_indexes_size(c.oid) AS index_bytes,
       (pg_total_relation_size(c.oid) =
         pg_table_size(c.oid) + pg_indexes_size(c.oid))
           AS size_reconciles
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE c.relkind='r'
  AND n.nspname NOT IN ('pg_catalog','information_schema')
ORDER BY total_bytes DESC LIMIT 50;

-- Relation index inventory
SELECT schemaname,
       relname AS table_name,
       indexrelname AS index_name,
       pg_relation_size(indexrelid) AS index_main_fork_bytes,
       idx_scan
FROM pg_stat_user_indexes
ORDER BY index_bytes DESC LIMIT 50;
~~~~

**Important — prevent double counting:** `pg_table_size` includes the table and TOAST data but excludes associated table indexes; `pg_indexes_size` counts its indexes; `pg_total_relation_size = pg_table_size + pg_indexes_size` (per table). `pg_database_size` already includes the database's table, index and TOAST storage; never add the per-table total to that same database baseline. Per-table totals may not reconcile to the whole database because of catalogs, other object types and metadata. `pg_relation_size(indexrelid)` measures the index **main fork**, not necessarily all of an index's forks.

The database-size and relation-size queries do **not** report WAL/archive files, temporary/log files outside those relation measurements, provider backup/object storage, physical free disk, or billed cloud capacity. Partitioned parents generally have little own storage: enumerate leaf tables and avoid double-counting parent/children. `idx_scan` can reset and does not authorize dropping indexes. For a large catalog, bound size inspections by an approved database, schema and frequency.

### CPU and transaction workload

~~~~sql
SELECT datname, numbackends, xact_commit, xact_rollback,
       blks_hit, blks_read, temp_bytes, deadlocks, stats_reset
FROM pg_stat_database WHERE datname IS NOT NULL;

SELECT state, count(*) AS sessions
FROM pg_stat_activity WHERE backend_type = 'client backend'
GROUP BY state;

SELECT slot_name, slot_type, active, restart_lsn,
       wal_status, safe_wal_size
FROM pg_replication_slots;

-- WAL generated since the statistics reset (counter, not retained disk usage).
SELECT wal_bytes, stats_reset
FROM pg_stat_wal;
~~~~

Use node exporter/OS or AWS CloudWatch, Azure Monitor and Google Cloud Monitoring for CPU, actual **instance-specific** physical used/free bytes, storage IOPS and latency. `pg_stat_wal.wal_bytes` is cumulative WAL **generated**, not WAL currently stored on disk or in an archive, nor a measure of billed backups. Compute counter deltas only when `stats_reset`, engine role and cluster identity are unchanged; discard/reset bad intervals after failover and counter resets. In an Aurora cluster, separately identify cluster shared-storage metrics versus instance-local metrics: do not multiply shared cluster volume bytes by the number of reader instances.

For reusable collection, see the [read-only V05 SQL pack](qa/V05-readonly-capacity-inventory.sql). Run it only with a bounded monitoring role on authorized staging; do not treat the SQL as a live cloud storage collector.

## 4. Snapshot-based growth schema

Persist **daily UTC** measurements keyed by provider/cluster ID, instance ID and **database name/OID**. Relation OIDs are database-local and can be reused after DROP/CREATE; retain schema/name, lifecycle identity and rename/recreation events. Persist SQL logical size metrics **separately** from provider/node physical used/free/allocated metrics, WAL generation counters, WAL retained on disk, backups and billing data. Do not sum different metrics with overlapping coverage. When a sample is missing, late, reset, from a changed primary or a different service tier, mark it INCOMPLETE/RESTART/FAILOVER and exclude it from a normal growth-rate calculation.

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
| sample_quality | COMPLETE, MISSING, PARTIAL, RESET, FAILOVER; record collector/privilege coverage |
| source_metric and scope | SQL logical database vs node disk vs Aurora shared volume vs backup billing |
| storage auto-growth and tier changes | Provisioned size change / max and effective free capacity |
| workload tag / usage | Daily transactions, p95/p99, peak batch/seasonality and idle cycles |

### Reporting periods

Daily, weekly, calendar monthly, quarterly, semiannual and annual comparisons, each calculated from retained time-series snapshots with a consistent UTC cutoff. Report net growth, new objects, dropped/archived objects and non-table WAL/backup usage independently.

### Projection formulas

- **Logical growth/day:** per-database or per-relation (current bytes − prior bytes) / elapsed days. Do not add databases and their component relations together.
- **Forecast:** current *physical used bytes* + positive median daily *physical used growth* × 30/60/90 days. Add a high-growth scenario using a measured upper quantile or documented batch/seasonal peak. A nonpositive observed median is NOT proof that no future capacity is needed.
- **Physical capacity:** take provider/OS-reported used/free/allocated bytes as the **top-level** baseline; those values generally already include table/index/TOAST. Account separately for possible WAL spikes, temp files, vacuum/index rebuild and restore/failover reserve **only as unallocated additional headroom**, never as duplicate currently consumed bytes.
- **Runway per instance/failure domain:** max(0, physical free bytes − approved minimum-free/rebuild reserve) / positive forecast physical growth rate. When rate is zero/negative or samples are incomplete, report **UNKNOWN / not estimable**, never infinite guaranteed runway.
- **Replication:** primary and each replica need independent physical storage/runway assessment. Count each physical copy when evaluating estate **cost**, but never add each replica's disk usage into the primary's storage percentage. For Aurora's shared cluster storage, distinguish shared-volume metrics from per-instance local metrics.
- **Counter and quality gates:** use only consistent, complete samples with the same source/scope and no stats reset or identity change. Record confidence and 14–30 day peak/weekend coverage before recommending a change.

**Illustrative only:** database logical footprint 2 TiB with net *logical* growth of 20 GiB/day implies +600 GiB in 30 days or +1,800 GiB in 90 days **for the logical database metric**, not physical disk or cost. To project storage exhaustion, independently measure *physical used/free bytes* including WAL/tmp/log and reserve. Do not add indexes or TOAST twice. The example is synthetic and is not an actual cluster forecast.

### Reference offline forecast calculator

The [V05 capacity forecast utility](qa/V05-capacity-forecast.py) accepts an operator-curated CSV of **daily physical used/free** bytes per instance and reports 30/60/90-day baseline and higher-growth runway. It refuses missing/duplicate daily samples, incomplete quality flags and negative sizes. It does **not** connect to PostgreSQL, issue cloud API calls, change capacity, or calculate real dollar savings. Its output is a planning aid only, especially when providers autoscale storage or workloads are seasonal. Use sample data and `--self-test` before accepting results as evidence.

Example input schema: `sample_date_utc,cluster_id,instance_id,used_bytes,free_bytes,reserve_bytes,quality`. The **operator must define** reserve_bytes for WAL spikes, reindex/maintenance, restore/failover and minimum free headroom. All bytes are base-2 for GiB reporting and stored as raw integer bytes; dates use YYYY-MM-DD UTC.

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
- **RDS PostgreSQL:** use instance-level FreeStorageSpace, TransactionLogsDiskUsage, TransactionLogsGeneration, CPU and IOPS plus cost details. The selected storage configuration and read replica/standby each have separate capacity and charges.
- **Aurora PostgreSQL:** cluster-level VolumeBytesUsed and backup metrics differ from RDS FreeStorageSpace; cluster shared storage should not be summed once per reader. Check per-instance/cluster cost and workload class.
- **Azure Flexible Server:** use `storage_used`, `storage_free`, `txlogs_storage_used`, `backup_storage_used`, `storage_percent`, CPU/IOPS and HA/auto-growth tier constraints.
- **Cloud SQL PostgreSQL:** use `database/disk/bytes_used_by_data_type`, quota, utilization, WAL/tmp breakdown and pricing/backup tier. Some PITR WAL may be in Cloud Storage rather than instance disk.
- **Self-managed:** include OS physical metrics, disks/tablespaces/WAL volume and operator, network and external backup cost. All provider metrics must be checked against the *actual* SKU/edition/region and source timestamp.

### Cost reconciliation rules

For the same comparable workload period, track billed compute, storage, provisioned IOPS/throughput, replica/HA, backup/archive/object storage, network transfer and operational transition expense. **Savings** = normalized baseline billed cost − post-change billed cost − transition cost, with actual negotiated rates, time-window boundaries, changing workload and credits/discounts recorded. A reduction in instance vCPU does not imply the same percentage reduction in bill.

### V05 static QA and staging readiness

The [V05 capacity/forecast QA report](qa/V05-capacity-growth-finops-review.md) documents documented-function verification, the physical/logical double-counting fix, reset-safe WAL usage, provider measurements and negative tests. A source-reviewed SQL pack and offline reference forecast are provided; **no production/staging PostgreSQL, provider telemetry, invoice or right-sizing change was tested**.

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

- [ ] Logical sizes, WAL, physical disk and backups all measured separately without double counting.
- [ ] V05 SQL read-only pack and offline forecast checked with deployment's real monitoring role and correct physical storage source.
- [ ] Physical daily sample coverage, reset/failover/identity changes and reserve requirements verified.
- [ ] Owner-attributed daily to annual growth data and object lineage available.
- [ ] 30/60/90-day forecasts include primary and standby capacity/failure headroom.
- [ ] Query, connection, autovacuum and WAL pressure correlated with peak load.
- [ ] Provider-specific pricing and limits verified.
- [ ] Right-sizing staged with performance, recovery, capacity and rollback tests.
- [ ] APP/DATA, DBRE, PLT, FIN and SM approve production proposal.
- [ ] Post-change SLO and actual spend are documented.

## References
- [PostgreSQL relation sizes](https://www.postgresql.org/docs/current/functions-admin.html)
- [PostgreSQL 14 pg_stat_wal and stats reset](https://www.postgresql.org/docs/14/monitoring-stats.html)
- [AWS RDS CloudWatch metrics](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-metrics.html)
- [AWS Aurora CloudWatch cluster metrics](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.AuroraMonitoring.Metrics.html)
- [Azure Flexible Server monitoring](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-monitoring)
- [Cloud SQL disk metrics](https://docs.cloud.google.com/sql/docs/postgres/admin-api/metrics)
- [PostgreSQL vacuum/autovacuum](https://www.postgresql.org/docs/current/routine-vacuuming.html)
- [PostgreSQL monitoring stats](https://www.postgresql.org/docs/current/monitoring-stats.html)
- [PostgreSQL resource settings](https://www.postgresql.org/docs/current/runtime-config-resource.html)
