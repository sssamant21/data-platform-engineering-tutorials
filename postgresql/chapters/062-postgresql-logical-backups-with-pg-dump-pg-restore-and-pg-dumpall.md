# Chapter 062 — PostgreSQL Logical Backups with pg_dump, pg_restore and pg_dumpall

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Authored; runtime validation pending

## 1. Mission and scope

Design, execute, inspect and validate logical backups with `pg_dump`, `pg_restore` and `pg_dumpall`. Recover databases, schemas and tables without confusing logical exports with physical backups or point-in-time recovery. Follows [Chapter 061 — Backup Strategy, RPO and RTO](061-postgresql-backup-strategy-rpo-and-rto-fundamentals.md).

A logical dump captures a consistent snapshot of database objects and data according to selected options. It does **not** include the entire PostgreSQL cluster's physical files or provide continuous WAL replay. `pg_dump` covers **one database**, not cluster-wide roles or tablespaces; capture globals separately.

## 2. Tool comparison

| Tool | Scope | Output | Restore |
|---|---|---|---|
| `pg_dump` | One database, optional object filters | Plain, custom, directory, tar | `psql` for plain; `pg_restore` for archives |
| `pg_restore` | Restore or inspect archive | Database objects and data | Supports selective and parallel restore |
| `pg_dumpall` | All databases or cluster globals | Plain SQL | `psql` |
| `pg_basebackup` | Physical cluster files | Physical backup | Physical recovery procedure, not `pg_restore` |

**Version rule:** use a `pg_dump` client at least as new as the source server's major version, and confirm target-server compatibility. Dumps are generally intended for newer PostgreSQL targets, not guaranteed backward compatibility. Extensions, collations, ownership and privileges need separate checks.

## 3. Archive formats

| Format | Flag | Advantages | Limitations |
|---|---|---|---|
| Plain SQL | `-Fp` (default) | Readable, `psql` restore | No `pg_restore` selective/parallel features |
| Custom | `-Fc` | Compressed archive, flexible selective restore | `pg_restore` required |
| Directory | `-Fd` | Parallel dump (`-j`), flexible restore | Directory of multiple files; protect whole set |
| Tar | `-Ft` | Single archive, portable | No parallel restore; less flexible than custom/directory |

**Parallelism:** `pg_dump -j` is supported with directory format; `pg_restore -j` supports custom and directory archives. Parallel workers open additional database connections and consume CPU/I/O; size against the connection budget.

## 4. Production-safe backup commands

PowerShell examples assume PostgreSQL binaries are on PATH and authentication is configured securely (service file, protected password file, or interactive prompt; never commit passwords).

```powershell
# Single database custom-format archive
pg_dump -h localhost -p 5432 -U backup_user -d appdb -Fc -f .\backups\appdb.dump

# Directory archive, four parallel dump workers
pg_dump -h localhost -U backup_user -d appdb -Fd -j 4 -f .\backups\appdb.dir

# Plain SQL (restore with psql, not pg_restore)
pg_dump -h localhost -U backup_user -d appdb -Fp -f .\backups\appdb.sql

# Cluster globals: roles and tablespace definitions
pg_dumpall -h localhost -U postgres --globals-only -f .\backups\globals.sql
```

Backup accounts need privileges to read all intended objects. Row-level security can affect dumping; `pg_dump` normally attempts to bypass RLS and may fail if the role lacks privileges. Validate roles and RLS expectations before backup. For globals, use an appropriately authorized account and restrict access to the output because it may contain sensitive role metadata.

## 5. Inspect before restoring

```powershell
pg_restore -l .\backups\appdb.dump
pg_restore --schema-only -f .\backups\schema-preview.sql .\backups\appdb.dump
```

The archive table of contents (TOC) supports selective restore with `-L`. Review dependencies before excluding objects. `--schema-only` is not a substitute for data verification.

## 6. Restore patterns

