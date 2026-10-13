# Chapter 043 — Physical Backups with pg_basebackup and Backup Manifests

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Authored; runtime validation pending

## 1. Mission

Produce a consistent physical PostgreSQL base backup, verify its manifest and WAL coverage, and prepare a controlled restore rehearsal. Understand the difference between a successfully copied backup, an integrity-verified backup and a recoverable PostgreSQL cluster. This chapter follows [Chapter 042 — Logical Backups](042-logical-backups-with-pg_dump-pg_restore-and-pg_dumpall.md).

## 2. Physical versus logical backups

A physical backup copies cluster-level data files and requires appropriate WAL for consistency. It is suited to full-cluster restoration and serves as the foundation for point-in-time recovery when combined with a continuous WAL archive. It is not a portable single-table export and cannot simply be restored into a running server's data directory.

A logical `pg_dump` archive can restore selected objects but does not provide arbitrary PITR. A streaming replica improves availability but can replicate accidental changes and is not an independent backup.

## 3. Architecture

```text
Primary PostgreSQL 18
  |-- base backup stream --> isolated backup destination
  |      |-- data files
  |      |-- backup_manifest
  |      +-- required WAL (depending on --wal-method)
  |
  +-- continuous WAL archive --> independent durable storage
                                     |
                              restore rehearsal
                                     |
                              isolated PGDATA
                                     |
                         verify, start, replay, validate
```

## 4. Preflight and permissions

Check PostgreSQL version, connection method, available disk and inodes, backup duration, WAL generation, replication slots, network bandwidth, archiving and backup retention. `pg_basebackup` requires a connection authorized for replication (a role with `REPLICATION` privilege or superuser, and suitable `pg_hba.conf` entry). Never embed a password in a command or commit it to a repository.

```sql
SELECT current_setting('server_version') AS server_version,
       current_setting('wal_level') AS wal_level,
       current_setting('max_wal_senders') AS max_wal_senders,
       current_setting('full_page_writes') AS full_page_writes;

SELECT slot_name, slot_type, active, restart_lsn
FROM pg_replication_slots;

SELECT archived_count, last_archived_time, failed_count, last_failed_time
FROM pg_stat_archiver;
```

A WAL sender must be available for the backup and, with WAL streaming, another sender may be required. Ensure `max_wal_senders` is sized accordingly.

## 5. Backup formats and WAL methods

```bash
# Plain format, with WAL streaming into backup directory
pg_basebackup -h 127.0.0.1 -p 5432 -U backup_user \
  -D /secure/backups/pg18-base-001 -Fp -Xs -P -v

# Tar format; WAL handling differs from plain output layout
pg_basebackup -h 127.0.0.1 -p 5432 -U backup_user \
  -D /secure/backups/pg18-tar-001 -Ft -Xs -P -v
```

Run these as **alternative examples** with distinct, empty destinations. Use a protected location, not a production data directory. `-Xs` streams WAL during backup. `-X fetch` retrieves required WAL at the end and needs enough source WAL retention; `-X none` requires another reliable way to obtain necessary WAL and is not a safe standalone backup. With `-R`, `pg_basebackup` writes standby configuration; do not enable it unless building a standby.

Backup manifests are enabled by default for supported formats; do not disable them when integrity verification is required. Compression, encryption, tablespaces and tar extraction change the restore workflow—document exact options.

## 6. Verify backup manifest

```bash
pg_verifybackup /secure/backups/pg18-base-001
```

`pg_verifybackup` reads the backup manifest, checks expected files and checksums, and validates WAL availability/readability as supported by the selected backup layout and tool options. It may invoke `pg_waldump`. A successful verification does **not** prove that the restored server will start, that every extension or external dependency is present, or that a target-time PITR can complete.

For tar-format backups, extract into an isolated staging area according to PostgreSQL documentation before running a verification workflow appropriate to the extracted layout; do not point the verifier blindly at compressed tar artifacts.

## 7. Restore rehearsal (isolated only)

1. Record source major version, tablespaces, backup start/end, manifest, timeline and required WAL.
2. Provision a new isolated host or container with compatible PostgreSQL 18 binaries and filesystem layout.
3. Restore the backup into an **empty**, exclusively owned PGDATA directory, including tablespace paths and required WAL.
4. Ensure correct ownership and restrictive permissions. Keep the original cluster untouched.
5. Configure recovery only for the intended objective (standby, base-backup recovery or PITR); do not reuse primary identities blindly.
6. Start isolated PostgreSQL, inspect startup/recovery logs and confirm consistency.
7. Run application smoke tests, relation checks and business invariants; measure elapsed restore and replay time.
8. Retain evidence and securely remove only the lab-owned environment after approval.

**Do not run `initdb` on top of a restored PGDATA, overwrite a live PGDATA, or point two running postmasters at the same data directory.**

## 8. Failure scenarios and troubleshooting

| Symptom | Likely cause | Safe response |
|---|---|---|
| Replication connection denied | Role privilege or pg_hba mismatch | Review dedicated backup role and connection rules |
| WAL sender unavailable | max_wal_senders capacity | Reschedule or adjust approved capacity |
| Backup stalls or destination fills | I/O/network/disk constraints | Stop safely, retain logs, choose new destination |
| Manifest verification fails | Missing/changed files or WAL | Treat backup as unverified; do not mark usable |
| Restore cannot find tablespace | Missing mapped path | Restore approved tablespace mapping |
| Startup requests missing WAL | Incomplete WAL chain | Inspect archive continuity and backup method |
| Restored data appears stale | Recovery target or replay gap | Measure achieved recovery point and reconcile RPO |

## 9. Monitoring and production acceptance

Alert on backup failures, last successful backup age, manifest verification failures, WAL archive errors, replication-slot WAL retention, backup duration, backup storage growth, last successful isolated restore and achieved RPO/RTO. Retain encrypted, access-controlled copies in a separate failure domain; test access and restore procedures periodically.

**Acceptance:** record backup command, destination, WAL method, manifest result, independent startup and query verification, backup duration, recovery duration and a documented stop/rollback plan.

## 10. Hands-on lab

[Chapter 043 lab](../labs/043-physical-backups-with-pg_basebackup-and-backup-manifests-lab.md) includes a safe preflight SQL script, local physical backup commands, manifest verification, restore checklist and acceptance matrix. The lab deliberately does not automate destructive PGDATA replacement.

**Runtime status:** authored; PostgreSQL 18 physical backup/restore not executed.

## Official references

- [pg_basebackup](https://www.postgresql.org/docs/18/app-pgbasebackup.html)
- [pg_verifybackup](https://www.postgresql.org/docs/18/app-pgverifybackup.html)
- [Continuous archiving](https://www.postgresql.org/docs/18/continuous-archiving.html)
- [Backup manifest file format](https://www.postgresql.org/docs/18/backup-manifest-format.html)

**Next:** Chapter 044 — WAL Archiving, Restore Commands and PITR Foundations.
