# Chapter 047 — PostgreSQL Replication Slots, WAL Retention and Failure Modes

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Authored; runtime validation pending

## 1. Mission

Diagnose WAL retention caused by physical and logical replication slots; distinguish healthy lag from an abandoned consumer; understand `restart_lsn`, `confirmed_flush_lsn`, `wal_status`, `safe_wal_size`, `max_slot_wal_keep_size` and PostgreSQL 18 slot behavior; and respond without losing replica or CDC continuity. This chapter follows [Chapter 046 — Backup Monitoring](046-backup-monitoring-restore-validation-and-recovery-automation.md).

## 2. How slots work

A replication slot records the WAL and, for logical slots, catalog history needed by a replication consumer. Slots can prevent required WAL from being recycled. A physical slot retains WAL for a physical standby; a logical slot retains WAL and may hold back catalog cleanup until its consumer progresses.

```text
Primary WAL generation --> current LSN
             |               |
             +-- physical slot restart_lsn -> standby
             +-- logical slot restart_lsn  -> decoder/CDC
                                      confirmed_flush_lsn -> consumer acknowledgment
```

A slot is not a backup. Slots do not replace base backups or WAL archives and may amplify a storage incident when a consumer is offline.

## 3. Important fields

| Field | Meaning | Operational interpretation |
|---|---|---|
| `slot_name`, `slot_type` | Slot identity and physical/logical kind | Map to replica or CDC owner |
| `active`, `active_pid` | Current consumer connection | Inactive does not automatically mean unused |
| `restart_lsn` | Oldest WAL position potentially needed | Basis for retained-WAL estimate |
| `confirmed_flush_lsn` | Logical consumer's acknowledged position | Logical-only; not equivalent to restart_lsn |
| `wal_status` | WAL retention state | `reserved`, `extended`, `unreserved`, `lost` |
| `safe_wal_size` | Bytes that may be written before slot risks `lost` | NULL when unlimited retention or already lost |
| `xmin`, `catalog_xmin` | Tuple/catalog retention horizons | Investigate vacuum/catalog bloat |
| `inactive_since` | Time slot became inactive | Use with owner and workload evidence |
| `invalidation_reason` | Why a slot was invalidated | Relevant when slot becomes unusable |

On PostgreSQL 18, slot metadata can also include failover-related fields for logical slots. Check your exact server's `pg_replication_slots` view; avoid assuming all fields are available on older major versions.

## 4. Read-only investigation

```sql
SELECT slot_name,slot_type,active,active_pid,
       restart_lsn,confirmed_flush_lsn,
       wal_status,safe_wal_size,inactive_since,
       xmin,catalog_xmin,invalidation_reason,
       CASE WHEN restart_lsn IS NOT NULL
         THEN pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(),restart_lsn)::bigint)
       END AS retained_wal_estimate
FROM pg_replication_slots
ORDER BY slot_name;
```

The estimate is LSN distance, **not** exact on-disk `pg_wal` bytes or guaranteed reclaimable storage. WAL may also be retained by archiving, checkpoints, `wal_keep_size`, replication senders and other slots. Execute the query on the primary; `pg_current_wal_lsn()` is not a standby-safe function.

Check physical replication:

```sql
SELECT pid,application_name,client_addr,state,sync_state,
       sent_lsn,write_lsn,flush_lsn,replay_lsn,
       write_lag,flush_lag,replay_lag
FROM pg_stat_replication;
```

For logical replication subscribers, also inspect subscription workers and the publisher's slot. Subscriber progress and publisher WAL retention require both sides' evidence.

## 5. Retention controls

