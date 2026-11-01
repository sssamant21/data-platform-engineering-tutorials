# PostgreSQL DBRE V02 — SQL Catalog, Version and Cloud Compatibility Review

**Status:** V02-A source-based static review completed with **3 confirmed corrections**. **V02-B database execution and managed-service compatibility are PENDING**. Not production certified.  
**Review date:** 2026-11-01 UTC  
**Repository scope:** Seven DBRE operating guides, with SQL examples in pages 02–07  
**Supported upstream releases reviewed:** PostgreSQL 14, 15, 16, 17 and 18 (PG 19 RC is **not** treated as GA).

## 1. Outcome and review boundary

- Examined **20 fenced SQL examples** across six guides: Page 02 (6), Page 03 (1), Page 04 (9), Page 05 (2), Page 06 (1), Page 07 (1). Each block can contain multiple SQL statements.
- Compared referenced PostgreSQL monitoring views/catalog columns, built-in functions, and version-dependent features with official PostgreSQL documentation, particularly the PG 14 and 17–18 reference.
- Reviewed high-level privilege, backup, PITR and role limitations for self-managed PostgreSQL, AWS RDS for PostgreSQL and Aurora PostgreSQL, Azure PostgreSQL Flexible Server and Google Cloud SQL for PostgreSQL.
- Corrected **three** documented issues in the guides below.
- No SQL statements were run against PostgreSQL and no cloud accounts, databases, extensions or staging infrastructure were accessed.
- The remaining unexecuted statements are **not claimed fully validated**. V02 requires test evidence for each supported version, provider and intended monitoring role.

## 2. Confirmed defects corrected

| ID | Severity | Guide | Defect | Remediation |
|---|---|---|---|---|
| V02-F01 | High — query would fail | 05 Capacity and FinOps | Query selected `tablename` and `indexname` from `pg_stat_user_indexes`; that view instead exposes `relname` and `indexrelname`. | Replace with `relname AS table_name`, `indexrelname AS index_name`. |
| V02-F02 | Low — misleading label | 02 Operations | `now() AS sampled_at_utc` renders using the SQL session time zone, not necessarily UTC. | Explicit `now() AT TIME ZONE 'UTC'` (a UTC wall-clock timestamp without time-zone designation). |
| V02-F03 | Medium — misleading diagnostic identity | 04 Incident response | `relid::regclass` for `pg_stat_progress_vacuum` can resolve an OID against the current database when a row describes another database. OIDs for relations are database-local. | Show `relid AS relation_oid` and `datname`; resolve the OID in the matching database only. |

**Fix verification criteria:** Confirm corrected query text, that old invalid column names are absent in the affected relation query, and that changes remain read-only. Actual SQL run/results are still required for final pass.

## 3. PostgreSQL release compatibility matrix

| View/function/feature in the guides | PG14 | PG15 | PG16 | PG17 | PG18 | Restriction and interpretation |
|---|---|---|---|---|---|---|
| `pg_stat_activity` incl. `backend_type`, wait events | Reference | Reference | Reference | Reference | Reference | Visibility of other sessions requires appropriate roles; query text is sensitive |
| `pg_stat_database`, `stats_reset` | Reference | Reference | Reference | Reference | Reference | Counters reset; not comparable without reset-aware sampling |
| `pg_stat_user_tables`, `pg_stat_user_indexes` | Reference | Reference | Reference | Reference | Reference | Estimates and counts; no complete business usage audit |
| `pg_class`, `pg_database`, `pg_inherits`, `pg_namespace` | Reference | Reference | Reference | Reference | Reference | Relation OIDs valid only in their database; privileges may restrict visibility |
| `pg_stat_replication`, `pg_replication_slots` | Reference | Reference | Reference | Reference | Reference | Primary/replication topology; empty output may be expected |
| `pg_stat_archiver` | Reference | Reference | Reference | Reference | Reference | Does not certify a complete WAL archive or cloud-provider PITR |
| `pg_last_wal_receive_lsn`, `pg_last_wal_replay_lsn` | Reference | Reference | Reference | Reference | Reference | Standby-side assessment; not direct business RPO |
| `pg_current_wal_lsn`, `pg_wal_lsn_diff` | Reference | Reference | Reference | Reference | Reference | Primary-only in the slot-retention calculation |
| `pg_stat_progress_vacuum` | Reference | Reference | Reference | Reference | Reference | Captured OID + database; do not resolve against unrelated database |
| `pg_blocking_pids`, `cardinality` | Reference | Reference | Reference | Reference | Reference | Monitoring role should have sufficient activity visibility |
| `pg_stat_io` | Not available | Not available | Available | Available | Available | PG16+; only mentioned as version-gated extension to dashboards |
| `pg_stat_checkpointer` | Not available | Not available | Not available | Available | Available | PG17+; only mentioned as version-gated extension to dashboards |
| Incremental physical backup/`pg_combinebackup` | Not available | Not available | Not available | Available | Available | PG17+; not a runnable procedure in this guide |
| `pg_stat_statements` | Optional | Optional | Optional | Optional | Optional | Requires extension availability/configuration; never assume installed |

