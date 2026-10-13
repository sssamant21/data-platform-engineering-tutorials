# Chapter 048 — Replication Lag, Standby Conflicts and Recovery Operations

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Authored; runtime validation pending

## 1. Mission

Diagnose PostgreSQL streaming replication lag across transport, write, flush and replay; understand hot-standby query conflicts; and recover a delayed replica without hiding data loss or disrupting production. This chapter follows [Chapter 047 — Replication Slots and WAL Retention](047-postgresql-replication-slots-wal-retention-and-failure-modes.md).

## 2. Replication data path

```text
Primary commits -> WAL generation -> walsender -> network -> walreceiver
                                                        |
                                                standby WAL write
                                                        |
                                                standby WAL flush
                                                        |
                                                startup/replay process
                                                        |
                                                standby query visibility
```

**Transport lag** occurs before WAL reaches the standby. **Write/flush lag** occurs when received WAL is slow to persist. **Replay lag** occurs when WAL is available but the standby has not applied it. These are different bottlenecks with different remedies.

## 3. Primary-side metrics

```sql
SELECT pid,application_name,client_addr,state,sync_state,
       sent_lsn,write_lsn,flush_lsn,replay_lsn,
       pg_wal_lsn_diff(pg_current_wal_lsn(),sent_lsn) AS unsent_bytes,
       pg_wal_lsn_diff(sent_lsn,write_lsn) AS network_write_gap_bytes,
       pg_wal_lsn_diff(write_lsn,flush_lsn) AS unflushed_bytes,
       pg_wal_lsn_diff(flush_lsn,replay_lsn) AS replay_gap_bytes,
       write_lag,flush_lag,replay_lag
FROM pg_stat_replication;
```

Lag interval fields are observations for recent WAL and synchronous-replication acknowledgments; they are **not** a reliable prediction of catch-up time. NULL does not necessarily mean zero lag. LSN differences are bytes, not seconds. Correlate with WAL generation rate, network, disk throughput and replica CPU.

## 4. Standby-side metrics

```sql
SELECT pg_is_in_recovery() AS is_standby,
       pg_last_wal_receive_lsn() AS received_lsn,
       pg_last_wal_replay_lsn() AS replayed_lsn,
       pg_wal_lsn_diff(pg_last_wal_receive_lsn(),pg_last_wal_replay_lsn())
          AS received_not_replayed_bytes,
       pg_last_xact_replay_timestamp() AS last_replayed_commit_time;

SELECT status,receive_start_lsn,written_lsn,flushed_lsn,
       latest_end_lsn,latest_end_time,slot_name,sender_host,sender_port
FROM pg_stat_wal_receiver;

SELECT datname,confl_tablespace,confl_lock,confl_snapshot,
       confl_bufferpin,confl_deadlock,confl_active_logicalslot
FROM pg_stat_database_conflicts;
```

Run these on the standby. `pg_last_xact_replay_timestamp()` reflects the most recent replayed commit, not a universal wall-clock lag gauge. On a quiet primary it may appear stale even when a replica is fully caught up. Confirm current activity and LSN positions.

## 5. Hot standby conflicts

Read queries on a hot standby can conflict with recovery: vacuum cleanup records, DDL locks, dropped tablespaces, buffer pins and snapshot visibility can delay replay or force query cancellation. PostgreSQL records conflict counts in `pg_stat_database_conflicts`; these counters are cumulative and can reset.

Key settings:

- `max_standby_streaming_delay`: total delay budget for applying streamed WAL before conflicting standby queries may be canceled; **not** a per-query execution timeout.
- `max_standby_archive_delay`: analogous budget when replaying WAL from archive.
- `hot_standby_feedback`: standby informs upstream about snapshots to reduce some cleanup conflicts, but can increase dead tuples and table bloat on the primary. It does not eliminate all conflict types.
- `recovery_min_apply_delay`: intentionally delays replay for delayed-standby use cases; account for it when interpreting lag.
- `statement_timeout` and `idle_in_transaction_session_timeout`: can bound problematic standby queries, but require application review.

