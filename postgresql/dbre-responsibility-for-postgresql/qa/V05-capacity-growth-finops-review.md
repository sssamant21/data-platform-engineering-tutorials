# PostgreSQL DBRE V05 — Capacity, Growth and FinOps Static QA

**Date:** 2026-11-01 UTC  
**Status:** SOURCE REVIEW AND REFERENCE MATERIAL COMPLETE; LIVE CAPACITY/BILLING VALIDATION PENDING  
**Reviewed:** Page 05 PostgreSQL Capacity/FinOps, SQL size functions (PG14–18), WAL stats, cloud physical-storage metrics.  
**No changes to production.** No live PostgreSQL, host, Prometheus, AWS/Azure/GCP billing, or cloud metrics were accessed.

## 1. Findings and corrections

| Finding | Risk | Resolution |
|---|---|---|
| V05-F01 — Logical size double counting | Adding table/index/TOAST to pg_database_size inflates projection | Explicit pg_total_relation_size = pg_table_size + pg_indexes_size; database top-line already covers components |
| V05-F02 — Physical capacity baseline ambiguity | Logical database bytes do not equal actual disk usage, free bytes or billed storage | Separate SQL logical sizes, WAL produced, host/cloud physical used/free, allocated and backup usage; never add overlapping metrics |
| V05-F03 — Individual index main fork vs full index | pg_relation_size(indexrelid) describes main fork, not all index forks | Rename result index_main_fork_bytes; use pg_indexes_size(table_oid) for associated index totals |
| V05-F04 — WAL generated vs WAL retained | pg_stat_wal.wal_bytes is cumulative generated WAL; reset/failover can create false rates | Add stats_reset, changed-primary detection, slot-state review, physical pg_wal/cloud measurements separately |
| V05-F05 — Partition and replica accounting | Parent plus leaves or Aurora shared volume per replica can double count | Per-database/leaf attribution; per-instance physical capacity and distinct Aurora cluster-volume/cost accounting |
| V05-F06 — Forecast and runway assumptions | Negative/zero growth, missing days, autoscaling and reserve omitted | Daily complete-series acceptance, median positive daily physical deltas, p90 peak case, free-minus-reserve runway; uncertainty documented |
| V05-F07 — Savings proof | CPU/GB reduction assumed equal billed cost reduction | Normalize workload/discounts and compare actual spend incl. compute, IO, storage, replica, backup, network and one-time transition |
| V05-F08 — Provider monitoring differences | One cloud metric name/aggregation used in all platforms | RDS, Aurora, Azure and Cloud SQL provider-specific measurement matrix |

## 2. PostgreSQL source-verified semantics

- pg_database_size returns database object disk usage in bytes; it is not total host disk allocation or WAL/backup archive footprint.
- pg_table_size includes TOAST table but excludes associated table indexes. pg_indexes_size counts associated indexes. pg_total_relation_size is their sum. Do not add these metrics to each other **and** pg_database_size when forming the same top-line.
- pg_relation_size(indexrelid) reports the index's main fork when no fork argument is given.
- A partitioned parent relation can have very little local storage; a leaf table contains storage. Sum one consistent hierarchy without parent/leaf double counting.
- pg_stat_wal.wal_bytes is a cumulative counter of WAL generated, not WAL currently retained on disk or backup. stats_reset and primary identity matter when computing deltas.
- pg_stat_user_indexes.idx_scan is a stats metric, not a complete unused-index classification.

## 3. Provider physical storage and cost sources

| Platform | Physical and WAL source to validate | Billing/cost caution |
|---|---|---|
| Self-managed PG14–18 | OS/node_exporter volume metrics per data/WAL mount, actual filesystem allocated/used/free, backup repository metrics | Count every replica/volume and ops cost, but separately from logical DB |
| AWS RDS PostgreSQL | CloudWatch FreeStorageSpace, TransactionLogsDiskUsage, TransactionLogsGeneration, IOPS, DB storage class | RDS instance vs replica storage and backups billed according to configuration; check actual SKU |
| Aurora PostgreSQL | CloudWatch VolumeBytesUsed is **cluster** storage, with separate instance metrics and backup metrics | Never add shared cluster volume once per reader/instance; Aurora differs from RDS storage |
| Azure Flexible Server | storage_used, storage_free, storage_percent, txlogs_storage_used, backup_storage_used | storage_used can include more than table data; HA/tier/autogrow and billing separately |
| Google Cloud SQL PostgreSQL | database/disk/bytes_used_by_data_type, database/disk/quota, utilization and IO metrics | Separate WAL/archive/temp/log categories; PITR WAL may reside in Cloud Storage |

Each metric is a provider/account/region/edition/configuration-specific assertion requiring independent live validation, not proof of currently enabled metrics.

## 4. Reference artifacts

- [Read-only V05 SQL inventory](V05-readonly-capacity-inventory.sql) — current database, tables/leaf sizes, index main-fork, WAL generated and slots, with bounded SQL timeout. **NOT EXECUTED**.
- [Offline physical-disk forecast script](V05-capacity-forecast.py) — CSV in bytes by instance/day; 14 consecutive COMPLETE days minimum; rate, 30/60/90-day and headroom/runway output. Uses stdlib, no PostgreSQL connection, no changes.
- Monthly report contract: primary, each replica and any shared Aurora cluster volume; physical usage/free and required reserve; logical per-DB growth; archive/backup and real bill.

## 5. Offline model assumptions and negative cases

### Input

The source data MUST be exported from a known **physical storage metric** for the same instance/volume at a consistent daily UTC cutoff:

