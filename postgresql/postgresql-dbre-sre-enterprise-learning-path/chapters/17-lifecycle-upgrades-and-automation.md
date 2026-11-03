# Chapter 17 — Lifecycle, Upgrades and Automation

**Audience:** DBRE/SRE · **Duration:** 60 minutes · **Status:** Authored, not runtime validated

## Objectives and prerequisites
Explain PostgreSQL release lifecycle, minor versus major upgrades, staged upgrade choices, rollback limits, and automation safety. Prerequisites: Chapters 01–16, Docker Desktop with Linux containers, Docker CLI, 2 GB free memory, and PowerShell or bash. All executable examples target the official `postgres:17` image and a disposable local instance. Version 17 is a teaching baseline, not a claim that it is the newest supported major release. Check the upstream version policy before planning production changes.

## 60-minute teaching plan
| Minutes | Activity |
|---|---|
| 0–10 | Release lifecycle, security patches and version inventory |
| 10–20 | Minor versus major upgrades and ownership |
| 20–30 | Architecture: backups, extensions, replicas, application compatibility |
| 30–45 | Local inventory and reversible schema migration lab |
| 45–55 | Change gates, rollback and automation design |
| 55–60 | Acceptance and incident scenarios |

## Fundamentals and architecture
PostgreSQL minor releases stay within the same major version and normally replace server binaries while retaining the existing data directory; follow vendor/platform-specific restart and patch instructions. Major releases require a migration mechanism such as `pg_upgrade`, logical replication or dump/restore. Never assume a major-version data directory can be mounted into a different-major server image.

A safe enterprise pipeline is **inventory → compatibility analysis → tested backup and restore → staging rehearsal → change approval → execution → application validation → monitoring → closure**. Capture database size, server version, installed extensions and their compatibility, collation dependencies, replication topology, HA orchestration, parameter changes, RPO/RTO targets, maintenance window and client/driver support. AWS RDS and Kubernetes operators have distinct upgrade procedures; local Docker exercises do not simulate them.

### Strategy comparison
| Method | Typical scope | Key consideration |
|---|---|---|
| Minor release patch | Same major version | Plan restart, HA and replica order; preserve backups |
| `pg_upgrade` | Major version | Requires compatible old/new binaries and extensions; rehearsed cutover |
| Dump and restore | Major migration | More portable but potentially lengthy; measure downtime |
| Logical replication | Low-downtime migration | Schema/DDL and sequences need explicit coordination; cutover consistency |
| Blue/green platform feature | Managed environments | Verify provider-specific support and rollback semantics |

**Rollback distinction:** a schema migration may be reversed if explicitly designed for it. A committed major upgrade or data transformation cannot safely be rolled back merely by switching binaries. Define restore/rebuild and data reconciliation procedures before cutover.

## Local exercise
Follow [Chapter 17 lab](../labs/chapter-17/README.md). Inventory with `SHOW server_version;`, `SELECT current_setting('server_version_num');`, `SELECT extname, extversion FROM pg_extension;` and `SELECT datname FROM pg_database WHERE datallowconn;`. Create a synthetic table, apply an additive migration, verify it and reverse it safely. Expected: server major 17, a table column added then removed, and no changes to external databases.

## Automation guardrails
- Require explicit environment identity, inventory snapshot and dry-run diff.
- Never automate production major upgrades, promotions or destructive schema changes without human change approval and recovery evidence.
- Use a least-privileged identity, redact credentials, and avoid embedding passwords in scripts or Git.
- Apply timeouts, concurrency controls, maintenance windows, idempotency checks and post-change SLO checks.
- Separate authoring, static checking, actual staging execution, independent review and production authorization.
- Record before/after versions, change ticket, backups, rollback trigger, owner and timestamp.

## Troubleshooting
| Symptom | Diagnosis | Safe response |
|---|---|---|
| Docker daemon unavailable | `docker info` | Start Docker Desktop; do not target another host |
| Version mismatch | `SHOW server_version;` | Stop and verify environment; do not attach old data directory |
| Extension unavailable | `SELECT * FROM pg_extension;` | Review compatibility and extension upgrade guidance |
| Migration lock wait | `pg_stat_activity`, `pg_locks` | Set bounded lock timeout; cancel local migration |
| App query fails after migration | Re-run application smoke tests | Stop rollout; use tested rollback/recovery plan |

## Acceptance checklist
- [ ] Describe patch versus major upgrade accurately.
- [ ] Inventory major version, extensions and database identity.
- [ ] Run additive and reverse schema migration only in isolated local PostgreSQL.
- [ ] Capture expected SQL results and a rollback decision.
- [ ] Produce an upgrade change plan with backup/restore and approval gates.
- [ ] Mark actual runtime execution and independent review separately; no production certification implied.

## Official references
- [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/)
- [PostgreSQL 17 upgrading](https://www.postgresql.org/docs/17/upgrading.html)
- [PostgreSQL 17 pg_upgrade](https://www.postgresql.org/docs/17/pgupgrade.html)
- [PostgreSQL 17 backup and restore](https://www.postgresql.org/docs/17/backup.html)
- [PostgreSQL 17 ALTER TABLE](https://www.postgresql.org/docs/17/sql-altertable.html)
- [Amazon RDS PostgreSQL upgrades](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_UpgradeDBInstance.PostgreSQL.html)
- [CloudNativePG documentation](https://cloudnative-pg.io/docs/)