**Tradeoff:** allowing long read queries on a standby may increase recovery lag; prioritizing replay may cancel reads. Set policies by workload and SLO.

## 6. Investigation workflow

1. Establish topology, PostgreSQL versions, primary/standby roles, replication mode and recent failovers.
2. On primary, capture `pg_stat_replication`, WAL generation, `pg_replication_slots`, archiver health and filesystem pressure.
3. On standby, capture `pg_stat_wal_receiver`, receive/replay LSNs, conflicts, active sessions, wait events, disk latency and CPU.
4. Compare repeated samples to determine whether **unsent**, **unflushed** or **unreplayed** bytes are growing. Avoid diagnosing from a single sample.
5. Inspect standby logs for recovery conflicts, canceled statements, missing WAL and receiver reconnections.
6. Identify root cause: network congestion, saturated storage, CPU contention, long queries, cleanup conflicts, intentional delay, missing WAL or consumer disconnect.
7. Choose the least disruptive corrective action; document recovery risks and validate catch-up.

## 7. Incident patterns

| Symptom | Likely cause | Response |
|---|---|---|
| Sender state disconnected | Network, credentials, upstream failure | Inspect receiver logs and connectivity |
| sent/write gap grows | Network or standby write bottleneck | Measure network, receiver and disk |
| write/flush gap grows | Standby disk flush pressure | Check fsync latency, IOPS and WAL storage |
| flush/replay gap grows | Slow apply, conflicts, CPU/I/O | Inspect standby waits, conflicts and queries |
| Conflict cancellations increase | Vacuum cleanup, DDL, buffer pins | Tune query workload and standby policy |
| WAL unavailable | Slot lost or archive gap | Reinitialize standby from verified backup |
| Replica never catches up | Sustained WAL generation exceeds replay throughput | Capacity, workload and resync assessment |
| Standby stale after idle | No new commits | Compare LSNs; do not rely on timestamp alone |

## 8. Safe recovery operations

- Prefer resolving underlying network, I/O, query or resource constraints before changing recovery parameters.
- Consider canceling a problematic standby query only after verifying ownership and impact; avoid indiscriminate backend termination.
- Treat `hot_standby_feedback` as a primary-bloat tradeoff, not a universal performance fix.
- Do not manually delete WAL, blindly drop slots, change synchronous replication quorum, or promote a lagging standby without an approved failover decision.
- If WAL continuity is lost, rebuild the standby from a verified physical backup; document expected RPO, downtime and resynchronization load.
- For a planned restart, verify replica catch-up and downstream application read routing before and after maintenance.

## 9. Monitoring and alerting

Track lag by stage (LSN bytes), WAL generation and replay rates, receiver connectivity, conflict deltas, standby query cancellations, primary WAL retention, archive failures, standby disk latency, CPU, replica restart age and achieved data freshness. Alert on sustained SLO violations and projected storage exhaustion, not on a single idle timestamp.

## 10. Lab and acceptance

[Chapter 048 lab](../labs/048-replication-lag-standby-conflicts-and-recovery-operations-lab.md) provides primary/standby read-only SQL and a controlled workload worksheet. The lab does not automate failover, termination or replication reconfiguration.

**Acceptance:** distinguish lag stages; interpret conflict counters; identify a safe intervention and validate catch-up; document primary bloat and data-loss tradeoffs. **Runtime:** pending.

## Official references

- [Streaming replication monitoring](https://www.postgresql.org/docs/18/warm-standby.html#STREAMING-REPLICATION-MONITORING)
- [Monitoring statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [Hot standby](https://www.postgresql.org/docs/18/hot-standby.html)
- [Replication settings](https://www.postgresql.org/docs/18/runtime-config-replication.html)

**Next:** Chapter 049 — Replication Failover, Rejoin and Timeline Recovery.
