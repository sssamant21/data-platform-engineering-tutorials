# Chapter 063 — Physical Backup and Verification Lab

**PostgreSQL 18 · Windows PowerShell · Disposable instance only · Runtime pending**

## 1. Safety preflight

Use a dedicated PostgreSQL 18 test instance, isolated restore machine or container, replication-capable lab role, free disk space at least twice the cluster data size plus WAL, and separate backup and restore paths. Confirm backup paths do not already contain data. Do not use production PGDATA, source tablespaces, replication endpoints or production ports for restore. Record the backup and restore host identities and available disk.

## 2. Inspect source

From the repository root:

```powershell
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f postgresql/labs/sql/063-preflight.sql
pg_basebackup --version
pg_verifybackup --version
```

Check `pg_hba.conf` replication rules, TLS, `max_wal_senders`, role privileges and WAL retention. Record all tablespace paths.

## 3. Take physical backup

```powershell
New-Item -ItemType Directory -Force -Path .\backups\ch063 | Out-Null
pg_basebackup -h localhost -p 5432 -U backup_repl -D .\backups\ch063\base001 -Fp -X stream -P -c fast --manifest-checksums=SHA256
if ($LASTEXITCODE -ne 0) { throw 'Backup failed; do not proceed' }
```

Use a dedicated replication account and secure authentication. The destination `base001` must be new/empty. Capture backup duration and size.

## 4. Verify backup integrity

```powershell
pg_verifybackup .\backups\ch063\base001
if ($LASTEXITCODE -ne 0) { throw 'Backup verification failed' }
Get-FileHash .\backups\ch063\base001\backup_manifest -Algorithm SHA256
```

Preserve command output. A manifest PASS is not proof of a successful startup or application recovery.

## 5. Isolated restore drill

Copy the verified plain-format backup to an unused directory on an isolated PostgreSQL 18 test host. Inspect and correct `postgresql.conf`, `postgresql.auto.conf`, `standby.signal`, `recovery.signal`, SSL file paths, permissions and `pg_tblspc` links. Ensure the clone cannot connect to production. Only then run:

```powershell
pg_ctl -D .\pgdata-ch063-restored -o '-p 55433 -c listen_addresses=localhost' -l .\ch063-restore.log start
pg_isready -h localhost -p 55433
psql -X -h localhost -p 55433 -U postgres -d postgres -c 'SELECT version(),pg_is_in_recovery();'
pg_ctl -D .\pgdata-ch063-restored stop -m fast
```

These commands assume the restored PGDATA is already prepared. On Windows, use the appropriate PostgreSQL service account and ACLs; do not attempt to run `pg_ctl` as an incompatible administrator identity.

## 6. Acceptance worksheet

| Gate | Evidence | Status |
|---|---|---|
| Source inventory and tablespaces | | Pending |
| Backup exit code 0 | | Pending |
| Manifest checksum recorded | | Pending |
| pg_verifybackup PASS | | Pending |
| Restored PGDATA isolated | | Pending |
| PostgreSQL startup succeeds | | Pending |
| Application validation succeeds | | Pending |
| Full recovery time measured | | Pending |
| Backup retention and key recovery checked | | Pending |

Record error details and corrective actions. A failed gate means the backup is not accepted.

**Runtime:** pending.
