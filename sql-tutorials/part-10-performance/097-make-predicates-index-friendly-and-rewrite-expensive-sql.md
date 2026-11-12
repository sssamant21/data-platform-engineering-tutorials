# 097 — Make Predicates Index-Friendly and Rewrite Expensive SQL

**Part 10 — SQL Performance & Query Optimization** · **60 minutes** · **PostgreSQL 18 lab baseline** · **Audience:** data engineers, DBRE/SRE, analysts

[Master TOC](../MASTER-TOC.md) · [Index](../README.md) · [SQL lab](../labs/097-index-friendly-predicates-rewrites.sql) · [Previous: 096](096-optimizer-statistics-and-postgresql-maintenance-basics.md) · Next: 098 — Optimize joins, aggregations, and subqueries (planned)

## 1. Outcomes and prerequisites (0–5 minutes)

After this chapter, you can: recognize predicates that prevent efficient index access; rewrite timestamp, text, and numeric filters without changing semantics; compare estimated plans; validate result equivalence including duplicates and NULLs; and prepare a production-safe tuning proposal. Review [091 — EXPLAIN](091-read-execution-plans-with-explain.md), [093 — B-tree](093-btree-indexes-and-common-index-access-patterns.md), [094 — composite indexes](094-composite-indexes-and-column-order.md), and [096 — statistics](096-optimizer-statistics-and-postgresql-maintenance-basics.md).

**Scenario:** A fictional payment dashboard scans far more rows than expected. Its filter applies a function to every event timestamp. A rewrite may allow an existing index to narrow the scan, but the engineer must prove that the result set is unchanged.

## 2. Concepts and portable syntax (5–15 minutes)

A *search argument* is a condition an access method may use to locate rows. For a B-tree index on `event_at`, `event_at >= lower_bound AND event_at < upper_bound` is generally easier to use as an index range than `CAST(event_at AS DATE) = day`. Wrapping the indexed column in a function or arithmetic expression often prevents use of a plain index, although an expression index, optimizer transformation, or other access method may help. **Index-friendly does not mean index-guaranteed.** PostgreSQL may correctly choose a sequential scan for small tables or low-selectivity filters.

| Pattern | Potentially expensive form | More index-friendly form | Semantic caution |
|---|---|---|---|
| Date filter | `event_at::date = DATE '2026-11-10'` | `event_at >= TIMESTAMP '2026-11-10 00:00:00' AND event_at < TIMESTAMP '2026-11-11 00:00:00'` | For `timestamptz`, choose explicit business timezone and compute correct instants; DST days need not be 24 hours |
| Case-insensitive email | `lower(email) = 'a@example.test'` | Match normalized stored key, or index `lower(email)` | Never silently switch to case-sensitive equality |
| Numeric comparison | `amount + 5 > 25` | `amount > 20` | Check overflow, NULL, floating-point and type behavior |
| Prefix search | `name LIKE 'Acme%'` | Keep anchored prefix with appropriate collation/operator class | A leading wildcard like `'%Acme'` is different |
| OR across fields | `a = 1 OR b = 2` | Consider separate branches with `UNION` or `UNION ALL` | `UNION` removes duplicates; `UNION ALL` can duplicate matching rows |

**Portable concepts:** range comparisons, `AND`, `LIKE`, `UNION`, `EXISTS`, `CASE`. **PostgreSQL-specific details:** `::date`, expression/partial indexes, `EXPLAIN (BUFFERS)`, `ILIKE`, operator classes, `timestamptz` and `AT TIME ZONE`. Other platforms have different computed-column, function-index and date-conversion capabilities.

## 3. Walkthrough (15–30 minutes)

The examples use synthetic `timestamp without time zone` values interpreted as a single agreed business-local clock. This avoids implying a universal UTC or daylight-saving policy.

### A. Date extraction versus half-open range

```sql
WITH events(event_id, event_at, amount) AS (
 VALUES
 (1, TIMESTAMP '2026-11-09 23:59:59', 10::numeric),
 (2, TIMESTAMP '2026-11-10 00:00:00', 20::numeric),
 (3, TIMESTAMP '2026-11-10 12:00:00', 30::numeric),
 (4, TIMESTAMP '2026-11-10 23:59:59', 40::numeric),
 (5, TIMESTAMP '2026-11-11 00:00:00', 50::numeric)
)
SELECT event_id, amount
FROM events
WHERE event_at >= TIMESTAMP '2026-11-10 00:00:00'
  AND event_at < TIMESTAMP '2026-11-11 00:00:00'
ORDER BY event_id;
```

**Expected (reasoned, not runtime-verified):** event IDs 2, 3, 4; sum 90. A half-open interval includes midnight at the start and excludes the next day's midnight. Avoid `BETWEEN` with a fabricated end-of-day timestamp: fractional seconds can be lost.

For `timestamptz`, first determine the intended timezone and boundaries. For example, PostgreSQL `TIMESTAMP '2026-11-10 00:00:00' AT TIME ZONE 'America/New_York'` yields an instant. Apply the timezone conversion to **constant boundaries**, not to every indexed column value. Confirm daylight-saving behavior and data type before deployment.

### B. Case folding and expression indexes

```sql
-- Correct case-insensitive semantics; may need an expression index:
SELECT customer_id
FROM customers
WHERE lower(email) = lower('ALICE@example.test');
-- PostgreSQL-specific, documentation only; NOT executed in the lab:
-- CREATE INDEX CONCURRENTLY ... ON customers (lower(email));
```

