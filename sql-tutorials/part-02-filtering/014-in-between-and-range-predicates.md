# Chapter 014 — IN, BETWEEN, and Range Predicates

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: Chapter 013](013-null-handling-and-sql-three-valued-logic.md) · [Next: Chapter 015 (planned)](../MASTER-TOC.md)
>
> **Part 02 — Filtering, Sorting & Conditional Logic** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBRE/SRE
>
> **Status:** Authored/published; targeted static inspection only. Independent editorial review, comprehensive SQL syntax checks, and actual isolated PostgreSQL 18 runtime acceptance pending.

## Learning objectives and schedule (0–5 minutes)

After completing this chapter, you can use `IN`, `NOT IN`, `BETWEEN`, and explicit inequalities; identify inclusive versus exclusive boundaries; avoid NULL traps; build safe timestamp windows; and reconcile expected record IDs before operational use.

| Time | Activity |
|---|---|
| 0–5 min | Prerequisites, goals, and sandbox verification |
| 5–15 min | Membership and range semantics |
| 15–30 min | Six worked examples and expected results |
| 30–50 min | Read-only PostgreSQL 18 lab and independent exercises |
| 50–55 min | Troubleshooting, portability, and DBRE/SRE safeguards |
| 55–60 min | Review questions and answer key |

**Prerequisites:** [Chapter 011](011-where-and-comparison-operators.md), [Chapter 013](013-null-handling-and-sql-three-valued-logic.md), and [Chapter 003 setup](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md). The lab uses only synthetic inline rows; no persistent objects are required. Verify the database endpoint is an isolated disposable PostgreSQL 18 environment before running anything. A database-name check alone cannot establish isolation.

## 1. Concepts (5–15 minutes)

`x IN (a,b,c)` asks whether `x` equals at least one member. It is equivalent to `x=a OR x=b OR x=c` for ordinary scalar comparisons, including SQL's three-valued logic. `NOT IN` negates that result. **Beware:** if the list contains NULL and no member matches, the result is UNKNOWN rather than TRUE. `WHERE` retains only TRUE.

`x BETWEEN low AND high` is inclusive at **both** ends: it is equivalent to `x >= low AND x <= high` for these ordinary scalar comparisons. `NOT BETWEEN` negates the result. If an operand is NULL, results follow three-valued logic; do not assume every such expression is UNKNOWN, because FALSE/TRUE can sometimes be determined from the other comparison. Reversed bounds (`BETWEEN 100 AND 50`) match no non-NULL numbers; do not expect SQL to swap them.

For event timestamps, prefer a **half-open** window: `event_ts >= start_ts AND event_ts < end_ts`. It includes the beginning and excludes the end, preventing overlap between adjacent daily partitions. Avoid `BETWEEN '2026-11-01' AND '2026-11-02'` when the intention is to include the *entire* second day; a midnight upper bound excludes later events on that day.

**Portability:** `IN`, `NOT IN`, `BETWEEN`, `NOT BETWEEN`, `AND`, and `OR` are widely supported standard SQL. PostgreSQL-specific syntax in this lab includes `::type`, `timestamp '...'` literals as used here, `BEGIN READ ONLY`, `current_database()`, `current_setting()`, and array assertions. Timestamp-literal and timezone behavior must be verified per vendor. In PostgreSQL, `timestamp without time zone` does not encode an offset; real pipelines should establish a UTC/timestamptz contract.

## 2. Worked examples (15–30 minutes)

All examples use the same fictional events:

| event_id | category | amount | event_ts | Meaning |
|---:|---|---:|---|---|
| 501 | payment | 25 | 2026-11-01 00:00 | lower boundary |
| 502 | refund | 50 | 2026-11-01 12:30 | inside day |
| 503 | payment | 75 | 2026-11-01 23:59:59 | end of day |
| 504 | adjustment | 100 | 2026-11-02 00:00 | next-day boundary |
| 505 | NULL | 125 | 2026-11-02 08:00 | missing category |
| 506 | payment | NULL | 2026-11-03 00:00 | missing amount |

### A. Membership list

```sql
WITH events(event_id, category) AS (
  VALUES (501,'payment'::text),(502,'refund'::text),
         (503,'payment'::text),(504,'adjustment'::text),
         (505,NULL::text),(506,'payment'::text)
)
SELECT event_id FROM events
WHERE category IN ('payment','refund') ORDER BY event_id;
-- Expected: 501, 502, 503, 506
```

### B. NULL-safe exclusion

```sql
SELECT 7 NOT IN (1, NULL) AS unsafe_exclusion,
       7 NOT IN (1, 2) AS known_exclusion;
-- Expected: NULL (UNKNOWN), TRUE
```

If NULL category should count as an exception, express that contract explicitly: `category NOT IN ('payment','refund') OR category IS NULL`. On the six-row data, expected IDs are **504, 505**. If NULL means “unknown; investigate,” do not silently classify it as an ordinary category.

### C. Inclusive numeric range

```sql
WITH amounts(event_id,amount) AS (
  VALUES (501,25::numeric),(502,50::numeric),(503,75::numeric),
         (504,100::numeric),(505,125::numeric),(506,NULL::numeric)
)
SELECT event_id FROM amounts
WHERE amount BETWEEN 50 AND 100 ORDER BY event_id;
-- Expected: 502, 503, 504 (both endpoints included)
```

### D. Exclusive numeric range

```sql
WITH amounts(event_id,amount) AS (
  VALUES (501,25::numeric),(502,50::numeric),(503,75::numeric),
         (504,100::numeric),(505,125::numeric),(506,NULL::numeric)
)
SELECT event_id FROM amounts
WHERE amount > 50 AND amount < 100 ORDER BY event_id;
-- Expected: 503
```

