# Page 04 — Snowflake Incident Response & Troubleshooting

**Document ID:** SF-DBRE-OPS-004 | **Owner:** DBRE On-call | **Status:** DRAFT — Not production-certified  
**Applicability:** Snowflake managed service, warehouses, account objects, application/ETL interfaces and vendor escalation

## 1. Incident sequence and severity

**Detect → classify business impact → preserve query IDs and telemetry → read-only diagnosis → coordinate vendor/owner → authorized mitigation → verify application and data freshness → blameless RCA.**

| Priority | Impact example | Action |
|---|---|---|
| P1 | Broad business reporting/query outage, major data unavailability/security risk | Immediate incident command, DBRE, APP/DATA, Snowflake Support |
| P2 | Major query SLA breach, critical task backlog, warehouse unavailable | Urgent DBRE and service owner |
| P3 | Localized regression, unusual credit growth, intermittent failures | Assigned operational ticket |
| P4 | Informational, capacity/change review | Scheduled work |

Service availability is NOT measured by SQL success alone: distinguish Snowflake-side outages, warehouse state, network/SSO, apps, pipelines, data semantics and Snowflake vendor incidents.

### First response — read-only SQL

~~~~sql
SELECT CURRENT_ACCOUNT(), CURRENT_REGION(), CURRENT_ROLE(),
       CURRENT_WAREHOUSE(), CURRENT_TIMESTAMP();

SHOW WAREHOUSES;

-- Recent completed/historical query errors; Account Usage is delayed
SELECT query_id, start_time, user_name, warehouse_name,
       execution_status, error_code, total_elapsed_time,
       queued_overload_time, queued_provisioning_time,
       transaction_blocked_time
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE start_time >= DATEADD('hour', -6, CURRENT_TIMESTAMP())
ORDER BY start_time DESC
LIMIT 100;

-- Historical warehouse queue signals
SELECT warehouse_name, start_time, avg_running,
       avg_queued_load, avg_queued_provisioning, avg_blocked
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY
WHERE start_time >= DATEADD('hour', -12, CURRENT_TIMESTAMP())
ORDER BY start_time DESC LIMIT 100;
~~~~

Use Snowsight/Information Schema query history for near-current events. Query IDs and time ranges should be saved with access-controlled case records, not embedded full SQL text with sensitive literals.

## 2. SF-INC-001 — Snowflake account/service inaccessible

**Signals:** Connection/auth errors across users, no query execution, account unavailable, vendor service incident. Confirm scope across accounts, users, clients, regions, and connectivity. Check Snowflake public service status and account/client error logs. Test approved synthetic health query only. PLT investigates private connectivity, DNS, proxies and SSO. SEC handles authentication policy; DBRE opens vendor case with account locator/region, UTC incident timestamps, sanitized errors. Do not disable SSO, network policies or security controls to regain access. **Validate:** authorized clients connect, smoke queries pass, APP and DATA workflows recover.

## 3. SF-INC-002 — Slow SQL/reporting queries

**Signals:** p95/p99 regression, timeouts, high scan/spill, repeated expensive SQL. Investigate one stable workload/query tag at a time: query history, Query Profile, elapsed versus compilation/execution/queue time, rows and bytes scanned, partition pruning, join and aggregation behavior, spills, result size and cache. Determine whether APP SQL or DATA model is responsible versus warehouse contention. APP owns query changes; DBRE supports profile review and size/isolation guidance. Test against representative dataset and peak workload. **Do not** blindly enlarge every warehouse. **Validate:** client p95/p99, errors and workload throughput.

### Illustrative historical query performance

~~~~sql
SELECT query_id, warehouse_name, query_type,
       total_elapsed_time, execution_time, compilation_time,
       queued_overload_time, bytes_scanned,
       bytes_spilled_to_local_storage, bytes_spilled_to_remote_storage,
       start_time
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE start_time >= DATEADD('hour', -24, CURRENT_TIMESTAMP())
  AND warehouse_name IS NOT NULL
