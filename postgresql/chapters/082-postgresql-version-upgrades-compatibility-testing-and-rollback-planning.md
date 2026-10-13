# Chapter 082 — PostgreSQL Version Upgrades, Compatibility Testing and Rollback Planning

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 target | **Status:** Authored; runtime validation pending

## 1. Objectives

Plan and validate minor and major PostgreSQL upgrades without assuming that a successful server startup means the application is ready. Integrate [Chapter 081 — Extensions and Compatibility](081-postgresql-extensions-compatibility-and-operational-lifecycle.md), backups, replication, query performance, application testing and operational rollback.

By the end, you should be able to select an upgrade approach, build a compatibility inventory, rehearse `pg_upgrade --check`, set cutover gates, and explain exactly when rollback is still safe.

## 2. Upgrade types

| Type | Mechanism | Main concern |
|---|---|---|
| Minor release, same major | Replace binaries/packages; restart or provider-managed maintenance | Extension/OS packaging, restart and replication compatibility |
| Major version, in-place cluster migration | `pg_upgrade` with old and new binaries | Catalog/data compatibility, extension binaries, downtime, rollback boundary |
| Major version, logical migration | Logical replication, dump/restore or managed migration | Schema/DDL coordination, sequences, replication lag and cutover consistency |
| New cluster restore | `pg_dump`/`pg_restore` to supported target | Restore time, schema compatibility, object ownership and extension availability |

PostgreSQL minor releases within one major version use compatible data directories, but still require controlled package and process management. Major releases are **not** in-place binary swaps of an existing data directory.

## 3. Preflight inventory

Collect:
- Exact source/target PostgreSQL major and minor versions, OS, architecture, package repositories and provider restrictions.
- All databases, roles, privileges, tablespaces, collation providers/versions, locales and encoding.
- Extensions and native libraries on every server; `shared_preload_libraries`, background workers and version support.
- Replication topology, physical slots, logical publications/subscriptions, replication origins, WAL archive, backups and PITR.
- Application drivers, ORMs, SQL syntax, prepared statements, stored procedures, authentication/TLS and poolers.
- Database size, index size, transaction throughput, WAL generation, free disk space, CPU/IO headroom and maintenance-window constraints.
- Measured RPO/RTO, application error budget and business change freeze.

Run [082 preflight SQL](../labs/sql/082-upgrade-preflight.sql) in each relevant database. SQL alone cannot verify OS package compatibility, cloud provider support, or extension binary availability.

## 4. Choosing the method

### pg_upgrade

Appropriate when source/target are supported by `pg_upgrade`, downtime is acceptable and extension requirements are satisfied. Requires both old and new PostgreSQL installations, separate data directories and a cleanly shut down old cluster. Read the official version-specific upgrade documentation.

```bash
# Illustrative only: adapt actual binary/data paths and port options.
# Run as the PostgreSQL OS account in a disposable rehearsal.
<new-bin>/pg_upgrade \
  --old-bindir=<old-bin> \
  --new-bindir=<new-bin> \
  --old-datadir=<old-data> \
  --new-datadir=<new-data> \
  --check
```

Replace placeholders before execution. Do not run against live production clusters. Test the actual `pg_upgrade` mode and tablespace layout; link mode and clone mode have different storage/rollback characteristics. In link mode, starting the new cluster can make reuse of the old cluster unsafe. Preserve a separate restorable backup regardless of mode.

### Logical migration

Useful for controlled cutover and potentially reduced downtime. Initial data load plus change replication can bridge versions when supported. However, built-in logical replication does not automatically reproduce every database object or DDL change; sequence state, roles, large objects, extensions and replication configuration require explicit planning. Replication compatibility and limitations vary by source and target versions. Freeze or coordinate DDL and perform a final consistent write cutover.

### Dump and restore

Useful for smaller databases, reorganization or version leaps where direct physical migration is unsuitable. Test roles/global objects, extensions, ownership, collations, restore ordering and elapsed time.

## 5. Compatibility testing matrix

