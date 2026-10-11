# PostgreSQL Tutorial Master Plan — DBRE and SRE

## Audience and scope

**Audience: DBRE and SRE teams only.** The series teaches how to deploy, operate, observe, troubleshoot, secure, recover and scale PostgreSQL in production. SQL, schemas and application behavior appear when needed to explain reliability or diagnose incidents. General application development, ORM training and analytics coursework are outside scope.

**Curriculum: 100 chapters in 20 modules.** This is a proposed plan; chapters are not yet marked complete. Self-managed PostgreSQL is the common foundation. Managed services and Kubernetes are separate deployment tracks.

## Prerequisites and lab design

- Linux command line, basic networking, Git and elementary SQL.
- Disposable Linux VMs or containers for the core lab, with a primary and two standbys introduced progressively.
- A repeatable synthetic workload, separate backup destination and configurable storage limits.
- Optional provider and Kubernetes sandboxes for the corresponding tracks; these may incur charges.
- Pin the PostgreSQL major version and all tool versions when each lab is authored. Annotate version-dependent views, settings, privileges and feature availability. Use official documentation for the selected versions.
- Run failure injection and destructive SQL only in disposable environments. Administrative examples use restricted roles where possible and explain when elevated access is required.

## Documentation and version policy

Use the [latest stable official PostgreSQL documentation](https://www.postgresql.org/docs/current/) as the primary source. The reference major for this curriculum is PostgreSQL 18, checked on 2026-10-11. Pin the exact minor version used for each lab and retain version-specific /docs/18/ links for reproducibility. Review release notes before updating the baseline. Document differences for older production versions and provider-supported versions; beta and development releases are optional preview topics.

## Chapter standard

Every chapter follows the same operational format:

1. Operational problem, learning objectives and prerequisite chapters.
2. Concepts and architecture relevant to the DBRE/SRE decision.
3. Deployment and version assumptions, privileges and lab preparation.
4. Commands and SQL with expected output and interpretation.
5. Hands-on exercise with baseline measurements and a reproducible trigger.
6. Diagnosis: symptom → evidence → cause → mitigation → verification.
7. Production procedure: prechecks, blast radius, stop conditions and recovery or rollback boundaries.
8. Monitoring, alert signals and workload-specific thresholds.
9. Cleanup and restoration of the lab baseline.
10. Acceptance checks and evidence to retain.
11. Troubleshooting table and official references.

Use service objectives and measured workloads to choose thresholds. Avoid universal tuning values. Restore and failover exercises must measure achieved RPO and RTO; a successful backup command alone is insufficient evidence of recoverability.

## Master chapter list

### Module 01 — Operational Foundations

| Chapter | Tutorial | Status |
|---|---|---|
| 001 | [PostgreSQL Responsibilities for DBRE and SRE](chapters/001-postgresql-responsibilities-for-dbre-and-sre.md) | Authored; lab execution pending |
| 002 | [Architecture: Processes, Memory, Storage and WAL](chapters/002-architecture-processes-memory-storage-and-wal.md) | Authored; lab execution pending |
| 003 | [Linux, Networking and Storage Prerequisites](chapters/003-linux-networking-and-storage-prerequisites.md) | Authored; lab execution pending |
| 004 | [Build a Reproducible PostgreSQL Operations Lab](chapters/004-build-a-reproducible-postgresql-operations-lab.md) | Authored; lab execution pending |
| 005 | [psql, System Catalogs and Safe Administrative SQL](chapters/005-psql-system-catalogs-and-safe-administrative-sql.md) | Authored; lab execution pending |

**Module acceptance lab:** Build a disposable primary and two standbys; record topology and baseline evidence.

### Module 02 — Installation and Service Operations

| Chapter | Tutorial | Status |
|---|---|---|
| 006 | [Installation, Packages and Directory Layout](chapters/006-installation-packages-and-directory-layout.md) | Authored; lab execution pending |
| 007 | [Initialization, Checksums, Locale and Encoding](chapters/007-initialization-checksums-locale-and-encoding.md) | Authored; lab execution pending |
| 008 | [Configuration Precedence, Reloads and Restarts](chapters/008-configuration-precedence-reloads-and-restarts.md) | Authored; lab execution pending |
| 009 | [systemd, Startup, Shutdown and Crash Recovery](chapters/009-systemd-startup-shutdown-and-crash-recovery.md) | Authored; lab execution pending |
| 010 | [Configuration Drift and Baseline Acceptance](chapters/010-configuration-drift-and-baseline-acceptance.md) | Authored; lab execution pending |

**Module acceptance lab:** Recover a failed start and demonstrate reload versus restart using controlled configuration changes.

### Module 03 — Access and Security

| Chapter | Tutorial | Status |
|---|---|---|
| 011 | [Roles, Ownership, Membership and Least Privilege](chapters/011-roles-ownership-membership-and-least-privilege.md) | Authored; lab execution pending |
| 012 | pg_hba.conf, Authentication and Connection Diagnosis | Planned |
| 013 | TLS Certificates, Verification and Rotation | Planned |
| 014 | Secrets Rotation and Service Account Lifecycle | Planned |
| 015 | Audit Logging, Network Isolation and Security Acceptance | Planned |

**Module acceptance lab:** Provision restricted service access; diagnose authentication failures and rotate credentials.

### Module 04 — Transactions and Concurrency

| Chapter | Tutorial | Status |
|---|---|---|
| 016 | MVCC, Snapshots and Tuple Visibility | Planned |
| 017 | Isolation Levels and Application Failure Patterns | Planned |
| 018 | Locks, Blocking Chains and Deadlocks | Planned |
| 019 | Long Transactions, Idle Sessions and Transaction Timeouts | Planned |
| 020 | Safe Cancellation, Termination and Concurrency Incident Lab | Planned |

**Module acceptance lab:** Create a blocking chain and deadlock; identify the owner, impact and safest mitigation.

### Module 05 — Observability and SLOs

| Chapter | Tutorial | Status |
|---|---|---|
| 021 | Database SLIs, SLOs and Error Budgets | Planned |
| 022 | Statistics Views, Resets and Measurement Windows | Planned |
| 023 | Query Statistics with pg_stat_statements | Planned |
| 024 | Logs, Slow Statements and Correlation with Application Traces | Planned |
| 025 | Prometheus, Grafana and Actionable Alert Acceptance | Planned |

**Module acceptance lab:** Build an operational dashboard and alerts; distinguish user latency from aggregate database metrics.

### Module 06 — Performance Diagnosis

| Chapter | Tutorial | Status |
|---|---|---|
| 026 | Performance Triage and Evidence Collection | Planned |
| 027 | EXPLAIN and EXPLAIN ANALYZE Safely | Planned |
| 028 | Planner Estimates, Statistics and Extended Statistics | Planned |
| 029 | CPU, Memory, I/O and Wait Event Diagnosis | Planned |
| 030 | Production Slowness Investigation Project | Planned |

**Module acceptance lab:** Diagnose a slow workload with plans, waits and OS evidence; validate improvement against a baseline.

### Module 07 — Indexes and Safe Schema Operations

| Chapter | Tutorial | Status |
|---|---|---|
| 031 | B-tree and Other Index Types: Operational Tradeoffs | Planned |
| 032 | Composite, Partial, Expression and Covering Indexes | Planned |
| 033 | Unused, Duplicate and Bloated Index Diagnosis | Planned |
| 034 | Concurrent Index Builds, Failed Builds and Reindexing | Planned |
| 035 | DDL Locking, Schema Changes and Migration Acceptance | Planned |

**Module acceptance lab:** Reproduce DDL blocking and an invalid concurrent index; complete a monitored change with recovery steps.

### Module 08 — Vacuum and Data Lifecycle

| Chapter | Tutorial | Status |
|---|---|---|
| 036 | VACUUM, ANALYZE and Visibility Maps | Planned |
| 037 | Autovacuum Workers, Thresholds and Per-table Tuning | Planned |
| 038 | Transaction ID and Multixact Wraparound Protection | Planned |
| 039 | Bloat, HOT Updates and Space Reclamation | Planned |
| 040 | Retention, Partition Maintenance and Vacuum Incident Lab | Planned |

**Module acceptance lab:** Create churn, detect vacuum blockers and establish a safe remediation plan with measurable thresholds.

### Module 09 — Storage, WAL and Capacity

| Chapter | Tutorial | Status |
|---|---|---|
| 041 | Heap Pages, TOAST, Forks and Tablespaces | Planned |
| 042 | WAL Generation, Checkpoints and Recovery Tradeoffs | Planned |
| 043 | WAL Retention, Archiving and Replication Slot Growth | Planned |
| 044 | Disk Latency, Throughput, Filesystem and Storage Capacity | Planned |
| 045 | Disk-full and WAL-growth Recovery Acceptance | Planned |

**Module acceptance lab:** Fill a constrained lab volume; identify the cause and recover without deleting database or WAL files.

### Module 10 — Connections and Resource Control

| Chapter | Tutorial | Status |
|---|---|---|
| 046 | Connection Capacity and Backend Resource Costs | Planned |
| 047 | PgBouncer Pool Modes and Application Compatibility | Planned |
| 048 | Pool Sizing, Queueing and Connection Storms | Planned |
| 049 | Memory Budgets: Shared Buffers, Work Memory and Maintenance | Planned |
| 050 | Connection Exhaustion and Out-of-memory Incident Lab | Planned |

**Module acceptance lab:** Generate a connection storm and concurrent memory pressure; tune pools and admission limits.

### Module 11 — Backup and Restore

| Chapter | Tutorial | Status |
|---|---|---|
| 051 | Backup Architecture, RPO, RTO and Failure Domains | Planned |
| 052 | pg_dump, pg_restore and Logical Recovery | Planned |
| 053 | Physical Base Backups and Backup Verification | Planned |
| 054 | WAL Archiving and Point-in-time Recovery | Planned |
| 055 | Backup Tooling: pgBackRest or Barman Acceptance | Planned |

**Module acceptance lab:** Restore into an isolated target; verify data, permissions and measured recovery time.

### Module 12 — Disaster Recovery

| Chapter | Tutorial | Status |
|---|---|---|
| 056 | Accidental DELETE, TRUNCATE and DROP Recovery | Planned |
| 057 | Tablespace, Host and Storage Loss Recovery | Planned |
| 058 | Corruption Detection, Checksums and Escalation | Planned |
| 059 | Cross-region Recovery and Dependency Readiness | Planned |
| 060 | Disaster Recovery Drill and Evidence Review | Planned |

**Module acceptance lab:** Recover from a timestamped destructive event; reconcile recovered records and document achieved RPO/RTO.

### Module 13 — Streaming Replication

| Chapter | Tutorial | Status |
|---|---|---|
| 061 | Physical Replication Architecture and WAL Flow | Planned |
| 062 | Build and Secure Streaming Standbys | Planned |
| 063 | Asynchronous and Synchronous Replication Tradeoffs | Planned |
| 064 | Replication Lag: Send, Write, Flush and Replay | Planned |
| 065 | Slots, Cascading Replication and Standby Query Conflicts | Planned |

**Module acceptance lab:** Interrupt replication, measure lag correctly and recover while managing retention and read conflicts.

### Module 14 — High Availability and Failover

| Chapter | Tutorial | Status |
|---|---|---|
| 066 | HA Topology, Quorum, Fencing and Split-brain Prevention | Planned |
| 067 | Patroni and Distributed Consensus Operations | Planned |
| 068 | Planned Switchover and Client Reconnection | Planned |
| 069 | Unplanned Failover and Data-loss Assessment | Planned |
| 070 | Rejoin, pg_rewind, Rebuild and Failback Acceptance | Planned |

**Module acceptance lab:** Exercise switchover and fenced failure; prove a single writable primary and validate client recovery.

### Module 15 — Logical Replication and Migrations

| Chapter | Tutorial | Status |
|---|---|---|
| 071 | Publications, Subscriptions and Replica Identity | Planned |
| 072 | Initial Synchronization and Slot Capacity | Planned |
| 073 | Logical Replication Lag, Conflicts and Recovery | Planned |
| 074 | Schema, Sequence and DDL Coordination | Planned |
| 075 | Low-downtime Migration and Cutover Acceptance | Planned |

**Module acceptance lab:** Migrate a lab workload; reconcile schema and sequences, test cutover and define rollback boundaries.

### Module 16 — Maintenance and Upgrades

| Chapter | Tutorial | Status |
|---|---|---|
| 076 | Maintenance Planning and Production Change Controls | Planned |
| 077 | Minor Updates, Extensions and Restart Coordination | Planned |
| 078 | Major Upgrades with pg_upgrade | Planned |
| 079 | Major Upgrades Using Logical Migration | Planned |
| 080 | Upgrade Rehearsal, Rollback and Post-change Validation | Planned |

**Module acceptance lab:** Rehearse a major upgrade on a restored copy; measure downtime and verify workload and extension compatibility.

### Module 17 — Managed PostgreSQL

| Chapter | Tutorial | Status |
|---|---|---|
| 081 | RDS PostgreSQL Responsibility Boundaries and Parameters | Planned |
| 082 | RDS Backups, Recovery and Multi-AZ Operations | Planned |
| 083 | Aurora PostgreSQL Architecture and Operational Differences | Planned |
| 084 | Azure and Google Cloud PostgreSQL Operations | Planned |
| 085 | Managed-service Failover, Scaling and Migration Acceptance | Planned |

**Module acceptance lab:** Use one supported provider sandbox to test backup recovery, parameter changes and endpoint behavior.

### Module 18 — Kubernetes Operations

| Chapter | Tutorial | Status |
|---|---|---|
| 086 | PostgreSQL on Kubernetes: Suitability and Failure Modes | Planned |
| 087 | Operators, Reconciliation and Supported Topologies | Planned |
| 088 | Persistent Volumes, Scheduling and Failure Domains | Planned |
| 089 | Operator-managed Backups, Upgrades and Recovery | Planned |
| 090 | Kubernetes Database Failure and Restore Acceptance | Planned |

**Module acceptance lab:** Use one selected operator; test a pod/node failure, restore and document storage and fencing behavior.

### Module 19 — Reliability Engineering and Automation

| Chapter | Tutorial | Status |
|---|---|---|
| 091 | Capacity Forecasting and Cost Optimization | Planned |
| 092 | Infrastructure as Code and Configuration Management | Planned |
| 093 | Operational Scripts, Idempotency and Guardrails | Planned |
| 094 | Load Testing, Chaos Experiments and Reliability Limits | Planned |
| 095 | Incident Command, RCA and Preventive Action Tracking | Planned |

**Module acceptance lab:** Automate read-only health checks and bounded changes; conduct a failure exercise and write an evidence-based RCA.

### Module 20 — Production Runbooks and Capstone

| Chapter | Tutorial | Status |
|---|---|---|
| 096 | Slowness, Blocking and Connection Incident Runbooks | Planned |
| 097 | Replication Lag, Failover and WAL-growth Runbooks | Planned |
| 098 | Vacuum, Wraparound, Disk-full and Corruption Runbooks | Planned |
| 099 | Production Readiness Review and Operational Handover | Planned |
| 100 | End-to-end PostgreSQL Reliability Acceptance Project | Planned |

**Module acceptance lab:** Run a workload, inject failures, recover service and data, and submit an operational evidence pack.

## Learning routes

| Route | Modules | Outcome |
|---|---|---|
| Core on-call operations | 01–10 | Diagnose access, latency, locks, vacuum, storage and connection incidents. |
| Recovery and availability | 11–14 | Prove restore capability and operate replication and failover safely. |
| Migration and lifecycle | 15–16 | Plan migrations and upgrades with rehearsed cutover and recovery procedures. |
| Managed-service specialization | 17 | Apply the foundation to a selected provider and document service-specific limits. |
| Kubernetes specialization | 18 | Operate a selected PostgreSQL operator with tested persistent-storage recovery. |
| Production qualification | 19–20 | Automate operations, run incident exercises and complete readiness acceptance. |

Complete both deployment specializations if the team's ownership spans both environments. Otherwise qualify on the team's actual deployment track and record the other as not applicable rather than completed.

## Required operational deliverables

- Architecture and dependency diagram; database, role, extension and configuration inventory.
- Service objectives, baseline workload results and a capacity forecast.
- Dashboard and actionable alerts with owners and linked runbooks.
- Backup policy, retention model, restore evidence and measured RPO/RTO.
- Failover, fencing, rejoin and client reconnection procedures.
- Security baseline, access review and credential/certificate rotation procedure.
- Upgrade and migration plans with explicit rollback boundaries.
- Incident evidence template, escalation map, RCA and tracked preventive actions.

## Capstone acceptance criteria

1. A representative workload runs with agreed latency, throughput and availability targets.
2. Blocking, connection exhaustion, replication interruption and controlled storage pressure are detected and diagnosed from evidence.
3. An isolated restore recovers the expected data and roles; achieved RPO/RTO are recorded.
4. A failover exercise demonstrates a single writable primary and successful client reconnection.
5. A rehearsed maintenance or upgrade change passes prechecks and post-change verification.
6. Dashboards, alerts, runbooks and handover material allow another operator to repeat the procedures.

## Suggested repository structure

This folder starts the new DBRE/SRE curriculum. Previous tutorial content remains available in Git history. Add the following directories as chapters and labs are completed.

- `postgresql/MASTER-PLAN.md` — scope, sequence and chapter index.
- `postgresql/PROGRESS.md` — authored, reviewed and lab-verified status tracked separately.
- `postgresql/chapters/001-postgresql-responsibilities-for-dbre-and-sre.md` — numbered canonical chapters.
- `postgresql/labs/001-operations-foundations-lab.md` — matching lab instructions.
- `postgresql/scripts/` — reusable shell and SQL helpers.
- `postgresql/runbooks/` — production incident and maintenance procedures.
- `postgresql/projects/` — acceptance projects and evidence templates.

## Authoring workflow

Finish one chapter and its lab before advancing. Validate commands on the pinned environment, review operational impact, then update the tracker. A chapter is **complete** only when its content, lab, expected results, cleanup and acceptance evidence have been reviewed. Repository publication is a separate tracked action.

**First chapter: 001 — PostgreSQL Responsibilities for DBRE and SRE.**