ORDER BY total_elapsed_time DESC LIMIT 50;
~~~~

## 4. SF-INC-003 — Warehouse overload and queuing

**Signals:** sustained queued overload and low throughput. Separate queue caused by warehouse overload, provisioning/resume, or transaction blocking. Compare warehouse size, max/min cluster count (when enabled), auto-suspend, workload isolation, startup cold cache and query concurrency. Options: tune APP concurrency, isolate batch/BI, consider multi-cluster for concurrency and resize for single-query performance. All changes require APP/FIN impact review, budget and rollback. **Validate:** queue duration, p95/p99, cost/credit use, no severe spill or starvation.

## 5. SF-INC-004 — Unexpected suspended warehouse / provisioning delay

Check warehouse state and recent suspend/resume events, resource monitor settings, ownership, client retries and queue provisioning. Assess whether resource monitor exceeded threshold or warehouse lacks auto-resume. Do not automatically resume a budget-suspended critical warehouse without FIN and incident authorization; suspend policy may protect spend. APP validates restored request flow.

## 6. SF-INC-005 — Task graph or dynamic table freshness failure

**Signals:** task failure, skipped run, predecessor/backlog, stale target. Check task history and event timestamps, graph dependencies, enabled status, owner role, warehouse/serverless size and source data arrival. Dynamic table lag must be validated against the assigned TARGET_LAG and actual freshness; not all failures are compute issues. DATA owns transformation and replay; DBRE owns platform diagnostics. Never indiscriminately rerun non-idempotent DML. **Validate:** source-target reconciliation, no duplicates, target SLO.

~~~~sql
SELECT database_name, schema_name, name, state, scheduled_time,
       error_code, error_message
FROM SNOWFLAKE.ACCOUNT_USAGE.TASK_HISTORY
WHERE scheduled_time >= DATEADD('day', -2, CURRENT_TIMESTAMP())
ORDER BY scheduled_time DESC
LIMIT 100;
~~~~

## 7. SF-INC-006 — Snowpipe / COPY ingestion errors

Inspect COPY_HISTORY (for Snowpipe and bulk load history), pipe status (with approved access), stage notifications, cloud integrations, file format, missing permissions and dedupe/replay semantics. Do not rely only on LOAD_HISTORY; it does not include Snowpipe history. DATA owns source schema, data correctness, event delivery and safe replay; PLT owns cloud integration/network. Avoid blind reprocessing of files without dedupe validation.

## 8. SF-INC-007 — Locks and transaction blocking

Find the transaction, long-running DML, blocked time and business owner from query history/LOCK_WAIT_HISTORY or Snowsight. Confirm impact before cancelling any query; cancellation can interrupt transactional work or downstream dependents. APP/Data Owner authorizes workload intervention; DBRE executes only through incident change control. **Validate:** queues drain, correctness checks pass and blocked workload does not recur.

## 9. SF-INC-008 — Credit consumption spike

Separate warehouse compute from cloud services and serverless Snowpipe/tasks/automatic clustering/search optimization/AI spend. Use meter history and query tags, last changed settings and current workload. Coordinate with FIN before a suspend trigger: hard resource monitor SUSPEND/SUSPEND_IMMEDIATE can disrupt critical workflows. A resource monitor does **not** cover every serverless charge. For billing, reconcile with METERING_DAILY_HISTORY and organization invoices, not gross warehouse credits only.

## 10. SF-INC-009 — Authentication, authorization or access regression

Distinguish SSO/OAuth/key rotation, missing role/grant, managed access schema policy, network policy and masking/row-access policy. SEC approves security changes; PLT validates identity infrastructure. Avoid using ACCOUNTADMIN as a shortcut or disabling row-level protection. Test exact service role and authorized/unauthorized cases; redact tokens and PHI.

## 11. SF-INC-010 — Accidental DROP/DELETE/UPDATE

**FIRST:** stop further damaging writes through authorized change controls, identify exact object, statement ID, time, table type and retention setting, and involve DATA/SEC.

