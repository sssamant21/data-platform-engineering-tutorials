# Chapter 18 — Capacity Planning, Performance and FinOps

**Audience:** DBRE/SRE and platform engineers · **Duration:** 60 minutes · **Status:** Authored; runtime untested; independent review pending.

## Learning outcomes and prerequisites
Estimate storage, compute and connection capacity using measured workload data; distinguish logical table size, physical database footprint, WAL, backups and replica costs; define SLO-based scaling triggers and a defensible cost decision. Prerequisites: Chapters 01–17, Docker Desktop (Linux engine), Docker CLI, terminal (PowerShell or bash), 2 GB available RAM and sufficient free disk space for a small disposable PostgreSQL 17 instance. No cloud account or paid service is needed. Examples use the official `postgres:17` image; exact minor version is image-dependent.

## 60-minute teaching outline
| Minutes | Topic |
|---|---|
| 0–10 | Workload profile: reads/writes, peak concurrency, latency SLOs |
| 10–20 | Capacity architecture: data, indexes, WAL, backups, replicas, growth |
| 20–30 | Measurements and forecasting assumptions |
| 30–45 | Isolated Docker SQL lab and evidence |
| 45–53 | FinOps scenario and right-sizing decision |
| 53–60 | Guardrails, troubleshooting and acceptance |

## Fundamentals and architecture
A PostgreSQL capacity plan starts with **business workload → application connection pools → PostgreSQL CPU/memory/I/O → storage/WAL → backup and recovery**. Capture peak QPS/TPS, active connections, transaction duration, query latency percentiles, cache hit ratio (context-dependent), physical reads/writes, WAL generation, dead tuples, index growth, replication lag, maintenance demand and backup/restore duration. Average utilization alone hides bursts. Establish a representative peak period, forecast horizon, headroom policy and owner-approved SLOs.

### Storage accounting
- `pg_relation_size` is a relation's main fork; `pg_table_size` includes associated TOAST and other table storage; `pg_indexes_size` covers indexes; `pg_total_relation_size` combines table and indexes. Avoid double-counting.
- `pg_database_size` covers database files, not a complete bill for WAL, archived WAL, backups, replicas, storage snapshots or network transfer.
- MVCC updates/deletes can leave reclaimable dead tuples; statistics are estimates and not a direct measurement of bloat. `VACUUM` generally reuses space rather than shrinking relation files.
- WAL rates depend on write pattern, checkpoints, full-page images and maintenance. Measure with `pg_stat_wal` over a defined interval; a single cumulative counter is not a rate.
- Capacity includes resilience: primary + replicas, retained backups, PITR WAL archives, maintenance workspace and restore headroom. Do not assume a replica replaces backups.

### Worked forecast (illustrative, not measured)
Assume **200 GiB** current physical database footprint, **8 GiB/week** net growth and **26 weeks** forecast:
`forecast = 200 + 8 × 26 = 408 GiB`. With 30% *free-space target* (not 30% additive headroom), provision at least `408 / 0.70 ≈ 583 GiB` for that database footprint. This excludes separate WAL/archive/backup allocations and replicas. Forecast uncertainty should be captured as low/base/high scenarios; revise from weekly observed deltas.

### Performance and cost decision
| Signal | Investigate before scaling | Possible response |
|---|---|---|
| CPU saturation + expensive queries | `pg_stat_activity`, `EXPLAIN (ANALYZE, BUFFERS)` on safe synthetic queries | Index/query tuning; then measured CPU scale |
| Read I/O pressure | working set, cache behavior, plan changes, storage latency | Index tuning, memory/storage IOPS evaluation |
| Connection pressure | pool sizing, idle transactions, `max_connections` | Pooling and concurrency limits before raising cap |
| WAL/storage growth | long transactions, slots, archiving failures, churn | Resolve retention causes, validate backups |
| High cost/low utilization | peak profile, availability/RPO/RTO requirements | Rightsize after staged SLO and failover checks |

FinOps comparisons must use **total cost of ownership**: compute, provisioned storage/IOPS, replicas, backups, WAL archive, transfer, monitoring, licenses where applicable and engineering labor. Managed services and Kubernetes add different operational ownership. Never infer actual cloud prices from local Docker timings.

## Guided exercise
Complete the [Chapter 18 local lab](../labs/chapter-18/README.md). Its SQL creates synthetic rows and reads `pg_database_size`, `pg_total_relation_size`, `pg_stat_user_tables`, `pg_stat_database` and `pg_stat_wal`. Capture a before/after measurement; identify that cumulative statistics and table sizes have different semantics. Run `EXPLAIN (ANALYZE, BUFFERS)` only on the lab's small synthetic SELECT.

Example read-only production *diagnostic pattern* (execute only with approved read access):
```sql
SELECT current_database() AS database_name,
       pg_size_pretty(pg_database_size(current_database())) AS database_size;
SELECT relname, n_live_tup, n_dead_tup, last_autovacuum
FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 10;
```
Expected: database size and approximate row statistics; estimates may lag until ANALYZE and are not guarantees.

## Safety, rollback and governance
Use an isolated container with **no published host port**. Confirm container identity before running; never reuse a production endpoint or paste a credential into logs. Do not change production `max_connections`, autovacuum, checkpoint settings, storage allocation or instance class from these examples. Scaling/downscaling requires backup/recovery proof, peak workload tests, replication checks, rollback trigger, maintenance approval and post-change SLO monitoring. Lab rollback is limited to deleting the synthetic table and the uniquely named lab container. No broad Docker prune commands.

## Troubleshooting
| Symptom | Diagnosis | Safe action |
|---|---|---|
| Docker unavailable | `docker info` | Start Docker Desktop; do not switch context silently |
| Name conflict | `docker container inspect pg-dbre-ch18` | Stop; do not remove an unknown container |
| `pg_isready` not ready | `docker logs pg-dbre-ch18` | Retry after startup; verify exact container |
| Size hardly changes | Page allocation, caching, small dataset | Compare bytes and repeat with larger synthetic dataset |
| Stats show zero or stale counts | Async stats, missing ANALYZE, snapshot caching | Run lab ANALYZE and start fresh session |
| Query plan differs | Version, statistics, cache and platform | Record actual plan; do not hardcode timing expectations |
| Unexpected disk pressure | `docker system df`, host free space | Stop lab; inspect before any cleanup |

## Acceptance checklist
- [ ] Identify database, table, index, WAL, backup and replica capacity separately.
- [ ] Run the isolated lab and record server/image identity.
- [ ] Record physical size and cumulative-stat observations without conflating them.
- [ ] Calculate 26-week low/base/high forecast and explicit free-space headroom.
- [ ] Present a scale-versus-tune decision with SLO and cost assumptions.
- [ ] Show bounded cleanup and define a production change/rollback gate.
- [ ] Keep authored, runtime-tested, independently reviewed and production-certified statuses separate.

## Official references
- [PostgreSQL 18 database object size functions](https://www.postgresql.org/docs/18/functions-admin.html#FUNCTIONS-ADMIN-DBSIZE)
- [PostgreSQL 18 monitoring statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [PostgreSQL 18 EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)
- [PostgreSQL 18 routine vacuuming](https://www.postgresql.org/docs/18/routine-vacuuming.html)
- [PostgreSQL 18 resource consumption](https://www.postgresql.org/docs/18/runtime-config-resource.html)
- [PostgreSQL 18 WAL configuration](https://www.postgresql.org/docs/18/wal-configuration.html)
- [Official PostgreSQL Docker image](https://hub.docker.com/_/postgres)
