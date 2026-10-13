# Chapter 072 — PostgreSQL High Availability Observability and Failure Recovery

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Build actionable PostgreSQL HA observability and a safe post-failover recovery process. Detect primary/standby degradation, DCS quorum loss, fencing failure, replication lag, stale writer routing, failed application transactions and broken backup continuity. Restore not just database leadership, but **end-to-end service availability and redundancy**. Builds on [Chapter 071 — HA Automation](071-postgresql-ha-automation-leader-election-and-failover-orchestration.md).

## 2. Operational architecture

```text
PostgreSQL primary + standbys --- pg_stat_* / logs -----------+
Patroni agents + DCS --------- leader/quorum/fencing events ---+--> metrics/logs --> alerts --> on-call
HAProxy / PgBouncer ----------- writer route / sessions -------+
Application ------------------ success, errors, retries ------+
Backup / WAL archive --------- backup age, WAL continuity -----+
                                                                |
                                                     incident timeline + recovery gates
```

PostgreSQL exposes database state but does not expose authoritative Patroni/DCS quorum and fencing state by itself. Combine database, HA manager, proxy, infrastructure and application telemetry. No single metric proves failover safety.

## 3. Golden signals and SLOs

| Signal | Source | Operational question |
|---|---|---|
| Current writable leader count | PostgreSQL + HA manager + routing | Is there exactly one authoritative writer? |
| DCS quorum and lease renewal | etcd/Patroni | Can leadership be maintained safely? |
| Fencing/watchdog result | HA manager, infrastructure audit | Can the old leader still accept writes? |
| Replica receive/replay LSN | pg_stat_replication, pg_stat_wal_receiver | Is standby eligible and current? |
| WAL retention and archive failures | pg_replication_slots, pg_stat_archiver | Is recovery continuity at risk? |
| Sync commit waits | pg_stat_activity / pg_stat_replication | Are COMMITs blocked on standby acknowledgment? |
| Proxy writer backend | HAProxy/PgBouncer | Do client writes reach the elected primary? |
| Application success/error rate | APM and synthetic writes | Is the service actually available? |
| Backup restore freshness | Backup system and restore drills | Can the system recover historically? |

Suggested SLOs must be explicitly negotiated: successful write availability, p95/p99 transaction latency, recovery time, data-loss window, replica lag, backup freshness and alert delivery. Avoid arbitrary universal thresholds.

## 4. PostgreSQL diagnostic SQL

Run [072 HA observability SQL](../labs/sql/072-ha-observability-inspect.sql) on each node with role-appropriate monitoring privileges:

```sql
SELECT pg_is_in_recovery() AS is_standby, clock_timestamp() AS inspected_at;

SELECT application_name,state,sync_state,
       sent_lsn,write_lsn,flush_lsn,replay_lsn,
       write_lag,flush_lag,replay_lag
FROM pg_stat_replication;

SELECT slot_name,slot_type,active,restart_lsn,wal_status,safe_wal_size
FROM pg_replication_slots;

SELECT pid,application_name,wait_event_type,wait_event
FROM pg_stat_activity
WHERE wait_event='SyncRep';
```

`write_lag`, `flush_lag` and `replay_lag` are not continuously updated elapsed-time backlog measures. They may be NULL on idle systems. `pg_last_xact_replay_timestamp()` can look old when there are no new commits. Correlate byte LSN gap, change rate, replay progression and application freshness.

## 5. HA control plane monitoring

Collect Patroni leader/replica status and failover history through the installed version's supported CLI or restricted API. Collect etcd member health, leader changes, quorum status, storage alarms and lease renewal failures using authenticated etcd telemetry. Collect watchdog/fencing outcomes from a **separate authority**, not solely the node being fenced. Track HA manager process restarts and DCS latency.

**Quorum loss is a safety event, not merely a monitoring outage.** A partitioned node must not self-elect without authority. Fail closed and escalate when fencing cannot be proven.

## 6. Alerting strategy

