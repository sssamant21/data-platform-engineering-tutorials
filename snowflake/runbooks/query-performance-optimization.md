# Snowflake Query Performance Optimization — DBRE/SRE Runbook

**Audience:** Data Engineers, DBRE/SRE, Snowflake platform administrators  
**Scope:** Production investigation, controlled optimization, evidence, and rollback  
**Status:** Operational draft — SQL examples require validation with your Snowflake roles, edition, and staging workload  
**Change policy:** Read-only diagnosis first. SQL rewrites, table-layout services, and warehouse changes require the appropriate owners and change approval.

> **Purpose:** An actionable, concise companion to [Chapter 76 — Query Slowness Troubleshooting](../76-snowflake-query-slowness-troubleshooting.md), not a new numbered tutorial. For details, also see [Query Profile](../37-query-profile-deep-dive.md), [Pruning](../38-micro-partitions-pruning.md), [Clustering](../39-clustering-automatic-clustering.md), [Warehouse Sizing](../43-warehouse-sizing-scaling.md), and [Query History](../47-query-history-workload-analysis.md).

## 1. Triage: identify the slow query

1. Capture incident time (UTC), application/workload, environment, impact, warehouse, user/role, query ID, and normal vs. current latency.
2. In Snowsight, navigate to **Monitoring → Query History**, filter the relevant period and workload, then open the query's **Query Profile**.
3. For historical investigation, run this **read-only** query with an approved monitoring role:

```sql
SELECT
    query_id,
    user_name,
    warehouse_name,
    query_hash,
    ROUND(total_elapsed_time / 1000.0, 2) AS elapsed_sec,
    ROUND(execution_time / 1000.0, 2) AS execution_sec,
    ROUND(queued_overload_time / 1000.0, 2) AS overload_queue_sec,
    ROUND(queued_provisioning_time / 1000.0, 2) AS provisioning_queue_sec,
    ROUND(compilation_time / 1000.0, 2) AS compilation_sec,
    ROUND(bytes_scanned / POWER(1024, 3), 2) AS scanned_gib,
    partitions_scanned,
    partitions_total,
    ROUND(bytes_spilled_to_remote_storage / POWER(1024, 3), 2) AS remote_spill_gib
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE start_time >= DATEADD(hour, -24, CURRENT_TIMESTAMP())
  AND execution_status = 'SUCCESS'
  AND warehouse_name IS NOT NULL
ORDER BY total_elapsed_time DESC
LIMIT 20;
```

**Telemetry caveat:** `ACCOUNT_USAGE` is delayed and should not be used as a real-time incident feed. Use Snowsight or the appropriate Information Schema query-history function for recent activity. An approved role needs access to this view. Avoid copying sensitive `QUERY_TEXT` or production patient data into tickets.

## 2. Determine where time was spent

Use the affected query ID, then examine each component rather than only total elapsed time:

```sql
SELECT
    query_id,
    warehouse_name,
    ROUND(total_elapsed_time / 1000.0, 2) AS elapsed_sec,
    ROUND(compilation_time / 1000.0, 2) AS compilation_sec,
    ROUND(execution_time / 1000.0, 2) AS execution_sec,
    ROUND(queued_overload_time / 1000.0, 2) AS overload_queue_sec,
    ROUND(queued_provisioning_time / 1000.0, 2) AS provisioning_queue_sec,
    ROUND(queued_repair_time / 1000.0, 2) AS repair_queue_sec,
    ROUND(transaction_blocked_time / 1000.0, 2) AS blocked_sec,
    partitions_scanned,
    partitions_total,
    ROUND(bytes_spilled_to_local_storage / POWER(1024, 3), 2) AS local_spill_gib,
    ROUND(bytes_spilled_to_remote_storage / POWER(1024, 3), 2) AS remote_spill_gib
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE query_id = '<QUERY_ID>';
```

