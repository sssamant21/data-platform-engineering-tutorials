# DBRE Responsibility for PostgreSQL

**Enterprise PostgreSQL DBRE / SRE Operational Standards** | **Confluence-ready Markdown** | **Status: DRAFT**

This separate, practice-focused operational track complements the [existing PostgreSQL Chapters 001–100](../README.md). It establishes DBRE ownership, support boundaries, checklists, monitoring and service SLOs, incident runbooks, capacity reporting and FinOps, backup/HA/DR, and safe database lifecycle governance.

> **Delivery vs certification:** Seven documents are authored and published. No live PostgreSQL queries, staging restore/failover tests, production change, owner approval or security certification has been executed for this track.

## Seven published milestones

| Page | Document | What it defines | Status |
|---|---|---|---|
| 01 | [Ownership & RACI](01-ownership-and-raci.md) | DBRE/APP/DATA/PLT/SEC/FIN/SM ownership and provider boundaries | Draft |
| 02 | [Daily/Weekly/Monthly Operations](02-daily-weekly-monthly-operations.md) | Primary/replica checks, locks, WAL, vacuum, queries and backup review | Draft |
| 03 | [Monitoring, Alerting & SLOs](03-monitoring-alerting-slos.md) | postgres_exporter, Prometheus/Grafana, APP metrics, alerts and SLOs | Draft |
| 04 | [Incident Response & Troubleshooting](04-incident-response-troubleshooting.md) | 13 PostgreSQL incident scenarios, escalation and recovery validation | Draft |
| 05 | [Capacity Planning, Growth & FinOps](05-capacity-growth-finops.md) | Database/table/index/WAL growth, 30/60/90d forecasts and cost controls | Draft |
| 06 | [Backup, HA & Disaster Recovery](06-backup-high-availability-disaster-recovery.md) | Base backup/WAL/PITR, replication, independent fencing, cloud restores | Draft |
| 07 | [Data Lifecycle & Safe Maintenance](07-data-lifecycle-safe-maintenance.md) | Autovacuum/index/partition governance, read-only candidate discovery and deletion approvals | Draft |
| QA | [Validation & Acceptance Register](VALIDATION.md) | SQL review, evidence, staging and stakeholder certification | Pending |

## Confluence navigation hierarchy

- PostgreSQL DBRE — Responsibility & Operations (parent page)
  - 01 — Roles, Ownership & RACI
  - 02 — Daily, Weekly, Monthly & Quarterly Operations
  - 03 — Monitoring, Alerting & SLOs
  - 04 — Production Incident Response & Troubleshooting
  - 05 — Capacity, Database Growth & FinOps
  - 06 — Backup, High Availability, DR & Restore Testing
  - 07 — Data Lifecycle & Safe Maintenance
  - Validation Register and Implementation Evidence

## Applies to

- **Self-managed PostgreSQL:** DBRE/PLT operate OS, database process, backup archive, HA/orchestration and storage.
- **AWS RDS for PostgreSQL:** provider-managed infrastructure/backup mechanism; DBRE owns customer settings, application SQL diagnostics, monitoring and recovery validation.
- **Amazon Aurora PostgreSQL:** separate writer/reader/cluster-storage topology; verify Aurora-specific differences.
- **Azure Database for PostgreSQL Flexible Server:** provider-managed HA/backup/PITR with distinct network/restore rules.
- **Google Cloud SQL for PostgreSQL:** provider-managed HA/backup/PITR; verify account and edition/instance settings.

All guides are intended to be version-aware. Do not assume PostgreSQL 18-only statistics and capabilities exist on older releases or in managed providers. As of October 2026, PostgreSQL 18 is the current major stable release; PostgreSQL 14 support ends November 12, 2026. Confirm each cluster's exact engine version and support status.

## Critical safeguards

1. Never run destructive commands from a routine monitoring or candidate-discovery job.
2. Do not delete apparently unused tables, indexes, partitions, databases, replication slots or WAL.
3. Data Owner decides business retention and disposal; DBRE manages safe technical execution with APP/SEC/SM approval gates.
4. Keep application SLO and data correctness separate from engine health metrics.
5. A standby/read replica is not a backup; a complete base backup plus verified WAL or managed PITR must be tested.
6. Failover must have **independent fencing** and validated **single-writer behavior** before application cutover.
7. Monitor transaction wraparound/freeze, replication lag, slot-retained WAL and backup integrity as critical reliability risks.
8. Use least-privilege monitoring roles; avoid superuser-only commands and exposing secrets or PHI in query text/logs.
9. Self-managed and provider-managed PostgreSQL have different restrictions, backup controls and recovery methods.
10. No milestone is production-certified until its validation/acceptance items have been evidenced and signed off.

## QA progress — V01 through V06

**Static/documentation workstreams are all documented; production validation is not complete.** See the [live validation register](VALIDATION.md) for the exact pending evidence and acceptance gates.

| QA milestone | Current disposition | Evidence |
|---|---|---|
| V01 — Markdown/navigation/safety | Static PASS; external link reachability still pending | [Audit](qa/V01-structure-link-safety-audit.md) |
| V02 — SQL/catalog and provider compatibility | Source review completed; live SQL still pending | [Audit](qa/V02-sql-version-provider-compatibility.md) |
| V03 — Monitoring/alerting and security | Source review + sample alerts; live collector and SEC approval pending | [Audit](qa/V03-monitoring-alerting-security-review.md) |
| V04 — Incident and runtime safety | Source review and read-only SQL; 13 staging scenarios pending | [Audit](qa/V04-incident-runtime-safety-review.md) |
| V05 — Capacity, growth, FinOps | Static review and synthetic offline model tests PASS; real data/billing pending | [Audit](qa/V05-capacity-growth-finops-review.md) |
| V06 — Backups, PITR, HA/DR | Source review, read-only SQL and 12-scenario acceptance matrix; staged restore/fencing pending | [Audit](qa/V06-backup-HA-DR-review.md) |

**V07 independent certification process:** [Evidence collection and approval workflow](qa/V07-staging-evidence-and-certification.md) · [Offline evidence validator](qa/V07-evidence-gate.mjs) · [Unfilled template](qa/V07-evidence-template.json). The offline metadata gate has synthetic checks only and **cannot certify production**.

**Next operational phase:** Gather authorized evidence from the exact deployed PostgreSQL versions and providers: isolated PITR, independent fencing where HA is in scope, measured APP/DATA RPO/RTO, exporter alert tests, security review, capacity/billing and signed stakeholder acceptance. No data deletion, production failover, backend termination or production right-sizing is authorized by these drafts.

## References

- [PostgreSQL official documentation](https://www.postgresql.org/docs/current/)
- [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/)
- [PostgreSQL monitoring statistics](https://www.postgresql.org/docs/current/monitoring-stats.html)
- [PostgreSQL physical backups and PITR](https://www.postgresql.org/docs/current/continuous-archiving.html)
- [Prometheus Community postgres_exporter](https://github.com/prometheus-community/postgres_exporter)
