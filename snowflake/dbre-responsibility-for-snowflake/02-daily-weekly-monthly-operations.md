# Page 02 — Snowflake DBRE Daily, Weekly, Monthly & Quarterly Operations

**Document ID:** SF-DBRE-OPS-002 | **Owner:** Snowflake DBRE | **Status:** DRAFT — Unvalidated in production

## 1. Daily operating objective

Identify problems affecting **availability, workload performance, data freshness, security and cost**. Snowflake is a managed platform: monitor the customer account, warehouses, SQL workload, pipelines, data objects and integrations rather than host JVM/disk/shards.

| ID | Check | What to review | Owner/action |
|---|---|---|---|
| D01 | Service/account access | Login and known-good synthetic query, service alerts | DBRE / vendor |
| D02 | Warehouse state | Suspended/running, expected availability, scaling events | DBRE |
| D03 | Query SLOs | APP P95/P99, success, timeouts and errors | APP + DBRE |
| D04 | Warehouse queue | Overload, provisioning and blocked queries | DBRE |
| D05 | Expensive SQL | High execution, compile, spill, scan, profile regressions | DBRE + APP |
| D06 | Tasks/dynamic tables | Missed/failed runs, target lag or staleness | DATA + DBRE |
| D07 | Snowpipe/ingestion | Files/rows loaded, failures, freshness | DATA |
| D08 | Locks/transactions | Blocking and long-running statements | DBRE + APP |
| D09 | Credit anomalies | Warehouse/serverless/cloud-services consumption | DBRE + FIN |
| D10 | Authentication/access | Login denials, integrations, expired keys | SEC + PLT |
| D11 | Replication/DR | Secondary refresh age and recoverability | DBRE + DATA |
| D12 | Alerts/telemetry | Missing monitors, stale Account Usage collection | DBRE |

**Use near-real-time sources for incidents:** Snowsight activity pages, Information Schema query/warehouse load history, active sessions and pipelines. ACCOUNT_USAGE views are delayed, sometimes by hours. Record the data-source freshness and privileges of the monitoring role.

### Read-only SQL — daily pack (privileges vary)

~~~~sql
-- Warehouse configuration and state inventory
SHOW WAREHOUSES;

-- Account historical query exceptions; NOT real-time
SELECT query_id, warehouse_name, query_type, execution_status,
       total_elapsed_time, queued_overload_time,
       queued_provisioning_time, start_time
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE start_time >= DATEADD('hour', -24, CURRENT_TIMESTAMP())
  AND (execution_status <> 'SUCCESS' OR queued_overload_time > 0)
ORDER BY start_time DESC
LIMIT 100;

-- Recent warehouse load (Account Usage, potentially delayed)
SELECT start_time, warehouse_name, avg_running, avg_queued_load,
       avg_queued_provisioning, avg_blocked
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY
WHERE start_time >= DATEADD('day', -1, CURRENT_TIMESTAMP())
ORDER BY start_time DESC
LIMIT 100;

-- Warehouse credit consumption
SELECT TO_DATE(start_time) AS usage_day, warehouse_name,
       SUM(credits_used_compute) AS compute_credits,
       SUM(credits_used_cloud_services) AS cloud_services_credits
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE start_time >= DATEADD('day', -7, CURRENT_TIMESTAMP())
GROUP BY 1,2 ORDER BY 1 DESC, 3 DESC;
~~~~

These are **read-only**, but data collection consumes compute and the SNOWFLAKE database access must be controlled. Avoid query_text in broadly shared reports because SQL may contain confidential literals. Query history status values/columns must be verified against your account; do not rely on Account Usage alone to detect a currently running failure.

### Near-real-time alternative (Information Schema)

~~~~sql
-- Executes in a context with access to the required INFORMATION_SCHEMA.
-- Results/visibility depend on role and may be limited to last seven days.
SELECT query_id, query_type, execution_status, total_elapsed_time, start_time
FROM TABLE(
  INFORMATION_SCHEMA.QUERY_HISTORY(
    DATE_RANGE_START => DATEADD('hour', -1, CURRENT_TIMESTAMP()),
    RESULT_LIMIT => 100
  )
)
ORDER BY start_time DESC;
~~~~

