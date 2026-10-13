# Chapter 064 — PostgreSQL WAL Archiving and Point-in-Time Recovery

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Configure continuous WAL archiving, prove archive continuity, and restore a physical PostgreSQL backup to a chosen point in time on an isolated host. This follows [Chapter 063 — Physical Backups](063-postgresql-physical-backups-with-pg-basebackup-and-backup-verification.md). A completed archive command alone is not a PITR acceptance test.

## 2. Architecture

```text
Primary PostgreSQL -> WAL segment completion -> archive_command/archive_library -> protected archive
        |                                                           |
        +-> pg_basebackup -> backup manifest -> isolated recovery PGDATA
                                                    |
                                     restore_command + recovery_target_time
                                                    |
                                     replay WAL -> recovery target -> promote
```

Physical base backup + uninterrupted required WAL + timeline history + valid encryption keys and restore tooling form a recoverable chain. A streaming replica is not a historical backup; deletes and corruption can replicate.

## 3. PostgreSQL settings and prerequisites

| Setting | Role | Caution |
|---|---|---|
| wal_level=replica | Required WAL information for physical archiving | Restart may be required |
| archive_mode=on | Enables archive processing | Restart required |
| archive_command | Shell command invoked for completed WAL files | Must safely preserve existing archive files and return nonzero on failure |
| archive_library | Alternative archiver module | Do not configure both active archive approaches |
| archive_timeout | Forces periodic segment switches | Too short can increase archive volume |
| full_page_writes=on | Protects recovery from torn-page risks | Keep enabled |
| restore_command | Fetches WAL during recovery | Must return nonzero for unavailable WAL |
| recovery_target_time | Target timestamp with timezone | Confirm incident timeline and inclusivity |
| recovery_target_action | pause, promote, shutdown | Choose deliberately; pause requires operator action |
| recovery_target_inclusive | Whether target transaction is included | Matters at boundary |
| recovery_target_timeline | Timeline to replay | History files needed across promotions |

Use [inspection SQL](../labs/sql/064-archive-inspect.sql) to capture settings and archiver counters. Check pg_stat_archiver failure increments, last success timestamp, archive storage age and oldest retained base backup. pg_stat_archiver counts can reset, and WAL segments are normally archived when completed: low write rates can make last_archived_time appear old even when archiving is healthy.

## 4. Design an idempotent archive command

On a disposable Linux PostgreSQL host, an example using a dedicated local archive directory:

```conf
wal_level = replica
archive_mode = on
archive_command = 'test ! -f /var/lib/postgresql/wal-archive/%f && cp %p /var/lib/postgresql/wal-archive/%f'
archive_timeout = '60s'
```

This example is for a lab only. It intentionally refuses to overwrite an existing archive object. In production, use a robust script or managed archive tool that checks existing object integrity, writes atomically, retries transient errors and uses protected off-host storage. If the archive already contains an identical segment, a production-safe implementation should recognize that success rather than permanently fail. Test shell quoting, OS permissions, volume capacity and crash safety. archive_mode changes require a restart; archive_command reloads according to its configuration context.

**Never return success without durable storage.** A command that silently discards WAL can permanently destroy PITR coverage. A failing archive command causes pg_wal growth and may exhaust disk; monitor and intervene before disk pressure.

## 5. Generate and verify WAL

```sql
SELECT pg_switch_wal();
SELECT archived_count,last_archived_wal,last_archived_time,failed_count,last_failed_wal,last_failed_time
FROM pg_stat_archiver;
```

pg_switch_wal() requires appropriate privileges and generates extra WAL; use only in a disposable lab or approved maintenance procedure. Confirm the expected segment is present in archive storage, readable by the restore identity and protected against overwrites. Do not assume a single latest archived segment proves a continuous chain.

## 6. Establish the base backup

```bash
pg_basebackup -h 127.0.0.1 -p 5432 -U backup_repl -D /backups/ch064/base001 -Fp -X stream -P --manifest-checksums=SHA256
pg_verifybackup /backups/ch064/base001
```

Ensure the destination is unused and backup files remain protected. -X stream captures WAL needed to make the base backup consistent, but PITR **after** the backup requires subsequent archived WAL. Capture the backup start/end timestamps, manifest, source system identifier and archive retention boundaries.

## 7. Controlled incident timeline

Create an isolated database and fixture using [064-fixture.sql](../labs/sql/064-fixture.sql). Perform an initial transaction, record a UTC recovery target, wait sufficiently to distinguish commit times, then execute a second destructive test transaction. Record actual commit evidence, client clock sync and server clock. A timestamp target must be chosen *between* the transactions, not merely between command starts.

