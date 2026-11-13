# 114 — Data Warehouse SQL and Analytical Cost Considerations

**Part 12 — Data Engineering, SQL Dialects & Final Projects | 60 minutes | Audience:** data engineers, analysts, DBREs, SREs.

**Validation:** Authored; targeted static reasoning only. Independent editorial review and actual PostgreSQL 18 runtime validation **pending**. Expected results below are calculated, not observed.

## 1. Learning objectives and prerequisites (0–5 minutes)

By the end, identify scan, join, shuffle, sort and spill costs; calculate safe aggregations at a declared grain; explain partition pruning, clustering, materialization, concurrency and warehouse billing; and write a cost-aware validation checklist. Read [111 — OLTP versus OLAP](111-oltp-versus-olap-query-design.md), [112 — Star schemas](112-star-schemas-facts-dimensions-and-surrogate-keys.md), and [113 — ELT and CDC](113-elt-incremental-loads-and-change-data-capture-patterns.md).

**Agenda:** outcomes 5 min; concepts 10; examples 15; lab 20; troubleshooting 5; review 5.

## 2. Concepts: cost is more than SQL text (5–15 minutes)

A data warehouse executes analytical queries over many rows, often in column-oriented storage. The **grain** of a fact table defines what one row represents. Query correctness comes before performance: joining order headers to multiple lines and then summing header amounts repeats the header amount once per line.

Key resource drivers:

| Driver | Why it matters | First control |
|---|---|---|
| Scanned bytes/partitions | I/O and sometimes per-byte billing | Restrict columns and partition-aligned date ranges |
| Join cardinality | One-to-many joins multiply rows | Declare grain; aggregate lines before joining |
| Distributed shuffle | Moving rows across workers consumes network/memory | Filter early, reduce rows, align distribution where supported |
| Sort/window state | Large ORDER BY and windows can spill | Partition windows appropriately; inspect plans |
| Repeated computation | The same expensive transform runs many times | Consider governed incremental tables/materializations |
| Concurrency | Queues, autoscaling, memory contention | Set workload classes and query limits |

**Pruning** means skipping irrelevant storage segments. Partitioning by a date can help queries constrained by that date, but over-partitioning creates metadata overhead and tiny files. Clustering/sort keys and micro-partition pruning are vendor-specific. A filter such as `DATE(event_ts) = DATE '2026-01-01'` can be less pruning-friendly than a half-open range `event_ts >= TIMESTAMP '2026-01-01 00:00:00' AND event_ts < TIMESTAMP '2026-01-02 00:00:00'` (timezone and timestamp types must be deliberate).

**Billing differs by platform.** Snowflake commonly charges warehouse compute while running, subject to its metering/minimums; BigQuery offers on-demand bytes-processed and capacity pricing models; PostgreSQL cost is usually provisioned compute/storage, not a per-query invoice. A PostgreSQL `EXPLAIN` cost is an optimizer-relative estimate, **not dollars or bytes billed**. Use each provider's actual billing and query-history telemetry rather than inferring cost from row counts.

## 3. Worked example: protect grain before tuning (15–30 minutes)

Fictional orders have header amounts 40.00, 60.00, 30.00, and 70.00, with respectively 2, 1, 2, and 1 order lines. Four orders total **200.00**. Summing header amount *after* joining six lines incorrectly gives **270.00**: order 1 contributes 80 instead of 40 and order 3 contributes 60 instead of 30.

**Portable-style query** (widely supported `WITH`, `VALUES`, `GROUP BY`; check vendor `VALUES`-as-table syntax):

```sql
WITH orders(order_id, region, amount) AS (
  VALUES (1,'East',40.00),(2,'East',60.00),
         (3,'West',30.00),(4,'West',70.00)
)
SELECT region, COUNT(*) AS orders, SUM(amount) AS revenue
FROM orders
GROUP BY region
ORDER BY region;
```

**Calculated result:** East = 2 orders, 100.00; West = 2 orders, 100.00. Never join a line-level table merely to count or sum order-level facts. If line-level conditions are necessary, use `EXISTS` for a semijoin or aggregate lines to one row per order first.

A second example uses a half-open date filter:

