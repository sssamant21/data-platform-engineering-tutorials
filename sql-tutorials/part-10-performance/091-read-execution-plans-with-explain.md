# 091 — Read Execution Plans with EXPLAIN

**Part 10 — SQL Performance & Query Optimization** · **60 minutes** · **PostgreSQL 18 lab baseline** · **Audience:** data engineers, analysts, DBRE/SRE

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Read-only SQL lab](../labs/091-read-execution-plans-with-explain.sql) · [Previous: 090](../part-09-functions-views-json/090-lab-09-build-reusable-reporting-objects.md) · Next: 092 — Table scans, index scans, row estimates, and selectivity (planned)

## 1. Learning objectives and prerequisites (0–5 minutes)

By the end, explain the difference between a SQL query and its physical execution plan; identify scan, filter, sort, aggregate, and join nodes; interpret estimated rows, startup/total cost, and plan indentation; explain why estimates are not measurements; and collect a safe baseline before changing SQL or indexes. Review [Chapter 090](../part-09-functions-views-json/090-lab-09-build-reusable-reporting-objects.md) and basic SELECT, WHERE, GROUP BY, and JOIN.

**Scenario:** a fictional operations team wants to understand why a customer revenue report could slow down as order volume grows. The lesson uses only synthetic records and a read-only PostgreSQL 18 transaction. A tiny VALUES dataset teaches plan anatomy, **not production index selection**.

## 2. Core concepts and portability (5–15 minutes)

A *logical query* says what rows are wanted. A *physical plan* describes how the database proposes to obtain them. PostgreSQL's `EXPLAIN` displays an estimated plan without executing the target statement; `EXPLAIN ANALYZE` **actually executes** it and measures runtime. Never assume `EXPLAIN ANALYZE` is safe for writes or costly production reads.

| Plan field/node | Meaning | Caution |
|---|---|---|
| `Seq Scan` / `Values Scan` | Reads a table / inline values | A sequential scan can be optimal for small tables |
| `Filter` | Predicate applied by a node | `Rows Removed by Filter` appears with ANALYZE where supported |
| `Sort` | Orders rows | May consume memory or spill on large inputs |
| `Aggregate` / `HashAggregate` | Computes grouped or overall metrics | Group count and cardinality affect resources |
| `Nested Loop`, `Hash Join`, `Merge Join` | Join algorithms | Algorithm alone does not prove good/bad performance |
| `cost=a..b` | Planner's estimated startup and total cost | **Not milliseconds**, not currency, not directly comparable across unrelated environments |
| `rows=n` | Estimated output rows per node invocation | Not necessarily actual count; may differ significantly |
| `width=n` | Estimated average row width in bytes | Not actual disk storage |

Read PostgreSQL text plans from the most deeply indented children upward. The parent consumes child output. Plan costs are optimizer units influenced by configuration and statistics. In `EXPLAIN (ANALYZE, BUFFERS)`, actual time and rows describe measured execution; loops mean a node may execute repeatedly, and per-loop row/time values require care. `BUFFERS` shows buffer activity, **not an exact count of physical disk reads**. Planning and execution time are separate.

**Portability:** `SELECT`, `WHERE`, `JOIN`, `GROUP BY` are broadly portable. `EXPLAIN (FORMAT JSON)`, `ANALYZE`, `BUFFERS`, `SET LOCAL`, and plan-node names here are PostgreSQL-specific. MySQL uses EXPLAIN variants, SQL Server has estimated/actual execution plans, and Snowflake/BigQuery provide different profile/explain facilities. Do not compare numeric costs between engines.

## 3. Guided walkthrough (15–30 minutes)

Start with a simple, reproducible query:

```sql
EXPLAIN (FORMAT TEXT, COSTS ON)
SELECT customer_id, SUM(amount) AS paid_total
FROM (VALUES (1, 'paid', 20.00::numeric),
             (1, 'paid', 15.00::numeric),
             (2, 'pending', 90.00::numeric),
             (2, 'paid', 10.00::numeric))
     AS orders(customer_id, status, amount)
WHERE status = 'paid'
GROUP BY customer_id
ORDER BY customer_id;
```

Expect a tree with a values source, filtering, aggregation, and ordering; **the exact node types and order are planner-dependent**. The SQL result, if run separately, is customer 1 = 35.00 and customer 2 = 10.00. `EXPLAIN` itself returns a plan, not those two result rows.