- `max_slot_wal_keep_size = -1` permits unbounded slot-related WAL retention, subject to disk limits. Set an approved finite cap only after evaluating replica/CDC recovery needs.
- `max_slot_wal_keep_size` is enforced at checkpoints; exceeding the cap can make required WAL unavailable and invalidate a slot. It is not a guarantee that disk usage will stay below the configured size at every instant.
- `wal_keep_size` is a minimum WAL retention target for standbys, not a per-slot upper bound.
- `max_wal_size` is a soft checkpoint/WAL management target, not a hard disk limit.
- `idle_replication_slot_timeout` in PostgreSQL 18 can invalidate slots inactive beyond a configured duration, with checkpoint-based enforcement and important applicability exceptions. Review official documentation before enabling it for production.
- `pg_replication_slot_advance` can skip WAL; it can create irreversible replication/CDC gaps. Never use it as a routine disk-pressure workaround.

## 6. Incident: pg_wal filling due to an inactive slot

1. Declare storage risk; record `pg_wal` free space, growth rate, archive health, checkpoint pressure and all slot metadata.
2. Identify the owning standby, subscriber or CDC service and the last acknowledged position. Contact the owner.
3. Check whether the consumer can resume safely and catch up before disk exhaustion. Confirm network, authentication, throughput and upstream errors.
4. Evaluate immediate safe capacity relief (storage expansion, fixing archiving, reducing WAL-generating workload with approval).
5. Before any slot change, document recovery strategy, resnapshot/reinitialization cost, business impact and approval.
6. **Only if explicitly approved and proven obsolete:** drop an inactive slot using the appropriate PostgreSQL function. A slot cannot normally be dropped while active; dropping it may make a disconnected replica or CDC consumer unrecoverable without reinitialization.
7. Verify WAL retention and disk behavior after checkpoints, replica/CDC health and data consistency. Record incident actions.

**Do not manually delete files from `pg_wal`, blindly drop slots or advance a logical slot to hide lag.**

## 7. Failure patterns

| Symptom | Likely cause | Response |
|---|---|---|
| WAL grows despite low traffic | Old inactive slot, archive backlog | Correlate slot LSN, archiver and disk |
| Slot `extended` | WAL beyond normal budget retained for slot | Check consumer catch-up and storage headroom |
| Slot `unreserved` | Required WAL no longer fully reserved | Act urgently; next checkpoint may remove it |
| Slot `lost` | Required WAL removed | Rebuild/reinitialize consumer using approved process |
| Logical CDC stops progressing | Consumer errors or blocked acknowledgments | Check consumer logs and confirmed_flush_lsn |
| Vacuum/catalog bloat | Logical slot xmin/catalog_xmin horizon | Diagnose logical decoding and retention |
| Slot appears inactive | Planned maintenance or orphaned consumer | Verify owner before intervention |

## 8. Monitoring and SLOs

Track retained WAL estimate by slot, active state, `inactive_since`, `wal_status`, `safe_wal_size`, `catalog_xmin`, `pg_wal` filesystem headroom, WAL generation rate, archive lag and subscriber replay/CDC delay. Alert on predicted time to disk exhaustion rather than relying only on absolute bytes. Use separate alerts for slot data-loss risk (`unreserved`/`lost`) and storage pressure.

## 9. Lab and acceptance

[Chapter 047 lab](../labs/047-postgresql-replication-slots-wal-retention-and-failure-modes-lab.md) runs read-only slot and WAL diagnostics, optionally creates a **temporary physical slot** in a disposable PostgreSQL 18 cluster, generates a bounded amount of WAL and observes retention before approved cleanup. No production slot is modified.

**Acceptance:** identify slot owner and retained-WAL estimate; explain physical/logical fields; distinguish slot lag from archive backlog; document a safe response and reinitialization consequences. **Runtime:** not executed.

## Official references

- [Streaming replication slots](https://www.postgresql.org/docs/18/warm-standby.html#STREAMING-REPLICATION-SLOTS)
- [pg_replication_slots](https://www.postgresql.org/docs/18/view-pg-replication-slots.html)
- [Replication settings](https://www.postgresql.org/docs/18/runtime-config-replication.html)
- [Replication management functions](https://www.postgresql.org/docs/18/functions-admin.html#FUNCTIONS-REPLICATION)

**Next:** Chapter 048 — Replication Lag, Standby Conflicts and Recovery Operations.