~~~~text
sample_date_utc,cluster_id,instance_id,used_bytes,free_bytes,reserve_bytes,quality
2026-10-01,example,primary,1073741824000,1288490188800,107374182400,COMPLETE
~~~~

The one-row sample is not a valid forecast. Record at least 14 consecutive daily rows. When storage auto-grows during collection, record the tier and provisioned size separately and review the meaning of free space. Do not combine per-node disk with Aurora shared cluster-volume metrics in one series.

### Test cases

| Test ID | Condition | Required outcome |
|---|---|---|
| V05-T01 | 14 daily COMPLETE rows, stable growth 20 GiB/day | Baseline/peak rates and 30/60/90-day forecasts deterministic |
| V05-T02 | One missing day | FAIL CLOSED |
| V05-T03 | Duplicate UTC date | FAIL CLOSED |
| V05-T04 | Non-COMPLETE/stale data | FAIL CLOSED |
| V05-T05 | Negative bytes or malformed integer | FAIL CLOSED |
| V05-T06 | Zero/negative median daily growth | Runway UNKNOWN, not infinity |
| V05-T07 | Reserve changes in series | FAIL CLOSED until reviewed |
| V05-T08 | WAL stats reset or primary changed | Do not compare counter deltas across resets; independent operator gate |
| V05-T09 | Parent+leaf partition aggregation | No double counting; SQL reconciliation |
| V05-T10 | Aurora shared volume plus multiple readers | Do not multiply cluster physical bytes |
| V05-T11 | Physical free close to rebuild/failover reserve | High-risk runway, no downsize |
| V05-T12 | App peak workload under proposed right-sizing | Staging p95/p99, locks, vacuum, repl and recovery pass |
| V05-T13 | Provider storage auto-growth enabled/disabled | Forecast scenarios distinguish allocation changes |
| V05-T14 | Cloud invoice with compute/IO/replica/backup/network | FIN validates billed savings, not size proxy |

All V05-T01–T14 require explicit test result/evidence before declaring V05 runtime certified. The offline utility contains limited deterministic self-tests but is not a substitute for real data lineage, tests or workload safety.

## 6. Acceptance and data evidence

- [x] Catalog size and WAL semantics checked against PostgreSQL 14/18 docs.
- [x] Forecast model and provider physical-vs-logical distinction documented.
- [x] Reference read-only SQL pack and offline physical forecast supplied.
- [ ] Run SQL with approved staging monitoring roles on deployed PG versions.
- [ ] Obtain at least 14 COMPLETE daily physical capacity samples for each relevant instance/volume; longer peak/weekend samples required for right-sizing.
- [x] Offline reference script passed Python compilation and the built-in synthetic self-test in a local Python runtime; additional CSV quality checks passed (details below).
- [ ] Re-run the script under the DBRE team's approved Python runtime, record exact version/environment and independent reviewer.
- [ ] Validate physical metrics/cloud permissions, reset/failover, seasonal peaks and Aurora aggregation.
- [ ] Test right-sized instance performance/replica recovery/failover and independent APP SLO.
- [ ] Review invoice, discount and provider storage bills with FIN; document savings.
- [ ] DBRE, PLT, APP, DATA, FIN and Change Management approval.

**V05 result: static QA and model design complete, production validation NOT CERTIFIED.**

## 7. Locally executed offline reference-model checks

**Execution scope:** only the Python standard library and artificial data on the assistant's isolated working container; **no** PostgreSQL, cloud provider, invoice, Grafana or real user file was accessed.

**Published-source verification:** the local tested Python file has Git blob SHA `08dfec451866cf7fece20075b86bbe7714780d6b`, matching the published repository's V05-capacity-forecast.py blob SHA.

| Check | Observed output | Result |
|---|---|---|
| `python -m py_compile V05-capacity-forecast.py` | No compilation error | PASS |
| `python V05-capacity-forecast.py --self-test` | `PASS: offline V05 forecast deterministic self-tests (synthetic data)` | PASS |
| 14 synthetic daily CSV samples, +20 GiB/day | Latest used 1,260 GiB; free 940 GiB; reserve 100 GiB; 30-day free 340 GiB; runway 42 days | PASS |
| Partial quality row | Rejected: non-COMPLETE sample | PASS |
| Negative used_bytes | Rejected: negative byte measurement | PASS |
| Missing day | Rejected: fewer than 14 complete daily rows | PASS |
| Duplicate date | Rejected: duplicate sample dates | PASS |
| Changed reserve_bytes within series | Rejected: reserve policy changed | PASS |
| Flat used bytes / no growth | Runway reported UNKNOWN, not infinity | PASS (self-test) |

**Important limits:** The output projects physical free space under constant reported capacity and uses median/p90 net *observed physical used* daily changes. It is not a guarantee of future exhaustion, managed storage auto-grow behavior or an approved right-sizing decision. No real billing or utilization test was run.

## 8. Authoritative sources

- [PostgreSQL 18 object size functions](https://www.postgresql.org/docs/18/functions-admin.html)
- [PostgreSQL 14 WAL statistics](https://www.postgresql.org/docs/14/monitoring-stats.html)
- [PostgreSQL 18 stats](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [AWS RDS CloudWatch metrics](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-metrics.html)
- [Aurora CloudWatch metrics](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.AuroraMonitoring.Metrics.html)
- [Azure Flexible Server metrics](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-monitoring)
- [Cloud SQL PostgreSQL metrics](https://docs.cloud.google.com/sql/docs/postgres/admin-api/metrics)
