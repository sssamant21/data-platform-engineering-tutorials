# DBRE Responsibility for Snowflake

**Enterprise DBRE/SRE Operating Standards** | Snowflake managed platform | Confluence-ready Markdown | **Status: DRAFT**

This separate operations track complements the existing [90-chapter Snowflake curriculum](../README.md). It establishes ownership, operational cadence, monitoring, incident response, capacity/FinOps, backup/recovery and lifecycle governance. It does **not** certify live Snowflake functionality or authorize production changes.

## Published milestones

| Page | Title | Core scope | Status |
|---|---|---|---|
| 01 | [Ownership & RACI](01-ownership-and-raci.md) | DBRE, APP, DATA, PLT, SEC, FIN, SM and vendor boundaries | Draft |
| 02 | [Daily/Weekly/Monthly Operations](02-daily-weekly-monthly-operations.md) | Account and warehouse reviews, pipelines, credit/warehouse checks | Draft |
| 03 | [Monitoring, Alerting & SLOs](03-monitoring-alerting-slos.md) | Snowflake Account Usage, Information Schema, Grafana, SLOs | Draft |
| 04 | [Incident Response & Troubleshooting](04-incident-response-troubleshooting.md) | 12 on-call failure scenarios and escalation controls | Draft |
| 05 | [Capacity, Storage Growth & FinOps](05-capacity-storage-growth-finops.md) | Warehouse scaling, cloud/serverless credits, table/storage reports | Draft |
| 06 | [Backup, DR & Restore Testing](06-backup-disaster-recovery-restore-testing.md) | Time Travel, Fail-safe, backup sets/policies, replication/failover | Draft |
| 07 | [Data Lifecycle & Safe Maintenance](07-data-lifecycle-safe-maintenance.md) | Ownership, retention, safe read-only unused-object reporting | Draft |
| QA | [Validation & Acceptance Register](VALIDATION.md) | Syntax, privileges, edition coverage, staging tests and sign-off | Open |

## Confluence page organization

- Snowflake DBRE — Responsibilities & Operations
  - 01 — Ownership and RACI
  - 02 — Daily, Weekly, Monthly and Quarterly Operations
  - 03 — Monitoring, Alerting & SLOs
  - 04 — Incident Response & Troubleshooting
  - 05 — Capacity Planning, Storage Growth & FinOps
  - 06 — Backup, Disaster Recovery & Restore Testing
  - 07 — Data Lifecycle & Safe Maintenance
  - Validation Register

## Differences from Elasticsearch DBRE

| Elasticsearch concern | Snowflake equivalent / distinction |
|---|---|
| Shards, JVM, data/coordinator nodes | Virtual warehouses, query load, service credits; infrastructure managed by Snowflake |
| Index growth | Databases/tables, Time Travel, Fail-safe, clones, internal stages |
| ES snapshot repository and SLM | Snowflake Time Travel, Fail-safe, **backup sets/policies**, replication/failover |
| Prometheus ES exporter | Snowflake Account Usage, Information Schema functions, app telemetry and ETL instrumentation |
| ES ILM / index retirement | Business retention, Snowflake object lifecycle, Time Travel protection and governed DROP decisions |
| Node scaling | Warehouse size, multi-cluster behavior, autosuspend/resume and workload isolation |
| On-call recovery | Account/warehouse/client/pipeline issues, Snowflake Support escalation |

## Critical operational safeguards

1. Snowflake manages its own infrastructure; do not use Elasticsearch commands or concepts to operate Snowflake.
2. Use **read-only discovery** for unused-object candidates. Never infer that no observed query means safe deletion.
3. Business ownership, security/legal retention, application dependencies, source correctness, recovery and formal change authorization must precede any destructive data operation.
4. Use a monitoring role with approved access. Avoid routine ACCOUNTADMIN and never publish PHI, secrets, tokens or full confidential query text.
5. Account Usage history is delayed and not enough for minute-by-minute outages; use near-current client/Snowsight/Information Schema signals.
6. Resource monitors control warehouses; serverless/AI and other costs need budgets and separate metering.
7. Snowflake backups, Time Travel, Fail-safe and account replication are different recovery tools and must be tested independently.
8. Retention locks on backup sets can be **irreversible** and must not be configured without specific SEC/Legal/Finance approval.
9. DR failover is edition/feature dependent; APP/DATA must accept data-loss exposure and validate services after promotion.
10. All operational thresholds, examples, SQL privileges and version/edition rules require staging confirmation before adoption.

## Delivery vs certification

**Documentation:** 7/7 drafted and stored in GitHub.  
**Runtime tests:** Not executed.  
**Production approval:** Not granted.  
**Next phase:** V01–V06 documentation/syntax review, staging execution with test roles, SLO/DR exercises and independent stakeholder review.

## References

- [Snowflake ACCOUNT_USAGE](https://docs.snowflake.com/en/sql-reference/account-usage)
- [Snowflake warehouse monitoring](https://docs.snowflake.com/en/user-guide/warehouses-load-monitoring)
- [Snowflake recovery backups](https://docs.snowflake.com/en/user-guide/backups)
- [Snowflake business continuity](https://docs.snowflake.com/en/user-guide/replication-intro)
- [Snowflake resource monitors](https://docs.snowflake.com/en/user-guide/resource-monitors)
