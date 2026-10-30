# PostgreSQL Tutorial Master Plan — DBRE and SRE

## Audience and scope

**Audience: DBRE and SRE teams only.** The series teaches how to deploy, operate, observe, troubleshoot, secure, recover and scale PostgreSQL in production. SQL, schemas and application behavior appear when needed to explain reliability or diagnose incidents. General application development, ORM training and analytics coursework are outside scope.

**Curriculum: 100 published chapters in 20 modules.** Publication is complete; independent content review, lab execution, and certification are tracked separately. Self-managed PostgreSQL is the common foundation. The original proposed managed-service and Kubernetes tracks are not standalone modules in the published sequence.

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

## Master chapter list — current published curriculum

All 100 chapters below exist. **Authored/published** is not the same as **independently validated** or **lab verified**. See [PROGRESS.md](PROGRESS.md) and [V01 status](validation/V01-STATUS.md) for separate review gates.

### Module 01 — Operational Foundations

| Chapter | Tutorial | Publication / runtime state |
|---|---|---|
| 001 | [Responsibilities](chapters/001-postgresql-responsibilities-for-dbre-and-sre.md) | Authored; lab execution pending |
| 002 | [Architecture](chapters/002-architecture-processes-memory-storage-and-wal.md) | Authored; lab execution pending |
| 003 | [Linux, Networking and Storage Prerequisites](chapters/003-linux-networking-and-storage-prerequisites.md) | Authored; lab execution pending |
| 004 | [Reproducible Operations Lab](chapters/004-build-a-reproducible-postgresql-operations-lab.md) | Authored; lab execution pending |
| 005 | [psql, Catalogs and Safe SQL](chapters/005-psql-system-catalogs-and-safe-administrative-sql.md) | Authored; lab execution pending |

**Module acceptance target:** Demonstrate a safe baseline and operational ownership with retained evidence (pending runtime evidence).

### Module 02 — Installation and Service Operations

| Chapter | Tutorial | Publication / runtime state |
|---|---|---|
| 006 | [Installation, Packages and Directory Layout](chapters/006-installation-packages-and-directory-layout.md) | Authored; lab execution pending |
| 007 | [Initialization, Checksums, Locale and Encoding](chapters/007-initialization-checksums-locale-and-encoding.md) | Authored; lab execution pending |
| 008 | [Configuration Precedence, Reloads and Restarts](chapters/008-configuration-precedence-reloads-and-restarts.md) | Authored; lab execution pending |
| 009 | [systemd, Startup, Shutdown and Crash Recovery](chapters/009-systemd-startup-shutdown-and-crash-recovery.md) | Authored; lab execution pending |
| 010 | [Configuration Drift and Baseline Acceptance](chapters/010-configuration-drift-and-baseline-acceptance.md) | Authored; lab execution pending |

**Module acceptance target:** Verify installation, configuration changes and restart-versus-reload behavior (pending runtime evidence).

### Module 03 — Identity, Authentication and Security

| Chapter | Tutorial | Publication / runtime state |
|---|---|---|
| 011 | [Roles, Ownership, Membership and Least Privilege](chapters/011-roles-ownership-membership-and-least-privilege.md) | Authored; lab execution pending |
| 012 | [pg_hba.conf, Authentication and Connection Diagnosis](chapters/012-pg-hba-conf-authentication-and-connection-diagnosis.md) | Authored; lab execution pending |
| 013 | [TLS Certificates, Verification and Rotation](chapters/013-tls-certificates-verification-and-rotation.md) | Authored; lab execution pending |
| 014 | [Secrets Rotation and Service Account Lifecycle](chapters/014-secrets-rotation-and-service-account-lifecycle.md) | Authored; lab execution pending |
| 015 | [Audit Logging, Network Isolation and Security Acceptance](chapters/015-audit-logging-network-isolation-and-security-acceptance.md) | Authored; lab execution pending |

**Module acceptance target:** Exercise least-privilege access, TLS and rotation in an isolated environment (pending runtime evidence).

### Module 04 — Transactions and Concurrency

