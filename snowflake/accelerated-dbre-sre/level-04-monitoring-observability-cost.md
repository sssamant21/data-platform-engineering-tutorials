# Level 4 — Snowflake Monitoring, Observability, and Cost Optimization

**Track:** Snowflake Accelerated DBRE/SRE | **Duration:** 60 minutes | **Status:** DRAFT — static review pending; live Snowflake validation NOT RUN  
**Audience:** DBRE/SRE, observability and FinOps practitioners  
**Prerequisites:** Authorized Snowflake training account; basic SQL recommended for Levels 2–7.

## Learning objectives
Build a basic operational scorecard using historical usage views, understand metric latency, and identify cost growth.

## 60-minute lesson plan
| Topic | Time |
|---|---:|
| Golden signals and Snowflake telemetry | 10 min |
| Query, warehouse and pipeline monitoring | 15 min |
| Metering and credit economics | 10 min |
| Read-only dashboard query lab | 20 min |
| Review | 5 min |
| **Total** | **60 min** |

## Core concepts
### What an operator should observe
Track query failure rate, latency percentiles, overload queueing, warehouse state, task failures, data freshness, authentication events, credits and storage growth. Create application-specific SLOs; do not assume any generic five-second threshold applies to all analytics workloads.

### Fresh versus historical telemetry
Snowsight Query History and Information Schema query-history functions support more immediate triage (subject to permissions and retention). SNOWFLAKE.ACCOUNT_USAGE provides historical views, but latency varies: QUERY_HISTORY can lag about 45 minutes; WAREHOUSE_LOAD_HISTORY and WAREHOUSE_METERING_HISTORY can lag up to about three hours. A historical dashboard is not a real-time alert. **Important SQL distinction:** `ACCOUNT_USAGE.QUERY_HISTORY.EXECUTION_STATUS` uses `success`, `fail`, and `incident` status values, whereas Information Schema query-history table functions use values such as `failed_with_error` and `failed_with_incident`. The failure-query example below intentionally targets **Account Usage**, not Information Schema.

### Warehouse metering
Credit use depends on warehouse size and runtime. AUTO_SUSPEND can reduce idle spend, while overly aggressive stopping and restarting can create overhead and provisioning delay. Multi-cluster and other serverless features affect billing differently. Resource monitors govern supported warehouses; they are not universal controls for all serverless usage.

### What an operations dashboard should show
| Panel | Metric | Decision supported |
|---|---|---|
| Query service | Failure count and p95 elapsed | Investigate application incident |
| Latency breakdown | Exec vs overload queue vs provisioning | SQL or capacity intervention |
| Warehouse utilization | AVG_RUNNING / AVG_QUEUED_LOAD | Concurrency management |
| FinOps | Credits by warehouse/day | Rightsizing and idle spend review |
| Pipeline | Task failures and freshness lag | Data owner escalation |
| Data growth | Storage trend and biggest tables | Capacity and retention planning |

For Grafana/Prometheus, collect approved, low-cardinality aggregates with a service identity and respect Snowflake rate, privilege and data-latency limits. Avoid exporting full query text or PII into dashboards.

## Hands-on lab and expected results
### Prerequisites
A read-only monitoring role with SELECT on the relevant SNOWFLAKE.ACCOUNT_USAGE views. If not available, perform the queries with an approved supervisor or review synthetic examples; do **not** use ACCOUNTADMIN merely for the lab.

### Step 1 — Credits by warehouse over 7 days
~~~sql
SELECT WAREHOUSE_NAME,
       ROUND(SUM(CREDITS_USED), 2) AS CREDITS_7D
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE START_TIME >= DATEADD('day', -7, CURRENT_TIMESTAMP())
GROUP BY WAREHOUSE_NAME
ORDER BY CREDITS_7D DESC;
~~~
Expected: one row per active billed warehouse with credits in the window; may return none in an unused training account.

### Step 2 — Warehouse queueing over 24 hours
~~~sql
SELECT WAREHOUSE_NAME, START_TIME,
       ROUND(AVG_RUNNING, 2) AS RUNNING_LOAD,
       ROUND(AVG_QUEUED_LOAD, 2) AS QUEUED_LOAD,
       ROUND(AVG_BLOCKED, 2) AS BLOCKED_LOAD
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY
WHERE START_TIME >= DATEADD('hour', -24, CURRENT_TIMESTAMP())
ORDER BY START_TIME DESC
LIMIT 50;
~~~
Expected: five-minute historical intervals. Load is a time ratio, not a count of users.

### Step 3 — Failure trend
~~~sql
SELECT DATE_TRUNC('hour', START_TIME) AS HOUR,
       COUNT(*) AS QUERY_COUNT,
       COUNT_IF(EXECUTION_STATUS = 'fail') AS FAIL_COUNT
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD('day', -1, CURRENT_TIMESTAMP())
GROUP BY 1 ORDER BY 1;
~~~
Expected: aggregate query and failure counts; ensure view latency is considered.

### Step 4 — Interpret a hypothetical case
Credits rise 40%, query count stays flat, AVG_QUEUED_LOAD stays low. Evaluate warehouse runtime and size changes, ingestion changes and idle duration before claiming inefficiency.

**Pass:** identify one expensive warehouse, one contention signal, and write a draft alert with a measured baseline. No live alert configuration is required.

## DBRE/SRE troubleshooting quick reference
| Metric anomaly | Verify | Owner action |
|---|---|---|
| Credit spike | Metering, resize history, idle runtime | FinOps + warehouse owner |
| Query failure spike | Query IDs, error codes, role | Application + DBRE |
| Queueing spike | Load history plus recent query history | DBRE capacity review |
| Stale dashboard | Account Usage latency | Change alert source, not warehouse size |

Do not set an automatic suspend-on-budget threshold for a critical warehouse without an approved availability impact assessment.

## Knowledge check (with answers)
1. **Are Account Usage metrics real time?** No.
2. **What does AVG_QUEUED_LOAD represent?** Average query load queued for capacity.
3. **What drives warehouse credits?** Compute size and running time.
4. **Should p95 thresholds be global?** No, tie to workload SLO.
5. **Are resource monitors universal for serverless?** No.

## Operational safety and validation
- Use a **designated lab account/warehouse** and synthetic data. Protect query-history text and any personal or customer information.
- SQL that creates/changes warehouse, roles, objects, retention or data requires appropriate role, approval and isolated test scope.
- Expected outcomes describe intended behavior, **not proof of execution**. No SQL was run against live Snowflake when authoring this lesson.
- If a command is not applicable to the account edition or current role, document the limitation rather than escalating privileges.
- **Acceptance:** instructor checks concepts, learner documents observed output, and a separate runtime review confirms SQL syntax/permissions and clean-up.

## Continue into the full 90-chapter curriculum
[46 Account Usage](../46-account-usage-information-schema.md), [48 Warehouse Monitoring](../48-warehouse-monitoring.md), [50 Observability](../50-alerts-notifications-observability.md), [55 FinOps](../55-snowflake-finops-cost-optimization-canonical.md)

## Official documentation
- https://docs.snowflake.com/en/sql-reference/account-usage
- https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_load_history
- https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_metering_history

[Back to accelerated track index](README.md) | [Validation tracker](STATUS.md)
