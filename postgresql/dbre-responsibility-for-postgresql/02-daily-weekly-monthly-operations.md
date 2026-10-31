# Page 02 — PostgreSQL Daily, Weekly, Monthly & Quarterly DBRE Operations

**Document ID:** PG-DBRE-OPS-002 | **Owner:** PostgreSQL DBRE | **Status:** DRAFT — staging validation pending  
**Scope:** Self-managed and managed PostgreSQL. Read-only SQL is illustrative and depends on permissions/version.

## 1. Daily operational checklist

| ID | Check | Evidence / action |
|---|---|---|
| D01 | Primary database reachability / health | Confirm approved synthetic read/write or psql monitoring check |
| D02 | Replicas and HA | Primary/standby state, client endpoint, replication lag, failover state |
| D03 | Connections | Active/idle/idle in transaction, approaching max_connections |
| D04 | SQL responsiveness | APP p95/p99, errors, timeouts, query regressions and wait events |
| D05 | Locks/deadlocks | Blocking chains, deadlock rate and long transactions |
| D06 | Vacuum / freeze | Dead tuples, autovacuum age, tables near wraparound risk |
| D07 | Storage and WAL | Free bytes, WAL disk usage, archiver status, slots retaining WAL |
| D08 | Backups / PITR | Last completed recoverable backup and last restorable timestamp versus RPO |
| D09 | Replication/WAL archives | Lag, last receive/replay, failed archive jobs |
| D10 | Host/managed metrics | CPU, memory pressure, IO latency, storage, network and restarts |
| D11 | Query statistics / collectors | pg_stat_statements/pg_exporter and Grafana coverage |
| D12 | Open incidents and changes | Incident, RCA action, scheduled maintenance and current risks |

**Safety:** Do not issue VACUUM FULL, REINDEX, role changes, pg_terminate_backend, pg_drop_replication_slot or failover from a routine monitoring checklist.

### Daily read-only SQL: version, identity and recovery role

~~~~sql
SELECT current_database() AS database_name,
       current_user AS monitor_role,
       current_setting('server_version') AS version,
       pg_is_in_recovery() AS is_standby,
       now() AS sampled_at_utc;

SELECT datname, numbackends, xact_commit, xact_rollback,
       blks_read, blks_hit, deadlocks, stats_reset
FROM pg_stat_database
WHERE datname IS NOT NULL
ORDER BY datname;

SELECT state, wait_event_type, wait_event, count(*) AS sessions
FROM pg_stat_activity
WHERE backend_type = 'client backend'
GROUP BY 1,2,3
ORDER BY sessions DESC;
~~~~

One snapshot is not a utilization/throughput trend. pg_stat_database counters can reset after unclean shutdown, explicit reset or restoration. Track deltas with stats_reset and database identity.

### Current blockers and long transactions

~~~~sql
SELECT pid, datname, usename, state, wait_event_type, wait_event,
       now() - xact_start AS xact_age, pg_blocking_pids(pid) AS blockers
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
ORDER BY xact_start ASC
LIMIT 30;
~~~~

pg_blocking_pids returns blockers; do not terminate a session until APP owners and transaction consequences are reviewed. Query text may contain PHI/secrets: exclude it from general reporting.

### Primary replication and slot inventory

~~~~sql
-- On primary; no rows is normal if no streaming replicas are connected.
SELECT application_name, client_addr, state, sync_state,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;

-- Monitor WAL retained by slots; works in supported recent releases.
SELECT slot_name, slot_type, active, restart_lsn,
       CASE WHEN restart_lsn IS NOT NULL
            THEN pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)
       END AS approx_retained_wal_bytes
FROM pg_replication_slots;
~~~~

**Role limitation:** pg_current_wal_lsn() is primary-specific; execute slot-size query only on an authorized primary. Replication lag interval fields are not direct guaranteed end-to-end RPO measurements and can become NULL when idle.

### Archive and vacuum evidence

~~~~sql
SELECT archived_count, last_archived_wal, last_archived_time,
       failed_count, last_failed_wal, last_failed_time, stats_reset
FROM pg_stat_archiver;

SELECT schemaname, relname, n_live_tup, n_dead_tup,
       last_autovacuum, last_autoanalyze, autovacuum_count
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC LIMIT 30;
~~~~

Cloud service-managed backups and WAL are not always exposed via pg_stat_archiver. Provider backup/restore telemetry takes precedence.

## 2. Weekly review

