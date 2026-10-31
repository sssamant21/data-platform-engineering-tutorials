# Level 7 — Snowflake Production Troubleshooting and Incident Response

**Track:** Snowflake Accelerated DBRE/SRE | **Duration:** 60 minutes | **Status:** DRAFT — V01/V02 automated static QA PASS; independent content review PENDING; Snowflake runtime validation NOT RUN (deferred)  
**Audience:** Production DBRE/SRE engineers, incident commanders, developers and data owners  
**Prerequisites:** Authorized Snowflake training account; basic SQL recommended for Levels 2–7.

## Learning objectives
Run a structured, blameless Snowflake incident from detection through validation and prevention.

## 60-minute lesson plan
| Topic | Time |
|---|---:|
| Incident scope, severity and SLO | 10 min |
| Five incident failure modes | 10 min |
| SQL evidence capture and triage | 15 min |
| Tabletop runbook exercise | 20 min |
| Review | 5 min |
| **Total** | **60 min** |

## Core concepts
### What counts as an incident?
An incident is a measurable degradation of a service or business SLO: failed reports, unexpected authentication failures, query p95 latency regression, delayed ingestion, missing data or a cost-related operational impact. Document the affected application, customer-facing symptom, earliest observed time, severity and incident commander.

### Triage framework
~~~text
Detection -> Scope -> Evidence -> Hypothesis
   -> Approved mitigation -> Validation
   -> Monitoring -> Blameless RCA -> Prevention
~~~
Preserve QUERY_ID, WAREHOUSE_NAME, ROLE_NAME, timestamps, error code and affected job/run IDs. The Information Schema query-history table functions and historical ACCOUNT_USAGE view differ in scope, latency and status values; use the former for recent visible incidents and the latter for approved historical investigation. Treat full SQL text and query bindings as potentially sensitive; never post raw patient identifiers or secrets in tickets.

### Five common incident tracks
1. **Slowness:** compare execution, overload queueing, provisioning and transaction blocking; examine Query Profile.
2. **Warehouse unavailable:** verify state, privileges, auto-resume and service status.
3. **Ingestion stale:** check task state, load history, upstream source and transformation dependencies.
4. **Authentication/authorization:** check active role, grants, identity provider and relevant audit records.
5. **Unexpected data change:** freeze destructive changes, inspect retention and use an approved recovery plan.

### Mitigation priorities
Mitigations should restore business functionality with minimum risk. Candidate actions include reverting a recent SQL deployment, routing a report to an isolated warehouse, pausing an unsafe pipeline under owner approval, or scaling a warehouse after confirming a capacity bottleneck. Treat SUSPEND, CANCEL, GRANT, DROP and data restores as privileged production actions.

### RCA quality
A good postmortem distinguishes trigger, contributing conditions, detection gap, user impact, mitigation and measurable preventive actions; it avoids blaming individual operators.

## Hands-on lab and expected results
### Step 1 — Read active context
~~~sql
SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE();
~~~

### Step 2 — Inspect recent visible queries
With a database selected:
~~~sql
SELECT QUERY_ID, WAREHOUSE_NAME, EXECUTION_STATUS,
       TOTAL_ELAPSED_TIME, EXECUTION_TIME,
       QUEUED_OVERLOAD_TIME, QUEUED_PROVISIONING_TIME,
       TRANSACTION_BLOCKED_TIME, START_TIME
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION(RESULT_LIMIT => 1000))
ORDER BY START_TIME DESC;
~~~
Expected: current-session query records, potentially including running queries, subject to the seven-day history window and result limit. This demonstrates evidence capture but does not expose all queries across the production account; account-wide incident review requires separately authorized monitoring. Avoid exporting `QUERY_TEXT` or sensitive bind data.

### Step 3 — Tabletop scenario A: report latency
At 09:05 p95 report time rises 3s -> 40s; overload queueing is 34s while execution is 5s. Investigate concurrent workloads and queuing; propose isolating heavy ETL jobs rather than changing SQL blindly.

### Step 4 — Tabletop scenario B: stale patient analytics
The data freshness SLO is 15 minutes; dashboard is 75 minutes behind. Verify ingestion/source health, task failure details and downstream refresh; do not assume Snowflake query execution is the root cause.

### Step 5 — Optional account-wide historical review
For an approved monitoring role, follow the read-only [Level 7 smoke script](validation/runtime/level-07-smoke.sql) to inspect anonymized hourly counts, failures and overload queueing. `ACCOUNT_USAGE.QUERY_HISTORY` uses `success` / `fail` / `incident` and may lag approximately 45 minutes. The Information Schema function instead uses statuses such as `failed_with_error` / `failed_with_incident`. During a live outage, use a lower-latency source.

### Step 6 — Write a mini incident record
Include: impact, severity, UTC start/end, incident commander, two query IDs or simulated evidence identifiers, leading hypothesis, authorized mitigation, before/after SLO, rollback strategy and preventive action owner. **Pass:** the report could support an audit without revealing sensitive data. Mark any missing role/warehouse visibility or account-history data as **BLOCKED** rather than assuming healthy services.

## DBRE/SRE troubleshooting quick reference
| Situation | Evidence | Owner / escalation |
|---|---|---|
| Query slowness | Query ID, profile, queueing, spills | DBRE + app owner |
| Task / pipeline failures | Task history, copy history, dependencies | Data engineering |
| Permissions | Role and granted privileges | Security / IAM |
| Cost spike | Warehouse metering / usage by hour | DBRE + FinOps |
| Accidental destructive SQL | Query history, retention, exact object | Data owner + recovery lead |
| Regional outage | Cloud status and failover plan | Incident commander + DR lead |

**Suggested communication cadence:** initial acknowledgement, evidence-based updates at the cadence set by severity, final recovery confirmation, and tracked RCA actions.

## Knowledge check (with answers)
1. **First task in an incident?** Confirm impact and scope.
2. **Why save query IDs?** Correlate evidence and query profiles.
3. **What does high overload queueing suggest?** Concurrency/capacity pressure.
4. **Should an operator cancel unknown production queries?** No, follow approval and impact assessment.
5. **What makes an RCA useful?** Verified cause, impact, mitigation and prevention.

## Operational safety and validation
- Use a **designated lab account/warehouse** and synthetic data. Protect query-history text and any personal or customer information.
- SQL that creates/changes warehouse, roles, objects, retention or data requires appropriate role, approval and isolated test scope.
- Expected outcomes describe intended behavior, **not proof of execution**. No SQL was run against live Snowflake when authoring this lesson.
- If a command is not applicable to the account edition or current role, document the limitation rather than escalating privileges.
- **Acceptance:** instructor checks concepts, learner documents observed output, and a separate runtime review confirms SQL syntax/permissions and clean-up.

## Continue into the full 90-chapter curriculum
[75 Admin Runbook](../75-snowflake-production-administration-runbook.md), [76 Slow Queries](../76-snowflake-query-slowness-troubleshooting.md), [78 Snowpipe Troubleshooting](../78-snowflake-data-loading-snowpipe-troubleshooting.md), [80 Incident Runbook](../80-snowflake-production-incident-investigation-runbook.md)

## Official documentation
- https://docs.snowflake.com/en/sql-reference/functions/query_history
- https://docs.snowflake.com/en/sql-reference/account-usage/query_history
- https://docs.snowflake.com/en/sql-reference/account-usage
- https://docs.snowflake.com/en/user-guide/ui-query-profile

[Back to accelerated track index](README.md) | [Validation tracker](STATUS.md)
