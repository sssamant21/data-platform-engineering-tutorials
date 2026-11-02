# Master Table of Contents — PostgreSQL Enterprise DBRE/SRE Learning Path

**20 chapters · 5 parts · approximately 20 hours of guided learning (excluding additional practice).** Each chapter targets a 60-minute training session; duration varies with lab prerequisites.

## Part 1 — PostgreSQL foundations

| Chapter | Topic | Status |
|---|---|---|
| [01](chapters/01-postgresql-fundamentals-and-architecture.md) | PostgreSQL Fundamentals and Architecture | Authored; runtime lab pending |
| [02](chapters/02-databases-schemas-tables-and-relationships.md) | Databases, Schemas, Tables and Relationships | Authored; runtime lab pending |
| [03](chapters/03-sql-transactions-acid-and-mvcc.md) | SQL Transactions, ACID and MVCC | Authored; runtime lab pending |
| 04 | PostgreSQL Internals: WAL, Buffers and Checkpoints | Planned |
| 05 | Indexes, Query Plans and Performance | Planned |

## Part 2 — Deployment platforms

| Chapter | Topic | Status |
|---|---|---|
| 06 | PostgreSQL on Bare Metal | Planned |
| 07 | PostgreSQL on AWS RDS | Planned |
| 08 | PostgreSQL on Kubernetes | Planned |
| 09 | Selecting the Right Enterprise PostgreSQL Architecture | Planned |

## Part 3 — Reliability and operations

| Chapter | Topic | Status |
|---|---|---|
| 10 | Streaming Replication and High Availability | Planned |
| 11 | Backup, Restore, PITR and Disaster Recovery | Planned |
| 12 | Monitoring, Alerting and Observability | Planned |
| 13 | VACUUM, Autovacuum, Bloat and Maintenance | Planned |
| 14 | Troubleshooting and Incident Response | Planned |

## Part 4 — Enterprise fleet management

| Chapter | Topic | Status |
|---|---|---|
| 15 | Fleet Inventory and Governance | Planned |
| 16 | Security, Roles, Secrets and Compliance | Planned |
| 17 | Lifecycle, Upgrades and Automation | Planned |
| 18 | Capacity Planning, Performance and FinOps | Planned |

## Part 5 — Collaboration and capstone

| Chapter | Topic | Status |
|---|---|---|
| 19 | Application Requirement Gathering and Database Design | Planned |
| 20 | Enterprise PostgreSQL DBRE/SRE Capstone | Planned |

## Learning standards and platform boundaries

- Bare metal: own OS/storage/PostgreSQL configuration, HA orchestration and recovery procedures.
- AWS RDS: validate managed-service responsibilities, Multi-AZ mode, backups, parameter groups, observability, and user-owned application configuration.
- Kubernetes: use a maintained PostgreSQL operator with persistent storage, backup, topology, identity, and fencing controls.
- Record actual RPO/RTO from isolated exercises; do not equate a successful backup with verified recovery.
- Do not run failover, chaos, destructive operations, or cleanup commands against live systems without documented approval.

See the existing [PostgreSQL operational tutorials](../README.md) for deeper coverage of a topic once introduced here.
