# Chapter 067 — PostgreSQL Streaming Replication and High Availability Architecture

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Design and observe a PostgreSQL primary/standby topology that balances availability, data-loss exposure, query offload and operational safety. Understand streaming replication internals, WAL retention, synchronous commit tradeoffs, read routing, failover coordination and split-brain prevention. This chapter follows the [backup and DR acceptance capstone](066-postgresql-backup-and-disaster-recovery-acceptance-lab.md).

## 2. Reference topology

```text
                    application write endpoint
                              |
                   HA routing / leader discovery
                              |
                       PostgreSQL PRIMARY
                         |           |
              WAL stream (async)    WAL stream (sync candidate)
                         |           |
                    STANDBY A     STANDBY B
                         |           |
                     read endpoint (only if lag and consistency policy allow)

     DCS / orchestrator + fencing + quorum + monitoring + backups/PITR
```

Streaming replication transmits WAL records to standby servers, which replay them to maintain physical copies. PostgreSQL's built-in replication does **not** automatically provide safe leader election, fencing, client endpoint switching or split-brain prevention. Use a tested HA manager (for example Patroni with a supported distributed configuration store) or managed-service orchestration; a load balancer alone is insufficient.

## 3. Primary, standby and WAL lifecycle

- The primary generates WAL and exposes WAL sender processes.
- The standby receives WAL via a WAL receiver, writes it, and replays it for consistent reads.
- Streaming may be supplemented by archived WAL for catch-up and disaster recovery.
- A standby can lag due to network delay, I/O, CPU, long read queries or replay conflicts.
- Physical replication is cluster-wide; the standby normally runs in recovery and cannot accept ordinary writes.

## 4. Asynchronous vs synchronous replication

| Mode | Commit behavior | Availability impact | Data-loss exposure |
|---|---|---|---|
| Asynchronous | Primary can acknowledge before standby receives WAL | Usually lower write latency | Recent acknowledged transactions may be lost if primary is unrecoverable |
| Synchronous remote_write | Wait for WAL to be written by synchronous standby | Depends on standby/network | Not the same as durable flush |
| Synchronous on | Wait for standby durable WAL flush | Can block writes when required standby unavailable | Stronger protection for acknowledged commits |
| Synchronous remote_apply | Wait for standby replay | Highest latency potential | Read-after-write visibility on synchronous standby |

PostgreSQL synchronous replication depends on **both** synchronous_standby_names and transaction-level synchronous_commit semantics. With an empty synchronous_standby_names, the remote wait modes do not wait for a synchronous standby. Select ANY/FIRST standby policies and failure behavior intentionally. Synchronous replication is not a substitute for independent historical backups.

## 5. WAL retention and replication slots

Slots can prevent removal of WAL required by a lagging standby, but an abandoned or stalled slot can cause unbounded pg_wal growth unless max_slot_wal_keep_size and monitoring are configured appropriately. wal_keep_size is a minimum WAL retention setting, not a guarantee of enough history for arbitrary outages. Archive continuity and slot restart_lsn should be observed. Do not drop or advance slots without proving consumers and recovery implications.

## 6. Baseline configuration

Illustrative settings for a disposable PostgreSQL 18 lab:

```conf
wal_level = replica
max_wal_senders = 10
max_replication_slots = 10
hot_standby = on
wal_keep_size = '256MB'
```

These values are **not production sizing recommendations**. Configure replication-role credentials, pg_hba.conf, TLS and an explicit standby primary_conninfo with protected credentials. Build a standby using pg_basebackup -R only after reviewing source and target configuration; it writes standby.signal and connection settings to the target. The target data directory must be new/empty and must never overlap primary PGDATA.

## 7. Monitoring queries

On the primary:

```sql
SELECT application_name,client_addr,state,sync_state,
       sent_lsn,write_lsn,flush_lsn,replay_lsn,
       write_lag,flush_lag,replay_lag
FROM pg_stat_replication;

SELECT slot_name,slot_type,active,restart_lsn,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(),restart_lsn)) AS retained_wal
FROM pg_replication_slots WHERE restart_lsn IS NOT NULL;
```

On the standby:

```sql
SELECT pg_is_in_recovery() AS standby,
       pg_last_wal_receive_lsn() AS receive_lsn,
       pg_last_wal_replay_lsn() AS replay_lsn,
       pg_last_xact_replay_timestamp() AS last_replayed_commit;
SELECT status,receive_start_lsn,written_lsn,flushed_lsn,latest_end_lsn
FROM pg_stat_wal_receiver;
```

**Interpretation caveat:** write_lag/flush_lag/replay_lag are not continuously updated wall-clock backlog metrics and may be NULL. pg_last_xact_replay_timestamp can appear old on an idle system. Correlate LSN byte lag, workload rate, receive/replay progression and application freshness before paging.

## 8. Read replicas and consistency

Read replicas can reduce primary read pressure but may return stale results. Define acceptable freshness per application operation. Long-running queries on standby can conflict with WAL replay; max_standby_streaming_delay and hot_standby_feedback involve tradeoffs, including primary bloat. Do not route read-after-write or critical financial/clinical workflows to a lagging standby without explicit consistency handling.

## 9. Failover architecture and fencing

1. Detect genuine primary failure and distinguish network partition from host failure.
2. Establish authoritative leadership through quorum/coordination.
3. **Fence** the old primary from accepting writes before promoting a replacement.
4. Choose the best eligible standby using replay/flush state and data-loss policy.
5. Promote exactly one standby and verify timeline change.
6. Update writer routing, invalidate stale connections and restore application health.
7. Rejoin former primary only after it is fenced and rebuilt or safely rewound using a verified procedure.

Do not issue pg_promote() against a live production standby solely because the primary is temporarily unreachable. Without fencing and leader coordination, both nodes may accept writes and diverge.

## 10. Failure patterns and runbooks

| Symptom | Likely cause | Safe action |
|---|---|---|
| Standby disconnected | Network, auth, TLS, sender limits | Inspect primary pg_stat_replication and standby logs |
| Receive LSN advances, replay stalls | Replay conflict, long query, I/O | Check standby waits and conflicts |
| WAL storage grows | Abandoned replication slot, archiver failure | Identify consumer before slot changes |
| Synchronous commits hang | Required synchronous standby absent | Invoke approved availability/data-loss policy |
| Read replica stale | Replay lag or idle timestamp ambiguity | Correlate LSN and application checks |
| Two leaders suspected | Partition / failed fencing | Stop writes and invoke split-brain incident plan |

## 11. Lab and acceptance

See [Chapter 067 lab](../labs/067-postgresql-streaming-replication-and-high-availability-architecture-lab.md) and [replication inspection SQL](../labs/sql/067-replication-inspect.sql). The lab creates a disposable primary/standby, validates replay, observes lag and documents failover safety without promoting a live production server.

**Acceptance:** standby in recovery, primary sees streaming sender, WAL receive/replay progress, test data appears on standby, slot retention is bounded and HA/fencing responsibilities are documented. Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/warm-standby.html
- https://www.postgresql.org/docs/18/runtime-config-replication.html
- https://www.postgresql.org/docs/18/monitoring-stats.html
- https://www.postgresql.org/docs/18/app-pgbasebackup.html

**Next:** Chapter 068 — PostgreSQL Replication Slots, WAL Retention and Lag Management.