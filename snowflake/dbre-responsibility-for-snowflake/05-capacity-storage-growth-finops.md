# Page 05 — Snowflake Capacity Planning, Storage Growth & FinOps

**Document ID:** SF-DBRE-OPS-005 | **Owner:** DBRE + FinOps | **Status:** DRAFT — Not validated

## 1. Objective

Deliver measurable performance and cost optimization for Snowflake **virtual warehouse compute, serverless compute, storage and data transfer** while preserving business SLIs, recovery/retention rules and ingestion freshness.

Snowflake capacity is not Elasticsearch shard/disk sizing. It is a **warehouse sizing, scaling, concurrency, workload isolation, table/micro-partition efficiency, metering, and storage lifecycle** exercise.

## 2. Baseline / ownership

Record account, region, cloud, edition, cost center, warehouse owner, size, auto-suspend/resume, multi-cluster settings, query tags, batch/business hours, expected peak concurrency, query SLO, data freshness, storage class and privacy/regulatory obligations.

| Category | Measurement | Decision owner |
|---|---|---|
| Warehouse compute | Billed credits, runtime, queue, query duration | DBRE + APP |
| Serverless services | Snowpipe, tasks, auto clustering, search optimization, AI, etc. | DATA/APP + FIN |
| Storage | Active, Time Travel, Fail-safe, clone-retained, stages | DATA + DBRE |
| Replication/data transfer | Region/cloud movement and additional account spend | PLT + FIN |
| Account spend | Actual billed credits, contract rate and budgets | FIN |
| Query performance | P95/P99, execution, queue, spill and pruning | APP + DBRE |

## 3. Read-only cost and storage queries

Warehouse credits by day:

~~~~sql
SELECT TO_DATE(start_time) AS usage_day, warehouse_name,
       SUM(credits_used_compute) AS compute_credits,
       SUM(credits_used_cloud_services) AS cloud_services_credits,
       SUM(credits_used) AS gross_credits
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE start_time >= DATEADD('day', -30, CURRENT_TIMESTAMP())
GROUP BY 1,2 ORDER BY 1 DESC,4 DESC;
~~~~

Total billed credits by day (note financial adjustments and view latency):

~~~~sql
SELECT usage_date, SUM(credits_billed) AS billed_credits
FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_DAILY_HISTORY
WHERE usage_date >= DATEADD('day', -30, CURRENT_DATE())
GROUP BY usage_date ORDER BY usage_date DESC;
~~~~

Warehouse queue and utilization:

~~~~sql
SELECT warehouse_name,
       AVG(avg_running) AS avg_running,
       AVG(avg_queued_load) AS avg_queued_load,
       AVG(avg_queued_provisioning) AS avg_queued_provisioning,
       AVG(avg_blocked) AS avg_blocked
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY
WHERE start_time >= DATEADD('day', -14, CURRENT_TIMESTAMP())
GROUP BY warehouse_name ORDER BY avg_queued_load DESC;
~~~~

Database historical average storage in TiB:

~~~~sql
SELECT usage_date, database_name,
       average_database_bytes / POWER(1024,4) AS stored_tib,
       average_failsafe_bytes / POWER(1024,4) AS failsafe_tib
FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY
WHERE usage_date >= DATEADD('day', -90, CURRENT_DATE())
ORDER BY usage_date DESC, stored_tib DESC;
~~~~

Table-level storage, including retained historical/clone data:

~~~~sql
SELECT table_catalog, table_schema, table_name,
       active_bytes, time_travel_bytes, failsafe_bytes,
       retained_for_clone_bytes, deleted
FROM SNOWFLAKE.ACCOUNT_USAGE.TABLE_STORAGE_METRICS
ORDER BY active_bytes DESC LIMIT 100;
~~~~

Table storage metrics include dropped table versions. Reconcile duplicates and avoid attributing retained clone bytes twice. Schema naming and privileges must be validated on the actual account/edition.

## 4. Growth reporting

Persist historical daily snapshots of table/database bytes and source timestamps. Required periods: **daily, weekly, monthly, quarterly, semiannual, annual**. Capture UTC calendar boundaries and account view latency. Split data:
- Active table storage.
- Historical Time Travel bytes.
- Fail-safe bytes.
- Clone-retained bytes.
- Internal stages and optionally external storage (billed by external cloud provider).
- Archive/other tier bytes if enabled.
- Serverless metering spend associated with maintenance.

