# Chapter 063 — PostgreSQL Physical Backups with pg_basebackup and Backup Verification

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Learning objectives

Create a cluster-wide physical backup, verify its manifest and required WAL, restore to an isolated host, measure recovery time and identify failure modes. Unlike Chapter 062 logical backups, physical backups cover the entire PostgreSQL cluster and are not selective table/database exports.

## 2. Architecture and safety

Source PostgreSQL -> replication protocol -> pg_basebackup -> protected storage -> pg_verifybackup -> isolated restore -> application validation.

**Never back up into or restore over an active production PGDATA.** Confirm the target directory is unused, storage capacity is sufficient, credentials are protected, and a separate restoration host or isolated container is available. A successful backup or verification does not prove the restored database will start.

## 3. Preflight

Check PostgreSQL and client versions, replication access, max_wal_senders, archive health, backup storage, tablespace mappings, backup encryption, backup destination, and performance headroom. pg_basebackup uses a replication connection and -X stream uses another connection for WAL streaming. Prefer a dedicated least-privilege role with REPLICATION and pg_hba.conf access.

Run [preflight SQL](../labs/sql/063-preflight.sql) before proceeding.

## 4. Backup formats and WAL modes

| Option | Choice | Operational consideration |
|---|---|---|
| -F | plain or tar | Plain creates a data directory; tar creates archive files |
| -X stream | WAL streamed concurrently | Recommended lab default; consumes an additional replication connection |
| -X fetch | WAL retrieved at backup end | Source must retain all needed WAL until fetch completes |
| -X none | No WAL included | Requires separately retained WAL for consistent recovery |
| -P | Progress | Useful for operator observation |
| -c fast | Fast checkpoint | May increase source I/O |
| --manifest-checksums=SHA256 | File checksums in manifest | Enables integrity checks |

## 5. Execute backup (PowerShell, disposable PostgreSQL 18 only)

```powershell
New-Item -ItemType Directory -Force -Path .\backups\ch063 | Out-Null
pg_basebackup -h localhost -p 5432 -U backup_repl -D .\backups\ch063\base001 -Fp -X stream -P -c fast --manifest-checksums=SHA256
if ($LASTEXITCODE -ne 0) { throw 'pg_basebackup failed' }
```

The destination base001 must not exist or must be empty, depending on command requirements. The backup includes a backup_manifest unless disabled. Store the manifest with the backup, protect all contents, and record duration, source identity, size and backup ID.

## 6. Integrity verification

```powershell
pg_verifybackup .\backups\ch063\base001
if ($LASTEXITCODE -ne 0) { throw 'pg_verifybackup failed' }
Get-FileHash .\backups\ch063\base001\backup_manifest -Algorithm SHA256
```

pg_verifybackup compares files with the manifest and verifies WAL required for consistency using pg_waldump when available. It cannot prove application-level data correctness, extension availability, configuration compatibility or that PITR WAL after backup completion exists.

## 7. Restore and recovery drill

On a disposable isolated machine, copy the verified plain-format backup into a new PGDATA. Review postgresql.conf, postgresql.auto.conf, standby.signal, recovery.signal, TLS paths, replication settings and pg_tblspc links before starting. Use a different port, localhost-only listener, separate OS/service identity and compatible PostgreSQL binaries. Never allow the clone to reconnect to a production replication upstream without explicit approval.

```powershell
Copy-Item .\backups\ch063\base001 .\pgdata-ch063-restored -Recurse
pg_ctl -D .\pgdata-ch063-restored -o '-p 55433 -c listen_addresses=localhost' -l .\ch063-restore.log start
pg_isready -h localhost -p 55433
psql -X -h localhost -p 55433 -U postgres -d postgres -c 'SELECT version(),pg_is_in_recovery();'
pg_ctl -D .\pgdata-ch063-restored stop -m fast
```

This is a conceptual standalone lab flow: filesystem permissions, platform-specific PostgreSQL service accounts, tablespace paths, and copied source configuration must be corrected before execution. Do not attempt this sequence on an existing cluster. Verify expected databases, roles, extensions, row counts, constraints and application reads.

## 8. Common failure modes

| Symptom | Investigation | Mitigation |
|---|---|---|
| Replication connection refused | pg_hba.conf, TLS, REPLICATION privilege | Correct narrowly scoped replication access |
| max_wal_senders exceeded | Active replication senders | Increase planned capacity or schedule backup |
| Missing WAL on -X fetch | WAL retention/recycling | Prefer streaming or retention guarantees |
| Manifest mismatch | Corrupted/incomplete backup | Quarantine artifact, retake backup |
| Restore cannot start | WAL, permissions, version, tablespaces, copied settings | Inspect isolated startup logs |
| Backup harms workload latency | Checkpoint/IO pressure | Throttle, reschedule, validate standby backup strategy |

## 9. RPO/RTO and retention

Measure backup age, actual recoverable WAL endpoint, archive gaps, storage transfer time, replay time, startup and validation time. A physical base backup plus required WAL is needed for consistency; WAL archiving beyond that enables later PITR. Retain the full WAL chain required by the oldest retained recovery base and any restore targets. Test encryption key availability and offsite copies.

## 10. Acceptance gates

Require a successful backup exit code, valid manifest, pg_verifybackup PASS, protected artifact, isolated startup, expected database and application validation, measured full restore time, and a documented rollback plan. Mark unexecuted tests NOT VERIFIED rather than PASS.

See [Chapter 063 lab](../labs/063-postgresql-physical-backups-with-pg-basebackup-and-backup-verification-lab.md).

## References

- https://www.postgresql.org/docs/18/app-pgbasebackup.html
- https://www.postgresql.org/docs/18/app-pgverifybackup.html
- https://www.postgresql.org/docs/18/continuous-archiving.html

**Next:** Chapter 064 — PostgreSQL WAL Archiving and Point-in-Time Recovery.