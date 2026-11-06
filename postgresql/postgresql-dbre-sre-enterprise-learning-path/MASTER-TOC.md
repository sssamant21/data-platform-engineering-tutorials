# Master Table of Contents — PostgreSQL Enterprise DBRE/SRE Learning Path

**20 chapters · 5 parts · approximately 20 hours of guided learning (excluding additional practice).** Each chapter targets a 60-minute training session; duration varies with lab prerequisites.

## Documentation and runtime versions

- **Documentation baseline: PostgreSQL 18**, effective 2026-11-06. See the [baseline and migration policy](POSTGRESQL-18-BASELINE.md).
- **Legacy lab runtime assumptions: PostgreSQL 17** until each lab is explicitly migrated to, and execution-verified on, PostgreSQL 18. This table's “Authored” status does not imply PostgreSQL 18 runtime acceptance.

## Part 1 — PostgreSQL foundations

| Chapter | Topic | Status |
|---|---|---|
| [01](chapters/01-postgresql-fundamentals-and-architecture.md) | PostgreSQL Fundamentals and Architecture | Authored; runtime lab pending |
| [02](chapters/02-databases-schemas-tables-and-relationships.md) | Databases, Schemas, Tables and Relationships | Authored; runtime lab pending |
| [03](chapters/03-sql-transactions-acid-and-mvcc.md) | SQL Transactions, ACID and MVCC | Authored; runtime lab pending |
| [04](chapters/04-postgresql-internals-wal-buffers-and-checkpoints.md) | PostgreSQL Internals: WAL, Buffers and Checkpoints | Authored; runtime lab pending |
| [05](chapters/05-indexes-query-plans-and-performance.md) | Indexes, Query Plans and Performance | Authored; runtime lab pending |

## Part 2 — Deployment platforms

| Chapter | Topic | Status |
|---|---|---|
| [06](chapters/06-postgresql-on-bare-metal.md) | PostgreSQL on Bare Metal | Authored; runtime lab pending |
| [07](chapters/07-postgresql-on-aws-rds.md) | PostgreSQL on AWS RDS | Authored; runtime lab pending |
| [08](chapters/08-postgresql-on-kubernetes.md) | PostgreSQL on Kubernetes | Authored; runtime lab pending |
| [09](chapters/09-selecting-the-right-enterprise-postgresql-architecture.md) | Selecting the Right Enterprise PostgreSQL Architecture | Authored; runtime lab pending |

## Part 3 — Reliability and operations

| Chapter | Topic | Status |
|---|---|---|
| [10](chapters/10-streaming-replication-and-high-availability.md) | Streaming Replication and High Availability | Authored; runtime lab pending |
| [11](chapters/11-backup-restore-pitr-and-disaster-recovery.md) | Backup, Restore, PITR and Disaster Recovery | Authored; runtime lab pending |
| [12](chapters/12-monitoring-alerting-and-observability.md) | Monitoring, Alerting and Observability | Authored; runtime lab pending |
| [13](chapters/13-vacuum-autovacuum-bloat-and-maintenance.md) | VACUUM, Autovacuum, Bloat and Maintenance | Authored; runtime lab pending |
| [14](chapters/14-troubleshooting-and-incident-response.md) | Troubleshooting and Incident Response ([lab](labs/chapter-14/README.md)) | Authored; runtime lab pending |

## Part 4 — Enterprise fleet management

| Chapter | Topic | Status |
|---|---|---|
| [15](chapters/15-fleet-inventory-and-governance.md) | Fleet Inventory and Governance ([lab](labs/chapter-15/README.md)) | Authored; runtime lab pending |
| [16](chapters/16-security-roles-secrets-and-compliance.md) | Security, Roles, Secrets and Compliance ([lab](labs/chapter-16/README.md)) | Authored; runtime lab pending |
| [17](chapters/17-lifecycle-upgrades-and-automation.md) | Lifecycle, Upgrades and Automation ([lab](labs/chapter-17/README.md)) | Authored; runtime lab pending |
| [18](chapters/18-capacity-planning-performance-and-finops.md) | Capacity Planning, Performance and FinOps ([lab](labs/chapter-18/README.md)) | Authored; runtime lab pending |

## Part 5 — Collaboration and capstone

| Chapter | Topic | Status |
|---|---|---|
| [19](chapters/19-application-requirement-gathering-and-database-design.md) | Application Requirement Gathering and Database Design ([lab](labs/chapter-19/README.md)) | Authored; runtime lab pending |
| [20](chapters/20-enterprise-postgresql-dbre-sre-capstone.md) | Enterprise PostgreSQL DBRE/SRE Capstone ([lab](labs/chapter-20/README.md)) | Authored; runtime lab pending |

## Learning standards and platform boundaries

- Bare metal: own OS/storage/PostgreSQL configuration, HA orchestration and recovery procedures.
- AWS RDS: validate managed-service responsibilities, Multi-AZ mode, backups, parameter groups, observability, and user-owned application configuration.
- Kubernetes: use a maintained PostgreSQL operator with persistent storage, backup, topology, identity, and fencing controls.
- Record actual RPO/RTO from isolated exercises; do not equate a successful backup with verified recovery.
- Do not run failover, chaos, destructive operations, or cleanup commands against live systems without documented approval.

See the existing [PostgreSQL operational tutorials](../README.md) for deeper coverage of a topic once introduced here.