**Reference** means the documented upstream interface was reviewed, **not** that the actual SQL/role was executed on that release. Feature flags/parameter availability and exact provider restrictions still require empirical checks.

**Release lifecycle (review date):** PostgreSQL 18 is the current stable major; PG19 RC1 was released October 15, 2026 with GA planned November 19, 2026. PG14 support ends November 12, 2026. Do not target RC builds as production baseline.

## 4. Deployment/provider compatibility and ownership

| Environment | SQL monitoring expectation | Restriction / qualification | PITR / HA difference |
|---|---|---|---|
| Self-managed PG14–18 | Standard catalogs, statistics, WAL and activity views | Monitoring role needs `pg_read_all_stats` or carefully scoped equivalent where sensitive activity is involved; host storage/OS is DBRE/PLT responsibility | Physical base+WAL or approved backup manager and independently fenced HA |
| AWS RDS PostgreSQL | SQL metadata generally available per engine version/role | No unrestricted PostgreSQL superuser or OS access; `rds_superuser` is an administrative role with restricted scope | Provider-controlled backups, RDS instance restore, Multi-AZ/replicas depend on selected features |
| Amazon Aurora PostgreSQL | PG-compatible SQL subset and Aurora-specific monitoring | Version/cluster-writer versus reader semantics and restricted features must be tested separately from plain RDS | Aurora cluster storage, endpoints, backups and failover are not identical to RDS PostgreSQL |
| Azure PostgreSQL Flexible Server | Standard supported PostgreSQL SQL with role limits | Administrator is member of `azure_pg_admin` but cannot become true superuser; managed parameters/HA/backup via Azure control plane | Server PITR produces a new server and networking/HA state must be validated |
| Google Cloud SQL PostgreSQL | Standard supported PostgreSQL SQL with role limits | No customer superuser; `cloudsqlsuperuser` is restricted, service-control functions limited | PITR creates a new instance; enabled-by-default behavior varies by edition/creation path |

**Privilege rule:** A command that is *read-only* may still return incomplete/redacted activity data or fail without privileges. An empty replication query is not necessarily a broken standby; verify role and intended target.

## 5. SQL placement matrix (required execution contexts)

| Class | Examples | Required context |
|---|---|---|
| Any properly authorized connection | `current_setting`, `pg_is_in_recovery`, `pg_stat_database`, size/catalog view inspection | Correct database for per-relation results |
| Primary only | `pg_current_wal_lsn` plus `pg_replication_slots.restart_lsn`, primary `pg_stat_replication` | Confirm `pg_is_in_recovery() = false`; absent replicas may legitimately yield no rows |
| Standby only to assess replay | `pg_last_wal_receive_lsn`, `pg_last_wal_replay_lsn`, `pg_last_xact_replay_timestamp` | Confirm `pg_is_in_recovery() = true`; latest replay timestamp can be old when idle |
| Requires monitoring privilege and privacy restrictions | `pg_stat_activity` queries inspecting users/processes, `pg_blocking_pids`, `pg_stat_progress_vacuum` | Least-privilege approved role, redact usernames/queries as policy requires |
| Requires provider metrics / control plane | Actual free disk, CPU, cloud backup coverage, latest restorable time, managed failover state | Cloud monitoring/IAM separate from PostgreSQL SQL privileges |
| Requires installed extension | `pg_stat_statements` workload history | Check installed extension and preload, supported version and access role |

## 6. Recommended non-destructive staging preflight pack

Use only a named authorized test DB/role with a statement timeout and database identity captured. This is a suggested test pack, **not** evidence of execution.

~~~~sql
-- 1. Establish target role, major/minor version and primary/standby identity.
SELECT current_database() AS database_name,
       current_user AS monitor_role,
       current_setting('server_version_num')::int AS server_version_num,
       pg_is_in_recovery() AS is_standby,
       (now() AT TIME ZONE 'UTC') AS sampled_at_utc;

