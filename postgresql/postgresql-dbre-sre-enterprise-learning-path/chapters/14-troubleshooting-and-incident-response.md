# Chapter 14 — Troubleshooting and Incident Response

**Audience:** PostgreSQL DBRE/SRE and application on-call engineers · **Duration:** 60 minutes · **Reference:** PostgreSQL 17, local Docker (Linux containers; Windows PowerShell examples) · **Status:** Authored only; runtime execution and independent review pending.

[Learning path](../README.md) · [Master TOC](../MASTER-TOC.md) · [Chapter 14 lab](../labs/chapter-14/README.md) · [Progress tracker](../STATUS-TRACKER.md)

## Learning objectives

Triage PostgreSQL incidents without worsening them; distinguish symptoms from causes; inspect connection pressure, blocking locks, deadlocks, WAL/replication lag, storage exhaustion, and slow queries; identify safe mitigation boundaries; communicate impact and recovery evidence. **Never treat a diagnostic query as authorization for a production change.**

## Prerequisites and version/platform assumptions

Complete Chapters 01–05 and preferably Chapters 10–13. Be comfortable with SQL transactions, MVCC, locks, WAL, and PostgreSQL statistics. Examples target PostgreSQL **17** on a **disposable local Docker container**, with no host port, no cloud account, and no production data. Some monitoring views require elevated privileges for full visibility; on AWS RDS or operator-managed Kubernetes, permissions and host-level access differ. Never assume the local superuser model applies to managed PostgreSQL.

## 60-minute teaching outline

| Minutes | Topic | Outcome |
|---|---|---|
| 0–10 | Incident command, impact, scope, safety | Establish identity, severity, evidence owner |
| 10–20 | Connection exhaustion and query latency | Distinguish saturation from waiting |
| 20–30 | Locks, deadlocks and safe mitigation | Identify blockers and transaction boundaries |
| 30–45 | [Isolated Chapter 14 lab](../labs/chapter-14/README.md) | Reproduce and observe a bounded lock wait |
| 45–53 | Replication, WAL, storage and recovery | Interpret failure patterns and escalation |
| 53–60 | Acceptance, communications, post-incident actions | Produce a blameless incident note |

## 1. Operational architecture: where incidents appear

~~~text
Client / application pool
  |  connections, retries, timeouts
  v
PostgreSQL listener -> backend processes -> locks / MVCC / SQL plans
                           |                   |
                           v                   v
                     shared buffers       table/index storage
                           |
                       WAL writer -> pg_wal -> archive / standby
                           |
                 checkpoint / OS filesystem
~~~

The same application symptom can have different root causes. A timeout might be a saturated connection pool, a lock wait, slow I/O, a bad query plan, a network interruption, or a standby replay conflict. **Correlate** application error rate and latency with PostgreSQL evidence and infrastructure signals before selecting a remedy.

### Incident operating sequence

1. **Declare:** incident ID, severity, business SLO, affected services, owner, UTC timeline and change freeze.
2. **Verify target:** environment, cluster identity, host/instance, database, primary versus standby, PostgreSQL version and recent changes.
3. **Preserve evidence:** timestamped snapshots of metrics, logs, SQLSTATE/error codes, active sessions, storage, replication and deployment events; redact secrets and patient/customer data.
4. **Diagnose:** compare current state to a known-good baseline; form and test a hypothesis using read-only queries.
5. **Mitigate only with approval:** identify action owner, blast radius, dependencies, rollback, stop conditions and communication cadence.
6. **Validate:** user-visible error rate and latency, application connectivity, writer identity, WAL retention, replication and disk headroom.
7. **Close and learn:** document causal chain, contributing conditions, gaps, owner and preventive work without blaming individuals.

## 2. Read-only triage SQL (PostgreSQL 17)

Run in the intended database. Query text can contain sensitive values; collect only sanitized output. Some other-user activity fields are restricted without pg_read_all_stats or superuser privileges.

### Identity, uptime and configuration

~~~sql
SELECT now() AS observed_at, current_database() AS db,
       current_user AS observer, version() AS server_version,
       pg_is_in_recovery() AS is_standby,
       pg_postmaster_start_time() AS started_at;
SHOW max_connections;
SHOW superuser_reserved_connections;
SHOW reserved_connections;
SHOW statement_timeout;
SHOW lock_timeout;
~~~

The reserved connection settings matter: not all configured connection slots are available to ordinary roles. **Do not use max_connections minus a simple count as an exact admission guarantee.**

### Connection pressure and transaction age

~~~sql
SELECT datname, state, wait_event_type, count(*) AS sessions
FROM pg_stat_activity
WHERE backend_type = 'client backend'
GROUP BY datname, state, wait_event_type
ORDER BY sessions DESC;