| Alert | Trigger concept | Priority | Required action |
|---|---|---|---|
| Dual writer suspected | More than one writable primary / inconsistent leader identity | Critical | Freeze writes and initiate split-brain response |
| DCS quorum lost | Majority unavailable or lease renewal failing | Critical | Validate fencing, stop unsafe promotions |
| Writer endpoint wrong | Proxy backend disagrees with leader | Critical | Fail closed, drain stale sessions |
| No eligible standby | No healthy candidate for failover | High | Restore redundancy |
| WAL retention risk | Low safe_wal_size / disk time-to-full | High | Repair consumer, protect WAL and disk |
| Archive failures | Increasing failed_count / no valid WAL continuity | High | Repair archive and verify backup chain |
| SyncRep blocked | Persistent synchronous wait and write errors | High | Recover standby or invoke approved policy |
| HA application probe fails | Synthetic write/read unsuccessful | High | Trace routing, DB and application |

Route alerts to named owners with deduplication, inhibition and escalation. Use multiple observations and failure-domain context to avoid paging on idle replication timestamps. Alerts should link directly to runbooks.

## 7. Failure triage decision tree

1. **Confirm impact:** app errors, failed synthetic writes, latency, active incidents and blast radius.
2. **Check single-writer invariant:** compare DCS leader, Patroni role, PostgreSQL `pg_is_in_recovery()` and proxy target. If inconsistent, stop writes.
3. **Check control plane:** DCS quorum, leader lease, watchdog/fencing and orchestration events.
4. **Check replication:** sender/receiver state, LSN progression, slot retention, synchronous commit waits and standby logs.
5. **Check routing:** DNS, proxy backend, connection pools, stale sessions and credential/TLS errors.
6. **Check recoverability:** backup freshness, archive status, storage, WAL continuity and latest recovery point.
7. **Restore safely:** fix cause, recover redundancy, reconcile ambiguous commits, verify application SLOs, then close incident.

## 8. Post-failover recovery checklist

- Prove exactly one writable leader and that old primary is fenced.
- Verify promotion timeline, DCS lease ownership, proxy routing and application reconnection.
- Reconcile timed-out transactions using idempotency keys; never assume a timeout means rollback.
- Safely rewind or rebuild the former primary; verify its new standby role and replay.
- Restore synchronous replica count, replication slots, WAL archive and backup schedules.
- Verify client latency/error rate and successful synthetic write/read checks.
- Record incident start, detection, fencing, promotion, routing, validation and redundancy restoration timestamps separately.
- Recalculate achieved RPO/RTO and capture follow-up action items.

## 9. Failure injection and acceptance

Use [Chapter 072 lab](../labs/072-postgresql-high-availability-observability-and-failure-recovery-lab.md), [SQL diagnostics](../labs/sql/072-ha-observability-inspect.sql) and [incident acceptance scorecard](../labs/acceptance/072-ha-observability-scorecard.csv).

| Scenario | Expected detection | Recovery evidence |
|---|---|---|
| Replica disconnect | Receiver/sender missing, lag rises | Standby reconnected and replay caught up |
| Synchronous standby unavailable | SyncRep waits and app write latency/errors | Eligible standby restored, policy unchanged or approved |
| DCS voter failure | Quorum/member health warning | Majority maintained and voter recovered |
| Quorum loss | Critical coordination alert | No unsafe second writer; quorum restored |
| Stale proxy backend | App probe failure / route mismatch | Endpoint corrected, stale connections drained |
| Primary failure | Leader change, client errors | Fencing, one leader, RPO/RTO measured |
| Backup/archive failure | Backup age/archive failure alert | Backup and WAL continuity revalidated |

A green database health check is not sufficient to pass. Mandatory gates include single-writer safety, alert delivery, transaction reconciliation, restored redundancy, application recovery and backup continuity. Unexecuted tests are **NOT VERIFIED**, not PASS.

## 10. References

- https://www.postgresql.org/docs/18/monitoring-stats.html
- https://www.postgresql.org/docs/18/warm-standby.html
- https://patroni.readthedocs.io/
- https://etcd.io/docs/

**Next:** Chapter 073 — PostgreSQL Multi-Zone High Availability and Disaster Recovery Design.