| ID | Focus | Decision / deliverable |
|---|---|---|
| W01 | Largest/growing databases, tables and indexes | Per-owner growth, expected runway |
| W02 | Autovacuum and freeze age | Wraparound / bloat risk tickets |
| W03 | Long transactions and recurring blockers | APP transaction changes and timeout review |
| W04 | pg_stat_statements hot queries | Plan/index review, performance tickets |
| W05 | Index usage and bloat | Candidate maintenance only, no automatic drop |
| W06 | Replica health, slots and WAL archiving | Lag/retention/failover risk |
| W07 | Connections/PgBouncer | Pool sizing and saturation improvements |
| W08 | Backup freshness, restore evidence | Recovery exceptions |
| W09 | Slow I/O and checkpoints | Backend I/O/host or managed metrics |
| W10 | Failed jobs, migrations and security changes | Owner-based action report |

### Relation sizes by database (run in each database)

~~~~sql
SELECT n.nspname AS schema_name, c.relname AS relation_name,
       c.relkind, pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
       pg_total_relation_size(c.oid) AS total_bytes
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r','m','p')
  AND n.nspname NOT IN ('pg_catalog','information_schema')
ORDER BY total_bytes DESC LIMIT 30;

SELECT datname, pg_size_pretty(pg_database_size(datname)) AS logical_size
FROM pg_database
WHERE datallowconn
ORDER BY pg_database_size(datname) DESC;
~~~~

Relation stats can double-count parent and child if aggregation is naive. pg_database_size excludes WAL/logs/backups and must not be substituted for disk actual usage.

### Transaction ID age

~~~~sql
SELECT datname, age(datfrozenxid) AS xid_age,
       current_setting('autovacuum_freeze_max_age')::bigint AS freeze_max_age
FROM pg_database
ORDER BY xid_age DESC;
~~~~

age(datfrozenxid) is an **early-warning approximate**; critical wraparound assessment must include per-table relfrozenxid, multixact age, disabled/autovacuum exclusion, blockers and transaction rate. Autovacuum freeze_max_age is not a universal critical alert threshold or hard cutoff.

## 3. Monthly operations

- Review per-database and per-relation growth by day/week/month and 30/60/90-day forecast.
- Check bloat/autovacuum tuning and transaction age/long idle sessions.
- Compare database SLO, connection pool usage, query-plan regressions and CPU/IO.
- Validate a controlled restore/PITR sample and RPO/RTO with APP/DATA.
- Review physical/logical replication slots, archive performance and HA topology.
- Evaluate instance/storage/IOPS sizing and cloud costs with PLT/FIN.
- Audit owner lists, privileged roles, certificates, network access and recent DDL.
- Plan patch/major version upgrades and standby compatibility.
- Update incident RCA corrective actions and on-call runbooks.

## 4. Quarterly operations

Perform HA/DR tabletop or approved staging rehearsal; examine data correctness after failover, single-writer fencing, backup recovery, regional failure, security review, retention and compliance, growth/capacity, annual lifecycle and cost strategy. Record named owner, evidence, action/ticket and independent acceptance.

## 5. Cloud-specific review

| Provider | Additional checks |
|---|---|
| AWS RDS for PostgreSQL | Instance/standby status, Multi-AZ config, backup retention/latest restorable time, enhanced monitoring/Performance Insights where enabled |
| Amazon Aurora PostgreSQL | Cluster writer/reader endpoints, instances, failover priorities, Aurora-specific cluster storage/replica metrics and backups |
| Azure Flexible Server | HA zone choice, backup/PITR coverage, restart/maintenance events, Azure Monitor storage/CPU connections |
| Cloud SQL PostgreSQL | HA configuration, latest PITR window, read-replica lag, storage and Cloud Monitoring |
| Self-managed | OS/filesystems, service process, archiving, replication slots, WAL shipping, operator/orchestrator fencing |

## 6. Review record and acceptance

| Field | Value |
|---|---|
| Cluster/provider/version/region | |
| Reported UTC period and DBRE owner | |
| Availability and APP latency SLI | |
| Replication/slot/archive state | |
| Vacuum/transaction age/bloat | |
| Top relations and WAL growth | |
| Current locks, long transactions, pool status | |
| Backup/recovery evidence | |
| Open risks / approvals / ticket | |

- [ ] Daily on-call checks have automated sources, thresholds and owners.
- [ ] Weekly/monthly capacity, vacuum and SQL performance reports retained.
- [ ] Read-only SQL verified for each supported engine version/managed provider.
- [ ] Backup/PITR readiness and provider-specific restrictions documented.
- [ ] APP, DATA and PLT approve operational review process.

## References
- [PostgreSQL statistics system](https://www.postgresql.org/docs/current/monitoring-stats.html)
- [PostgreSQL routine vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html)
- [PostgreSQL WAL settings](https://www.postgresql.org/docs/current/runtime-config-wal.html)
