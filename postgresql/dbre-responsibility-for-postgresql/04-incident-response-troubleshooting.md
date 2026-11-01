# Page 04 — PostgreSQL Incident Response & Troubleshooting Runbooks

**Document ID:** PG-DBRE-OPS-004 | **Owner:** DBRE on-call | **Status:** DRAFT — not production-certified
**Applies:** Self-managed PostgreSQL and provider-supported AWS RDS/Aurora, Azure Flexible Server and Cloud SQL configurations.

> **Production safety:** Diagnostic queries below are read-only. Do not issue pg_terminate_backend, pg_cancel_backend, DROP/ALTER, pg_promote, pg_drop_replication_slot, RESET WAL, VACUUM FULL, or failover commands from a generic triage guide. Such operations require incident/change authorization, impact analysis and recovery/rollback plans.

## 1. Incident workflow and severity

**Detect → confirm business impact → identify primary/replica and environment → preserve evidence → read-only diagnosis → route ownership → authorize mitigation → validate APP+DATA service → record RCA.**

| Severity | Example | Handling |
|---|---|---|
| P1 | Primary outage, two active writers, lost business data, widespread transaction failure | Immediate incident commander + DBRE, APP, PLT, SEC/DATA as needed |
| P2 | Major query SLO breach, severe replication/backup lag, near storage or wraparound exhaustion | Urgent on-call, coordinated mitigation |
| P3 | Recurrent blocking, bloat, deadlock growth, low capacity runway | Assigned remediation ticket |
| P4 | Routine trend and maintenance need | Scheduled review |

Record UTC timestamps, instance and region, engine version, endpoint, primary/standby role, affected applications, known changes, incident lead and vendor case.

### Read-only first-response SQL

~~~~sql
SELECT current_database() AS db, current_user AS monitor,
       current_setting('server_version') AS version,
       pg_is_in_recovery() AS standby,
       now() AS sample_time;

SELECT datname, numbackends, xact_commit, xact_rollback,
       blks_hit, blks_read, deadlocks, stats_reset
FROM pg_stat_database WHERE datname IS NOT NULL;

SELECT pid, datname, usename, state,
       wait_event_type, wait_event, now()-xact_start AS transaction_age,
       pg_blocking_pids(pid) AS blocking_pids
FROM pg_stat_activity
WHERE backend_type = 'client backend'
ORDER BY xact_start NULLS LAST LIMIT 50;

SELECT application_name, state, sync_state,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;

SELECT archived_count, last_archived_time, failed_count,
       last_failed_time, stats_reset FROM pg_stat_archiver;
~~~~

**Important:** On replicas, primary-specific pg_stat_replication may be empty by design. Use standby status/pg_stat_wal_receiver and provider monitoring. Cumulative stats can reset; one-time deltas may mislead. Managed providers may restrict permissions or use proprietary HA/backups.

## 2. PG-INC-001 — Database unavailable / primary down

**Symptoms:** connection refused/timeouts, service fails, database accepts no connections.

1. Confirm DNS, credentials, network, TLS, account/region and whether outage affects other apps.
2. Use approved synthetic read-only health check and provider status/host monitoring.
3. Determine whether primary, reader endpoint, pooler or only a dependent service failed.
4. Check PostgreSQL logs, storage health, recent maintenance and unexpected restart.
5. For self-managed, PLT/DBRE inspect instance/service state; for managed services check provider events and open ticket.
6. Before any promotion, confirm **independent fencing of old primary**, current recovery point and business failover authority.

**Recovery validation:** one writer only, correct endpoint, read/write application smoke tests, active standbys/slots, performance and freshness SLO.

## 3. PG-INC-002 — High connections / connection-pool exhaustion

**Symptoms:** "too many clients already", pool waiting, application timeouts, many idle sessions.

~~~~sql
SELECT datname, usename, state, COUNT(*) AS sessions
FROM pg_stat_activity
GROUP BY datname, usename, state
ORDER BY sessions DESC;

SHOW max_connections;
SHOW superuser_reserved_connections;
~~~~

Inspect APP pool size versus actual DB configured max, transaction pooling limitations, idle-in-transaction sessions, connection churn and authentication errors. Do not blindly increase max_connections: each connection consumes resources. APP owns pool/concurrency changes; DBRE governs database slots and capacity. Do not kill sessions as a routine shortcut.

## 4. PG-INC-003 — Slow queries / high CPU / I/O

**Symptoms:** APP p95/p99 rises, heavy waits, CPU or storage read latency increases.

~~~~sql
SELECT pid, datname, usename, state, wait_event_type,
       wait_event, now()-query_start AS runtime
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY query_start NULLS LAST LIMIT 30;

SELECT datname, blks_read, blks_hit, tup_returned,
       tup_fetched, temp_files, temp_bytes
FROM pg_stat_database WHERE datname IS NOT NULL;
~~~~

