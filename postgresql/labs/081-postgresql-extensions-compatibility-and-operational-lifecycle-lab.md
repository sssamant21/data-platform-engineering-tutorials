# Chapter 081 — Extensions, Compatibility and Operational Lifecycle Lab

**PostgreSQL 18 · Disposable lab only · Runtime pending**

## 1. Prerequisites

Use a disposable PostgreSQL 18 instance and a lab database. Have administrator access for installing server-side extension packages where required, a fresh backup, and a separate restore target. Do not install unknown extensions or run upgrade scripts in production.

## 2. Inventory

Run [081 read-only SQL](../labs/sql/081-extension-lifecycle-inspect.sql) in **each database**. Record PostgreSQL version, installed extensions, available versions, dependencies, preload settings, and OS package versions from outside SQL. Complete [compatibility matrix](../labs/acceptance/081-extension-compatibility-matrix.csv).

## 3. Safe installation

Create a disposable database and use a supported built-in/contrib extension such as `pg_trgm`, if available:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
SELECT extname,extversion FROM pg_extension WHERE extname='pg_trgm';
SELECT similarity('postgres','postgress');
```

If unavailable, record NOT VERIFIED rather than installing an unapproved binary. Confirm only authorized roles can create extensions.

## 4. Dependency and upgrade checks

Inspect `pg_depend` and `pg_extension_update_paths('pg_trgm')`. If a supported update path to a different available version exists, rehearse `ALTER EXTENSION pg_trgm UPDATE TO 'approved_version'` **only in the lab**. If not, document that no meaningful update was executed; do not mark an upgrade PASS.

## 5. Backup/restore and compatibility

Create a logical backup of the disposable database. Restore to a separate target with the matching extension package installed; validate `pg_extension` version and sample queries. For a major-upgrade rehearsal, check extension binary support on the target PostgreSQL version and use `pg_upgrade --check` in a disposable cluster.

## 6. Failure and rollback exercise

Simulate a missing extension package on a disposable restore target, capture the expected failure, install the supported package, and retry. Document the rollback method: not every extension supports downgrade. Confirm the backup and restore path before approving an update.

## 7. Acceptance and cleanup

Complete [081 scorecard](../labs/acceptance/081-extension-lifecycle-scorecard.csv). Record SQL output, package versions, UTC timestamps, approvals and application smoke-test results. Drop only the disposable database after preserving evidence.

**Runtime:** pending; unsupported or skipped extension upgrades remain NOT VERIFIED.
