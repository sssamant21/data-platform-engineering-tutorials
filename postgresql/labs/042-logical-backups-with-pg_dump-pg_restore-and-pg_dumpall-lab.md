# Chapter 042 — Logical Backups Lab

**PostgreSQL 18 · Disposable local databases only · Runtime validation pending.**

## 1. Safety and preflight

Use local databases `ch042_source` and `ch042_restore`. Verify neither exists before creating them. Do not execute on production or shared staging. The lab never overwrites the source database.

```bash
pg_dump --version
pg_restore --version
psql -X -d postgres -c "SELECT datname FROM pg_database WHERE datname IN ('ch042_source','ch042_restore');"
createdb ch042_source
createdb ch042_restore
psql -X -v ON_ERROR_STOP=1 -d ch042_source -f postgresql/labs/sql/042-fixture.sql
```

## 2. Custom archive and independent restore

```bash
pg_dump -Fc --no-owner -d ch042_source -f ch042-source.dump
pg_restore --list ch042-source.dump
pg_restore --exit-on-error --no-owner --no-privileges -d ch042_restore ch042-source.dump
psql -X -v ON_ERROR_STOP=1 -d ch042_source -f postgresql/labs/sql/042-verify.sql
psql -X -v ON_ERROR_STOP=1 -d ch042_restore -f postgresql/labs/sql/042-verify.sql
```

Compare row count, aggregate amount, deterministic digest, index definitions and sequence values. Record dump and restore elapsed time.

## 3. Alternative formats

Run these only as **alternative backup artifacts**; do not restore repeatedly into the already populated target.

```bash
pg_dump -Fp -d ch042_source -f ch042-source.sql
pg_dump -Fd -j 2 -d ch042_source -f ch042-source-dir
pg_dump -Ft -d ch042_source -f ch042-source.tar
pg_dumpall --globals-only -f ch042-globals.sql
```

The globals file can contain sensitive configuration. Review it securely and **do not execute it** as part of this lab. To test parallel restore, provision another new empty lab database first and use `pg_restore -j 2` against the custom or directory archive.

## 4. Failure drill and decision worksheet

| Test | Expected evidence |
|---|---|
| Archive inventory | pg_restore --list succeeds |
| Restore | Exit code zero and no SQL errors |
| Table data | Source and restore counts/digest match |
| Indexes | Required indexes exist |
| Sequence | Next generated ID exceeds existing IDs |
| Permissions | Ownership/grant strategy documented |
| Globals | Inspected, not applied |
| RTO | Measured restore + validation duration |

Discuss missing roles, extensions, version mismatches, disk exhaustion, and partial selective backups. Stop if the target is not empty or a command would overwrite existing data.

## 5. Cleanup

Keep archives until evidence is reviewed. Remove the two databases only after confirming they are exclusively lab-owned and no applications depend on them. Use your approved local database cleanup procedure.

**Pass:** independent validated restore with documented limitations and RPO/RTO evidence. **Runtime:** pending.
