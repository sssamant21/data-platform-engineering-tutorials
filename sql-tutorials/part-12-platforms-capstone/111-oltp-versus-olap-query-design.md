# 111 — OLTP versus OLAP Query Design

**Part 12 — Data Engineering, SQL Dialects & Final Projects** · **60 minutes** · **Audience:** SQL beginners, data engineers, application engineers, DBRE/SRE

**Lab target:** isolated PostgreSQL 18 database `sql_tutorials`. All examples use fictional retail data. This lesson compares query *intent and access patterns*, not measured database performance.

## 1. Learning outcomes and prerequisites (0–5 minutes)

By the end, explain why transaction processing and analytical reporting need different SQL patterns; identify query grain, cardinality and selectivity; write a selective OLTP lookup and a grouped OLAP report; detect join fan-out; reconcile transactional detail against aggregate output; and propose safe operational controls.

Prerequisites: [041 — Join fundamentals](../part-05-joins/041-join-fundamentals-and-relationship-cardinality.md), [052 — GROUP BY and aggregation grain](../part-06-aggregation/052-group-by-and-aggregation-grain.md), [091 — EXPLAIN](../part-10-performance/091-read-execution-plans-with-explain.md), and [110 — Operational incident lab](../part-11-security-operations/110-lab-11-operational-sql-incident-and-recovery-exercise.md).

## 2. Concepts and architecture (5–15 minutes)

**OLTP (online transaction processing)** supports many short, concurrent business operations such as fetching one order, reserving inventory, or recording a payment. It prioritizes correct transactions, bounded response times, concurrency, and predictable selective access. **OLAP (online analytical processing)** supports broader questions such as monthly revenue by region. It often scans, joins, groups, and summarizes many records. These are *workload descriptions*, not hard rules about which SQL statement or database product is allowed.

| Dimension | OLTP-oriented | OLAP-oriented |
|---|---|---|
| Typical question | What is order 1002? | What are sales by region? |
| Result grain | One order or a few rows | One group per region/month |
| Typical access | Selective predicates, often indexed | Broad scans, aggregation, columnar-friendly |
| Concurrency | Many small read/write transactions | Fewer, often heavier read queries |
| Correctness | Constraints, isolation, durability | Reconciliation, lineage, freshness, consistent snapshot |
| Operational risk | Locking, connection saturation | Memory, I/O, long scans, workload contention |

**Grain** is what one row represents. An order header has one row per order; an order line has one row per order-and-line; a region summary has one row per region. Joining orders to lines and then summing a header-level order amount **duplicates** that amount once per line. Aggregate line amounts at the correct grain instead.

**Architecture example:** transactional PostgreSQL → approved incremental extraction/CDC → warehouse/lakehouse → dashboards. An analytical replica or warehouse may isolate heavy queries, but replicas have lag and neither CDC nor replicas automatically guarantee exactly-once business semantics. Define freshness SLAs and reconciliation checks.

## 3. Worked SQL examples (15–30 minutes)

The following SQL uses a synthetic inline dataset. `VALUES`, `JOIN`, `WHERE`, `GROUP BY`, `SUM`, and `ORDER BY` are broadly portable SQL concepts; explicit casts and `WITH` support/details vary by platform.

**OLTP-style selective order lookup** (illustrative, not an index benchmark):

```sql
WITH orders(order_id, customer_id, region, amount) AS (
  VALUES (1001, 11, 'East', 40.00),
         (1002, 12, 'West', 25.00),
         (1003, 11, 'East', 35.00),
         (1004, 13, 'West', 50.00),
         (1005, 14, 'East', 20.00)
)
SELECT order_id, customer_id, amount
FROM orders
WHERE order_id = 1002;
```

Expected: **1002 | 12 | 25.00**. In a real table, a suitable unique index on `order_id` may make this selective lookup efficient; an inline `VALUES` CTE does not demonstrate index use.

**OLAP-style grouped revenue report:**

```sql
WITH orders(order_id, customer_id, region, amount) AS (
  VALUES (1001, 11, 'East', 40.00),
         (1002, 12, 'West', 25.00),
         (1003, 11, 'East', 35.00),
         (1004, 13, 'West', 50.00),
         (1005, 14, 'East', 20.00)
)
SELECT region, COUNT(*) AS order_count, SUM(amount) AS revenue
FROM orders
GROUP BY region
ORDER BY region;
```

