# Snowflake Accelerated DBRE/SRE — Validation Tracker

**Last authored:** 2026-10-30  
**Source:** seven-course onboarding request  
**Scope:** `snowflake/accelerated-dbre-sre/` only; canonical 90-chapter curriculum unchanged.

| Level | File | Authored | Markdown/static QA | Snowflake runtime lab | Independent tech review | Production certification |
|---|---|---|---|---|---|---|
| 1 | [Snowflake Fundamentals](level-01-snowflake-fundamentals.md) | DRAFT | Not independently checked | NOT RUN | PENDING | NOT CERTIFIED |
| 2 | [Snowflake Administration Fundamentals](level-02-administration-fundamentals.md) | DRAFT | Not independently checked | NOT RUN | PENDING | NOT CERTIFIED |
| 3 | [Snowflake Performance Tuning and Query Optimization](level-03-performance-query-optimization.md) | DRAFT | Not independently checked | NOT RUN | PENDING | NOT CERTIFIED |
| 4 | [Snowflake Monitoring, Observability, and Cost Optimization](level-04-monitoring-observability-cost.md) | DRAFT | Not independently checked | NOT RUN | PENDING | NOT CERTIFIED |
| 5 | [Snowflake Security, RBAC, and Governance](level-05-security-rbac-governance.md) | DRAFT | Not independently checked | NOT RUN | PENDING | NOT CERTIFIED |
| 6 | [Snowflake Data Recovery and Disaster Recovery](level-06-data-recovery-disaster-recovery.md) | DRAFT | Not independently checked | NOT RUN | PENDING | NOT CERTIFIED |
| 7 | [Snowflake Production Troubleshooting and Incident Response](level-07-production-incident-response.md) | DRAFT | Not independently checked | NOT RUN | PENDING | NOT CERTIFIED |

## Validation gates
- **V01 Structure:** headings, all seven agenda totals = 60 minutes, README navigation, cross-links and status labels.
- **V02 Safety:** SQL syntax and least privilege; no live secrets, no destructive production operations, training account requirements explicit.
- **V03 Runtime:** execute labs with minimal roles in a training account; record actual outputs, account edition, query IDs and costs.
- **V04 Independent review:** Snowflake administrator and application/data-owner approval.
- **V05 Certification:** applicable enterprise SLOs, security controls, operational sign-off and periodic revalidation.

## Initial validation evidence
- Authored seven standalone lessons with objectives, 60-minute agenda, concepts, hands-on lab, expected outcomes, troubleshooting, quiz/answers and official docs.
- Static authoring checks can verify file links, durations and Markdown fences; **no live Snowflake environment was accessed**.
- Do not count the courses as certified or claim runtime results from illustrative expected outputs.
