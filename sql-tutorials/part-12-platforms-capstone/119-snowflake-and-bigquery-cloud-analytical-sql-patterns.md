# 119 — Snowflake and BigQuery: Cloud Analytical SQL Patterns

**Part 12 — Data Engineering, SQL Dialects & Final Projects | 60 minutes | Audience:** SQL beginners, data engineers, analytics engineers, DBREs, and SREs.

**Status:** Authored learning material. Expected results are calculated from synthetic rows, not observed on a database. Independent editorial review, comprehensive static QA, PostgreSQL 18 runtime validation, and Snowflake/BigQuery cross-engine execution remain pending.

## 1. Learning outcomes and prerequisites (0–5 minutes)

After this chapter, you can: (1) explain warehouse-style analytical query design and data grain; (2) compare portable SQL with Snowflake and Google BigQuery extensions; (3) use QUALIFY, safe date filters, and deduplication patterns; (4) avoid join fan-out and excessive scans; (5) specify a cross-engine correctness and cost test plan.

Read [111 — OLTP versus OLAP](111-oltp-versus-olap-query-design.md), [112 — star schemas](112-star-schemas-facts-dimensions-and-surrogate-keys.md), [113 — incremental loads and CDC](113-elt-incremental-loads-and-change-data-capture-patterns.md), [114 — warehouse cost](114-data-warehouse-sql-and-analytical-cost-considerations.md), [115 — portability](115-portable-sql-versus-vendor-specific-syntax-and-testing.md), and [003 — isolated lab setup](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md).

**Agenda:** objectives 5 minutes; concepts 10; examples 15; lab 20; troubleshooting 5; review 5.

## 2. Concepts and dialect matrix (5–15 minutes)

A cloud analytical warehouse favors large scans, columnar processing, aggregations, and distributed execution. A query's correctness depends on **grain** (what one row represents), while its cost depends on scanned bytes, compute, caching, data layout, and service configuration. Do not equate PostgreSQL EXPLAIN cost units with Snowflake credits or BigQuery billed bytes.

| Topic | Portable/PG-oriented approach | Snowflake | BigQuery (GoogleSQL) |
|---|---|---|---|
| Window result filtering | Subquery/CTE plus WHERE | QUALIFY | QUALIFY |
| Latest event per key | ROW_NUMBER in CTE | ROW_NUMBER plus QUALIFY | ROW_NUMBER plus QUALIFY |
| Safe date boundaries | Half-open range `>= start AND < end` | DATE/TIMESTAMP functions; clustering and micro-partition pruning | Partition filter on partitioning column; partition pruning |
| Semi-structured data | PostgreSQL JSONB operators (vendor-specific) | VARIANT, colon path, FLATTEN | JSON functions, UNNEST for arrays |
| Nested arrays | Model or expand relationally | FLATTEN | UNNEST |
| Upsert | PostgreSQL ON CONFLICT or MERGE | MERGE | MERGE |
| Cost controls | EXPLAIN, statement timeout | Warehouse sizing, auto-suspend, query profile, resource monitors | Bytes processed, dry run, maximum bytes billed, slot reservations |
| Identifiers | PostgreSQL double quotes | Double-quoted identifiers | Backticks for qualified table paths |

**Important:** Snowflake and BigQuery both support QUALIFY, but function behavior, timestamp types, collation, NULL ordering, JSON extraction, and MERGE edge cases can differ. Snowflake micro-partitions are managed automatically; BigQuery supports table partitioning and clustering. Neither engine's pricing or performance can be inferred from this tiny PostgreSQL lab. Snowflake's warehouse credits and BigQuery's on-demand bytes/slot capacity are different billing models; check current vendor documentation and your contract.

## 3. Worked examples (15–30 minutes)

Use this fictional CDC delivery stream (amount is in hypothetical currency units):

| event_id | order_id | event_ts (UTC) | operation | amount |
|---:|---:|---|---|---:|
| 1 | 501 | 2026-01-01 09:00 | U | 40.00 |
| 2 | 502 | 2026-01-01 09:05 | U | 20.00 |
| 3 | 501 | 2026-01-01 10:00 | U | 55.00 |
| 4 | 503 | 2026-01-02 08:00 | U | 30.00 |
| 5 | 502 | 2026-01-02 09:00 | D | NULL |
| 6 | 503 | 2026-01-02 10:00 | U | 35.00 |

**Portable-style pattern (CTE + ROW_NUMBER):** Use a unique, stable ordering key to break timestamp ties.

```sql
WITH ranked AS (
  SELECT order_id, operation, amount,
         ROW_NUMBER() OVER (
           PARTITION BY order_id ORDER BY event_ts DESC, event_id DESC
         ) AS rn
  FROM order_events
)
SELECT order_id, amount
FROM ranked
WHERE rn = 1 AND operation <> 'D'
ORDER BY order_id;
```

Calculated result: (501, 55.00), (503, 35.00); two active orders, total 90.00. Order 502 is deleted. Filtering out deletes *before* ranking would incorrectly resurrect its older update.

**Snowflake and BigQuery dialect extension (QUALIFY):**

```sql
-- Run only after creating an equivalent disposable order_events table
-- on the chosen warehouse; not executable in the PostgreSQL companion lab.
SELECT order_id, operation, amount
FROM order_events
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY order_id ORDER BY event_ts DESC, event_id DESC
) = 1;
```

