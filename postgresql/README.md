# PostgreSQL — DBRE and SRE Tutorials

[Master plan](MASTER-PLAN.md) · [Progress tracker](PROGRESS.md)

Chapters 001–035 are authored and reviewed statically. Actual lab execution remains pending.

- [001 — Responsibilities](chapters/001-postgresql-responsibilities-for-dbre-and-sre.md)
- [002 — Architecture](chapters/002-architecture-processes-memory-storage-and-wal.md)
- [003 — Linux, Networking and Storage Prerequisites](chapters/003-linux-networking-and-storage-prerequisites.md)
- [004 — Reproducible Operations Lab](chapters/004-build-a-reproducible-postgresql-operations-lab.md)
- [005 — psql, Catalogs and Safe SQL](chapters/005-psql-system-catalogs-and-safe-administrative-sql.md)
- [006 — Installation, Packages and Directory Layout](chapters/006-installation-packages-and-directory-layout.md)
- [007 — Initialization, Checksums, Locale and Encoding](chapters/007-initialization-checksums-locale-and-encoding.md)
- [008 — Configuration Precedence, Reloads and Restarts](chapters/008-configuration-precedence-reloads-and-restarts.md)
- [009 — systemd, Startup, Shutdown and Crash Recovery](chapters/009-systemd-startup-shutdown-and-crash-recovery.md)
- [010 — Configuration Drift and Baseline Acceptance](chapters/010-configuration-drift-and-baseline-acceptance.md)
- [011 — Roles, Ownership, Membership and Least Privilege](chapters/011-roles-ownership-membership-and-least-privilege.md)
- [012 — pg_hba.conf, Authentication and Connection Diagnosis](chapters/012-pg-hba-conf-authentication-and-connection-diagnosis.md)
- [013 — TLS Certificates, Verification and Rotation](chapters/013-tls-certificates-verification-and-rotation.md)
- [014 — Secrets Rotation and Service Account Lifecycle](chapters/014-secrets-rotation-and-service-account-lifecycle.md)
- [015 — Audit Logging, Network Isolation and Security Acceptance](chapters/015-audit-logging-network-isolation-and-security-acceptance.md)
- [016 — MVCC, Snapshots and Tuple Visibility](chapters/016-mvcc-snapshots-and-tuple-visibility.md)
- [017 — Isolation Levels and Application Failure Patterns](chapters/017-isolation-levels-and-application-failure-patterns.md)
- [018 — Locks, Blocking Chains and Deadlocks](chapters/018-locks-blocking-chains-and-deadlocks.md)

- [019 — Long Transactions, Idle Sessions and Transaction Timeouts](chapters/019-long-transactions-idle-sessions-and-transaction-timeouts.md)

- [020 — Safe Cancellation, Termination and Concurrency Incident Lab](chapters/020-safe-cancellation-termination-and-concurrency-incident-lab.md)

- [021 — Database SLIs, SLOs and Error Budgets](chapters/021-database-slis-slos-and-error-budgets.md)

- [022 — Statistics Views, Resets and Measurement Windows](chapters/022-statistics-views-resets-and-measurement-windows.md)

- [023 — Query Statistics with pg_stat_statements](chapters/023-query-statistics-with-pg-stat-statements.md)

- [024 — Logs, Slow Statements and Correlation with Application Traces](chapters/024-logs-slow-statements-and-correlation-with-application-traces.md)

- [025 — Prometheus, Grafana and Actionable Alert Acceptance](chapters/025-prometheus-grafana-and-actionable-alert-acceptance.md)

- [026 — Performance Triage and Evidence Collection](chapters/026-performance-triage-and-evidence-collection.md)

- [027 — EXPLAIN and EXPLAIN ANALYZE Safely](chapters/027-explain-and-explain-analyze-safely.md)

- [028 — Planner Estimates, Statistics and Extended Statistics](chapters/028-planner-estimates-statistics-and-extended-statistics.md)

- [029 — CPU, Memory, I/O and Wait Event Diagnosis](chapters/029-cpu-memory-io-and-wait-event-diagnosis.md)

- [030 — Production Slowness Investigation Project](chapters/030-production-slowness-investigation-project.md)

- [031 — B-tree and Other Index Types: Operational Tradeoffs](chapters/031-b-tree-and-other-index-types-operational-tradeoffs.md)

- [032 — Composite, Partial, Expression and Covering Indexes](chapters/032-composite-partial-expression-and-covering-indexes.md)

- [033 — Index Build, Reindex and Concurrent Maintenance](chapters/033-index-build-reindex-and-concurrent-maintenance.md)

- [034 — Index Bloat, Usage and Lifecycle Decisions](chapters/034-index-bloat-usage-and-lifecycle-decisions.md)

- [035 — VACUUM, Autovacuum and Index Cleanup](chapters/035-vacuum-autovacuum-and-index-cleanup.md)

Next: Chapter 036 — Autovacuum Tuning, Freeze and Wraparound Incident Response.
