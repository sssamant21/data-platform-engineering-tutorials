# 098 — Optimize Joins, Aggregations, and Subqueries

**Part 10 — SQL Performance & Query Optimization** · **60 minutes** · **PostgreSQL 18 baseline** · **Audience:** data engineers, DBRE/SRE, analysts

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Read-only SQL lab](../labs/098-optimize-joins-aggregations-subqueries.sql) · [Previous: 097](097-make-predicates-index-friendly-and-rewrite-expensive-sql.md) · Next: 099 — Keyset pagination, benchmarking, and regression tests (planned)

## 1. Learning outcomes and prerequisites (0–5 minutes)

You will identify accidental join fan-out, distinguish INNER JOIN from EXISTS, aggregate at the intended grain, rewrite correlated subqueries when appropriate, inspect estimated PostgreSQL plans, and prove rewritten queries return the same multiset of rows. Review [041 — join fundamentals](../part-05-joins/041-join-fundamentals-and-relationship-cardinality.md), [048 — semi-joins](../part-05-joins/048-semi-joins-and-anti-joins-using-exists-and-not-exists.md), [052 — grouping grain](../part-06-aggregation/052-group-by-and-aggregation-grain.md), and [091 — EXPLAIN](091-read-execution-plans-with-explain.md).

**Scenario:** A fictional retail dashboard joins orders to order lines and payments. Some orders have multiple lines and multiple payment attempts. A naive join multiplies the amounts, overstating revenue and slowing the query.

## 2. Core concepts and portable SQL (5–15 minutes)

- **Join cardinality:** one-to-many joins increase row counts. Joining two independent one-to-many relations on a common parent produces a multiplication per parent.
- **Aggregation grain:** determine the unique business key of each output row (for example, one row per order) *before* summing monetary values.
- **EXISTS:** use a semi-join when asking whether a related row exists, rather than joining and using DISTINCT to undo duplicates.
- **Pre-aggregation:** aggregate child rows to one row per parent before combining multiple child relations.
- **Correlated subquery:** logically depends on the outer row; optimizers may decorrelate it, so do not assume it always runs once per row.
- **Plan choices:** PostgreSQL may use nested-loop, hash, or merge joins; HashAggregate or GroupAggregate; and a semi-join. No operator is universally fastest.

**Portable:** INNER/LEFT JOIN, EXISTS, GROUP BY, derived tables, CTEs and CASE. **PostgreSQL-specific:** EXPLAIN options, FILTER aggregates, DISTINCT ON, LATERAL, work_mem and planner statistics. Other systems use different plan operators, hints, and memory controls.

## 3. Walkthrough: avoid double-counting (15–30 minutes)

Synthetic orders: order 101 has two lines (30 and 20) and two payment attempts (one settled for 50, one failed for 50); order 102 has one line (40) and one settled payment (40); order 103 has one line (10) and no settled payment.

**Wrong approach:** joining lines and payments directly duplicates order 101's line values across its two attempts. This is not solved safely by SUM(DISTINCT amount): two legitimate equal-priced lines would collapse.

```sql
-- Illustrative anti-pattern; order 101 produces 2 x 2 = 4 rows.
SELECT o.order_id, SUM(l.line_amount) AS incorrect_total
FROM orders AS o
JOIN order_lines AS l ON l.order_id = o.order_id
JOIN payments AS p ON p.order_id = o.order_id
GROUP BY o.order_id;
```

**Correct pattern:** reduce each independent child relation to the order grain first.

```sql
WITH orders(order_id) AS (VALUES (101),(102),(103)),
lines(order_id,line_amount) AS (
 VALUES (101,30::numeric),(101,20::numeric),(102,40::numeric),(103,10::numeric)
),
payments(order_id,status,amount) AS (
 VALUES (101,'settled',50::numeric),(101,'failed',50::numeric),
        (102,'settled',40::numeric)
),
line_totals AS (
 SELECT order_id,SUM(line_amount) AS line_total FROM lines GROUP BY order_id
),
settled_totals AS (
 SELECT order_id,SUM(amount) AS settled_total
 FROM payments WHERE status='settled' GROUP BY order_id
)
SELECT o.order_id, l.line_total, COALESCE(p.settled_total,0) AS settled_total
FROM orders o
LEFT JOIN line_totals l ON l.order_id=o.order_id
LEFT JOIN settled_totals p ON p.order_id=o.order_id
ORDER BY o.order_id;
```

| order_id | line_total | settled_total |
|---:|---:|---:|
| 101 | 50 | 50 |
| 102 | 40 | 40 |
| 103 | 10 | 0 |

