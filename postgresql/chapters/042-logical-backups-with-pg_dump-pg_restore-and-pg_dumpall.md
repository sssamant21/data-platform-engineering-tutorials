# Chapter 042 — Logical Backups with pg_dump, pg_restore and pg_dumpall

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Draft; runtime verification pending

## 1. Objectives

Perform and validate logical backups using `pg_dump`, `pg_restore` and `pg_dumpall`; choose the correct format, scope and parallelism; preserve roles and permissions; restore selected objects safely; and diagnose incomplete restores. This chapter follows [Chapter 041 — Backup Architecture and Recovery Objectives](041-postgresql-backup-architecture-and-recovery-objectives.md).

## 2. Choose a backup format

| Format | Example | Strength | Limitation |
|---|---|---|---|
| Plain SQL | `pg_dump -Fp` | Readable, restore via psql | No pg_restore object selection or parallel restore |
| Custom | `pg_dump -Fc` | Compressed archive, selective and parallel restore | Dump creation itself is single-process |
| Directory | `pg_dump -Fd -j 4` | Parallel dump and restore | Directory contains multiple files; protect all |
| Tar | `pg_dump -Ft` | Portable archive | No parallel restore; restrictions on reordering |

Use `pg_dump` for one database and `pg_dumpall` for a cluster-wide logical export, including roles and tablespaces. `pg_dumpall --globals-only` exports global objects such as roles and tablespaces. A `pg_dump` archive alone does not preserve all cluster-level dependencies.

Logical backups capture a consistent snapshot of database contents but do not provide arbitrary point-in-time recovery; use physical backups plus continuous WAL archiving for PITR.

## 3. Preflight and security

Verify the source PostgreSQL major version, dump client version, database size, disk space, object ownership, extensions, collations, privileges and restore target compatibility. `pg_dump` cannot dump from a server newer than its own major version; restoring into an older major version is not guaranteed to work. Prefer matching or newer target tooling and test extensions and collation differences.

```bash
pg_dump --version
pg_restore --version
psql -X -d postgres -c "SELECT version();"
psql -X -d postgres -c "SELECT datname, pg_size_pretty(pg_database_size(oid)) FROM pg_database WHERE datallowconn;"
```

Use protected credentials (`.pgpass`, secret manager, or interactive prompt) rather than plaintext passwords on command lines. Encrypt backup storage and restrict file access. Protect dumps as production data.

## 4. Backup examples

```bash
# Custom-format full database
pg_dump -Fc --no-owner -d appdb -f appdb.dump

# Directory format with four parallel dump jobs
pg_dump -Fd -j 4 -d appdb -f appdb_dir

# Plain SQL, suitable for psql restore
pg_dump -Fp -d appdb -f appdb.sql

# One schema or table (external dependencies may be omitted)
pg_dump -Fc -n reporting -d appdb -f reporting.dump
pg_dump -Fc -t reporting.events -d appdb -f events.dump

# Cluster-global definitions (review secrets/roles in resulting SQL)
pg_dumpall --globals-only -f globals.sql
```

A selective `-t` dump does not automatically include everything needed by the selected table (e.g. external dependencies). A `-n` dump may omit objects outside the selected schema. Plan restore ordering.

## 5. Restore safely

**Never restore over a valuable database without a tested rollback.** Create an isolated recovery target first.

```bash
createdb appdb_restore
pg_restore --list appdb.dump
pg_restore --exit-on-error --no-owner --no-privileges -d appdb_restore appdb.dump

# Parallel restore of a custom/directory archive into a fresh target
pg_restore --exit-on-error -j 4 --no-owner --no-privileges -d appdb_restore appdb.dump

# Plain SQL
psql -X -v ON_ERROR_STOP=1 -d appdb_restore -f appdb.sql
```

The two `pg_restore` examples are alternatives, not sequential steps into the same populated database. A parallel restore uses multiple connections and can increase I/O/WAL pressure; size `-j` from CPU, disk and connection capacity.

To inspect or select objects:

```bash
pg_restore --list appdb.dump
pg_restore --schema=reporting --table=events --no-owner --no-privileges -d appdb_restore appdb.dump
```

Selective restore requires checking dependencies, ownership, grants, extension availability and sequences. Use `--clean` and `--if-exists` only after reviewing exactly what would be removed; do not treat them as safe defaults.

## 6. Globals and role restoration

```bash
pg_dumpall --globals-only -f globals.sql
# Review roles, permissions, tablespaces and credentials before applying.
# Restore only into an authorized isolated target:
psql -X -v ON_ERROR_STOP=1 -d postgres -f globals.sql
```

Globals may include sensitive role configuration and are cluster-scoped. Applying them can conflict with existing roles and tablespaces. The lab deliberately avoids applying globals automatically.

## 7. Verification checklist

1. Check exit codes and logs; `pg_restore --exit-on-error` prevents silent continuation after SQL errors.
2. Confirm restored schemas, tables, views, functions, sequences, indexes, constraints and extensions.
3. Compare row counts, aggregate checksums and application invariants. Counts alone are insufficient for complex data.
4. Check sequence next values, foreign keys, privileges and object ownership.
5. Run `ANALYZE` on restored tables where appropriate; optimizer statistics are not necessarily carried as current runtime stats.
6. Execute representative application queries and compare expected results.
7. Record elapsed backup/restore time, throughput, resource use and achieved RPO/RTO.

## 8. Troubleshooting

| Symptom | Likely cause | Response |
|---|---|---|
| pg_dump refuses newer server | Client/server version mismatch | Use compatible newer pg_dump |
| Restore role does not exist | Missing globals or owner mapping | Review roles or use approved no-owner restore |
| Extension missing | Target prerequisites absent | Install compatible extension before restore |
| Duplicate object errors | Target not empty | Restore into new isolated database |
| Disk/WAL saturation | Large restore or excessive parallelism | Throttle jobs, add headroom, monitor replicas |
| Missing dependencies in selective dump | Scope excludes referenced objects | Expand export/restore scope |
| Counts match but app fails | Grants, sequences, functions, collations | Run deeper validation and application smoke tests |

## 9. Hands-on lab

[Chapter 042 lab](../labs/042-logical-backups-with-pg_dump-pg_restore-and-pg_dumpall-lab.md) creates a disposable source database, takes a custom-format archive, restores into an independent target, verifies rows and indexes, and inspects global definitions without applying them.

**Acceptance:** format selection explained, independent restore validated, ownership/role considerations documented, restore duration measured, and no source overwrite. **Runtime status:** not executed.

## Official references

- [pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html)
- [pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html)
- [pg_dumpall](https://www.postgresql.org/docs/18/app-pg-dumpall.html)
- [Backup and restore](https://www.postgresql.org/docs/18/backup.html)

**Next:** Chapter 043 — Physical Backups with pg_basebackup and Backup Manifests.
