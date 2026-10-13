# Chapter 064 — WAL Archiving and PITR Lab

**PostgreSQL 18 · Isolated Linux/container test cluster · Runtime pending**

## 1. Preflight and isolation

Use a disposable PostgreSQL 18 primary, separate WAL archive volume, replication-capable backup role, and isolated restore host/container. Confirm all database names, PGDATA directories, archive directories and ports are lab-only. Ensure time synchronization and a separate admin connection. Do not perform destructive tests or recovery on production.

## 2. Inspect archiving

```bash
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f postgresql/labs/sql/064-archive-inspect.sql
```

Record wal_level, archive_mode, archive_command/archive_library, last archived WAL, failures, data checksums and server timezone.

## 3. Configure WAL archiving

In the disposable PostgreSQL server, create a secure archive directory accessible by the PostgreSQL service account. Set wal_level=replica, archive_mode=on, and an idempotent, durable archive_command appropriate to the lab filesystem. Restart only the lab server if required. Verify archive_command exits nonzero on failure and never overwrites differing existing WAL.

## 4. Create the fixture before the base backup

Create the disposable database and schema first:

```bash
createdb -U postgres ch064_lab
psql -X -v ON_ERROR_STOP=1 -U postgres -d ch064_lab -f postgresql/labs/sql/064-fixture.sql
```

Do not insert the before-target or after-target events until after the base backup is complete. This ensures both events can be replayed from archived WAL and the recovered schema exists.

## 5. Establish base backup

```bash
mkdir -p /backups/ch064
pg_basebackup -h 127.0.0.1 -U backup_repl -D /backups/ch064/base001 -Fp -X stream -P --manifest-checksums=SHA256
pg_verifybackup /backups/ch064/base001
```

Destination base001 must not exist before execution. Preserve manifest and tool output.

## 6. Produce the before/after transactions

The database and fixture were created before the base backup. Now execute two separate autocommit transactions.

In the source database:

```sql
INSERT INTO ch064.events(event_key,phase) VALUES ('before-target','keep');
SELECT clock_timestamp() AT TIME ZONE 'UTC' AS after_first_commit_utc;
```

Wait several seconds, record a UTC target between commits, then:

```sql
INSERT INTO ch064.events(event_key,phase) VALUES ('after-target','exclude');
SELECT clock_timestamp() AT TIME ZONE 'UTC' AS after_second_commit_utc;
SELECT pg_switch_wal();
```

The INSERTs run as separate autocommit statements. Verify the target timestamp is after the first commit and before the second; record exact server timestamps. Wait for archiver success and verify all required WAL files are available.

## 7. Recover in isolation

Copy the verified base backup to a new isolated PGDATA; adjust permissions, tablespaces and copied configuration. Configure restore_command for the lab archive, recovery_target_time with the actual UTC target, recovery_target_action='pause', recovery_target_inclusive=false, and a unique port. Create recovery.signal and start only the isolated server. Observe recovery logs. If WAL is missing or the target is not reached, stop and mark FAIL; do not claim success.

While paused, use read-only queries to confirm `before-target` exists and `after-target` does not. Preserve the logs and recovery timeline. Promote/resume only according to the isolated lab plan.

## 8. Acceptance worksheet

| Gate | Evidence | Status |
|---|---|---|
| Archive config valid | | Pending |
| Base backup verified | | Pending |
| Required WAL chain present | | Pending |
| Target timestamp between commits | | Pending |
| Recovery reaches target | | Pending |
| Pre-target row present | | Pending |
| Post-target row absent | | Pending |
| No production connection or routing | | Pending |
| RPO/RTO measured | | Pending |

## 9. Cleanup

Stop restored lab server and retain recovery evidence. Only remove directories and database objects positively identified as lab-owned. Never delete production WAL or an archive needed by retained backups.

**Runtime:** pending.