| Chapter | Tutorial | Publication / runtime state |
|---|---|---|
| 016 | [MVCC, Snapshots and Tuple Visibility](chapters/016-mvcc-snapshots-and-tuple-visibility.md) | Authored; lab execution pending |
| 017 | [Isolation Levels and Application Failure Patterns](chapters/017-isolation-levels-and-application-failure-patterns.md) | Authored; lab execution pending |
| 018 | [Locks, Blocking Chains and Deadlocks](chapters/018-locks-blocking-chains-and-deadlocks.md) | Authored; lab execution pending |
| 019 | [Long Transactions, Idle Sessions and Transaction Timeouts](chapters/019-long-transactions-idle-sessions-and-transaction-timeouts.md) | Authored; lab execution pending |
| 020 | [Safe Cancellation, Termination and Concurrency Incident Lab](chapters/020-safe-cancellation-termination-and-concurrency-incident-lab.md) | Authored; lab execution pending |

**Module acceptance target:** Diagnose lock chains and transaction anomalies and demonstrate safe mitigation (pending runtime evidence).

### Module 05 — Observability and SLOs

| Chapter | Tutorial | Publication / runtime state |
|---|---|---|
| 021 | [Database SLIs, SLOs and Error Budgets](chapters/021-database-slis-slos-and-error-budgets.md) | Authored; lab execution pending |
| 022 | [Statistics Views, Resets and Measurement Windows](chapters/022-statistics-views-resets-and-measurement-windows.md) | Authored; lab execution pending |
| 023 | [Query Statistics with pg_stat_statements](chapters/023-query-statistics-with-pg-stat-statements.md) | Authored; lab execution pending |
| 024 | [Logs, Slow Statements and Correlation with Application Traces](chapters/024-logs-slow-statements-and-correlation-with-application-traces.md) | Authored; lab execution pending |
| 025 | [Prometheus, Grafana and Actionable Alert Acceptance](chapters/025-prometheus-grafana-and-actionable-alert-acceptance.md) | Authored; lab execution pending |

**Module acceptance target:** Validate time-windowed database metrics and actionable alert behavior (pending runtime evidence).

### Module 06 — Performance Diagnosis

| Chapter | Tutorial | Publication / runtime state |
|---|---|---|
| 026 | [Performance Triage and Evidence Collection](chapters/026-performance-triage-and-evidence-collection.md) | Authored; lab execution pending |
| 027 | [EXPLAIN and EXPLAIN ANALYZE Safely](chapters/027-explain-and-explain-analyze-safely.md) | Authored; lab execution pending |
| 028 | [Planner Estimates, Statistics and Extended Statistics](chapters/028-planner-estimates-statistics-and-extended-statistics.md) | Authored; lab execution pending |
| 029 | [CPU, Memory, I/O and Wait Event Diagnosis](chapters/029-cpu-memory-io-and-wait-event-diagnosis.md) | Authored; lab execution pending |
| 030 | [Production Slowness Investigation Project](chapters/030-production-slowness-investigation-project.md) | Authored; lab execution pending |

**Module acceptance target:** Compare plans, wait events and resource evidence before and after safe mitigation (pending runtime evidence).

### Module 07 — Indexes and Safe Index Maintenance

| Chapter | Tutorial | Publication / runtime state |
|---|---|---|
| 031 | [B-tree and Other Index Types: Operational Tradeoffs](chapters/031-b-tree-and-other-index-types-operational-tradeoffs.md) | Authored; lab execution pending |
| 032 | [Composite, Partial, Expression and Covering Indexes](chapters/032-composite-partial-expression-and-covering-indexes.md) | Authored; lab execution pending |
| 033 | [Index Build, Reindex and Concurrent Maintenance](chapters/033-index-build-reindex-and-concurrent-maintenance.md) | Authored; lab execution pending |
| 034 | [Index Bloat, Usage and Lifecycle Decisions](chapters/034-index-bloat-usage-and-lifecycle-decisions.md) | Authored; lab execution pending |
| 035 | [VACUUM, Autovacuum and Index Cleanup](chapters/035-vacuum-autovacuum-and-index-cleanup.md) | Authored; lab execution pending |

**Module acceptance target:** Show index design tradeoffs, validity and operational rollout controls (pending runtime evidence).

### Module 08 — Autovacuum, Maintenance and Partitioning

| Chapter | Tutorial | Publication / runtime state |
|---|---|---|
| 036 | [Autovacuum Tuning, Freeze and Wraparound Incident Response](chapters/036-autovacuum-tuning-freeze-and-wraparound-incident-response.md) | Authored; lab execution pending |
| 037 | [Table and Index Maintenance Strategy](chapters/037-table-and-index-maintenance-strategy.md) | Authored; lab execution pending |
| 038 | [Table Partitioning Fundamentals and Operational Tradeoffs](chapters/038-table-partitioning-fundamentals-and-operational-tradeoffs.md) | Authored; lab execution pending |
| 039 | [Partition Pruning, Indexes and Query Performance](chapters/039-partition-pruning-indexes-and-query-performance.md) | Authored; lab execution pending |
| 040 | [Partition Lifecycle, Retention and Recovery Project](chapters/040-partition-lifecycle-retention-and-recovery-project.md) | Authored; lab execution pending |