Use appropriate database context before invoking Information Schema. Query visibility is privilege-dependent.

**Daily output:** exception register, evidence URLs, failed freshness/SLO incidents and follow-up owners.

## 2. Weekly operations

| ID | Review | Deliverable |
|---|---|---|
| W01 | Top slow/repeated/queued queries | APP/DBRE optimization backlog |
| W02 | Warehouse size, autosuspend and concurrency | Compute workload profile |
| W03 | Serverless tasks/pipes/dynamic tables | Cost and freshness issues |
| W04 | Warehouse credit trend and anomalies | FinOps exception summary |
| W05 | Table/database storage growth | Owner-attributed growth table |
| W06 | Query pruning/spill/clustering | Targeted query optimization candidates |
| W07 | Grants/network policy changes | Security review tickets |
| W08 | Recent failed loads, task and alert runs | Pipeline reliability actions |
| W09 | Time Travel and clones/retained bytes | Recoverability and storage findings |
| W10 | Vendor cases, repeat incidents | RCA and escalation tracking |

Example query for recent task failures (Account Usage is historical and delayed):

~~~~sql
SELECT database_name, schema_name, name AS task_name, state,
       scheduled_time, error_code, error_message
FROM SNOWFLAKE.ACCOUNT_USAGE.TASK_HISTORY
WHERE scheduled_time >= DATEADD('day', -7, CURRENT_TIMESTAMP())
  AND state = 'FAILED'
ORDER BY scheduled_time DESC
LIMIT 100;
~~~~

Audit visibility and permissions of error_message; do not post unredacted sensitive data into incidents.

## 3. Monthly operations

1. Review service SLO and data freshness achievement with APP/DATA.
2. Produce warehouse, serverless and cloud-services credit report; reconcile to billing.
3. Report database/table growth, Time Travel, Fail-safe and clone-retained storage.
4. Test query size/isolation opportunities against representative peak load.
5. Review warehouse auto-suspend/resume, size and multi-cluster settings; assess provisioning/queue effects.
6. Review cost monitors **and budgets**; warehouse resource monitors do not cover all serverless consumption.
7. Review account roles, key-pair/OAuth/SSO connectivity and audit findings with SEC.
8. Check recovery features, edition eligibility, replica refresh and recovery exercises.
9. Review DBRE toil, alerts, incident actions and operating documentation.

## 4. Quarterly operations

- DR tabletop and controlled failover rehearsal where supported and approved.
- Security and data lifecycle/retention attestation.
- Performance architecture, warehouse isolation and growth forecasts.
- Cost optimization outcomes with FinOps including service-tier and serverless costs.
- SLO review, recurring incident trends, vendor support escalations and runbook revalidation.
- Confirm ownership, account edition/region capabilities and policies.

## 5. Sample operational report

| Field | Entry |
|---|---|
| Account/environment and period | |
| DBRE reviewer | |
| Service availability and SLO | |
| Top failing/queued queries | |
| Warehouse state and queue trend | |
| Task/pipe freshness | |
| Storage growth (active/Time Travel/Fail-safe) | |
| Warehouse + serverless credit trend | |
| Security/access exceptions | |
| DR refresh / restore-readiness | |
| Incident, vendor case, owner and next action | |

## 6. Approval and acceptance

- [ ] Account inventory, warehouse roles and service owners complete.
- [ ] Daily checks assigned to on-call roster with automated signals.
- [ ] Information Schema versus Account Usage latency documented.
- [ ] Task/pipe/dynamic table freshness thresholds defined by DATA.
- [ ] Weekly reports and monthly billing/storage reviews evidenced.
- [ ] Cost and recovery safeguards reviewed.
- [ ] Real SQL, privilege access and performance tested in staging.
- [ ] DBRE, APP, DATA and PLT stakeholders sign off.

## References

- [ACCOUNT_USAGE views and latency](https://docs.snowflake.com/en/sql-reference/account-usage)
- [Query history](https://docs.snowflake.com/en/sql-reference/account-usage/query_history)
- [Warehouse load history](https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_load_history)
- [Task history](https://docs.snowflake.com/en/sql-reference/account-usage/task_history)