A plain index on `email` is not generally equivalent to an expression index on `lower(email)`. An index adds storage, write amplification, build time, and operational ownership. Do not create one without approval and representative evidence. Locale/collation and Unicode rules can affect case folding.

### C. Avoid hiding the indexed column

```sql
-- For exact NUMERIC values in the lab:
WHERE amount + 5 > 25
-- Equivalent in this constrained example:
WHERE amount > 20
```

The algebra is safe for the synthetic `numeric` inputs, but not universally safe for every SQL type or expression. Integer overflow, implicit casts, rounding, NULL, and expression side effects matter. Always compare outputs.

### D. Read plans responsibly

```sql
EXPLAIN (COSTS ON)
SELECT event_id
FROM (VALUES (1, 10), (2, 20), (3, 30)) AS e(event_id, amount)
WHERE amount > 20;
```

This **estimated-only** example does not prove index use: inline `VALUES` has no persistent index or table statistics. In an approved isolated benchmark with representative indexed tables, compare `EXPLAIN (ANALYZE, BUFFERS)` for SELECT queries, actual versus estimated rows, buffer reads, execution times, and multiple runs. `EXPLAIN ANALYZE` executes statements; never apply it casually to DML. Cost units are not milliseconds.

## 4. Hands-on lab (30–50 minutes)

Use the disposable PostgreSQL 18 `sql_tutorials` database from [Chapter 003](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md). Do not connect with production credentials.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/097-index-friendly-predicates-rewrites.sql
```

The [lab](../labs/097-index-friendly-predicates-rewrites.sql) is read-only, guarded by PostgreSQL major version and database name, bounded by transaction-local timeouts, and ends in `ROLLBACK`. It contains synthetic data only, estimated plans, and bidirectional `EXCEPT ALL` assertions.

1. Predict IDs returned by the cast-to-date filter and the half-open range, including boundary events.
2. Execute the lab and compare the actual and expected multisets in both directions.
3. Explain why the inline plan cannot demonstrate an index scan even if the rewritten predicate is index-friendly.
4. Compare `lower(email)` equality with an unsafe case-sensitive rewrite. Why is the latter not an acceptable optimization?
5. For the numeric rewrite, verify NULL handling and boundary value 20. Explain why `>` must remain strict.
6. Draft an approval-ready tuning proposal: baseline query fingerprint, plan, row counts, existing index definition, data skew, workload/latency SLO, proposed rewrite, correctness checks, repeatable benchmark, monitoring, and rollback.

**Expected (reasoned):** 5 events; 3 events in the selected day (IDs 2,3,4), total 90; two case-insensitive matches in the separate synthetic email sample; numeric `amount > 20` returns IDs 3,4,5. The SQL file raises an exception if its equivalence or fixed expected-result assertions fail. These are not PostgreSQL runtime acceptance results.

## 5. Troubleshooting, guardrails and validation (50–55 minutes)

| Symptom | Check | Safe response |
|---|---|---|
| Sequential scan persists | Table size, selectivity, actual index definition, statistics, correlation, collation | Do not force index use; test on representative isolated workload |
| Date rewrite changes rows | `timestamp` vs `timestamptz`, session timezone, DST, inclusive/exclusive boundaries | Define business timezone and verify edge cases |
| Email matches change | Collation, normalization, case folding | Restore semantic equivalence; consider reviewed expression index |
| Query improves locally but regresses in service | Parameter distributions, plan caching, concurrency, I/O, data skew | Repeat tests and use monitored rollback |
| Assertion fails | Synthetic rows, duplicate multiplicity, NULL handling, `UNION` semantics | Stop; do not deploy rewrite |

**Production safeguards:** No index creation, DDL, statistics changes, or unbounded `EXPLAIN ANALYZE` in this lab. Do not run benchmark loads on production. An apparently faster rewrite is rejected if it changes output, duplicates, ordering guarantees, or security filters. Capture pre/post p50/p95/p99, query plan, rows, buffer reads, CPU/I/O, and error rates before approving a production change.

## 6. Review questions and answers (55–60 minutes)

1. **Why use `>= start AND < next_start`?** It expresses a precise half-open interval without guessing the last representable instant.
2. **Does a sargable predicate force an index scan?** No; the optimizer considers table size, selectivity, costs and statistics.
3. **Why is `email = 'alice@example.test'` not a drop-in replacement for `lower(email) = 'alice@example.test'`?** Case-insensitive and case-sensitive matching are not equivalent.
4. **What does `EXPLAIN` without `ANALYZE` show?** Planner estimates, not measured runtime.
5. **How do you prove two rewrites return the same rows?** Compare both directions with `EXCEPT ALL`, including duplicates and NULLs, and test representative boundary cases.
6. **Who approves a production index change?** Follow application/data-owner correctness review and DBRE/SRE change-management approval; assess locking, disk, write cost, monitoring and rollback.

## References

- [PostgreSQL 18 — Using EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html)
- [PostgreSQL 18 — Indexes on Expressions](https://www.postgresql.org/docs/18/indexes-expressional.html)
- [PostgreSQL 18 — Indexes and ORDER BY](https://www.postgresql.org/docs/18/indexes-ordering.html)
- [PostgreSQL 18 — Date/Time Types](https://www.postgresql.org/docs/18/datatype-datetime.html)
- [PostgreSQL 18 — Comparison Functions and Operators](https://www.postgresql.org/docs/18/functions-comparison.html)

**Publication is not runtime certification.** Independent editorial review, comprehensive static SQL/link QA and isolated PostgreSQL 18 execution with retained evidence remain pending.