**Module acceptance target:** Perform bounded maintenance and partition lifecycle with cleanup and evidence (pending runtime evidence).

### Module 09 — Backup Foundations and PITR

| Chapter | Tutorial | Publication / runtime state |
|---|---|---|
| 041 | [PostgreSQL Backup Architecture and Recovery Objectives](chapters/041-postgresql-backup-architecture-and-recovery-objectives.md) | Authored; lab execution pending |
| 042 | [Logical Backups with pg_dump, pg_restore and pg_dumpall](chapters/042-logical-backups-with-pg_dump-pg_restore-and-pg_dumpall.md) | Authored; lab execution pending |
| 043 | [Physical Backups with pg_basebackup and Backup Manifests](chapters/043-physical-backups-with-pg_basebackup-and-backup-manifests.md) | Authored; lab execution pending |
| 044 | [WAL Archiving, Restore Commands and PITR Foundations](chapters/044-wal-archiving-restore-commands-and-pitr-foundations.md) | Authored; lab execution pending |
| 045 | [Point-in-Time Recovery and Disaster Recovery Lab](chapters/045-point-in-time-recovery-and-disaster-recovery-lab.md) | Authored; lab execution pending |

**Module acceptance target:** Restore from a backup in a disposable target and show PITR checkpoints (pending runtime evidence).

### Module 10 — Backup Validation, Replication and Recovery

| Chapter | Tutorial | Publication / runtime state |
|---|---|---|
| 046 | [Backup Monitoring, Restore Validation and Recovery Automation](chapters/046-backup-monitoring-restore-validation-and-recovery-automation.md) | Authored; lab execution pending |
| 047 | [PostgreSQL Replication Slots, WAL Retention and Failure Modes](chapters/047-postgresql-replication-slots-wal-retention-and-failure-modes.md) | Authored; lab execution pending |
| 048 | [Replication Lag, Standby Conflicts and Recovery Operations](chapters/048-replication-lag-standby-conflicts-and-recovery-operations.md) | Authored; lab execution pending |
| 049 | [Replication Failover, Rejoin and Timeline Recovery](chapters/049-replication-failover-rejoin-and-timeline-recovery.md) | Authored; lab execution pending |
| 050 | [High Availability and Disaster Recovery Acceptance Project](chapters/050-high-availability-and-disaster-recovery-acceptance-project.md) | Authored; lab execution pending |

**Module acceptance target:** Measure recoverability and replication/failover readiness against objectives (pending runtime evidence).

### Module 11 — Security Architecture and Access Controls

| Chapter | Tutorial | Publication / runtime state |
|---|---|---|
| 051 | [PostgreSQL Security Architecture, Roles and Privilege Boundaries](chapters/051-postgresql-security-architecture-roles-and-privilege-boundaries.md) | Authored; lab execution pending |
| 052 | [PostgreSQL Authentication, pg_hba.conf and TLS Security](chapters/052-postgresql-authentication-pg-hba-conf-and-tls-security.md) | Authored; lab execution pending |
| 053 | [PostgreSQL Row-Level Security and Secure Application Access](chapters/053-postgresql-row-level-security-and-secure-application-access.md) | Authored; lab execution pending |
| 054 | [PostgreSQL Auditing, Logging and Security Monitoring](chapters/054-postgresql-auditing-logging-and-security-monitoring.md) | Authored; lab execution pending |
| 055 | [PostgreSQL Security Hardening and Access Control Acceptance Lab](chapters/055-postgresql-security-hardening-and-access-control-acceptance-lab.md) | Authored; lab execution pending |

**Module acceptance target:** Test access boundaries, auditing and hardening with least-privilege evidence (pending runtime evidence).

### Module 12 — PgBouncer and Connection Pooling