Check APP request and SQL query IDs, execution plan, read/write pressure, temp spills, index/pruning behavior, slow I/O, connection pool and host/cloud events. pg_stat_statements is optional and requires correct preload/extension; do not assume installed. EXPLAIN ANALYZE **executes** the statement and can cause changes or heavy load; first inspect EXPLAIN without ANALYZE or run safely in staging. APP owns SQL semantic refactor, DBRE diagnostics and index/tuning review. Validate end-to-end SLO and write throughput.

## 5. PG-INC-004 — Blocking locks and deadlocks

**Symptoms:** long lock wait, deadlock errors, growing blocked transactions.

~~~~sql
SELECT pid, usename, datname, state, wait_event_type, wait_event,
       now()-xact_start AS xact_age, pg_blocking_pids(pid) AS blockers
FROM pg_stat_activity
WHERE cardinality(pg_blocking_pids(pid)) > 0
ORDER BY xact_start NULLS LAST LIMIT 50;

SELECT datname, deadlocks, stats_reset
FROM pg_stat_database WHERE datname IS NOT NULL;
~~~~

Correlate blocker PID, transaction owner, statement class, migration/DML, timeouts and app deadlock retry semantics. Differentiate idle-in-transaction and active long transaction. Cancel versus terminate is not equivalent; neither is safe without business impact review. Document APP-approved victim selection, evidence and transaction correctness after mitigation.

## 6. PG-INC-005 — Replication lag / standby not receiving WAL

**Symptoms:** stale reads, standby replay time behind, failed HA readiness, growing slot retention.

~~~~sql
-- Primary
SELECT application_name, state, sync_state,
       sent_lsn, write_lsn, flush_lsn, replay_lsn,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;

-- Standby (run in standby context)
SELECT pg_is_in_recovery() AS standby,
       pg_last_wal_receive_lsn() AS last_received,
       pg_last_wal_replay_lsn() AS last_replayed,
       pg_last_xact_replay_timestamp() AS last_replay_commit_time;
~~~~

Intervals may be NULL or misleading on an idle primary. Confirm WAL LSN progress, write workload, network, IO, standby conflicts and physical/logical mode. **pg_last_xact_replay_timestamp** reflects the most recently replayed commit, not a direct RPO if no writes are occurring. Coordinate with APP/DATA before routing reads to lagging standby, forcing resync or promoting.

## 7. PG-INC-006 — Replication slot retaining WAL / disk runway

**Symptoms:** pg_wal disk fills despite ordinary table/storage growth, replication consumers down.

~~~~sql
-- On primary
SELECT slot_name, slot_type, active, restart_lsn,
       CASE WHEN restart_lsn IS NOT NULL
            THEN pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)
       END AS approx_retained_wal_bytes
FROM pg_replication_slots;

SELECT current_setting('max_slot_wal_keep_size') AS max_slot_wal_keep_size,
       current_setting('wal_keep_size') AS wal_keep_size;
~~~~

Replicas, logical subscribers and CDC tools may depend on each slot. Default max_slot_wal_keep_size=-1 can allow unbounded WAL retained by a slot. Restoring a disconnected consumer may require WAL from archive or a full resnapshot. Never drop a slot solely to free disk; DATA/APP must approve lost replay/resync risks. Check provider slots and storage limits.

## 8. PG-INC-007 — WAL archiving failure / PITR exposure

~~~~sql
SELECT archived_count, last_archived_wal, last_archived_time,
       failed_count, last_failed_wal, last_failed_time, stats_reset
FROM pg_stat_archiver;

SHOW archive_mode;
~~~~

Review last archived WAL against actual segment generation and backlog, repository permissions, archiver error logs, quota and network. Counters are not enough to guarantee an intact WAL chain. In managed services, rely on backup/PITR service last restorable time and cloud telemetry. Do not silently disable archiving, alter WAL settings or prune required WAL during an incident.

## 9. PG-INC-008 — Autovacuum lag / high bloat

~~~~sql
SELECT schemaname, relname, n_live_tup, n_dead_tup,
       last_vacuum, last_autovacuum, autovacuum_count,
       last_analyze, last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC LIMIT 50;

SELECT pid, datname, relid AS relation_oid,
       phase, heap_blks_total, heap_blks_scanned
FROM pg_stat_progress_vacuum;

-- Relation OIDs are database-local. Resolve relation_oid to a name only
-- while connected to the matching datname; do not cast a foreign
-- database's relation OID to regclass in your current database.
~~~~

Inspect long-running snapshots, replication feedback, vacuum cost delay, insert/update/delete churn, disk IO and table-level thresholds. Dead tuple estimates are approximate; do not automatically VACUUM FULL (exclusive lock and disk). Ordinary autovacuum/VACUUM can run without blocking normal reads/writes generally, though workloads and certain operations can still be impacted. Tune with controlled staging evidence.

## 10. PG-INC-009 — Transaction ID / multixact wraparound risk