For production investigations, capture the SQL fingerprint (without sensitive literals), schema/index definitions, PostgreSQL version, table size, row estimates, actual rows where safely approved, buffer metrics, timing under representative load, and settings affecting the optimizer. Do not make an index recommendation from one tiny example or one timing sample.

**A safer baseline sequence:** first inspect `EXPLAIN (FORMAT TEXT)`; independently run a bounded SELECT against synthetic/approved data; only in an isolated lab consider `EXPLAIN (ANALYZE, BUFFERS)` with timeouts and read-only transaction. Even read-only ANALYZE executes the query and can cause heavy CPU/I/O or contention.

## 4. Hands-on practice (30–50 minutes)

**Prerequisites:** disposable PostgreSQL 18 instance; database named `sql_tutorials`; non-production credentials. Use the [Chapter 003 isolated setup](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md).

Run from repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/091-read-execution-plans-with-explain.sql
```

The lab begins `BEGIN READ ONLY`, sets transaction-local timeouts, rejects wrong database/version, and ends `ROLLBACK`. It uses inline synthetic VALUES, prints estimated plans, runs bounded SELECT results, and performs fail-closed exact-result checks. No tables, indexes, privileges, or persistent objects are created.

1. Locate the values scan, filter and aggregation in the first plan; note that planner output may vary.
2. Compare `EXPLAIN` output with the actual SELECT results; explain why estimated `rows` is not the output count.
3. Inspect the join plan for a synthetic customer/order report. Identify the join algorithm and which input supplies each row.
4. Modify the **SELECT only** to filter customer 1; predict the result, then compare. Restore the original query before rerunning assertions.
5. Explain why a plan on four rows cannot establish whether an index is useful for ten million rows.

**Expected SQL results (calculated, not runtime-observed):**

| Customer | Paid orders | Paid total |
|---:|---:|---:|
| 1 | 2 | 35.00 |
| 2 | 1 | 10.00 |

Overall: four input orders, three paid, paid total **45.00**. The join exercise preserves a third customer with no paid orders and yields zero for that customer.

## 5. Troubleshooting and operational safeguards (50–55 minutes)

| Symptom | Likely explanation / safe next step |
|---|---|
| Plan differs from screenshot or sample | Planner versions, settings, statistics and query shape vary; compare semantics, not exact nodes |
| `EXPLAIN` shows costs but no execution time | Expected: plain EXPLAIN does not run the target query |
| Estimated rows differ from actual | Statistics or selectivity assumptions; examine with approved representative workload |
| `EXPLAIN ANALYZE` unexpectedly modifies rows | It **executes** DML; do not run it on production write statements |
| `BUFFERS` reports hits | Shared buffer hits do not imply a physical disk read |
| Timeout or database guard fails | Verify isolated DB, PostgreSQL 18 version, and privileges; never weaken guard for production |

**DBRE/SRE change gate:** obtain workload owner approval, a baseline and rollback plan before tuning indexes, statistics, parameters, or SQL. Measure p50/p95 latency, rows, buffers, CPU, concurrency, and regression impact. An improved plan cost does not guarantee improved production latency. Mask identifiers/literals when sharing plans; plan output may reveal schema names and predicates. No `ANALYZE` (statistics refresh), `CREATE INDEX`, `VACUUM`, or configuration changes are part of this lab.

## 6. Review questions and answers (55–60 minutes)

1. **Does plain EXPLAIN run a SELECT?** No; it estimates the plan.
2. **Does EXPLAIN ANALYZE execute its statement?** Yes; this includes data-changing statements.
3. **Is total cost measured in milliseconds?** No; it is an optimizer estimate in arbitrary cost units.
4. **Is Seq Scan always a problem?** No; it may be optimal for small or low-selectivity workloads.
5. **What does an underestimated row count suggest?** Inspect statistics, predicates, correlations and query shape; do not assume one cause.
6. **Why retain a baseline?** To compare correctness and performance after a controlled change.

## References and next step

- [PostgreSQL 18 — Using EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html)
- [PostgreSQL 18 — EXPLAIN command](https://www.postgresql.org/docs/18/sql-explain.html)
- [PostgreSQL 18 — Planner statistics](https://www.postgresql.org/docs/18/planner-stats.html)
- [PostgreSQL 18 — Monitoring database activity](https://www.postgresql.org/docs/18/monitoring-stats.html)

**Next:** 092 — Table scans, index scans, row estimates, and selectivity.

**Validation status:** authored; targeted manual/static reasoning only. Independent editorial review, comprehensive syntax/link QA and actual isolated PostgreSQL 18 runtime execution with reproducible evidence remain pending.