| Chapter | Tutorial | Publication / runtime state |
|---|---|---|
| 056 | [PostgreSQL Connection Management and PgBouncer Fundamentals](chapters/056-postgresql-connection-management-and-pgbouncer-fundamentals.md) | Authored; lab execution pending |
| 057 | [PgBouncer Pooling Modes, Sizing and Transaction Compatibility](chapters/057-pgbouncer-pooling-modes-sizing-and-transaction-compatibility.md) | Authored; lab execution pending |
| 058 | [PostgreSQL Connection Pool Saturation, Timeouts and Recovery](chapters/058-postgresql-connection-pool-saturation-timeouts-and-recovery.md) | Authored; lab execution pending |
| 059 | [PostgreSQL Connection Pool Monitoring, Capacity and Alerting](chapters/059-postgresql-connection-pool-monitoring-capacity-and-alerting.md) | Authored; lab execution pending |
| 060 | [PostgreSQL Connection Pooling and Availability Acceptance Project](chapters/060-postgresql-connection-pooling-and-availability-acceptance-project.md) | Authored; lab execution pending |

**Module acceptance target:** Characterize pool modes and saturation without production impact (pending runtime evidence).

### Module 13 — Backups, Retention and Restore Testing

| Chapter | Tutorial | Publication / runtime state |
|---|---|---|
| 061 | [PostgreSQL Backup Strategy, RPO and RTO Fundamentals](chapters/061-postgresql-backup-strategy-rpo-and-rto-fundamentals.md) | Authored; lab execution pending |
| 062 | [PostgreSQL Logical Backups with pg_dump, pg_restore and pg_dumpall](chapters/062-postgresql-logical-backups-with-pg-dump-pg-restore-and-pg-dumpall.md) | Authored; lab execution pending |
| 063 | [PostgreSQL Physical Backups with pg_basebackup and Backup Verification](chapters/063-postgresql-physical-backups-with-pg-basebackup-and-backup-verification.md) | Authored; lab execution pending |
| 064 | [PostgreSQL WAL Archiving and Point-in-Time Recovery](chapters/064-postgresql-wal-archiving-and-point-in-time-recovery.md) | Authored; lab execution pending |
| 065 | [PostgreSQL Backup Retention, Automation and Restore Testing](chapters/065-postgresql-backup-retention-automation-and-restore-testing.md) | Authored; lab execution pending |

**Module acceptance target:** Prove backup integrity, retention automation and restore acceptance (pending runtime evidence).

### Module 14 — Disaster Recovery and High Availability Fundamentals

| Chapter | Tutorial | Publication / runtime state |
|---|---|---|
| 066 | [PostgreSQL Backup and Disaster Recovery Acceptance Lab](chapters/066-postgresql-backup-and-disaster-recovery-acceptance-lab.md) | Authored; lab execution pending |
| 067 | [PostgreSQL Streaming Replication and High Availability Architecture](chapters/067-postgresql-streaming-replication-and-high-availability-architecture.md) | Authored; lab execution pending |
| 068 | [PostgreSQL Replication Slots, WAL Retention and Lag Management](chapters/068-postgresql-replication-slots-wal-retention-and-lag-management.md) | Authored; lab execution pending |
| 069 | [PostgreSQL Synchronous Replication and Commit Durability](chapters/069-postgresql-synchronous-replication-and-commit-durability.md) | Authored; lab execution pending |
| 070 | [PostgreSQL Planned Switchover, Failover and Split-Brain Prevention](chapters/070-postgresql-planned-switchover-failover-and-split-brain-prevention.md) | Authored; lab execution pending |

**Module acceptance target:** Exercise durability and controlled failover with explicit stop conditions (pending runtime evidence).

### Module 15 — HA Automation and Multi-region Readiness

| Chapter | Tutorial | Publication / runtime state |
|---|---|---|
| 071 | [PostgreSQL HA Automation, Leader Election and Failover Orchestration](chapters/071-postgresql-ha-automation-leader-election-and-failover-orchestration.md) | Authored; lab execution pending |
| 072 | [PostgreSQL High Availability Observability and Failure Recovery](chapters/072-postgresql-high-availability-observability-and-failure-recovery.md) | Authored; lab execution pending |
| 073 | [PostgreSQL Multi-Zone High Availability and Disaster Recovery Design](chapters/073-postgresql-multi-zone-high-availability-and-disaster-recovery-design.md) | Authored; lab execution pending |
| 074 | [PostgreSQL Cross-Region Replication, DR Cutover and Failback](chapters/074-postgresql-cross-region-replication-dr-cutover-and-failback.md) | Authored; lab execution pending |
| 075 | [PostgreSQL High Availability and Disaster Recovery Acceptance Project](chapters/075-postgresql-high-availability-and-disaster-recovery-acceptance-project.md) | Authored; lab execution pending |