| Region | Orders | Revenue |
|---|---:|---:|
| East | 3 | 95.00 |
| West | 2 | 75.00 |

Grand total: **5 orders, 170.00**. The grouping produces two result rows rather than five transaction rows.

**Fan-out warning:** if order 1001 has two lines, joining its header to those lines and summing `orders.amount` counts 40.00 twice. For line-level revenue, sum line amounts; for header-level revenue, aggregate orders *before* joining to detail, or use a properly deduplicated order-grain relation. `SUM(DISTINCT amount)` is **not** a general fix: two different orders may have identical amounts.

## 4. Hands-on PostgreSQL 18 lab (30–50 minutes)

Use the companion [read-only SQL lab](../labs/111-oltp-versus-olap-query-design.sql). From the repository root, after independently verifying your connection points to an isolated, disposable PostgreSQL **18** database named `sql_tutorials`:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/111-oltp-versus-olap-query-design.sql
```

The lab checks database name and PostgreSQL major version, starts a read-only transaction, sets local timeouts, models five orders and seven order lines using `VALUES`, and rolls back. It does **not** create tables, change roles, load data, or touch production. If your connection might target production, **do not run the command**.

**Tasks:** (1) identify the selective order; (2) calculate order counts and revenue by region; (3) calculate order-line totals; (4) observe that the naïve header-to-line join reports inflated revenue; (5) reconcile aggregate totals to the source; (6) explain which workload should run on a transactional primary versus an analytics system.

**Calculated expected results:** order 1002 = 25.00; East 3 orders / 95.00; West 2 / 75.00; five orders / 170.00; seven lines / 170.00; naïve joined-header sum **260.00** (overcount 90.00); zero reconciliation/assertion mismatches. These are reasoned expectations, **not observed PostgreSQL 18 runtime results**.

**Practice extension:** add a fictional sixth order in a scratch copy, recompute both group totals, and describe how you would protect the source OLTP system from an expensive dashboard query. Keep all changes inside the synthetic CTE.

## 5. Validation, troubleshooting and safety (50–55 minutes)

- **Wrong totals:** verify the grain on both sides of every join, check for duplicated keys and missing lines, and compare group totals with source totals.
- **Missing rows:** inspect inner versus outer join behavior and NULL handling; verify time-zone boundaries for real period reports.
- **Slow transactional query:** review selective predicates, actual cardinality, index suitability, locks, and connection utilization; use approved `EXPLAIN` on a safe environment. Do not add an index or terminate sessions without change approval.
- **Slow analytics:** check scanned rows, grouping cardinality, memory spill, partition pruning, concurrency, and freshness. Do not assume a warehouse is always faster without measurements.
- **Data consistency:** define a stable extraction watermark and reconciliation rules. A summary can be mathematically correct for a stale snapshot yet fail business freshness requirements.

**Guardrails:** never benchmark on production without authorization; do not run `EXPLAIN ANALYZE` on a write statement in production; do not infer actual query latency, index usage, or warehouse savings from the synthetic CTE. This chapter does not validate CDC, replication lag, or recovery.

## 6. Review questions and answers (55–60 minutes)

1. **Is `GROUP BY` always OLAP?** No. Workload scale and access pattern matter more than a single SQL keyword.
2. **Why can a join inflate totals?** One header can match multiple detail rows, duplicating header values.
3. **Why not fix fan-out with `SUM(DISTINCT amount)`?** Equal-valued but distinct business records would collapse.
4. **What protects OLTP performance?** Selective access, bounded transactions, indexes validated against workload, connection limits, and workload isolation.
5. **What makes a warehouse report trustworthy?** Correct grain, reconciled values, lineage, defined freshness, and access controls.

**Next:** [112 — Star schemas, facts, dimensions, and surrogate keys](112-star-schemas-facts-dimensions-and-surrogate-keys.md) (planned; link becomes active when published).

## References

- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — Using EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html)
- [PostgreSQL 18 — Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html)
- [PostgreSQL 18 — Monitoring Database Activity](https://www.postgresql.org/docs/18/monitoring-stats.html)

**Publication/validation:** Authorship and targeted static reasoning are separate from independent editorial review, comprehensive syntax/link QA, and isolated PostgreSQL 18 runtime execution; the latter remain pending until recorded evidence exists.
