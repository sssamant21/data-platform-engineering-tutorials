# Chapter 068 — PostgreSQL Replication Slots, WAL Retention and Lag Management

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Diagnose and control WAL retention caused by physical and logical replication slots, distinguish transport and replay lag, protect CDC consumers, and recover safely from stalled replication without deleting required WAL. Builds on [Chapter 067](067-postgresql-streaming-replication-and-high-availability-architecture.md).

## 2. Replication slots: guarantees and risks

Physical slots protect WAL needed by physical standby consumers; logical slots track decoding progress and may also retain catalog rows via catalog_xmin. Slots are stateful retention mechanisms, **not backups**. A consumer can disconnect while its slot continues retaining WAL. Unbounded retention can fill pg_wal and take the primary offline.

| Field | Meaning | Operational use |
|---|---|---|
| slot_name, slot_type | Physical or logical consumer | Map to owner and endpoint |
| active, active_pid | Current slot usage | Identify disconnected/stalled consumers |
| restart_lsn | Oldest WAL possibly required | Estimate WAL retention exposure |
| confirmed_flush_lsn | Logical consumer acknowledged progress | Diagnose CDC lag; not a physical-slot field |
| catalog_xmin | Catalog row horizon retained by logical slot | Monitor vacuum/catalog impact |
| wal_status | reserved, extended, unreserved, lost | Detect slot WAL safety |
| safe_wal_size | Bytes writable before slot risks lost state | Alert before slot becomes unusable; may be NULL |
| inactive_since | When slot became inactive | Investigate long inactivity |
| invalidation_reason | Why a slot became invalid | Triage unusable slots |

PostgreSQL 18 exposes additional slot fields and settings; verify exact behavior in installed-version documentation. A NULL restart_lsn or safe_wal_size must not be interpreted as zero risk. With max_slot_wal_keep_size=-1, a slot may retain unlimited WAL and safe_wal_size can be NULL.

## 3. WAL retention controls

| Control | What it does | What it does not do |
|---|---|---|
| wal_keep_size | Minimum extra WAL kept for standby catch-up | Does not cap slot retention |
| max_slot_wal_keep_size | Bounds slot WAL retention at checkpoint | Does not guarantee stalled consumer remains recoverable |
| max_wal_size | Soft WAL checkpoint trigger | Not a hard disk usage cap |
| archive_mode + archive_command | Stores completed WAL off-cluster | Does not automatically clean inactive slots |
| replication slot | Protects WAL for registered consumer | Does not replace backup/PITR |

Setting max_slot_wal_keep_size may eventually invalidate a lagging slot if required WAL is removed. This protects disk but can force a standby rebase or logical resnapshot. Align thresholds with WAL generation rate, maximum outage and reinitialization RTO.

## 4. Inspect replication slots and lag

Run [Chapter 068 SQL](../labs/sql/068-slot-and-lag-inspect.sql) on the **primary** with appropriate monitoring privileges.

```sql
SELECT slot_name,slot_type,active,active_pid,restart_lsn,
       confirmed_flush_lsn,wal_status,safe_wal_size,inactive_since,invalidation_reason,
       CASE WHEN restart_lsn IS NOT NULL
         THEN pg_wal_lsn_diff(pg_current_wal_lsn(),restart_lsn)
       END AS retained_wal_bytes
FROM pg_replication_slots ORDER BY slot_name;
```

```sql
SELECT application_name,client_addr,state,sync_state,
       sent_lsn,write_lsn,flush_lsn,replay_lsn,
       pg_wal_lsn_diff(pg_current_wal_lsn(),replay_lsn) AS replay_gap_bytes,
       write_lag,flush_lag,replay_lag
FROM pg_stat_replication;
```

Do not treat retained_wal_bytes as exact pg_wal directory size: WAL recycling, segment granularity, archiving and checkpoint timing affect actual disk usage. Replay lag timestamps may be NULL or stale on idle clusters; use byte LSN progression, workload rate and application freshness.

## 5. Logical CDC slots

A logical replication consumer may acknowledge changes later than it processes them. Confirm slot ownership, publication/subscription identity, connector offsets, source transaction volume, consumer errors and replay/checkpoint semantics. Logical slots may hold xmin/catalog_xmin horizons that affect vacuum. Dropping a slot can require a full resnapshot and duplicate/reconciliation handling; do not assume re-creation resumes exactly.

