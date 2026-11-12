# 100 — Lab 10: Baseline, Tune, and Remeasure a Slow Query

**Part 10 — SQL Performance & Query Optimization** · **60 minutes** · **PostgreSQL 18 teaching baseline** · **Audience:** data engineers, DBRE/SRE, application developers

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [SQL lab](../labs/100-lab-10-baseline-tune-remeasure.sql) · [Previous: 099](099-keyset-pagination-benchmarking-and-regression-tests.md) · Next: 101 — Least privilege and SQL access-control principles (planned)

## 1. Learning objectives and prerequisites (0–5 min)

By the end, you can: establish a repeatable baseline; distinguish correctness from speed; rewrite a non-index-friendly date predicate into a half-open range; inspect estimated plans; test exact multiset equivalence; and design an *honest* measured benchmark in an isolated environment. Review [091 — EXPLAIN](091-read-execution-plans-with-explain.md), [094 — composite indexes](094-composite-indexes-and-column-order.md), [097 — predicate rewrites](097-make-predicates-index-friendly-and-rewrite-expensive-sql.md), [098 — aggregation grain](098-optimize-joins-aggregations-and-subqueries.md), and [099 — benchmarking](099-keyset-pagination-benchmarking-and-regression-tests.md).

**Scenario:** A fictional tenant dashboard calculates daily paid revenue. A query becomes slow as its underlying table grows. Your task is to preserve the report contract while proposing a measurable optimization, not to assume an improvement.

## 2. Diagnose and baseline (5–15 min)

Define the contract *before* tuning: tenant 10, UTC calendar day 2026-11-01, status PAID, one row per order, sum of amounts in numeric currency units. Count and sum must remain identical. Capture original SQL, parameter values, schema and indexes, table size, statistics freshness, PostgreSQL version, plans, buffer usage, concurrency, and timing distribution.

**Baseline pattern (PostgreSQL-specific timestamp-to-date cast):**

```sql
SELECT count(*) AS paid_orders, sum(amount) AS paid_revenue
FROM orders
WHERE tenant_id = 10 AND status = 'PAID'
  AND created_at::date = DATE '2026-11-01';
```

For a `timestamp without time zone` column storing UTC, the cast may prevent a plain B-tree index on `created_at` from being used as an efficient timestamp range condition. PostgreSQL may still use an expression index or other plan. A cast on `timestamptz` depends on the session time zone: never rewrite it without first establishing the intended reporting time zone and boundary semantics.

**Candidate rewrite (portable SQL concepts):**

```sql
SELECT count(*) AS paid_orders, sum(amount) AS paid_revenue
FROM orders
WHERE tenant_id = 10 AND status = 'PAID'
  AND created_at >= TIMESTAMP '2026-11-01 00:00:00'
  AND created_at <  TIMESTAMP '2026-11-02 00:00:00';
```

The half-open interval avoids excluding fractional-second values near midnight. For `timestamptz`, bind explicit zone-aware boundaries; daylight-saving days may not be 24 hours. Never apply a blanket 24-hour shift to a local calendar day.

## 3. Worked example and expected results (15–30 min)

The lab creates a *logical* synthetic `orders` relation using an inline `VALUES` CTE: 12 orders across two tenants, PAID/PENDING statuses, and timestamps on either side of the selected day. It does not create a physical table.

| Query contract | Expected result, reasoned statically |
|---|---:|
| All synthetic orders | 12 |
| Tenant 10, PAID, Nov 1 | 4 |
| Tenant 10, PAID, Nov 1 revenue | 100.00 |
| Baseline vs candidate multiset differences | 0 |
| Nov 1 PAID orders for tenant 20 | 1 |

Both forms return the same **expected** (4, 100.00). An exact two-way `EXCEPT ALL` assertion detects missing rows, unexpected rows, and duplicate-count differences; comparing just totals could conceal offsetting mistakes.

**Estimated plan:** `EXPLAIN (COSTS ON)` shows optimizer choices without executing the SELECT. The inline CTE has no persistent index and only 12 rows, so the plan **cannot demonstrate an index-scan benefit**. Cost estimates are not elapsed milliseconds. `EXPLAIN ANALYZE` executes the query and reports actual timings; it is deliberately excluded from this read-only teaching lab. No benchmark timing is reported as measured.

**Physical design hypothesis (review only; do not run in this lab):** On an appropriately sized isolated table, evaluate an index whose leading keys match selective equality filters and then the range key, for example `(tenant_id, status, created_at)`. Index order, inclusion of amount, partial predicates, maintenance overhead, and whether the optimizer actually chooses the index depend on workload and distribution. Never create an index in production based solely on this example.

## 4. Hands-on lab (30–50 min)