### E. Half-open day window

```sql
WITH events(event_id,event_ts) AS (
  VALUES (501,timestamp '2026-11-01 00:00:00'),
         (502,timestamp '2026-11-01 12:30:00'),
         (503,timestamp '2026-11-01 23:59:59'),
         (504,timestamp '2026-11-02 00:00:00')
)
SELECT event_id FROM events
WHERE event_ts >= timestamp '2026-11-01 00:00:00'
  AND event_ts <  timestamp '2026-11-02 00:00:00'
ORDER BY event_id;
-- Expected: 501, 502, 503; 504 belongs to the next day
```

### F. Two adjacent windows and reconciliation

The Nov 1 window returns **501, 502, 503**; the Nov 2 window returns **504, 505** (assuming the full six-row dataset). The windows are disjoint: no boundary event belongs to both. This matters for daily ingestion checkpoints, retention filters, and reconciliation reports.

## 3. Hands-on lab (30–50 minutes)

Run [Chapter 014 SQL lab](../labs/014-in-between-range-predicates.sql) from the repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/014-in-between-range-predicates.sql
```

**Before execution:** independently confirm host/container identity and PostgreSQL 18, and use an isolated training database. The script opens a read-only transaction, checks version/database, performs synthetic queries, and fails on mismatched expected results. It ends with `ROLLBACK`. The lab contains no DDL, DML, or production credentials.

**Practice (20 minutes):**

1. Change the category membership list to only `'payment'`. Expected IDs: **501, 503, 506**.
2. Change `BETWEEN 50 AND 100` to `BETWEEN 100 AND 50`. Expected: **zero rows**.
3. Write a range `amount >= 75 AND amount < 125`. Expected IDs: **503, 504**.
4. Use `NOT BETWEEN 50 AND 100`. Expected IDs: **501, 505**; NULL amount at 506 is not included.
5. Construct the Nov 2 half-open window. Expected IDs: **504, 505**.
6. Predict `'refund' NOT IN ('payment',NULL)`. Expected: **UNKNOWN**.

**Acceptance:** the SQL lab returns an environment assertion of 1 and a final acceptance assertion of 1; its process exits zero; IDs and counts match the expectations. These are specified outcomes, **not evidence of actual execution**.

## 4. Troubleshooting and production safeguards (50–55 minutes)

| Symptom | Cause | Safe action |
|---|---|---|
| Last day missing from report | Inclusive date bound cast to midnight timestamp | Use half-open timestamp window |
| Same boundary record appears in two daily batches | Both windows include shared endpoint | Use `>= start AND < end` |
| `NOT IN` unexpectedly excludes many rows | NULL in exclusion set | Use explicit NULL policy or vetted `NOT EXISTS` |
| NULL amounts vanish from range report | Comparison evaluates UNKNOWN | Report missingness separately |
| Reversed bounds return no matches | `BETWEEN` does not reorder endpoints | Validate parameter ordering |
| Day counts change across systems | Timezone/type mismatch | Normalize UTC and inspect timestamp types |
| Lab guard fails | Wrong database/version | Stop; verify isolated endpoint |

**DBRE/SRE practices:** never reuse exploratory predicates directly in production `DELETE` or `UPDATE`; preview exact counts, boundary records, NULL rates, and representative IDs. For partition pruning and index-friendly filtering, prefer direct comparisons on the indexed timestamp column over wrapping it in a function; confirm plans with `EXPLAIN` in a safe environment. Validate timezone, daylight-saving behavior, and source-to-target inclusive/exclusive contracts before migrating ETL pipelines. A read-only transaction is a defense in depth, not permission to connect to production.

**Runtime evidence required for certification:** UTC time, Git commit and lab SHA, independent sandbox/container identity, PostgreSQL 18 server version/image digest, exact command, complete stdout/stderr, exit code, and reviewer approval.

## 5. Review questions with answers (55–60 minutes)

1. Is `BETWEEN 50 AND 100` inclusive? **Yes, both endpoints.**
2. How do you express an exclusive numeric interval? **`x > low AND x < high`.**
3. Why use half-open timestamp windows? **Adjacent windows do not double-count boundary events.**
4. Does `NOT IN (1,NULL)` return TRUE for 7? **No; UNKNOWN.**
5. Does `IN` match a NULL using `NULL` in the list? **No; use `IS NULL`.**
6. What happens with reversed numeric bounds? **No non-NULL matches in this example.**
7. Does `NOT BETWEEN` include NULL amounts? **No; NULL comparison is UNKNOWN here.**
8. Which events are on Nov 1 in the example? **501, 502, 503.**
9. Why avoid `DATE(event_ts)` in a large filtering query? **It can make index/partition access less efficient; direct range predicates are often preferable.**
10. What must happen before runtime certification? **Execute on isolated PostgreSQL 18 and retain reproducible evidence.**

## References

- [PostgreSQL 18 comparison functions and BETWEEN](https://www.postgresql.org/docs/18/functions-comparison.html)
- [PostgreSQL 18 row and array comparisons, IN/NOT IN](https://www.postgresql.org/docs/18/functions-comparisons.html)
- [PostgreSQL 18 date/time types](https://www.postgresql.org/docs/18/datatype-datetime.html)
- [PostgreSQL 18 transaction commands](https://www.postgresql.org/docs/18/sql-begin.html)
- [Chapter 015 — LIKE, wildcard matching, and ILIKE (planned)](../MASTER-TOC.md)
