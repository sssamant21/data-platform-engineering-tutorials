# Chapter 062 — Logical Backups with pg_dump, pg_restore and pg_dumpall Lab

**PostgreSQL 18 · Windows PowerShell · Runtime validation pending**

## 1. Safety

Use a disposable PostgreSQL 18 instance and confirm `ch062_source` and `ch062_restored` do not already exist. Never use `--clean` against production. Store dumps in a protected directory; dumps may contain credentials or personal data.

## 2. Provision source

```powershell
createdb -U postgres ch062_source
psql -X -v ON_ERROR_STOP=1 -U postgres -d ch062_source -f postgresql/labs/sql/062-fixture.sql
```

The fixture refuses to run outside `ch062_source`.

## 3. Back up and inspect

```powershell
New-Item -ItemType Directory -Force -Path .\backups\ch062 | Out-Null
pg_dump -U postgres -d ch062_source -Fc -f .\backups\ch062\source.dump
pg_restore -l .\backups\ch062\source.dump
Get-FileHash .\backups\ch062\source.dump -Algorithm SHA256

# Parallel dump needs DIRECTORY format.
pg_dump -U postgres -d ch062_source -Fd -j 2 -f .\backups\ch062\source.dir
```

Do not rerun directory dump against an existing nonempty output directory without removing only the **lab-owned** archive first.

## 4. Restore in isolation

```powershell
createdb -U postgres ch062_restored
pg_restore -U postgres -d ch062_restored --exit-on-error --verbose .\backups\ch062\source.dump
psql -X -v ON_ERROR_STOP=1 -U postgres -d ch062_restored -f postgresql/labs/sql/062-verify.sql
```

Verify expected rows, table/constraint presence and sequence behavior. Record restore duration. For a parallel restore experiment, create a **second empty database** rather than restoring again into the populated target.

## 5. Globals inventory

```powershell
pg_dumpall -U postgres --globals-only -f .\backups\ch062\globals.sql
```

Review and protect this file; **do not execute it** in the lab unless role/tablespace changes are explicitly approved. Explain why globals are not included in a single-database `pg_dump`.

## 6. Acceptance checklist

| Gate | Expected | Evidence |
|---|---|---|
| Custom archive created | Successful exit | |
| TOC readable | `pg_restore -l` succeeds | |
| SHA-256 captured | Digest recorded | |
| Directory archive created | Complete directory | |
| Isolated restore | No errors | |
| Row and constraint checks | Match fixture | |
| Sequence state | Next generated ID valid | |
| Globals reviewed | Separate artifact | |
| RPO/RTO assessment | Documented | |

## 7. Cleanup

Only after retaining evidence and confirming ownership, drop the lab databases and securely dispose of lab artifacts according to retention policy. Never remove a production backup.

**Runtime:** pending.