-- 2. Confirm expected monitoring system views exist before testing more.
SELECT v.view_name,
       to_regclass('pg_catalog.' || v.view_name) AS available_as
FROM (VALUES ('pg_stat_activity'),
             ('pg_stat_database'),
             ('pg_stat_user_tables'),
             ('pg_stat_user_indexes'),
             ('pg_stat_replication'),
             ('pg_replication_slots'),
             ('pg_stat_archiver'),
             ('pg_stat_progress_vacuum')) AS v(view_name);

-- 3. Confirm allowed monitoring privileges in the intended test role.
SELECT current_user AS role_name,
       pg_has_role(current_user, 'pg_read_all_stats', 'MEMBER') AS has_stats_role;

-- 4. Validate index catalog column names without reading business data.
SELECT a.attname AS column_name
FROM pg_catalog.pg_attribute AS a
WHERE a.attrelid = 'pg_catalog.pg_stat_user_indexes'::regclass
  AND a.attnum > 0
  AND NOT a.attisdropped
ORDER BY a.attnum;
~~~~

**Note:** Privilege checks alone cannot prove the role can see all needed sessions or execute every function. Test the actual read-only statements with `psql -X -v ON_ERROR_STOP=1` and logging in **authorized staging**, with real provider/role credentials supplied securely. Do not collect full business query text or patient records.

### Mandatory test evidence per guide and platform

| Test ID | Guide/scope | Minimum evidence |
|---|---|---|
| V02-T01 | 02 Daily | Executed SQL/EXPLAIN, role, primary/standby, version, row schema |
| V02-T02 | 03 Monitoring | pg_exporter actual metric labels; any SQL data source; privacy review |
| V02-T03 | 04 Incident | Blocking, replica lag, archive, vacuum, XID and slot diagnostics |
| V02-T04 | 05 Capacity | Corrected index inventory, sizes, partition parent/leaf, volume metrics |
| V02-T05 | 06 Backup/DR | SQL read-only diagnostics plus provider archive/backup status, no promotion |
| V02-T06 | 07 Lifecycle | Catalog/usage/constraints, restricted monitoring role, no DDL |
| V02-T07 | Self-managed / RDS / Aurora / Azure / Cloud SQL | Each deployed version and provider with monitoring access/feature notes |
| V02-T08 | Error/denial paths | Query on a standby when primary-only; low-privilege role; missing extension |

## 7. Outstanding acceptance gates

- [x] Statistically/source-based review of all **20 SQL blocks** in the existing seven guides.
- [x] Three confirmed guide defects patched.
- [x] Main views/functions version-gated and primary/standby placement documented.
- [x] Cloud-provider superuser/managed-service restrictions documented.
- [ ] Syntax and result schema executed on a controlled PG14–18 staging matrix (at least exact versions actually deployed).
- [ ] Managed RDS/Aurora/Azure/Cloud SQL role-specific SQL behavior verified.
- [ ] Exporter collection, labels, alerts and APP SLIs checked (V03).
- [ ] Read-only role and PHI-safe evidence accepted by Security.
- [ ] DBRE peer review and independent technical approval.

**V02 status: STATIC REVIEW COMPLETE WITH FIXES; runtime verification PENDING.** Do **not** mark the entire V02 test phase PASS until actual SQL/permissions/managed-provider evidence exists.

## 8. Source documents

- [PostgreSQL 14 statistics (catalogs and column names)](https://www.postgresql.org/docs/14/monitoring-stats.html)
- [PostgreSQL 17 statistics (checkpointer and I/O)](https://www.postgresql.org/docs/17/monitoring-stats.html)
- [PostgreSQL 14 vacuum progress view](https://www.postgresql.org/docs/14/progress-reporting.html)
- [PostgreSQL 16 I/O statistics release](https://www.postgresql.org/about/press/presskit16/)
- [PostgreSQL release policy and supported versions](https://www.postgresql.org/support/versioning/)
- [PostgreSQL 19 RC and GA plan (October 15, 2026)](https://www.postgresql.org/about/news/postgresql-19-rc-1-released-3409/)
- [AWS RDS restricted rds_superuser](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.PostgreSQL.CommonDBATasks.Roles.rds_superuser.html)
- [Azure Flexible Server roles](https://learn.microsoft.com/en-us/azure/postgresql/configure-maintain/concepts-servers)
- [Cloud SQL PostgreSQL users and restricted superuser](https://docs.cloud.google.com/sql/docs/postgres/users)
- [Cloud SQL PITR creates new instance](https://docs.cloud.google.com/sql/docs/postgres/backup-recovery/pitr)