Example 30/60/90-day estimate: latest bytes + median recent daily net growth × forecast days, with separate peak/onboarding and retention scenarios. Do not treat Time Travel/Fail-safe storage or dropped object retention as instantly recoverable cost savings from a DROP command.

### Forecast register

| Workload | Current storage | 7d/30d net growth | 90d forecast | Owner / action |
|---|---:|---:|---:|---|
| Example analytics DB | TBD | TBD | TBD | DATA / DBRE |
| Example staging area | TBD | TBD | TBD | DATA |
| Example warehouse compute | credits/day | peak and median | 90d billed forecast | FIN / DBRE |

## 5. Warehouse right-sizing

Separate **concurrency** from **single query duration**:
- Increase cluster count (multi-cluster, where supported) to address concurrent queue load.
- Change warehouse size based on execution time, spilling and query characteristics.
- Isolate batch, interactive BI and expensive transformation loads when their SLO/cost profiles differ.
- Set reasonable auto-suspend/auto-resume only after cold-cache and provisioning impacts are tested.
- Evaluate query design, clustering/search optimization materialization and bytes scanned before increasing compute.
- Use resource monitors to notify or suspend **warehouses**, but budgets/other controls for non-warehouse/serverless services.

### Staging benchmark matrix

| Test | Acceptance criteria |
|---|---|
| Normal workloads | APP P95/P99 and throughput maintained |
| Concurrent peak | Queue and failures remain acceptable |
| Big joins/aggregations | Scans/spill reduced or within controlled ceiling |
| Freshness | Tasks/pipes/dynamic tables meet deadlines |
| Auto-suspend/resume | Cold start does not violate SLO |
| Cost | Comparable credits per completed useful workload |
| Failure/retry | Idempotence and controlled recovery |
| Rollback | Old warehouse size/configuration restored safely |

### Illustrative proposal only

Resize a large intermittent BI warehouse down one size and lower auto-suspend from 15 to 5 minutes after peak and cold-start tests. **Do not assert a percentage savings based on size alone.** Metered credits, usage duration, cache effects and retries may change net spend.

## 6. Non-warehouse spend and budget controls

A Snowflake Resource Monitor **only covers warehouse-related credit usage**, not every serverless and AI cost category. Use Snowflake Budgets, account/organization metering and service-specific cost dashboards for other spending.

The billed-credit baseline should come from Snowflake metering adjusted to actual bills (including relevant credits/pricing and organization agreement). Query-level attribution is estimated, not necessarily billed by query.

**Never automate SUSPEND_IMMEDIATE for a critical production warehouse merely from budget threshold** without business/incident authorization and defined impact handling.

## 7. Change approval and post-change measurement

Before changes: 14–30d representative baseline, service workload tags, cost center, proposed modification, query SLO and freshness, safe cutover time, APP/DATA approval, FIN expectation, SM authorization and rollback.

After: compare full relevant weekday/weekend/peak cycles, total credits and dollars, request latency, queue, pipeline completion, Snowflake storage, serverless transfer and new incidents. **Net savings = corrected comparative cost − post-change comparative cost − one-time costs**, with contract rates/seasonality and billing delay noted.

## 8. Acceptance

- [ ] Account, warehouse, budget and workload owner inventory complete.
- [ ] Historical views and access verified; no incomplete billing windows treated as zero.
- [ ] Per-table/database daily-to-annual growth reports validated.
- [ ] Compute, serverless, cloud services and storage separately attributed.
- [ ] 30/60/90-day baseline and peak forecast approved.
- [ ] Warehouse changes pass peak/queue/auto-resume and rollback exercises.
- [ ] Data retention and recovery not reduced without business/security approval.
- [ ] FIN validates real billed savings and DBRE/APP validates unchanged SLOs.

## References
- [Warehouse monitoring](https://docs.snowflake.com/en/user-guide/warehouses-load-monitoring)
- [Resource monitors](https://docs.snowflake.com/en/user-guide/resource-monitors)
- [Warehouse metering history](https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_metering_history)
- [Table storage metrics](https://docs.snowflake.com/en/sql-reference/account-usage/table_storage_metrics)
- [Daily metering](https://docs.snowflake.com/en/sql-reference/account-usage/metering_daily_history)