Assess Time Travel, UNDROP, AT/BEFORE, safe clone or available backup set. **Never** run recovery operations on production in an exploratory manner; prefer isolated copy and reconciliation before replacing data. Permanent/transient/temporary tables have different retention/Fail-safe properties. Fail-safe is **Snowflake Support best-effort**, not a normal DBA self-restore. Recovery beyond Time Travel may be possible from a validated backup set if configured. Test data correctness and permissions.

## 12. SF-INC-011 — Replication/DR or cross-region problem

Determine account edition, group and object coverage, last successful secondary refresh, replication lag, target region and client redirect readiness. Failover group functionality needs eligible edition and privileges; **do not promote the secondary without incident commander and APP/DATA acceptance** of data loss/RPO exposure and read/write cutover consequences. Fencing, client endpoints and data reconciliation must be planned. Snowflake Support escalations supplement DBRE operations.

## 13. SF-INC-012 — Missing or stale observability

Verify role privileges, Account Usage latency, collector SQL failures, missing warehouse permissions, exporter connectivity and dashboard times. Alert if expected monitoring series disappear. Treat delayed Account Usage as historical, not proof of a healthy real-time workload. Use approved synthetic and Information Schema monitoring as fallback. Assess collector query cost and privacy.

## 14. Incident escalation and decision matrix

| Observation | DBRE initial role | Partner |
|---|---|---|
| Whole account fails | Triage, vendor case | PLT, APP, SF Support, SM |
| Query p99 spikes and remote spill | Profile/warehouse analysis | APP, DATA |
| Running queues / scaling | Warehouse isolation | APP, FIN |
| Freshness SLA missed | Service/warehouse evidence | DATA |
| 401/403 or login errors | Role diagnostics | SEC, PLT |
| Abnormal credits | Metering review | FIN, DATA |
| Wrong data/dropped objects | Time Travel/backup options | DATA, SEC, SM |
| DR replication failure | Secondary readiness | PLT, APP, DATA, SF |
| Internal Snowflake service issue | Vendor escalation & evidence | Snowflake Support |

## 15. Communication, evidence and RCA

**Incident report fields:** ID, severity, account/region/edition, UTC timeline, affected queries/query IDs/warehouses, affected pipelines, business impact, client error and latency SLI, source freshness, current mitigation, vendor case, approvals, next update and accountable lead.

**Evidence:** sanitized query IDs and Query Profile, warehouse load, task/pipe history, grants/integration errors, change logs, client SLO chart, Snowflake status/vendor incident notes and metering. Avoid secrets, full PHI-bearing SQL and private data samples.

**RCA:** triggering event, contributing factors, detection delay, safe mitigation, application/data validation, long-term prevention, named owner and acceptance test. Do not equate a resumed warehouse with completed business recovery.

## 16. Staging exercise and acceptance

- [ ] All 12 scenario runbooks have named owners/escalations.
- [ ] Read-only SQL and privileges validated in staging/approved account.
- [ ] SQL workload profile and warehouse queue tabletop passed.
- [ ] Task/pipe replay cases include idempotency and reconciliation.
- [ ] Credit spike handling includes FIN safeguards and non-warehouse cost.
- [ ] Recovery role/Time Travel/backup path and DR authorization verified.
- [ ] APP and DATA validate end-to-end business functionality.
- [ ] No unsafe blanket cancellation, SSO disablement or destructive SQL used.
- [ ] Incident templates and vendor escalation linked to on-call alerts.

## References
- [Query history](https://docs.snowflake.com/en/sql-reference/account-usage/query_history)
- [Warehouse load monitoring](https://docs.snowflake.com/en/user-guide/warehouses-load-monitoring)
- [Time Travel](https://docs.snowflake.com/en/user-guide/data-time-travel)
- [Snowflake backups](https://docs.snowflake.com/en/user-guide/backups)
- [Business continuity](https://docs.snowflake.com/en/user-guide/replication-intro)