SELECT pid, datname, usename, application_name, state,
       now() - xact_start AS transaction_age,
       wait_event_type, wait_event,
       left(query, 100) AS query_sample
FROM pg_stat_activity
WHERE backend_type = 'client backend'
ORDER BY xact_start NULLS LAST LIMIT 30;
~~~

**Interpretation:** idle sessions may be legitimate pool capacity; idle-in-transaction sessions may retain locks and snapshots. Look at client pool limits, connection churn, error codes, CPU/memory and application demand. Avoid increasing max_connections as an automatic fix: backend memory and OS resources are finite. A connection spike can be a symptom of slow queries or retries.

### Blocking graph and locks

~~~sql
SELECT a.pid AS waiting_pid, a.application_name, a.state,
       a.wait_event_type, a.wait_event,
       now() - a.query_start AS waiting_query_age,
       pg_blocking_pids(a.pid) AS blocking_pids
FROM pg_stat_activity AS a
WHERE cardinality(pg_blocking_pids(a.pid)) > 0
ORDER BY waiting_query_age DESC;

SELECT pid, locktype, mode, granted, relation::regclass AS relation_name
FROM pg_locks
WHERE database = (SELECT oid FROM pg_database WHERE datname=current_database())
  AND relation IS NOT NULL
ORDER BY granted, pid LIMIT 40;
~~~

The lock manager includes relation and transaction-ID locks; a blocked row update may be waiting on a transaction-ID lock rather than a row visible in pg_locks. Use **pg_blocking_pids** rather than relying on a naive self-join of pg_locks to infer the true blocking chain. A long query is not necessarily a blocker; a session can be idle in a transaction while retaining locks.

### Deadlocks versus ordinary lock waits

PostgreSQL detects a deadlock and aborts **one** participating transaction, reporting SQLSTATE **40P01**; it does not simply leave both sessions waiting forever. An ordinary lock wait may resolve when the holder commits/rolls back, or fail on lock_timeout (SQLSTATE **55P03**). Deadlock count is cumulative and may reset:

~~~sql
SELECT datname, deadlocks, conflicts, stats_reset
FROM pg_stat_database
WHERE datname = current_database();
~~~

For a real deadlock, collect sanitized server log details, transaction order, SQLSTATE, application retry behavior and indexing/transaction design. Prevention often means consistent row-update ordering, short transactions, appropriate indexes and bounded retries with jitter. **Do not reproduce a deadlock on production.**

### Slow queries and wait classification

~~~sql
SELECT pid, application_name, state, wait_event_type, wait_event,
       now() - query_start AS query_age,
       left(query, 120) AS query_sample
FROM pg_stat_activity
WHERE state='active' AND pid <> pg_backend_pid()
ORDER BY query_start NULLS LAST LIMIT 20;
~~~

An active backend with a wait_event can be waiting, not burning CPU. Combine query plans, lock graphs, I/O, CPU, pool metrics and historical baselines. EXPLAIN ANALYZE **executes** a query: do not run it on an unreviewed expensive or data-modifying production statement. Prefer reviewed EXPLAIN (without ANALYZE) or sanitized staging reproduction first.

### WAL, replication and storage

~~~sql
SELECT pg_is_in_recovery() AS is_standby,
       pg_size_pretty(pg_database_size(current_database())) AS db_size;
SELECT slot_name, slot_type, active, restart_lsn, wal_status,
       safe_wal_size
FROM pg_replication_slots;
SELECT application_name, state, sync_state,
       sent_lsn, write_lsn, flush_lsn, replay_lsn,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;
SELECT status, receive_start_lsn, written_lsn, flushed_lsn,
       latest_end_lsn, latest_end_time
FROM pg_stat_wal_receiver;
SELECT archived_count, failed_count, last_failed_time, stats_reset
FROM pg_stat_archiver;
~~~

Interpret **by topology**: pg_stat_replication is meaningful on a sending server, pg_stat_wal_receiver on a receiving standby, and empty results are normal on a single-instance lab. Reported lag intervals can be NULL even when replication is healthy; a byte distance is not the same as RPO time. For slot retention, compare restart_lsn to current WAL position on the **primary**, and inspect wal_status/safe_wal_size with configuration and storage capacity. Do not drop slots, reset WAL, remove pg_wal files, or promote a standby as a troubleshooting shortcut.

Check **host/container filesystem capacity** and inode availability separately from pg_database_size. A database-size query does not measure free disk, WAL, backups, or other files. Storage pressure can halt writes and compromise recovery; escalate promptly.

