# Chapter 049 — Replication Failover, Rejoin and Timeline Recovery

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Authored; runtime validation pending

## 1. Mission

Operate a PostgreSQL primary/standby failover safely: evaluate standby freshness, fence the failed primary, promote an approved candidate, recognize timeline divergence, and rejoin the old primary with `pg_rewind` or a fresh base backup. This chapter follows [Chapter 048 — Replication Lag, Standby Conflicts and Recovery Operations](048-replication-lag-standby-conflicts-and-recovery-operations.md).

## 2. Failover topology

```text
Before:
  Primary A (timeline 1) --> Standby B (timeline 1)

After approved failover:
  Primary A [FENCED/OFFLINE]     Primary B (timeline 2)
                                      |
                                  new replicas

Rejoin:
  Former A -- pg_rewind or rebuild --> standby of B
```

Promotion changes the timeline. An old primary that can still accept writes can cause **split-brain** and irreconcilable divergence. Fencing must precede exposing the new primary to writes.

## 3. Planned switchover versus unplanned failover

| Aspect | Planned switchover | Unplanned failover |
|---|---|---|
| Old primary | Can be quiesced cleanly | May be unreachable or ambiguous |
| Data-loss risk | Usually minimized with catch-up checks | Depends on last replayed durable WAL |
| Fencing | Planned shutdown and write-routing block | Mandatory independent confirmation |
| Promotion | After verified synchronization | After candidate assessment and approval |
| Rejoin | Rewind or rebuild as appropriate | More likely to require divergence analysis |

Synchronous replication can reduce acknowledged-transaction loss when correctly configured, but it does not replace fencing, backup validation or business-approved failover procedures.

## 4. Candidate readiness and diagnostic SQL

On the **old primary if reachable**, inspect replication state:

```sql
SELECT application_name,client_addr,state,sync_state,
       sent_lsn,write_lsn,flush_lsn,replay_lsn,
       pg_wal_lsn_diff(pg_current_wal_lsn(),replay_lsn) AS replay_gap_bytes
FROM pg_stat_replication;
```

On the **candidate standby**:

```sql
SELECT pg_is_in_recovery() AS in_recovery,
       pg_last_wal_receive_lsn() AS received_lsn,
       pg_last_wal_replay_lsn() AS replayed_lsn,
       pg_last_xact_replay_timestamp() AS last_replayed_commit;
SELECT status,latest_end_lsn,latest_end_time,sender_host,slot_name
FROM pg_stat_wal_receiver;
```

The last replay timestamp is not a dependable freshness indicator on an idle system. Correlate WAL positions, actual committed business records, replication mode, archive availability and recent logs. A standby with significant replay lag may lose acknowledged transactions if promoted.

## 5. Safe promotion runbook

1. Declare incident and capture application symptoms, topology, old-primary reachability and latest verified backup.
2. **Fence the old primary:** revoke write routing and independently ensure it cannot serve writes (e.g., infrastructure/network/cluster-manager fencing). DNS updates alone are not sufficient fencing.
3. Select a standby using replay LSN, available WAL, health, expected data loss and business-approved RPO.
4. Obtain failover approval and record the selected candidate, timestamp and evidence.
5. Promote **only the fenced, approved candidate**, via HA orchestrator or `pg_ctl promote` / `pg_promote()` as appropriate.
6. Confirm `pg_is_in_recovery() = false`, inspect logs and timeline history, and validate write capability on the intended primary.
7. Update connection routing, replicas, monitoring, backups and replication slots; perform application smoke tests.
8. Track actual RPO/RTO, preserve old-primary disks and logs, and prepare controlled rejoin.

**Do not promote multiple standbys, assume the old primary is dead, or resume old-primary writes after a new timeline exists.**

## 6. Timeline divergence and pg_rewind

`pg_rewind` can synchronize a stopped former primary's data directory to a new primary after divergence, avoiding a full base backup when prerequisites are met. It is **not** a generic data merge tool. It discards changes on the rewound target that are not on the new source timeline.

Prerequisites include compatible major versions and cluster ancestry; `wal_log_hints=on` **or** data checksums enabled before divergence, plus `full_page_writes=on`. Required WAL history from the divergence point must be available; a suitable `restore_command` and `pg_rewind --restore-target-wal` may help fetch target-side WAL. The target must be cleanly shut down (or handled according to documented crash-recovery procedure) and must never be running during rewind.

**Illustrative commands, not to be executed without approved fencing and verified paths:**

```bash
# Inspect a stopped former-primary target first
pg_controldata /isolated/old-primary-pgdata

# Dry run: shows proposed rewind work
pg_rewind --dry-run --target-pgdata=/isolated/old-primary-pgdata \
  --source-server="host=new-primary port=5432 user=rewind_user dbname=postgres"
```

For the actual rewind, remove `--dry-run` **only after** approved backup of the target, fencing, compatibility and WAL checks. The source account requires appropriate permissions; use a secured connection and follow PostgreSQL 18 documentation. After rewind, configure the target as a standby of the new primary (e.g., `standby.signal`, `primary_conninfo`, slots and recovery settings), then start and verify replay. If rewind cannot safely complete, rebuild the standby from a verified base backup.

## 7. Rejoin and rollback decisions

A former primary is **not** automatically safe to reconnect as a primary. Check timeline history, system identifier, WAL divergence, unreplicated writes, slots and archive coverage. Decide whether to preserve divergent data for reconciliation. Rebuild or rewind as a standby only after preserving evidence. Failback is a separate planned switchover with new fencing and approval—not an automatic reversal.

## 8. Troubleshooting

| Symptom | Risk | Safe response |
|---|---|---|
| Old primary intermittently reachable | Split-brain | Prove fencing before promotion |
| Candidate behind | Data loss | Quantify gap and obtain approval |
| `pg_rewind` lacks WAL | Incomplete rewind | Restore required WAL or rebuild |
| Rewind prerequisites absent | Unsupported target reconciliation | Fresh base backup |
| Rejoined standby will not connect | Auth/slot/configuration | Inspect receiver logs and connection settings |
| Timeline mismatch | Wrong branch | Review timeline history and restore configuration |
| Applications writing to both | Divergent data | Stop writes, preserve evidence, incident escalation |

## 9. Monitoring and acceptance

Monitor leader identity, fencing status, WAL replay LSN, timeline transitions, slot health, replica catch-up, endpoint routing, application errors and last validated backup. Record measured RPO/RTO and explicit failover decision evidence.

[Chapter 049 lab](../labs/049-replication-failover-rejoin-and-timeline-recovery-lab.md) includes read-only primary/standby checks, a controlled tabletop, a dry-run `pg_rewind` worksheet and an isolated failover/rejoin checklist. No automatic promotion, rewind or production routing change is provided.

**Runtime status:** PostgreSQL 18 failover/rewind not executed.

## Official references

- [Failover](https://www.postgresql.org/docs/18/warm-standby-failover.html)
- [pg_rewind](https://www.postgresql.org/docs/18/app-pgrewind.html)
- [Streaming replication](https://www.postgresql.org/docs/18/warm-standby.html)
- [Recovery configuration](https://www.postgresql.org/docs/18/runtime-config-wal.html)

**Next:** Chapter 050 — High Availability and Disaster Recovery Acceptance Project.
