# Chapter 082 — Version Upgrades, Compatibility Testing and Rollback Planning Lab

**PostgreSQL 18 target · Disposable source/target clusters · Runtime pending**

## 1. Safety and setup

Prepare two isolated PostgreSQL clusters: a supported older source version and PostgreSQL 18 target, plus a separate backup/restore location. Never run pg_upgrade on a live production data directory. Ensure matching source/target binaries, extension packages and sufficient disk space. Capture a verified independent backup before any experiment.

## 2. Source baseline

Run [082 preflight SQL](../labs/sql/082-upgrade-preflight.sql) in each source database. Record server version, database encodings/collations, extension versions, replication slots, configuration, WAL/archive status and current application behavior. Collect OS package and extension binary inventories separately.

## 3. Compatibility matrix

Complete [082 decision matrix](../labs/acceptance/082-upgrade-decision-matrix.csv). Mark unsupported source/target version combinations as BLOCKED. Check drivers, SQL, indexes, collations, TLS, RLS, backups, replication and monitoring.

## 4. pg_upgrade rehearsal

Install old/new binaries and create a clean new target cluster. Shut down the old cluster according to official guidance. Run `pg_upgrade --check` with actual paths and capture output. Resolve missing libraries or incompatible extensions before proceeding.

Only if checks pass and a tested independent backup exists, execute the chosen `pg_upgrade` method in the disposable lab. Avoid link mode if you need an independently reusable old data directory. Record full downtime and post-upgrade scripts.

## 5. Application and performance acceptance

Validate schema, row counts/checksums for chosen fixtures, CRUD, prepared statements, drivers, connection pools, TLS, RLS, extensions and representative query plans. Run required statistics collection. Rebuild/rejoin replicas using the approved target-version procedure; verify backups and WAL archive.

## 6. Rollback tabletop

Record three decision points: before freeze, after freeze but before target writes, and after target writes. For each, name authoritative writer, recovery path, data reconciliation and expected RPO/RTO. Do not route writes to a stale source after cutover.

## 7. Acceptance and cleanup

Fill [082 scorecard](../labs/acceptance/082-upgrade-acceptance-scorecard.csv) with UTC timestamps and evidence. Restore the disposable source from backup to prove recoverability. Remove lab clusters only after evidence is preserved.

**Runtime:** pending; do not mark pg_upgrade or rollback PASS without execution.