```powershell
# Restore to an existing EMPTY test database
createdb -h localhost -U postgres appdb_restore
pg_restore -h localhost -U postgres -d appdb_restore --exit-on-error --verbose .\backups\appdb.dump

# Parallel restore from custom archive; test CPU/I/O and connection impact
pg_restore -h localhost -U postgres -d appdb_restore -j 4 --exit-on-error .\backups\appdb.dump

# Restore a plain SQL dump to an empty database
psql -X -v ON_ERROR_STOP=1 -h localhost -U postgres -d appdb_restore -f .\backups\appdb.sql
```

Run each restore example against a **fresh empty database**; do not execute the three examples consecutively against the same populated target. `--clean` and `--create` change/drop objects and must never be used against a live database without explicit approval. `--single-transaction` can make compatible nonparallel restores atomic but may increase lock duration and cannot be combined with parallel jobs.

For a selective table restore:

```powershell
pg_restore -h localhost -U postgres -d isolated_restore --table=public.orders --exit-on-error .\backups\appdb.dump
```

Selective table restores do not automatically guarantee restoration of all dependent schema, extensions, sequences, roles or related data. Prefer restoring the full database into isolation, validating dependencies and then copying only the required data back under a reviewed change.

## 7. Roles, ownership and security

- Restore `pg_dumpall --globals-only` output **before** databases when ownership/role fidelity matters; review role names, passwords, privileges and tablespace paths first.
- `pg_restore --no-owner --no-acl` can simplify isolated migration tests but intentionally changes ownership/grant semantics; it is **not** a production-equivalent restore.
- Dumps can contain sensitive data. Encrypt in transit and at rest, limit retention, protect keys and audit access.
- A dump may contain SQL or extension definitions. Treat restores from untrusted sources as executable code; restore into an isolated environment first.
- Large objects, extensions, partitioned tables, foreign servers, publications and subscriptions need explicit inventory and validation. Not every external dependency is included in a database dump.

## 8. Integrity and recovery acceptance

Validate more than file existence:

1. Backup process exit status and archive TOC readability.
2. Artifact size, timestamp, checksum, secure storage and retention.
3. Isolated restore without unreviewed errors.
4. Database schemas, tables, row counts, key business queries and constraints.
5. Extensions, roles, ownership, grants, sequences, functions and application connectivity.
6. Timed recovery duration versus RTO and dump age versus RPO.
7. Offsite copy and restore credentials independently recoverable.

For a portable artifact checksum on Windows:

```powershell
Get-FileHash .\backups\appdb.dump -Algorithm SHA256
```

A checksum only verifies that the artifact matches a recorded digest; it does not prove logical correctness or completeness.

## 9. Operational pitfalls and troubleshooting

| Symptom | Cause | Response |
|---|---|---|
| `permission denied for table` | Backup role lacks read rights | Review privileges; avoid blind SUPERUSER grants |
| `role does not exist` | Globals not restored | Restore reviewed globals or map ownership |
| `extension is not available` | Target lacks extension package | Install compatible extension before restore |
| `relation already exists` | Target not empty | Restore into new isolated database |
| `could not open input file` | Wrong format/path | Check `pg_restore -l` and artifact integrity |
| Slow parallel restore | CPU, I/O, locks or indexes | Tune worker count and target capacity |
| Missing data after filtered restore | Dependency/selection mismatch | Restore full archive in isolation and reconcile |
| Different collation behavior | OS/ICU version mismatch | Validate collations and reindex requirements |

## 10. Lab

The [Chapter 062 lab](../labs/062-postgresql-logical-backups-with-pg-dump-pg-restore-and-pg-dumpall-lab.md) provisions a disposable source database, creates custom and directory backups, inspects archives, restores to an isolated target and verifies schema, row counts, constraints and sequence state. The [SQL fixture](../labs/sql/062-fixture.sql) and [verification SQL](../labs/sql/062-verify.sql) are scoped to lab databases.

**Acceptance:** valid archive, error-free isolated restore, matching expected data, validated ownership/grants and measured restore duration. **Runtime:** pending.

## References

- [PostgreSQL SQL dump](https://www.postgresql.org/docs/18/backup-dump.html)
- [pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html)
- [pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html)
- [pg_dumpall](https://www.postgresql.org/docs/18/app-pg-dumpall.html)

**Next:** Chapter 063 — PostgreSQL Physical Backups with pg_basebackup and Backup Verification.