## 3. Incident patterns and decision boundaries

| Symptom | Evidence to collect | Safe initial response | Requires change approval |
|---|---|---|---|
| Too many connections | SQLSTATE 53300, active/idle counts, pool size, application retries | Check pooler/client leak and recent deploy; preserve privileged access | Pool reconfiguration, max_connections, session termination |
| Lock waits | pg_blocking_pids, transaction age, app transaction ID | Contact transaction owner; identify blocker chain | pg_cancel_backend / pg_terminate_backend |
| Deadlocks | SQLSTATE 40P01, server logs, deadlock counter | Identify inconsistent lock ordering and retry policy | Application transaction changes |
| Slow queries | latency percentiles, wait events, plan, table/index statistics | Compare with baseline and recent schema changes | New indexes, config changes, query rewrites |
| Replication lag | sender/receiver state, WAL positions, slots, network, replay conflict | Assess lag trend and freshness SLO; check primary health | Slot changes, promotion, topology changes |
| WAL or disk pressure | df/inodes, WAL directory, archive errors, slots, write rate | Escalate storage risk and preserve WAL | Storage expansion, retention changes, restart |
| Vacuum/XID risk | age(datfrozenxid), dead tuples, long transactions | Identify blocking horizons; monitor worker progress | Vacuum tuning, transaction termination |

**Cancellation is not harmless:** pg_cancel_backend targets the current query; pg_terminate_backend ends a session and rolls back its active transaction, potentially affecting application work. Both require permission and an owner-approved decision. In HA, no remediation may violate single-writer/fencing requirements.

## 4. Guardrails, rollback and communication

**Before any production mitigation:** confirm environment and cluster ID twice; define impacted tenant/service and owner; obtain incident commander and DBRE/application approval per severity policy; establish an audit trail and known-good recovery path; ensure standby/backup health; set explicit stop conditions (increased error rate, latency, WAL growth, loss of quorum, ambiguous writer identity).

**Rollback examples:** reverse a reviewed pool/config change through the deployment mechanism; restore a previous application release; stop a planned maintenance operation if safe; **do not assume database changes are reversible** or a terminated session can be restored. Rollback for data-modifying operations requires a separately validated recovery strategy.

**Communication template:**
- Impact: affected service, start time UTC, symptom, current user-visible SLO.
- Findings: observed evidence with timestamps, confidence and remaining hypotheses.
- Action: approved owner, exact scope, expected risk, stop/rollback plan.
- Recovery: before/after metrics, application verification, primary identity, replication/storage health.
- Follow-up: preventive owner and due date, runbook/alert improvements.

## 5. Lab and acceptance

The [Chapter 14 lab](../labs/chapter-14/README.md) creates one isolated PostgreSQL 17 container and three psql sessions. It demonstrates a bounded row-lock wait with a third-session blocking-graph query. All data is synthetic, the demonstration updates are rolled back, and there is no deadlock generation, connection flood, failover, cloud usage or production operation.

**Acceptance checklist**
- [ ] Explain incident ownership, evidence preservation, blast radius and rollback boundary.
- [ ] Identify the correct database and primary/standby role before diagnosing.
- [ ] Read connection pressure and transaction age without assuming idle equals broken.
- [ ] Identify a blocker using pg_blocking_pids and distinguish it from a deadlock.
- [ ] Explain SQLSTATE 40P01 and 55P03 and why retries need bounds.
- [ ] Inspect WAL/replication/archiver and storage indicators without changing topology.
- [ ] Demonstrate a bounded synthetic lock wait in the disposable lab.
- [ ] Produce a sanitized incident summary with application verification and stop conditions.
- [ ] Separate written expected observations from **actual execution evidence** and independent review.

**Validation boundary:** Authored, not executed. No production-readiness certification.

## Official references (PostgreSQL 17)

- [Monitoring statistics: pg_stat_activity, pg_stat_replication, pg_stat_archiver](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [Viewing locks and pg_locks](https://www.postgresql.org/docs/18/monitoring-locks.html)
- [Explicit locking and deadlocks](https://www.postgresql.org/docs/18/explicit-locking.html)
- [Client connection defaults and timeouts](https://www.postgresql.org/docs/18/runtime-config-client.html)
- [Connection and authentication settings](https://www.postgresql.org/docs/18/runtime-config-connection.html)
- [Lock management and deadlock_timeout](https://www.postgresql.org/docs/18/runtime-config-locks.html)
- [Replication configuration and WAL retention](https://www.postgresql.org/docs/18/runtime-config-replication.html)
- [Continuous archiving and PITR](https://www.postgresql.org/docs/18/continuous-archiving.html)