## 8. PITR procedure (isolated lab only)

1. Stop the target test PostgreSQL instance. Never restore into the source PGDATA or over an active service.
2. Copy the verified plain-format base backup into a **new** target PGDATA with compatible PostgreSQL 18 binaries and correct ownership.
3. Review/remove copied upstream connection settings, replication slots, tablespace paths, port, listen addresses, TLS paths and archive_command; prevent accidental contact with production.
4. Configure restore_command to copy WAL from the **read-only** archive, set recovery_target_time with explicit UTC offset, and set recovery_target_action='pause' for inspection.
5. Create recovery.signal in the target PGDATA, start PostgreSQL on an isolated port, and monitor logs until replay reaches the target.
6. While paused, verify target recovery state and expected rows using read-only SQL. If the target was not reached or WAL is missing, **do not promote**; investigate archive continuity.
7. Once validated, execute pg_wal_replay_resume() if paused, with the recovery target action and promotion behavior understood; alternatively use pg_promote() only under the approved isolated drill plan. Never connect recovered test server to production routing.

Example recovery configuration (replace placeholders and adapt to OS):

```conf
restore_command = 'cp /var/lib/postgresql/wal-archive/%f %p'
recovery_target_time = '2026-10-13 15:00:00+00'
recovery_target_inclusive = false
recovery_target_action = 'pause'
recovery_target_timeline = 'latest'
port = 55464
listen_addresses = 'localhost'
```

Do not copy the illustrative timestamp into a real drill. Capture an actual target between commits. recovery.signal is a file in PGDATA; it is not a SQL command. Restore command must return nonzero if a WAL file is absent. PostgreSQL may request files beyond the target and log expected file-not-found messages; distinguish these from a missing required WAL segment.

## 9. Timeline history and recovery branches

Promotion creates a new timeline. Retain .history files and WAL from relevant parent/child timelines; backup retention must preserve all segments needed for the selected recovery path. A restored cluster that is promoted diverges from the original and must not be casually rejoined as if it were an unchanged replica.

## 10. Failure diagnosis

| Symptom | Cause | Safe response |
|---|---|---|
| Archived WAL not advancing | No completed segments, archiver failure, storage/auth issue | Check write rate, pg_stat_archiver, archive logs, storage |
| pg_wal disk growth | Repeated archive failures | Repair archiving and add capacity; do not delete live WAL manually |
| Requested WAL missing | Retention gap or wrong timeline | Stop acceptance, find valid chain or choose older recoverable target |
| Recovery pauses unexpectedly | recovery_target_action=pause | Verify target before controlled resume/promotion |
| Target includes deleted rows incorrectly | Wrong timezone/inclusive setting or target timestamp | Re-run isolated recovery with verified transaction timeline |
| Recovery too slow | Transfer/replay/IO throughput | Measure each stage; adjust RTO design |
| Restore cannot start | PGDATA permissions, tablespaces, incompatible settings | Inspect logs and correct only isolated target |

## 11. Monitoring, RPO and RTO

Track archive failures, archive latency, latest successfully stored segment, unarchived WAL bytes, storage growth, base backup age, WAL chain completeness, restore drill age and key accessibility. Actual RPO is measured against the latest **recoverable** point, not merely the latest WAL timestamp. Actual RTO includes detection, authorization, provisioning, transfer, replay, validation and cutover.

## 12. Acceptance gates

- Verified base backup manifest and integrity; independent archived WAL chain.
- Archive command rejects unsafe overwrite and surfaces errors.
- Recovery target is explicitly UTC and between two known commits.
- Isolated restored database includes the pre-target transaction and excludes the post-target transaction.
- Recovery logs show target reached, timeline captured and no missing required WAL.
- RPO/RTO measured and security/retention controls checked.
- No changes made to production source or production routing.

See [Chapter 064 lab](../labs/064-postgresql-wal-archiving-and-point-in-time-recovery-lab.md). **Runtime validation pending.**

## References

- https://www.postgresql.org/docs/18/continuous-archiving.html
- https://www.postgresql.org/docs/18/runtime-config-wal.html
- https://www.postgresql.org/docs/18/runtime-config-wal.html#RUNTIME-CONFIG-WAL-ARCHIVE-RECOVERY
- https://www.postgresql.org/docs/18/app-pgbasebackup.html

**Next:** Chapter 065 — PostgreSQL Backup Retention, Automation and Restore Testing.