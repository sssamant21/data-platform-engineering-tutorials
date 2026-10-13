# Chapter 044 — WAL Archiving, Restore Commands and PITR Foundations

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Authored; runtime validation pending

## 1. Mission

Understand how a consistent physical base backup and an uninterrupted WAL archive enable point-in-time recovery (PITR). Inspect archive health, design reliable archive/restore commands, choose recovery targets, recognize timeline changes and test recovery only in an isolated environment. This chapter follows [Chapter 043 — Physical Backups](043-physical-backups-with-pg_basebackup-and-backup-manifests.md).

## 2. Recovery architecture

```text
PostgreSQL primary
  |-- physical base backup ---------------------+
  |                                             |
  +-- WAL archive (continuous, durable) --------+--> isolated recovery host
                                                      |
                                              restore_command fetches WAL
                                                      |
                                              replay to recovery target
                                                      |
                                              validate + controlled cutover
```

A base backup establishes the starting state; archived WAL replays later changes. The archive must contain all required WAL across the interval from the base backup through the selected recovery point. An archive gap can make a desired PITR target unreachable.

## 3. Essential configuration

```sql
SELECT name,setting,source,pending_restart
FROM pg_settings
WHERE name IN ('wal_level','archive_mode','archive_command',
               'archive_library','archive_timeout','full_page_writes',
               'max_wal_senders')
ORDER BY name;

SELECT archived_count,last_archived_wal,last_archived_time,
       failed_count,last_failed_wal,last_failed_time,stats_reset
FROM pg_stat_archiver;
```

For a self-managed archive setup, `wal_level` must support the intended recovery strategy, `archive_mode` must be enabled and a reliable `archive_command` or `archive_library` must persist completed WAL segments. Some changes require restart. Do not make these changes directly on a live production primary without an approved plan.

`archive_timeout` can bound how long a quiet server waits to switch WAL segments, but it does not guarantee end-to-end archive delivery latency or a specific RPO. Monitor actual archival lag and archive integrity.

## 4. Archive command design

The archive command receives `%p` (source WAL path) and `%f` (WAL filename). It must exit with success only when the WAL file is durably stored. A destination collision must not silently overwrite different content. Failed commands are retried; persistent failure can cause `pg_wal` growth and disk exhaustion.

**Illustrative POSIX lab-only command**, requiring a protected local archive directory and verified atomicity/durability for the actual filesystem:

```conf
archive_mode = on
archive_command = 'test ! -f /lab/wal-archive/%f && cp %p /lab/wal-archive/%f'
```

This simplified example is **not** production-ready: it treats an existing destination as failure and does not establish robust durable storage, idempotency, encryption, remote-failure handling or checksum validation. Production archive tooling must safely accept an already archived *identical* file, reject mismatches, and acknowledge only durable completion. Use tested tools such as pgBackRest or Barman where appropriate, and validate the command under retries and partial failures.

Do not delete WAL files manually to resolve archive backlog. Diagnose archiver errors, destination capacity, network, permissions and retention dependencies first.

## 5. Restore command and recovery signals

An isolated recovery instance fetches WAL using `restore_command`. PostgreSQL substitutes `%f` for the requested filename and `%p` for the destination path in the recovery environment.

```conf
restore_command = 'cp /lab/wal-archive/%f %p'
recovery_target_time = '2026-10-13 10:00:00+00'
recovery_target_action = 'pause'
```

These are **illustrative settings**, not instructions to change production. For a PITR restore, provision an isolated PostgreSQL 18 data directory from a verified physical backup, configure recovery parameters and create `recovery.signal` before starting. The selected target must be within the available WAL history and later than the backup's recoverable start. Set an explicit timezone offset in timestamp targets.

Use `recovery_target_xid`, `recovery_target_lsn`, `recovery_target_name` or `recovery_target_time` when justified by evidence. `recovery_target_inclusive` controls whether a matching transaction is included. `recovery_target_action` can pause, promote or shut down; choose intentionally. Never promote before validating the intended recovery point and downstream consequences.

## 6. Timelines and PITR boundaries

Promotion creates a new timeline. A timeline history file records ancestry; the same wall-clock time may appear on multiple branches. `recovery_target_timeline` determines which timeline to follow. Keep timeline history files with the WAL archive, and confirm the desired branch after failover. Never assume that a timestamp alone uniquely identifies a transaction across diverged histories.

## 7. Archive and recovery observability

```sql
SELECT pg_current_wal_lsn() AS current_lsn,
       pg_walfile_name(pg_current_wal_lsn()) AS current_segment;

SELECT archived_count,failed_count,last_archived_time,last_failed_time
FROM pg_stat_archiver;

SELECT slot_name,active,restart_lsn
FROM pg_replication_slots;
```

Check archive destination manifests and WAL segment continuity, not only `pg_stat_archiver`. Counters may reset, and archive statistics can lag actual work. Monitor WAL directory free space, failed archive attempts, archive delivery latency, replication slot retention, backup age and last successful isolated PITR test.

## 8. PITR investigation and recovery runbook

1. Classify incident and freeze further damaging writes where operationally safe.
2. Capture target timestamp with timezone, or a known LSN/transaction marker; obtain business approval for expected data loss.
3. Identify verified base backup, backup manifest, timeline and continuous required WAL.
4. Restore to a **separate, empty, lab-owned** data directory on an isolated host.
5. Configure `restore_command`, selected target and `recovery.signal`; review permissions and PostgreSQL 18 compatibility.
6. Start the isolated instance and monitor recovery logs, WAL requests and target reached.
7. Validate critical records, schema, roles, extensions, sequence state, consistency and application invariants.
8. Measure achieved RPO and RTO; document cutover fencing and rollback before serving traffic.

For a single-table accidental deletion, restoring a separate cluster and reconciling selected rows may be safer than rolling back the whole production cluster.

## 9. Troubleshooting

| Symptom | Evidence | Response |
|---|---|---|
| WAL archive backlog | failed_count, pg_wal growth | Fix destination/permissions, preserve files |
| WAL segment missing | restore logs request filename | Verify archive chain, base backup and timeline |
| Target not reached | Recovery logs, chosen target | Check target timezone, LSN and available WAL |
| Wrong timeline | History files, promotion events | Select correct ancestor/branch |
| Restore loops on file | restore_command exit status | Fix file naming, permissions, command semantics |
| Backup verifies but recovery fails | WAL gap, external dependencies | Test full recovery chain, not manifest alone |

## 10. Lab and acceptance

[Chapter 044 lab](../labs/044-wal-archiving-restore-commands-and-pitr-foundations-lab.md) supplies read-only preflight SQL, a WAL-archive audit checklist, and an isolated PITR exercise. No automated destructive changes to production configuration or PGDATA are included.

**Acceptance:** distinguish base backup from WAL continuity; design safe archive/restore commands; identify recovery targets and timelines; document an isolated restore rehearsal and measured RPO/RTO. **Runtime:** pending.

## Official references

- [Continuous archiving and PITR](https://www.postgresql.org/docs/18/continuous-archiving.html)
- [WAL archiving settings](https://www.postgresql.org/docs/18/runtime-config-wal.html)
- [Recovery target settings](https://www.postgresql.org/docs/18/runtime-config-wal.html#RUNTIME-CONFIG-WAL-RECOVERY-TARGET)
- [pg_basebackup](https://www.postgresql.org/docs/18/app-pgbasebackup.html)

**Next:** Chapter 045 — Point-in-Time Recovery and Disaster Recovery Lab.