| Dominant symptom | Inspect first | Typical remediation (subject to testing) |
| --- | --- | --- |
| Overload queue | Workload concurrency, shared warehouse, long-running queries | Tune/isolate workload; assess multi-cluster or capacity |
| Provisioning queue | Suspended/resuming/resizing warehouse | Review auto-suspend/resume and workload schedule |
| Compilation | Complexity, deeply nested views, generated SQL | Simplify SQL/views; reduce redundant branches |
| Execution + large scan | TableScan, pruning, filters, data growth | Fix predicates, column selection, storage layout where justified |
| Join output explodes | Join keys and unique/business keys | Fix join predicates or deduplicate at correct grain |
| Remote spilling | Join/sort/aggregate/window operators, intermediate volume | Reduce intermediate data; benchmark larger warehouse if necessary |
| Transaction blocked | Concurrent writes, transaction duration | Coordinate transaction/ETL owners |
| Snowflake fast, app slow | Client fetch, networking, serialization, retries | Troubleshoot application path |

## 3. Inspect Query Profile before rewriting

Look for expensive **TableScan**, **Join**, **Aggregate**, **Sort**, **Window**, and **Exchange** operators. Review input/output row counts, partitions scanned/total, local/remote spill, and any Query Insights. An exploding join (many more output than input rows) usually merits a correctness check.

For a completed query from the last 14 days, with sufficient warehouse privileges:

```sql
SELECT *
FROM TABLE(GET_QUERY_OPERATOR_STATS('<QUERY_ID>'));
```

Do not assume a small `LIMIT` avoids scanning or sorting; check the actual plan. For tables with multiple scans, query-level partition metrics are aggregate signals, not proof that one particular table is poorly pruned.

## 4. Optimize SQL first (Data Engineering owner)

**Read only required columns** — use `SELECT claim_id, patient_id, service_date` rather than `SELECT *` if the consumer needs only those fields.

**Use direct date/timestamp range predicates** when filtering time:

```sql
-- Example assuming SERVICE_DATE is DATE or TIMESTAMP and the desired
-- time window is 2026-11-01 in the column's intended timezone.
SELECT claim_id, patient_id, claim_amount
FROM HEALTHCARE.CLAIMS
WHERE service_date >= '2026-11-01'
  AND service_date <  '2026-11-02';
```

Prefer this form over wrapping `SERVICE_DATE` in a function for a selective date filter. A speedup is not guaranteed: measure micro-partition pruning and confirm date/timezone semantics.

**Check join correctness:** Verify uniqueness and expected join cardinality; never use `DISTINCT` just to hide a many-to-many mistake. Reduce unnecessary sorting/aggregation and use `UNION ALL` only when duplicate elimination is not required.

## 5. Investigate storage layout, memory, and concurrency

- **Pruning:** Compare partitions scanned vs. total alongside bytes scanned and historical baseline. A high scan ratio may be legitimate for a broad analytical query.
- **Clustering:** For a frequently filtered, large table, inspect clustering *before* proposing a clustering key:

```sql
SELECT SYSTEM$CLUSTERING_INFORMATION(
    'HEALTHCARE.CLAIMS',
    '(SERVICE_DATE)'
);
```

- **Remote spilling:** Check whether a join, sort, or aggregation has large intermediate results; first reduce the data volume. A larger warehouse is a testable hypothesis, not the default fix.
- **Concurrency:** Compare query-history queues with warehouse load and workload schedules. Multi-cluster primarily addresses concurrency; resizing a single query is a different decision.
- **Advanced services:** Evaluate Automatic Clustering, Search Optimization Service, Query Acceleration Service, or materialization only when workload fit, edition, maintenance credits, and ownership have been reviewed.

**Never run warehouse resize, ALTER TABLE CLUSTER BY, or service enablement directly from this runbook in production.** Those require a separate approved change, rollback, and performance/cost test plan.

## 6. Controlled before/after validation

1. Save query ID, SQL version/commit, parameter values, data volume, warehouse name/size, concurrency, observed P50/P95 latency, bytes/partitions scanned, remote spill, and representative warehouse credits.
2. In a dedicated **test session**, avoid persisted result reuse during comparative execution tests:

