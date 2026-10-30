# Snowflake — Accelerated DBRE/SRE 60-Minute Courses

**Audience:** new DBREs/SREs, database administrators, data engineers, developers and data stakeholders.  
**Structure:** seven independent 60-minute workshops (7 hours total).  
**Status:** Initial draft published for review; live runtime validation pending.  

These courses are a **short onboarding track** and do **not** replace or renumber the parent [90-chapter canonical Snowflake curriculum](../MASTER-LAYOUT.md). Use the 90 chapters for deeper study.

## Seven-course path
| Level | Tutorial | Duration | Status |
|---|---|---:|---|
| 1 | [Snowflake Fundamentals](level-01-snowflake-fundamentals.md) | 60 min | DRAFT / runtime pending |
| 2 | [Snowflake Administration Fundamentals](level-02-administration-fundamentals.md) | 60 min | DRAFT / runtime pending |
| 3 | [Snowflake Performance Tuning and Query Optimization](level-03-performance-query-optimization.md) | 60 min | DRAFT / runtime pending |
| 4 | [Snowflake Monitoring, Observability, and Cost Optimization](level-04-monitoring-observability-cost.md) | 60 min | DRAFT / runtime pending |
| 5 | [Snowflake Security, RBAC, and Governance](level-05-security-rbac-governance.md) | 60 min | DRAFT / runtime pending |
| 6 | [Snowflake Data Recovery and Disaster Recovery](level-06-data-recovery-disaster-recovery.md) | 60 min | DRAFT / runtime pending |
| 7 | [Snowflake Production Troubleshooting and Incident Response](level-07-production-incident-response.md) | 60 min | DRAFT / runtime pending |
| **Total** | **7 courses** | **420 min (7 hours)** | |

## How to teach each course
1. Present architecture and core concepts for the stated module time.
2. Explain SQL with permission and cost context; run **only** approved examples in a nonproduction lab.
3. Compare actual results with the stated expected outcomes.
4. Review the failure scenario and operational safeguards.
5. Complete the knowledge check and record any findings in the [validation tracker](STATUS.md).

## Curriculum coverage
- L1: What Snowflake is, architecture, database objects, SQL
- L2: Warehouses, administration, roles and query-history basics
- L3: Query Profile, pruning, queueing and performance tuning
- L4: Observability, credits, account-usage lag and dashboards
- L5: Authentication, RBAC, governance and audit safety
- L6: Time Travel, clone, UNDROP, replication, RPO/RTO
- L7: Production triage, evidence capture, recovery and blameless RCA

## Production-safety boundary
All labs require a designated Snowflake training environment. Never use real patient/customer data. Read-only SQL is preferred; create/alter/drop/grant/recovery commands are either constrained to scratch objects or discussed as owner-approved examples. Account Usage grants and feature availability vary. **Published draft ≠ runtime validated ≠ production certified**.

## Training acceptance
See [STATUS.md](STATUS.md) for authoring and technical-validation gates. Every course requires successful manual/runtime checks in an authorized account before a reviewer marks it validated. For deeper topics, follow the cross-references included in each lesson.