**Prerequisites:** disposable PostgreSQL **18** database named `sql_tutorials`, nonproduction credentials, `psql` installed. Verify the connection points to your lab instance, not a production host. From the repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/100-lab-10-baseline-tune-remeasure.sql
```

The [SQL lab](../labs/100-lab-10-baseline-tune-remeasure.sql) begins a read-only transaction, sets local statement/lock/idle timeouts, checks database name and PostgreSQL major version, displays both query results and their estimated plans, tests the exact report contract and two-way equivalence, then rolls back. It uses only synthetic CTE rows. Expected success notice (not an observed run): `100 assertions passed: 12 orders, 4 paid, 100.00 revenue, zero differences`. With `ON_ERROR_STOP`, a failed assertion makes `psql` return nonzero.

**Exercise A (5 min):** Explain why `created_at <= '2026-11-01 23:59:59'` loses fractional-second rows. **Exercise B (5 min):** Alter a scratch copy's reporting window to Nov 2 and calculate expected results before running. **Exercise C (5 min):** Identify why a row with status PENDING must not count as revenue. **Exercise D (5 min):** Explain why identical results and different estimated costs do not establish a speedup.

### Controlled measurement protocol — separate optional isolated performance exercise

A real performance comparison requires an *approved*, representative physical fixture and retained evidence. In a dedicated disposable environment only, load synthetic rows at representative scale, create candidate indexes under change control, refresh statistics as appropriate, and record:

| Field | Baseline | Candidate |
|---|---|---|
| PostgreSQL version, host/CPU/RAM, dataset size and row distribution | Record | Same |
| SQL, parameters, index DDL, `ANALYZE` timestamp | Record | Record |
| Correctness assertion and output cardinality | Pass required | Pass required |
| `EXPLAIN (ANALYZE, BUFFERS, SETTINGS)` plan | Capture | Capture |
| Repeated latency median/p95 and variability | Measure | Measure |
| Shared hits/reads, temp I/O, sort spills, concurrency, cache state | Capture | Match/explain |
| Decision | Baseline | Accept only with measured, repeatable gain and no unacceptable write/storage regression |

Repeat each case under comparable cache and concurrency conditions, alternate order to reduce warm-up bias, and keep full SQL, setup, raw timings, plan text, PostgreSQL version, and cleanup logs. Do not infer p95 from a handful of runs; select a sufficient sample size and state it. The supplied 12-row CTE is a **correctness and plan-reading exercise**, not this performance fixture. No measured timing, production index recommendation, or runtime acceptance is claimed here.

## 5. Troubleshooting, operational safety and validation (50–55 min)

- **Different results:** compare timestamp type, time zone, boundary inclusivity, status filters, NULL semantics, tenant isolation, and aggregation grain before tuning.
- **Plan does not show an index:** the CTE has no physical index; a small physical table may also favor a sequential scan. Do not force planner switches merely to obtain a desired screenshot.
- **Slow even with an index:** check cardinality estimates, actual buffer reads, selectivity, heap fetches, concurrent load, and sort/aggregation costs; verify statistics and write overhead.
- **Lab refuses connection:** use an isolated database named `sql_tutorials` running PostgreSQL 18. Do not bypass the guard or run against production.
- **Safety:** no production credentials, no DDL/DML, no `EXPLAIN ANALYZE` on unsafe statements, transaction-local timeouts, read-only mode, synthetic data, and explicit rollback. For real-world index changes obtain DBRE approval, maintenance/rollback plan, monitoring and post-change review.

## 6. Review questions with answers (55–60 min)

1. **Why is a correctness baseline mandatory?** A faster query that returns wrong data is a regression.
2. **What is the expected daily tenant-10 paid revenue?** 100.00 across four orders.
3. **Why use a half-open timestamp interval?** It includes all values from the start while excluding the next day's start without precision-dependent end-of-day literals.
4. **Does EXPLAIN without ANALYZE measure latency?** No, it provides estimated plans/costs and does not execute the query.
5. **Why not conclude that the candidate is faster from this lab?** The tiny inline fixture has no index, no representative I/O and no repeated runtime measurements.
6. **Which evidence would justify a change?** Equivalent results plus repeatable measured improvements under representative load, with acceptable storage/write overhead and approved rollback.
7. **How can time zones invalidate a rewrite?** A `timestamptz::date` cast uses the session zone, while a naïve timestamp range may use different boundaries.

## References

- [PostgreSQL 18 — EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)
- [PostgreSQL 18 — Using EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html)
- [PostgreSQL 18 — Indexes and ORDER BY](https://www.postgresql.org/docs/18/indexes-ordering.html)
- [PostgreSQL 18 — Multicolumn indexes](https://www.postgresql.org/docs/18/indexes-multicolumn.html)
- [PostgreSQL 18 — Date/time types](https://www.postgresql.org/docs/18/datatype-datetime.html)
- [PostgreSQL 18 — ANALYZE](https://www.postgresql.org/docs/18/sql-analyze.html)

**Validation state:** Authored; targeted static/manual reasoning only. Independent editorial review, comprehensive parser-based SQL/link QA, and actual isolated PostgreSQL 18 runtime execution with retained evidence remain **pending**.