| Domain | Minimum acceptance |
|---|---|
| SQL and application | Representative CRUD, transactions, stored procedures and batch jobs pass |
| Driver/pooler | Connection, authentication, TLS and failover behavior verified |
| Extensions | Compatible binaries/control files and supported upgrade path |
| Query plans | Baseline vs target latency, plans, index usage and statistics |
| Collations | Version differences reviewed; affected indexes reindexed where required |
| Replication | Expected replicas/subscribers recreated or reattached safely |
| Backup/DR | Fresh backup, archive continuity and isolated restore |
| Security | Roles, HBA/TLS, RLS, audit and secrets verified |
| Observability | Metrics, exporter queries, logs, alerts and dashboards functional |
| Capacity | CPU, memory, disk, WAL and temporary space within approved limits |

For PostgreSQL 18, assess changed defaults and behavior against the **actual source version**, not only release highlights.

## 6. Production-grade rehearsal

1. Take a verified source backup and restore a representative copy in an isolated environment.
2. Install exact target packages and extension binaries.
3. Run compatibility and `pg_upgrade --check` or logical-migration preflight.
4. Measure the full procedure including shutdown, migration, `ANALYZE`, reindex work, extension update, pooler restart, application checks and replication recovery.
5. Compare query plans and performance under representative load.
6. Verify application write/read consistency, audit controls and backup restore.
7. Capture rollback timing, required approvals and point-of-no-return conditions.
8. Repeat until the measured end-to-end outage fits the approved maintenance window.

## 7. Cutover runbook

**Before:** obtain change approval, verify backups and restore credentials, stop risky schema changes, freeze relevant deployments, record current version/LSNs and alert baselines.

**During:** drain application writes, stop background jobs, reconcile active transactions, execute the chosen migration, start target, validate logs/extensions, update connection routing and reopen traffic only after smoke tests.

**After:** monitor error rates, latency, locks, autovacuum, WAL/archive, replication, backups, connections and application consistency. Update version inventory, documentation and incident playbooks.

## 8. Rollback and forward-recovery decision

| Stage | Rollback feasibility | Required decision |
|---|---|---|
| Before write freeze | Straightforward abort | Cancel change and leave source authoritative |
| After freeze, before target writes | Potentially return to untouched source, method-dependent | Verify old cluster safety and routing |
| After target accepts writes | Old source is stale | Do **not** simply redirect clients; reconcile or reverse-migrate writes |
| After pg_upgrade link-mode new-cluster start | Old cluster reuse may be unsafe | Restore from independent backup or use planned forward recovery |
| After logical cutover | Requires supported reverse replication or migration | Validate schema/sequence/DDL and transaction consistency |
| Corruption, missing extension or failed DR | Recovery procedure, not simple rollback | Restore verified backup and WAL; meet RPO/RTO |

**Never promise zero-data-loss rollback after the target has accepted writes unless a tested reverse data path proves it.** Preserve an immutable evidence timeline of last source commit, first target commit and routing changes.

## 9. Failure modes

- `pg_upgrade --check` failure: missing libraries, unsupported extension, locale or configuration differences.
- Startup failure: configuration parameters removed or changed; library ABI mismatch.
- Query regression: planner/statistics differences, collation or index behavior; compare `EXPLAIN (ANALYZE, BUFFERS)` safely on a clone.
- Logical replication lag: initial load, slot WAL retention or subscriber apply errors.
- Incomplete application cutover: stale pool connections or dual writers.
- Backup failures: missing target-compatible extension packages or archive configuration.
- Security drift: restored roles, default grants, HBA and RLS differ from approved state.

## 10. Acceptance

Use [Chapter 082 lab](../labs/082-postgresql-version-upgrades-compatibility-testing-and-rollback-planning-lab.md), [preflight SQL](../labs/sql/082-upgrade-preflight.sql), [upgrade decision matrix](../labs/acceptance/082-upgrade-decision-matrix.csv) and [acceptance scorecard](../labs/acceptance/082-upgrade-acceptance-scorecard.csv).

A PASS requires version and extension compatibility, clean preflight, tested application workload, restored backups, replication and monitoring, approved outage measurement, and an explicit rollback/forward-recovery boundary. Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/upgrading.html
- https://www.postgresql.org/docs/18/pgupgrade.html
- https://www.postgresql.org/docs/18/logical-replication.html
- https://www.postgresql.org/docs/18/release.html
- https://www.postgresql.org/docs/18/sql-alterextension.html

**Next:** Chapter 083 — PostgreSQL Configuration Management, Infrastructure as Code and Drift Detection.