**Module acceptance target:** Prove single-writer failover, alerting, runbooks and DR acceptance (pending runtime evidence).

### Module 16 — Advanced Security Operations

| Chapter | Tutorial | Publication / runtime state |
|---|---|---|
| 076 | [PostgreSQL Security Architecture, Roles and Privileges](chapters/076-postgresql-security-architecture-roles-and-privileges.md) | Authored; lab execution pending |
| 077 | [PostgreSQL Authentication, pg_hba.conf, TLS and Connection Security](chapters/077-postgresql-authentication-pg-hba-conf-tls-and-connection-security.md) | Authored; lab execution pending |
| 078 | [PostgreSQL Row-Level Security, Data Protection and Audit Controls](chapters/078-postgresql-row-level-security-data-protection-and-audit-controls.md) | Authored; lab execution pending |
| 079 | [PostgreSQL Encryption, Secrets Management and Security Hardening](chapters/079-postgresql-encryption-secrets-management-and-security-hardening.md) | Authored; lab execution pending |
| 080 | [PostgreSQL Security Operations, Incident Response and Compliance Acceptance Project](chapters/080-postgresql-security-operations-incident-response-and-compliance-acceptance-project.md) | Authored; lab execution pending |

**Module acceptance target:** Demonstrate access, encryption and incident control validation (pending runtime evidence).

### Module 17 — Extensions, Upgrades and Operational Governance

| Chapter | Tutorial | Publication / runtime state |
|---|---|---|
| 081 | [PostgreSQL Extensions, Compatibility and Operational Lifecycle](chapters/081-postgresql-extensions-compatibility-and-operational-lifecycle.md) | Authored; lab execution pending |
| 082 | [PostgreSQL Version Upgrades, Compatibility Testing and Rollback Planning](chapters/082-postgresql-version-upgrades-compatibility-testing-and-rollback-planning.md) | Authored; lab execution pending |
| 083 | [PostgreSQL Configuration Management, Infrastructure as Code and Drift Detection](chapters/083-postgresql-configuration-management-infrastructure-as-code-and-drift-detection.md) | Authored; lab execution pending |
| 084 | [PostgreSQL Maintenance Automation, Scheduling and Operational Runbooks](chapters/084-postgresql-maintenance-automation-scheduling-and-operational-runbooks.md) | Authored; lab execution pending |
| 085 | [PostgreSQL Production Operations, Change Management and Reliability Acceptance Project](chapters/085-postgresql-production-operations-change-management-and-reliability-acceptance-project.md) | Authored; lab execution pending |

**Module acceptance target:** Validate extension compatibility, change control and upgrade rollback criteria (pending runtime evidence).

### Module 18 — Capacity, FinOps and Geo-replication Foundations

| Chapter | Tutorial | Publication / runtime state |
|---|---|---|
| 086 | [PostgreSQL Capacity Forecasting, Cost Optimization and FinOps](chapters/086-postgresql-capacity-forecasting-cost-optimization-and-finops.md) | Authored; lab execution pending |
| 087 | [PostgreSQL Workload Forecasting, Performance Baselines and Capacity Stress Testing](chapters/087-postgresql-workload-forecasting-performance-baselines-and-capacity-stress-testing.md) | Authored; lab execution pending |
| 088 | [PostgreSQL Storage Growth, Retention and Lifecycle Optimization](chapters/088-postgresql-storage-growth-retention-and-lifecycle-optimization.md) | Authored; lab execution pending |
| 089 | [PostgreSQL Cloud Cost Governance, Rightsizing and FinOps Acceptance Project](chapters/089-postgresql-cloud-cost-governance-rightsizing-and-finops-acceptance-project.md) | Authored; lab execution pending |
| 090 | [PostgreSQL Multi-Region Architecture, Geo-Replication and Disaster Recovery Design](chapters/090-postgresql-multi-region-architecture-geo-replication-and-disaster-recovery-design.md) | Authored; lab execution pending |

**Module acceptance target:** Reconcile capacity forecasts and cost choices without violating reliability goals (pending runtime evidence).

### Module 19 — Multi-region Recovery and Enterprise Readiness