```sql
SELECT order_id, amount
FROM warehouse_orders
WHERE order_ts >= TIMESTAMP '2026-01-01 00:00:00'
  AND order_ts <  TIMESTAMP '2026-02-01 00:00:00';
```

`warehouse_orders` is illustrative, not a provided table; **do not run it** until you have an approved isolated dataset. The predicate is generally portable, but physical pruning depends on storage layout and optimizer.

**Warehouse query review:** (1) verify grain and totals; (2) capture scanned bytes, partitions, elapsed time, spill, and slots/credits as supported; (3) compare like-for-like workload and cache state; (4) optimize the biggest driver; (5) re-run assertions; (6) monitor actual spend and latency. Smaller scan bytes do not guarantee lower elapsed time or cost in every billing model.

## 4. Hands-on PostgreSQL 18 lab (30–50 minutes)

Run [114 — analytical cost and grain lab](../labs/114-data-warehouse-sql-analytical-cost.sql) in a **disposable isolated** PostgreSQL 18 database named `sql_tutorials`:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/114-data-warehouse-sql-analytical-cost.sql
```

The lab runs `BEGIN READ ONLY`, verifies database and major version, uses transaction-local timeouts, operates entirely on synthetic CTEs, asserts calculated outcomes, and ends with `ROLLBACK`. It does **not** measure cloud credits, create indexes, change server settings, or use production data.

**Practice sequence:** (1) identify order and line grains; (2) run the region aggregation; (3) compare the correct header total to the intentionally wrong join total; (4) explain why `EXISTS` avoids line fan-out; (5) compare a half-open date range with a cast-on-column filter conceptually; (6) describe what warehouse telemetry you would need to establish real cost savings. Optional: add a fifth synthetic order with zero lines and explain why an inner join would omit it.

**Calculated expected results:** 4 orders; 6 lines; East 100.00; West 100.00; correct total 200.00; naïve joined-header total 270.00; overcount 70.00; zero assertion mismatches.

## 5. Troubleshooting, safety and operations (50–55 minutes)

| Symptom | Investigation | Safe next step |
|---|---|---|
| Revenue larger after join | Compare row counts and key cardinalities | Aggregate at correct grain; reconcile |
| Large scanned bytes | Inspect selected columns, partitions and filters | Use narrow projection and pruning-compatible predicates |
| Slow query despite small scan | Look for shuffle, sort, skew, spills, queuing | Examine vendor query profile; test one change at a time |
| Sudden warehouse cost spike | Compare query history, schedule, concurrency and billing | Notify owners; enforce approved budgets/limits |
| Materialized results stale | Inspect freshness watermark and dependency graph | Block promotion; reconcile before refresh |

**Guardrails:** Use only synthetic data and a disposable PostgreSQL 18 instance for this lab. For real warehouse tuning, obtain workload owner approval, establish a baseline, limit resource consumption, avoid unbounded full scans, and record rollback. Never equate a PostgreSQL planner cost with billed cloud currency. Query history may contain sensitive SQL literals; restrict access and redact before sharing.

## 6. Review questions and answers (55–60 minutes)

1. **Why can a join inflate revenue?** One header repeats for every matching detail row; aggregate at the right grain.
2. **What does partition pruning save?** Unnecessary storage segments scanned, potentially I/O and billed bytes depending on vendor.
3. **Is PostgreSQL EXPLAIN cost a dollar estimate?** No; it is a planner-relative cost unit.
4. **Does a faster query always cost less?** No; pricing, capacity, caching, minimum charges and concurrency differ.
5. **What validates an optimization?** Matching row-level and aggregate outputs plus comparable runtime/resource/billing measurements.

## References and next step

- [PostgreSQL 18 — Using EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html)
- [PostgreSQL 18 — Table partitioning](https://www.postgresql.org/docs/18/ddl-partitioning.html)
- [Snowflake — Understanding compute cost](https://docs.snowflake.com/en/user-guide/cost-understanding-compute)
- [BigQuery — Estimate and control costs](https://cloud.google.com/bigquery/docs/best-practices-costs)
- [BigQuery — Query plan and performance insights](https://cloud.google.com/bigquery/docs/query-plan-explanation)

**Next:** Chapter 115 — Portable SQL versus Vendor-Specific Syntax and Testing (not yet published at time of authorship).
