# Page 03 — Snowflake Monitoring, Alerting & Service-Level Objectives

**Document ID:** SF-DBRE-OPS-003 | **Owner:** Snowflake DBRE / APP / DATA | **Status:** DRAFT — Not production validated

## 1. Monitoring architecture

Snowflake Information Schema, Account Usage views, Organization Usage/billing views, Snowsight, query profile, service/client synthetic probes and pipeline-specific telemetry feed monitored dashboards and approved alerting. Export time series to Prometheus/Grafana **only with controlled Snowflake roles, collection cost and data freshness rules**.

Snowflake has no customer-managed JVM, Elasticsearch-style shard cache or node OS metrics. Monitor warehouse load/queue, query execution and application SLOs instead.

### Data freshness caveat

ACCOUNT_USAGE is historical and delayed: QUERY_HISTORY may lag roughly 45 minutes, WAREHOUSE_LOAD_HISTORY up to 3 hours, some credit/storage views longer. Use Information Schema functions, Snowsight and client-side metrics for rapid incident detection. Alert if monitoring data collection becomes stale; never treat an empty delayed view as proof of zero errors.

## 2. Dashboard catalog

| ID | Dashboard | Panels and primary owner |
|---|---|---|
| SF-01 | Executive service reliability | Success, P95/P99, freshness and current alerts (APP/DBRE) |
| SF-02 | Warehouse utilization | Warehouse state, running/queued/provisioning/blocked, concurrency (DBRE) |
| SF-03 | Query latency/profiles | Elapsed/exec/compile/queue, scan, spill, pruning, repeated queries (DBRE/APP) |
| SF-04 | Pipelines and freshness | COPY, Snowpipe, stream, task and dynamic table lag/failure (DATA/DBRE) |
| SF-05 | Compute and credit usage | Warehouse credits, active time, spend anomaly (DBRE/FIN) |
| SF-06 | Serverless cost | Snowpipe, auto-clustering, tasks, AI/serverless services by metering type (FIN/DATA) |
| SF-07 | Storage/data growth | Databases/tables, active/Time Travel/Fail-safe/clones, 30/60/90-day forecast (DBRE) |
| SF-08 | Access and audit | Login failures, grants, network/identity changes (SEC) |
| SF-09 | Replication and DR | Secondary refresh age, eligible feature coverage, RPO/RTO drill (DBRE) |
| SF-10 | Alert quality / incident trends | Incident counts, missing telemetry, escalation, recurring RCA (DBRE) |

## 3. Historical dashboard SQL (read-only)

### Warehouse load / contention

~~~~sql
SELECT warehouse_name,
       DATE_TRUNC('hour', start_time) AS hour_utc,
       AVG(avg_running) AS running_load,
       AVG(avg_queued_load) AS queued_load,
       AVG(avg_queued_provisioning) AS provisioning_load,
       AVG(avg_blocked) AS blocked_load
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY
WHERE start_time >= DATEADD('day', -7, CURRENT_TIMESTAMP())
GROUP BY 1,2 ORDER BY hour_utc DESC, warehouse_name;
~~~~

### Query percentiles and error counts (historical, not APP end-to-end latency)

~~~~sql
SELECT warehouse_name,
       COUNT(*) AS query_count,
       APPROX_PERCENTILE(total_elapsed_time, 0.95) AS p95_ms,
       APPROX_PERCENTILE(total_elapsed_time, 0.99) AS p99_ms,
       COUNT_IF(execution_status <> 'SUCCESS') AS non_success_count,
       AVG(queued_overload_time) AS mean_queue_ms
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE start_time >= DATEADD('day', -1, CURRENT_TIMESTAMP())
  AND warehouse_name IS NOT NULL
GROUP BY warehouse_name
ORDER BY p95_ms DESC;
~~~~

Snowflake QUERY_HISTORY p95 reflects individual recorded SQL statement times, **not** full application response latency. Query history includes heterogeneous statements; filter by an approved workload/query tag or stable query class for defensible SLOs.

### Warehouse compute (do not conflate with total billed account credits)

~~~~sql
SELECT DATE_TRUNC('day', start_time) AS day_utc,
       warehouse_name,
       SUM(credits_used_compute) AS compute_credits,
       SUM(credits_used_cloud_services) AS cloud_service_credits
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE start_time >= DATEADD('day', -30, CURRENT_TIMESTAMP())
GROUP BY 1,2 ORDER BY day_utc DESC, compute_credits DESC;
~~~~

Billing credit adjustments and serverless services require separate account/organization metering reconciliation.

### Database storage history

~~~~sql
SELECT usage_date, database_name,
       average_database_bytes / POWER(1024,4) AS data_tib,
       average_failsafe_bytes / POWER(1024,4) AS failsafe_tib
FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY
WHERE usage_date >= DATEADD('day', -30, CURRENT_DATE())
ORDER BY usage_date DESC, data_tib DESC;
~~~~