## 6. Capacity model

```text
Estimated WAL backlog bytes = average WAL generation bytes/sec × consumer outage seconds
Disk headroom target >= expected backlog + burst margin + checkpoint/archive margin
Time to risk ≈ safe_wal_size / current WAL generation bytes/sec (if valid and rate > 0)
```

Use pg_stat_wal.wal_bytes deltas over a measured window to estimate WAL generation rate; counters can reset. Do not use transaction rate alone. Model peak bursts, checkpoints, archive delays, retention slots and recovery time. Alerts should fire well before disk exhaustion and before safe_wal_size reaches zero.

## 7. Operational decision tree

1. **Confirm impact:** pg_wal filesystem use, free space, archiver failures, slot states, WAL generation rate, current application errors.
2. **Identify consumer:** map slot to physical standby or logical CDC job; confirm owner, last successful consumption, service status and business importance.
3. **Recover consumer first:** repair network/auth/TLS, sender/receiver state, slow apply, CPU/I/O, conflicting long queries or CDC processing.
4. **Check safety:** wal_status, restart_lsn, safe_wal_size, oldest recoverable WAL, archived segments, backup chain, CDC offset and resnapshot plan.
5. **Escalate if critical:** provision temporary disk, throttle WAL-producing workload, repair archive pipeline and coordinate maintenance.
6. **Only after approval:** drop an abandoned slot or rebuild a lost consumer with documented impact and rollback. Never manually delete files in live pg_wal.

Example **read-only** inspection of logical progress:

```sql
SELECT slot_name,plugin,database,active,restart_lsn,confirmed_flush_lsn,catalog_xmin
FROM pg_replication_slots WHERE slot_type='logical';
```

Slot deletion syntax exists (`SELECT pg_drop_replication_slot('slot_name');`) but is intentionally **not** executed in this chapter's lab. It is destructive to the consumer's WAL retention guarantee.

## 8. Failure patterns

| Symptom | Likely cause | Safe response |
|---|---|---|
| Inactive slot and rising retained bytes | Consumer stopped or disconnected | Verify owner, restart consumer, capacity check |
| Slot wal_status=lost | Required WAL removed | Reinitialize/reseed consumer under approved plan |
| Logical slot catalog_xmin old | CDC not advancing | Investigate connector and vacuum pressure |
| Standby receives but does not replay | Replay conflict, I/O, long read query | Inspect standby waits and conflicts |
| Archive failures and WAL growth | Destination full/auth/command issue | Repair archiving; do not delete live WAL |
| Synchronous commit latency spikes | Required synchronous standby slow | Review sync policy and failover controls |

## 9. Monitoring and alerts

Monitor pg_wal disk utilization, WAL bytes/sec, slot retained bytes, slot age/inactivity, wal_status transitions, safe_wal_size, primary sender/standby receiver, replay LSN gap, archive failure delta, CDC checkpoint progress, replication errors and missing telemetry. Define warning/critical thresholds using **capacity and time-to-exhaustion**, not a universal fixed lag threshold. Differentiate critical production slots from intentionally idle test slots.

## 10. Hands-on lab and acceptance

Use [Chapter 068 lab](../labs/068-postgresql-replication-slots-wal-retention-and-lag-management-lab.md), [inspection SQL](../labs/sql/068-slot-and-lag-inspect.sql) and [WAL budget worksheet](../labs/monitoring/068-wal-capacity-worksheet.csv). The lab creates a disposable physical slot, observes retained WAL under bounded writes, checks consumer ownership and performs a dry-run recovery decision. Cleanup drops only a specifically verified **lab-owned** inactive slot.

**Acceptance:** correct slot/consumer mapping, WAL retention calculation, alerts and recovery decision documented, no production WAL removed, consumer impact evaluated. Runtime pending.

## References

- https://www.postgresql.org/docs/18/view-pg-replication-slots.html
- https://www.postgresql.org/docs/18/runtime-config-replication.html
- https://www.postgresql.org/docs/18/monitoring-stats.html
- https://www.postgresql.org/docs/18/warm-standby.html

**Next:** Chapter 069 — PostgreSQL Synchronous Replication and Commit Durability.