```sql
ALTER SESSION SET USE_CACHED_RESULT = FALSE;
-- Run approved original SELECT and save its query ID.
-- Run approved optimized SELECT with equivalent parameters and save its query ID.
ALTER SESSION SET USE_CACHED_RESULT = TRUE;
```

3. Compare repeated executions under similar conditions; account for warehouse local cache, warm-up, competing workloads, and underlying data changes.
4. Independently verify **result equivalence** (business keys, row counts, aggregates, null handling, timezone boundaries, duplicates). Faster but incorrect results fail acceptance.
5. Measure **cost** at the warehouse/workload level; dividing total warehouse credits by a single query is not reliable per-query cost attribution. Accept only changes that improve agreed performance **and** justify credit/storage maintenance impact.

| Evidence | Baseline | Optimized | Pass criteria |
| --- | --- | --- | --- |
| Query IDs / SQL versions | Record | Record | Traceable |
| P50/P95 duration (seconds) | Measure | Measure | Meets agreed SLO |
| Data scanned (GiB) / partitions | Measure | Measure | No unexplained regression |
| Queue time / remote spill | Measure | Measure | Bottleneck improved |
| Result correctness | Reference | Compared | Equivalent |
| Warehouse/feature credits | Workload baseline | Same representative workload | Within approved budget |
| Rollback readiness | Document | Confirm | Can restore safely |

## 7. Ownership, approvals, and rollback

| Team | Accountability |
| --- | --- |
| **Data Engineering (DATA)** | Query rewrite, join/business semantics, source/model correctness, result validation |
| **DBRE / Snowflake Platform** | Query Profile/metrics analysis, warehouse sizing, workload isolation, approved services, monitoring/FinOps |
| **Application team (APP)** | End-to-end latency, client fetch, concurrency and retries, application acceptance |
| **Change owner / approvers** | Production window, risk assessment, staged rollout, backout decision, sign-off |

For a failed change: revert the SQL to the known-good version; if a warehouse change was approved, restore its recorded prior configuration; if table organization or service settings changed, follow the individually approved rollback plan. Monitor correctness, P95, queueing, spill, and credits after rollback.

## 8. Completion checklist and ticket evidence

- [ ] Query ID, incident window, user impact, and baseline recorded
- [ ] Queueing, compilation, execution, blocking, and application time distinguished
- [ ] Query Profile and worst operators reviewed
- [ ] Scan/pruning, joins, aggregations, and spill examined
- [ ] SQL correctness validated by DATA / APP
- [ ] Alternatives tested one major change at a time
- [ ] Repeated performance and cost measurements attached
- [ ] Change/rollback approval documented (if applicable)
- [ ] Post-change monitoring and ownership assigned

**Ticket template**

```text
Incident / change ID:
Service / owner / environment:
UTC time range / customer impact:
Query ID / query hash:
Warehouse / size / concurrency:
Baseline P50/P95 / execution / queueing:
Bytes scanned / partitions scanned & total:
Local/remote spill / Query Profile evidence:
SQL/data/workload root cause:
Proposed change / approval / maintenance window:
Staging test query IDs and correctness evidence:
Before vs. after latency, scan, spill, and credits:
Rollback plan and trigger:
DATA sign-off / DBRE sign-off / APP acceptance:
Monitoring follow-up / post-change result:
```

## Official Snowflake references

- [ACCOUNT_USAGE.QUERY_HISTORY](https://docs.snowflake.com/en/sql-reference/account-usage/query_history)
- [Exploring query execution times](https://docs.snowflake.com/en/user-guide/performance-query-exploring)
- [GET_QUERY_OPERATOR_STATS](https://docs.snowflake.com/en/sql-reference/functions/get_query_operator_stats)
- [Query Insights](https://docs.snowflake.com/en/user-guide/query-insights)
- [Clustering keys](https://docs.snowflake.com/en/user-guide/tables-clustering-keys)
- [Optimizing query performance](https://docs.snowflake.com/en/user-guide/performance-query-options)

**Validation status:** Markdown and reference review only; no Snowflake staging/runtime execution or production certification has been performed for this runbook.
