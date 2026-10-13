# Chapter 065 — Backup Retention, Automation and Restore Testing Lab

**PostgreSQL 18 · Windows PowerShell · Disposable databases only · Runtime pending**

## 1. Preconditions and safety

Use a dedicated PostgreSQL 18 test server, protected local backup folder, test-only backup role, and two new database names: `ch065_lab` and `ch065_restore`. Confirm neither exists. Never delete WAL, backup objects, or production data during this lab. The retention exercise is **dry run only**.

## 2. Read-only inspection

```powershell
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f postgresql/labs/sql/065-backup-inspect.sql
```

Capture archive mode, WAL settings, latest archive success/failure, database sizes and version.

## 3. Create a source database

```powershell
createdb -U postgres ch065_lab
psql -X -v ON_ERROR_STOP=1 -U postgres -d ch065_lab -c "CREATE TABLE public.backup_probe(id integer PRIMARY KEY, marker text NOT NULL)"
psql -X -v ON_ERROR_STOP=1 -U postgres -d ch065_lab -c "INSERT INTO public.backup_probe VALUES (1,'retention-test'),(2,'restore-test')"
```

## 4. Automated logical backup with validation

```powershell
$ErrorActionPreference = 'Stop'
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$dir = Join-Path (Get-Location) 'backups\ch065'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$out = Join-Path $dir ("ch065_$stamp.dump")
pg_dump -U postgres -d ch065_lab -Fc -f $out
if ($LASTEXITCODE -ne 0) { throw 'Backup failed' }
pg_restore -l $out | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Archive inspection failed' }
Get-FileHash $out -Algorithm SHA256
```

Do not treat the checksum or archive listing as a successful restore.

## 5. Isolated restore acceptance

```powershell
createdb -U postgres ch065_restore
pg_restore -U postgres -d ch065_restore --exit-on-error $out
if ($LASTEXITCODE -ne 0) { throw 'Restore failed' }
psql -X -v ON_ERROR_STOP=1 -U postgres -d ch065_restore -c "SELECT count(*) AS restored_rows FROM public.backup_probe"
```

Expected row count: **2**. Confirm values, schema and constraint behavior. Record full restore duration and compare against the lab RTO.

## 6. Retention dependency exercise

Copy [retention decision worksheet](../labs/retention/065-retention-decision-template.csv) into your lab notes. Invent three base backups, multiple WAL intervals, one timeline switch and one immutable/legal-hold copy. For each candidate expiration, list required WAL segments, alternate recovery base, offsite status and hold status. A candidate is **NOT SAFE TO DELETE** unless every dependency and policy gate passes. Do not run any deletion command.

## 7. Recovery drill acceptance

| Gate | Evidence | Result |
|---|---|---|
| Backup artifact created | | Pending |
| Archive readable and hash recorded | | Pending |
| Restore to new database successful | | Pending |
| Data and schema validated | | Pending |
| Recovery time measured | | Pending |
| Retention dependency graph reviewed | | Pending |
| Legal hold / immutable copy checked | | Pending |
| WAL archive health inspected | | Pending |
| Offsite and key recovery plan documented | | Pending |

The logical restore test does **not** validate physical PITR. Repeat Chapter 064's isolated PITR drill before claiming WAL-retention acceptance.

## 8. Cleanup

After preserving evidence, remove only explicitly identified lab-owned databases/artifacts according to retention policy. Never remove live pg_wal or an archive segment used by a retained backup.

**Runtime:** pending.