| Chapter | Tutorial | Publication / runtime state |
|---|---|---|
| 091 | [PostgreSQL Cross-Region Failover, Fencing and Split-Brain Prevention](chapters/091-postgresql-cross-region-failover-fencing-and-split-brain-prevention.md) | Authored; lab execution pending |
| 092 | [PostgreSQL Cross-Region Backup, Restore and Disaster Recovery Automation](chapters/092-postgresql-cross-region-backup-restore-and-disaster-recovery-automation.md) | Authored; lab execution pending |
| 093 | [PostgreSQL Multi-Region Observability, DR Drills and Reliability Testing](chapters/093-postgresql-multi-region-observability-dr-drills-and-reliability-testing.md) | Authored; lab execution pending |
| 094 | [PostgreSQL Multi-Region Disaster Recovery Simulation and Acceptance Project](chapters/094-postgresql-multi-region-disaster-recovery-simulation-and-acceptance-project.md) | Authored; lab execution pending |
| 095 | [PostgreSQL Enterprise Reliability and Operational Readiness Review](chapters/095-postgresql-enterprise-reliability-and-operational-readiness-review.md) | Authored; lab execution pending |

**Module acceptance target:** Measure cross-region failover and restore evidence and complete readiness review (pending runtime evidence).

### Module 20 — Incident Response, Automation and Final Capstone

| Chapter | Tutorial | Publication / runtime state |
|---|---|---|
| 096 | [PostgreSQL Enterprise Incident Response, Escalation and Operational Command](chapters/096-postgresql-enterprise-incident-response-escalation-and-operational-command.md) | Authored; lab execution pending |
| 097 | [PostgreSQL Production Incident Simulation, Root Cause Analysis and Corrective Actions](chapters/097-postgresql-production-incident-simulation-root-cause-analysis-and-corrective-actions.md) | Authored; lab execution pending |
| 098 | [PostgreSQL Reliability Automation, Continuous Validation and Operational Excellence](chapters/098-postgresql-reliability-automation-continuous-validation-and-operational-excellence.md) | Authored; lab execution pending |
| 099 | [PostgreSQL Enterprise Reliability Engineering and Operational Acceptance Project](chapters/099-postgresql-enterprise-reliability-engineering-and-operational-acceptance-project.md) | Authored; lab execution pending |
| 100 | [PostgreSQL End-to-End Production Reliability and Recovery Final Capstone](chapters/100-postgresql-end-to-end-production-reliability-and-recovery-final-capstone.md) | Authored; lab execution pending |

**Module acceptance target:** Run end-to-end incident and recovery exercise with independent reviewer sign-off (pending runtime evidence).

## Learning routes — actual published modules

| Route | Current modules | Intended outcome |
|---|---|---|
| Core on-call operations | 01–08, 12 | Diagnose common access, performance, maintenance and pooling incidents |
| Backups and resilience | 09–10, 13–15 | Prove restore, replication, single-writer failover and RPO/RTO objectives |
| Security operations | 03, 11, 16 | Validate security boundaries, auditing and incident controls |
| Platform lifecycle and cost | 17–18 | Manage upgrades, drift, maintenance and reliability-aware FinOps |
| Multi-region and enterprise readiness | 18–20 | Validate cross-region recovery, operations reviews and final capstone |

**Scope reconciliation:** The earlier proposed plan included standalone managed PostgreSQL and Kubernetes specialization modules. The published 001–100 curriculum uses different chapter assignments; these specializations are **not represented as standalone modules** in this canonical published sequence. Validate any cloud-provider and Kubernetes material actually present in chapters separately; do not claim completion of the original proposed specialization tracks without evidence.

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

## Current repository structure

- `postgresql/README.md` — canonical chapter navigation.
- `postgresql/MASTER-PLAN.md` — the published chapter sequence, operational standards, and acceptance targets.
- `postgresql/PROGRESS.md` — authored, reviewed and runtime-lab status per chapter.
- `postgresql/chapters/` — numbered canonical chapter documents.
- `postgresql/labs/` — numbered lab instructions and supporting SQL, configuration, acceptance and monitoring assets.
- `postgresql/scripts/` — shared operational tooling.
- `postgresql/monitoring/`, `projects/` and `templates/` — supporting assets and evidence examples.
- `postgresql/validation/` — independent QA code and retained validation reports.

## Authoring and validation workflow

Keep chapter publication, editorial review, static checks, runnable example review, PostgreSQL runtime tests, destructive-operation controls, and independent acceptance as **separate statuses**. The final gate requires repeatable evidence and reviewer sign-off. See [the V01 audit](validation/V01-STATUS.md).

**Current publication:** Chapters 001–100 authored; runtime verification and certification pending.