Use ACCOUNT_USAGE.TABLE_STORAGE_METRICS for individual-table ACTIVE_BYTES, TIME_TRAVEL_BYTES, FAILSAFE_BYTES and RETAINED_FOR_CLONE_BYTES; note dropped objects and clone ownership can affect apparent totals.

## 4. SLI/SLO model

**Primary business SLIs, instrumented at the client/BI/pipeline level:**
- Query/search/report availability: eligible requests completed successfully / eligible attempts.
- End-to-end latency: P95/P99 from request start to usable result, not SQL execution only.
- Pipeline freshness: target business source event available within approved delay.
- Task reliability: completed expected task executions / scheduled eligible executions.
- Recovery: measured data loss (RPO) and service-restoration time (RTO).
- Cost: credits/approved budget, with freshness caveats for delayed billing data.

### Example proposals — require service owner approval

| Workload | Candidate objective | Owner |
|---|---|---|
| Interactive reporting | 99.9% request success over rolling 30 days | APP |
| Dashboard response | 95% of eligible requests under 5 seconds | APP |
| Incremental ingestion | 99% of expected updates available within 15 minutes | DATA |
| Critical task processing | Completion by approved cutoff | DATA |
| Disaster recovery | Signed RPO/RTO per data/service tier | APP + DATA |

Do not hardcode these as production standards or assume all warehouse queries share a single latency SLO. Define retries, cancellations, cached results, service errors and planned maintenance exclusions in writing.

## 5. Alert matrix and severity

| Signal | Proposed detection | On-call owner |
|---|---|---|
| Client synthetic test/auth failure | Consecutive failures / service error budget burn | DBRE + APP |
| High application P95/P99 | Measured violation of approved workload SLO | APP + DBRE |
| Queue saturation | Sustained avg_queued_load or overload time vs historical baseline | DBRE |
| Unexpected suspended warehouse | Required production warehouse unavailable to workload | DBRE |
| Recurring failed task / freshness breach | Failure and stale source watermark beyond SLA | DATA + DBRE |
| Snowpipe load/freshness issue | Missing arrivals or failed ingestion events | DATA |
| Credit spending anomaly | Approved daily/weekly budget variance | DBRE + FIN |
| Long transaction blocking | Persistent blocking and APP impact | DBRE |
| Replication refresh age | RPO exposure / failed secondary refresh | DBRE + DATA |
| Missing telemetry | Collector/query fails or delayed view beyond expected latency | DBRE |
| Security access anomaly | Failed sign-in or unusual role/grant change | SEC |

P1 for major service/business outage or severe SLO burn; P2 significant degradation/freshness breach; P3 operational problem needing ticket; P4 information. Severity must reflect impact and existing enterprise policy.

## 6. Snowflake Alerts and external routing

Snowflake Alerts can evaluate a SQL condition and perform an approved action or notification; usage/edition/privilege requirements depend on alert type and configuration. For reliable on-call paging, integrate monitored results with existing Grafana/Alertmanager/PagerDuty-equivalent workflows and test end-to-end routing.

Read-only history:

~~~~sql
SELECT name, state, scheduled_time, error_code
FROM SNOWFLAKE.ACCOUNT_USAGE.ALERT_HISTORY
WHERE scheduled_time >= DATEADD('day', -7, CURRENT_TIMESTAMP())
ORDER BY scheduled_time DESC
LIMIT 100;
~~~~

Confirm actual ALERT_HISTORY columns/availability in your account and access role before automated deployment; for immediate alert investigation prefer supported Information Schema functions.

## 7. Monitoring privacy and cost

- Avoid exporting SQL text with credentials, patient data, query literals or IDs in general telemetry.
- Limit query history view access; use safe query ID, tag, warehouse, duration and status for dashboards.
- Bound collection intervals and avoid high-cardinality per-query Prometheus labels.
- Monitor collector warehouse credits, latency and failure independently.
- Use account-scoped least-privilege Snowflake database roles instead of broad ACCOUNTADMIN.
- State the query source, refresh lag, report time zone and coverage on every dashboard.

## 8. Acceptance

- [ ] Business/client metrics, task/ingestion freshness and warehouse history are sourced correctly.
- [ ] Information Schema versus ACCOUNT_USAGE latency and permissions documented.
- [ ] All dashboards query valid columns and handle empty/missing data.
- [ ] P95/P99 measured at correct layer; query workload tagging established.
- [ ] Alert route tested, escalation owner named, no-data/error behavior verified.
- [ ] Account and serverless spending monitored separately.
- [ ] Privacy/PHI protection and least-privilege roles approved.
- [ ] Service owners sign SLOs and on-call adoption.

## References
- [Account Usage reference/latency](https://docs.snowflake.com/en/sql-reference/account-usage)
- [Query history view](https://docs.snowflake.com/en/sql-reference/account-usage/query_history)
- [Warehouse load history view](https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_load_history)
- [Setting up Snowflake alerts](https://docs.snowflake.com/en/user-guide/alerts)