This returns the three latest-key events, including the delete for order 502. To filter active orders, wrap this result in an outer SELECT with `WHERE operation <> 'D'`. A WHERE clause on the same SELECT runs before QUALIFY and can give the wrong answer.

**Half-open time window:** For timestamps, prefer `event_ts >= TIMESTAMP '2026-01-01 00:00:00' AND event_ts < TIMESTAMP '2026-01-02 00:00:00'` to avoid missing fractional seconds at day end. BigQuery and Snowflake timestamp literal/type syntax and timezone conversions must be verified separately. When querying a partitioned BigQuery table, ensure the predicate is compatible with its partitioning expression.

**Fan-out hazard:** Joining one order header to multiple event versions and summing header amount repeats the header. Deduplicate at the intended grain *before* joining, then reconcile row counts and totals.

## 4. Hands-on PostgreSQL 18 comparison lab (30–50 minutes)

The companion [Chapter 119 SQL lab](../labs/119-snowflake-bigquery-cloud-analytical-patterns.sql) uses only synthetic CTE data, runs in a read-only transaction, verifies the database name and PostgreSQL 18 version, sets transaction-local timeouts, and ends with ROLLBACK. It does **not** connect to Snowflake or BigQuery, create cloud resources, or measure cloud billing.

1. Use the disposable `sql_tutorials` database from [Chapter 003](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md). Never use production credentials.
2. From a trusted local PostgreSQL 18 `psql` client, run `psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/119-snowflake-bigquery-cloud-analytical-patterns.sql` (adjust path to your working directory). The guard aborts if the database/version does not match.
3. Compare the latest-event query to the deliberately incorrect prefiltered-delete query. Observe how delete tombstones affect correctness.
4. Confirm the exact-result assertions and rollback. **Expected, not runtime-observed:** six delivered events, three distinct keys, three latest-key events, two active orders, active sum 90.00, one tombstone, three first-day events, zero mismatches.
5. For an optional **separate, approved sandbox** on each cloud platform, port the synthetic dataset, execute the QUALIFY form, compare output row-for-row, and record query IDs, SQL dialect/version, scan metrics, and cost controls. Do not run unbounded queries against paid or production datasets.

**Practice:** Change event 5 from D to U with amount 25.00 in a disposable copy of the CTE. Predict three active orders and total 115.00; then restore the original. Add a duplicate delivery and reason about a stable deduplication key. Explain why timestamp alone is not sufficient if events tie.

## 5. Troubleshooting, validation, and operational guardrails (50–55 minutes)

| Symptom | Likely cause | Safe response |
|---|---|---|
| Older deleted order reappears | Tombstones filtered before ranking | Rank all changes first, then filter latest tombstones |
| Wrong totals after a join | Fan-out or mismatched grain | Compare counts, deduplicate, reconcile by business key |
| Large BigQuery scan | Partition filter absent/ineffective | Inspect dry-run bytes, add valid partition predicate and bytes cap |
| Unexpected Snowflake credit consumption | Oversized/long-running warehouse or poor pruning | Inspect query profile, warehouse size, auto-suspend, budgets |
| Different cross-engine output | NULL, timezone, collation, or tie ordering | Use explicit casts, UTC convention, deterministic tie breaker |
| Guard failure in lab | Wrong database or PostgreSQL major version | Stop; use isolated PostgreSQL 18 lab, do not bypass guard |

**DBRE/SRE acceptance checklist:** approved disposable environment; least-privilege access; synthetic data; query/statement limits; deterministic expected results; row-level reconciliation; cloud spend limits; reproducible evidence. Never treat a passing PostgreSQL comparison lab as Snowflake or BigQuery validation.

## 6. Review questions and answers (55–60 minutes)

1. **What is QUALIFY?** A dialect extension filtering rows after window-function evaluation; use a CTE for a more portable alternative.
2. **Why must deletes remain in the ranking input?** Otherwise an older update may be selected as the latest active record.
3. **What is the correct active total?** 90.00 across orders 501 and 503.
4. **Why use a half-open timestamp range?** It handles fractional seconds and adjacent windows without overlap.
5. **Why does a passing PostgreSQL lab not validate cloud costs?** Different engines, data layout, scale, caching, and billing models.
6. **What must be captured in a cloud test?** Engine/settings, exact SQL, query ID, input snapshot, output assertions, bytes/credits metrics, and spend controls.

## References and navigation

- [Snowflake QUALIFY documentation](https://docs.snowflake.com/en/sql-reference/constructs/qualify)
- [Snowflake query performance guidance](https://docs.snowflake.com/en/user-guide/performance-query-warehouse)
- [BigQuery QUALIFY and query syntax](https://cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax#qualify_clause)
- [BigQuery partition pruning](https://cloud.google.com/bigquery/docs/querying-partitioned-tables)
- [BigQuery cost controls](https://cloud.google.com/bigquery/docs/best-practices-costs)
- [PostgreSQL 18 window functions](https://www.postgresql.org/docs/18/tutorial-window.html)
- [Master TOC](../MASTER-TOC.md) · [Part 12 navigation](../README.md) · [Status tracker](../STATUS-TRACKER.md)

**Next:** Chapter 120 — Final Capstone: End-to-End Operational and Analytical SQL Project (planned; link added when published).