**Expected (reasoned only):** 100 total line value; 90 settled; 10 outstanding. Treat payment attempts as distinct events; filter to the settled business state before summing.

### Existence checks

```sql
SELECT o.order_id
FROM orders AS o
WHERE EXISTS (
 SELECT 1 FROM payments AS p
 WHERE p.order_id=o.order_id AND p.status='settled'
);
```

Expected IDs 101 and 102. EXISTS does not multiply order rows even if several matching payments exist. A join plus DISTINCT might return the same keys but do unnecessary work and can conceal a faulty join.

### Correlated aggregation versus grouped join

A scalar correlated subquery can be clear for a small filtered outer set:

```sql
SELECT o.order_id,
 (SELECT SUM(l.line_amount) FROM order_lines l WHERE l.order_id=o.order_id) AS total
FROM orders o;
```

For a large outer scan, compare against a grouped derived table joined on order_id. PostgreSQL may optimize either differently; use actual workload measurements in an approved isolated benchmark, not intuition.

## 4. Hands-on PostgreSQL 18 lab (30–50 minutes)

Run only against a disposable database named `sql_tutorials` using a nonproduction role. The [lab file](../labs/098-optimize-joins-aggregations-subqueries.sql) is read-only: inline VALUES, estimated EXPLAIN, transaction-local timeouts, database/version guards, and exact bidirectional EXCEPT ALL assertions. No tables or indexes are created.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/098-optimize-joins-aggregations-subqueries.sql
```

Exercises: (1) predict naive join rows per order; (2) compute line and settled totals independently; (3) compare EXISTS with a join-and-DISTINCT; (4) explain why an order with no payments survives the LEFT JOIN; (5) inspect estimated EXPLAIN operators without asserting a particular plan shape. Expected: naive join produces 4 rows for order 101, 1 for 102, 0 for 103; corrected results are as shown above.

## 5. Validation, troubleshooting and operational safeguards (50–55 minutes)

The lab compares complete row multisets using EXCEPT ALL in both directions; count-only checks can miss compensating errors. A correct result is not proof of faster execution. Inline VALUES are tiny and have no physical indexes; their estimated plan cannot establish production performance.

| Symptom | Likely cause | Safe investigation |
|---|---|---|
| Revenue inflated | independent child fan-out | count rows per order after each join |
| Missing orders | INNER JOIN excludes absent children | evaluate LEFT JOIN and NULL handling |
| Slow aggregation | too many input rows or spill | compare grouped grain and approved EXPLAIN ANALYZE BUFFERS in isolated environment |
| EXISTS rewrite differs | NULLs, predicate mismatch, or duplicate semantics | EXCEPT ALL both ways and verify keys |
| Planner chooses scan | small input, statistics, selectivity | check estimates, indexes and statistics before proposing changes |

**Guardrails:** Never run EXPLAIN ANALYZE on an unapproved production query: it executes the statement. Avoid tuning settings, creating indexes, or materializing intermediate tables in production without change approval, capacity review, rollback and measured baselines. Capture PostgreSQL version, row counts, parameter values, plans, p50/p95 latency, buffers, and concurrency before and after an approved change. Prefer parameterized queries and synthetic data.

## 6. Review questions and answers (55–60 minutes)

1. **Why can joining two child tables overcount totals?** Each parent may produce a Cartesian combination of its independent child matches.
2. **Why not SUM(DISTINCT amount)?** It discards legitimately repeated monetary values.
3. **When is EXISTS preferable?** When only the existence of a related row matters, not its columns or count.
4. **Does a CTE always materialize in PostgreSQL 18?** No; side-effect-free CTEs can be folded into the parent query depending on usage and planner rules.
5. **Does a hash join indicate a problem?** No; suitability depends on cardinality, memory, indexes, and cost.
6. **How prove equivalence with duplicates?** Compare both directions with EXCEPT ALL using identical columns and types.

## References and next step

- [PostgreSQL 18 — EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html)
- [PostgreSQL 18 — WITH queries](https://www.postgresql.org/docs/18/queries-with.html)
- [PostgreSQL 18 — Joins](https://www.postgresql.org/docs/18/tutorial-join.html)
- [PostgreSQL 18 — Aggregate functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [PostgreSQL 18 — Planner statistics](https://www.postgresql.org/docs/18/planner-stats.html)

**Validation status:** authored content; independent editorial review pending; targeted static/manual review only; actual PostgreSQL 18 execution pending. Expected outputs are calculated, not observed.
