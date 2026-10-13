# Chapter 061 — Backup Strategy, RPO and RTO Fundamentals Lab

**PostgreSQL 18 · Disposable database · Runtime validation pending**

## 1. Preconditions

Use a dedicated PostgreSQL 18 test instance and a writable local backup directory. Ensure `pg_dump`, `pg_restore`, `psql` and `createdb` match the server's major version where appropriate. Do not store backup files in a shared/public folder; backup data may be sensitive. Use a secure password mechanism, not inline command-line passwords.

## 2. Read-only backup baseline

From the repository root in PowerShell:

```powershell
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f postgresql/labs/sql/061-backup-inspect.sql
```

Record WAL level, archive mode, archiver failures, latest archive time, backup policy, data volume, encryption and retention. `pg_stat_archiver` is not a substitute for a restore drill.

## 3. Create disposable source database

```powershell
createdb -U postgres ch061_source
psql -X -v ON_ERROR_STOP=1 -U postgres -d ch061_source -c "CREATE TABLE public.backup_probe(id integer PRIMARY KEY, note text NOT NULL)"
psql -X -v ON_ERROR_STOP=1 -U postgres -d ch061_source -c "INSERT INTO public.backup_probe VALUES (1,'restore-verified'),(2,'rpo-test')"
```

Use unique database names and verify they do not already exist before creation.

## 4. Logical backup and isolated restore

```powershell
New-Item -ItemType Directory -Force -Path .\backups\ch061 | Out-Null
pg_dump -U postgres -d ch061_source -Fc -f .\backups\ch061\source.dump
pg_restore -l .\backups\ch061\source.dump
createdb -U postgres ch061_restored
pg_restore -U postgres -d ch061_restored --exit-on-error .\backups\ch061\source.dump
psql -X -v ON_ERROR_STOP=1 -U postgres -d ch061_restored -c "SELECT count(*) AS restored_rows FROM public.backup_probe"
```

The expected row count is **2**. Verify values, constraints, schema and application behavior rather than relying only on the count. This demonstrates logical restore, **not** WAL/PITR or physical backup validation.

## 5. RPO/RTO worksheet

| Recovery requirement | Target | Observed | Status |
|---|---|---|---|
| Maximum acceptable data loss (RPO) | | | Pending |
| Maximum recovery duration (RTO) | | | Pending |
| Latest valid backup timestamp | | | Pending |
| Latest recoverable WAL point | | | Pending |
| Backup age and integrity | | | Pending |
| Isolated restore duration | | | Pending |
| Application validation duration | | | Pending |
| Key/credential availability | | | Pending |
| Offsite/immutable copy | | | Pending |

## 6. Recovery design exercise

Choose a hypothetical 15-minute RPO and 2-hour RTO. Explain why a nightly dump alone cannot meet the RPO. Design physical base backup plus continuous WAL archiving, monitoring, retention, encryption and restore verification. Estimate full restore time and record assumptions. Do not claim PITR acceptance unless you actually perform a physical restore with required WAL.

## 7. Cleanup

After preserving evidence, drop `ch061_restored` and `ch061_source` only if they were created for this exercise and contain no shared data. Securely retain or dispose of the dump under policy. Do not delete backups required for a real recovery.

**Runtime:** pending.