~~~~sql
SELECT datname, age(datfrozenxid) AS database_xid_age,
       current_setting('autovacuum_freeze_max_age')::bigint AS freeze_max_age
FROM pg_database ORDER BY database_xid_age DESC;

SELECT n.nspname, c.relname,
       age(c.relfrozenxid) AS relation_xid_age
FROM pg_class c
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE c.relkind IN ('r','m') AND n.nspname NOT IN ('pg_catalog','information_schema')
ORDER BY relation_xid_age DESC LIMIT 50;
~~~~

Also assess multixact age, active and idle-in-transaction blockers, autovacuum workers and XID burn rate. Wraparound is a **data availability/correctness emergency**; do not disable autovacuum or defer anti-wraparound VACUUM. Escalate promptly, obtain qualified DBRE peer review and a recovery plan before heavy maintenance.

## 11. PG-INC-010 — Disk exhausted, WAL growth, temp-file explosion

**Symptoms:** "no space left on device", write/commit failures, high temp_bytes, WAL archive/slot failures.

- Check OS/cloud **actual free bytes** on data, WAL, temp and log volumes.
- Review table/index size and growth, WAL slot retention, replication/archiving and large sorts/temp files.
- For managed services examine storage autoscale/saturation and provider events.
- Prefer safe storage increase or recovery of stalled consumers; do not drop business tables, disable archiving, delete pg_wal contents, truncate logs unsafely or disable fsync to restore writes.

**Recovery:** verify WAL and backup coverage, writes, replication, disk forecast and APP integrity.

## 12. PG-INC-011 — Backup or PITR restore failure

Assess last successful **complete** base backup, archived WAL chain, manifest verification, provider backup status/latest restorable time, credentials, source version and restore target. A file dump is **not** a physical base backup and cannot be WAL-replayed for PITR. Run an authorized isolated restore in staging and prove recovery by querying test data and business functions. Any source-to-target cutover requires incident authority and APP/DATA sign-off.

## 13. PG-INC-012 — Split brain / failed promotion / failback risk

**Danger:** Two writable PostgreSQL primaries are a severe integrity risk. Immediately apply approved independent fencing/traffic isolation and incident command; do not simply repoint DNS and assume the old primary has stopped accepting writes. For controlled promotion record timeline, recovery target LSN, slot/rebuild strategy, WAL divergence, pg_rewind eligibility and recovery/rollback. Standby promotion and rewind are **not** reversible one-step operations. Validate **single-writer**, data reconciliation, client/pooler routing and approved RPO/RTO.

## 14. PG-INC-013 — Authentication, TLS or migration failure

Investigate pg_hba.conf rules (self-managed), SSL mode/cert chain, expired secrets, managed identity/IAM, service role grants, endpoint changes and failed schema migrations. SEC/PLT and APP own their respective parts. Never disable TLS/authentication or grant SUPERUSER broadly to resolve an incident. A migration lock or long DDL may impact live traffic; ensure rollback and migration-owner sign-off.

## 15. Mandatory evidence and communication template

| Field | Entry |
|---|---|
| Incident ID / P-level / UTC start | |
| Account/instance/region/version and role | |
| APP operations affected; read/write/error/SLO | |
| Locks, query IDs, waits, xact age and counters | |
| Replica/slot/WAL/archive state | |
| Disk, CPU, memory and managed service events | |
| Last complete backup, last restorable point | |
| Technical cause, uncertainty, recent changes | |
| Approved mitigation/rollback and executor | |
| APP/DATA reconciliation / service restore UTC | |
| Vendor ticket, RCA owner and next steps | |

Treat query text, user IDs, credentials and patient data as restricted. Prefer sanitized query IDs, time windows and trend charts. Declare recovery **only** after APP and DATA validate business workflows.

## 16. Staging/tabletop acceptance

- [ ] All 13 incident scenarios reviewed with named DBRE and partner owners.
- [ ] Read-only commands validated with intended PostgreSQL version and managed-service privileges.
- [ ] Lock/blocker, connection exhaustion, replica lag and WAL retention simulations conducted safely.
- [ ] Vacuum/freeze and storage pressure playbooks reviewed for data safety.
- [ ] Fencing/single-writer, promotion/rebuild/rewind and rollback rehearsal approved.
- [ ] PITR and full service recovery exercise produces measured RPO/RTO.
- [ ] APP query and DATA record checks pass after recovery.
- [ ] Vendor escalation, ticket templates, alert routing and RCA adopted.

## References
- [PostgreSQL monitoring](https://www.postgresql.org/docs/current/monitoring-stats.html)
- [Replication](https://www.postgresql.org/docs/current/warm-standby.html)
- [Vacuum and wraparound](https://www.postgresql.org/docs/current/routine-vacuuming.html)
- [WAL and archive](https://www.postgresql.org/docs/current/continuous-archiving.html)
