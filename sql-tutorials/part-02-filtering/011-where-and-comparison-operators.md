# Chapter 011 — WHERE and Comparison Operators

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: Chapter 010](../part-01-fundamentals/010-lab-01-explore-sample-database-and-write-first-queries.md) · Next: Chapter 012 — AND, OR, NOT, and Boolean Precedence (planned)
>
> **Part 02:** Filtering, Sorting & Conditional Logic · **Duration:** 60 minutes · **Audience:** SQL beginners, data engineers, DBRE/SRE · **Target lab:** isolated PostgreSQL 18
>
> **Status:** Authored/published; targeted static review only. Independent editorial review, comprehensive syntax review, and actual PostgreSQL 18 runtime validation pending.

## Learning objectives and agenda (0–5 minutes)

By the end you can (1) filter rows using `WHERE`; (2) distinguish `=`, `<>`, `<`, `<=`, `>`, and `>=`; (3) explain why `NULL` requires `IS NULL`; (4) write safe date and numeric predicates; (5) verify row counts and boundary conditions before using filters in data pipelines.

| Minutes | Focus | Evidence |
|---|---|---|
| 0–5 | Prerequisites and outcomes | Confirm isolated lab target |
| 5–15 | Syntax and comparison semantics | Predict which rows qualify |
| 15–30 | Worked examples | Match expected IDs |
| 30–50 | Guided PostgreSQL 18 lab | Execute SELECTs and assertions |
| 50–55 | Troubleshooting and operational safety | Explain failed predicates |
| 55–60 | Review questions | Compare with answer key |

**Prerequisites:** [Chapter 007 SELECT](../part-01-fundamentals/007-select-fundamentals-retrieve-rows-and-columns.md), [Chapter 009 types and NULL](../part-01-fundamentals/009-data-types-null-and-explicit-type-conversion.md), and [Chapter 003 lab setup](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md). Use only a disposable PostgreSQL 18 database named `sql_tutorials`. The name/version check in the lab is an additional guard, **not proof that an endpoint is non-production**.

## 1. Core concepts (5–15 minutes)

A `WHERE` predicate filters **input rows** before projection and grouping in the conceptual SQL query-processing model. A row is returned only if the predicate evaluates to **TRUE**. FALSE and UNKNOWN are both excluded.

```sql
SELECT order_id, amount
FROM orders
WHERE amount >= 100.00
ORDER BY order_id;
```

The `orders` relation above is illustrative; the executable lab below supplies it as an in-query `WITH ... VALUES` dataset. The `ORDER BY` makes the presentation deterministic.

| Operator | Meaning | Example | Portable? |
|---|---|---|---|
| `=` | equal | `status = 'paid'` | Yes |
| `<>` | not equal | `status <> 'paid'` | Yes |
| `<` | less than | `amount < 100` | Yes |
| `<=` | less than or equal | `amount <= 100` | Yes |
| `>` | greater than | `amount > 100` | Yes |
| `>=` | greater than or equal | `amount >= 100` | Yes |
| `IS NULL` | missing/unknown value | `status IS NULL` | Yes |
| `IS NOT NULL` | present value | `status IS NOT NULL` | Yes |

Use `<>` for portable inequality; PostgreSQL also accepts `!=`, but it is not the SQL-standard spelling. Use `DATE '2026-11-03'` for an explicitly typed SQL date; dialect support and implicit conversion rules vary. Avoid comparing a timestamp to a date without considering timezone and midnight boundaries. A half-open timestamp interval (`>= start AND < end`) will be developed in Chapter 014. Use `NUMERIC` for exact illustrative money-like values; actual financial systems also need currency and rounding policies.

### Sample rows

| order_id | customer | amount | status | order_date |
|---:|---|---:|---|---|
| 201 | Ava | 50.00 | paid | 2026-11-01 |
| 202 | Ben | 100.00 | pending | 2026-11-02 |
| 203 | Ava | 150.00 | paid | 2026-11-03 |
| 204 | Chen | 100.00 | NULL | 2026-11-04 |
| 205 | Ben | 0.00 | cancelled | 2026-11-05 |
| 206 | Chen | 200.00 | paid | 2026-11-06 |

Every record is fictional. The lab uses a CTE; it does not create or modify tables.

## 2. Worked examples (15–30 minutes)

### A. Exact match

```sql
WITH orders(order_id, amount, status) AS (
 VALUES (201,50.00::numeric,'paid'),
        (202,100.00::numeric,'pending'),
        (203,150.00::numeric,'paid'),
        (204,100.00::numeric,NULL),
        (205,0.00::numeric,'cancelled'),
        (206,200.00::numeric,'paid')
)
SELECT order_id FROM orders
WHERE status = 'paid'
ORDER BY order_id;
```

Expected: **201, 203, 206**. The `::numeric` cast is PostgreSQL syntax; portable alternatives use `CAST(value AS DECIMAL(10,2))`.

### B. Numeric boundaries

Change the final SELECT above to `SELECT order_id FROM orders WHERE amount >= 100 ORDER BY order_id;`. Expected: **202, 203, 204, 206**. The value 100 qualifies for `>=` but not `>`; zero does not qualify. For `amount > 100`, expected **203, 206**.

### C. Not equal and NULL

`WHERE status <> 'paid'` returns **202, 205** — not 204. The comparison with a NULL status evaluates to UNKNOWN, not TRUE. `WHERE status IS NULL` returns **204**. Do not assume that inequality includes missing values.

### D. Date comparison

```sql
WITH orders(order_id, order_date) AS (
 VALUES (201,DATE '2026-11-01'),(202,DATE '2026-11-02'),
        (203,DATE '2026-11-03'),(204,DATE '2026-11-04'),
        (205,DATE '2026-11-05'),(206,DATE '2026-11-06')
)
SELECT order_id FROM orders
WHERE order_date < DATE '2026-11-04'
ORDER BY order_id;
```

Expected: **201, 202, 203**. The boundary date itself is excluded.

### E. Filter vs projection

`SELECT order_id FROM orders WHERE amount = 100` returns two rows (202, 204), even though `amount` is not projected. Filtering does not require displaying the compared column.

## 3. Guided lab (30–50 minutes)

Use [011-where-comparison-operators.sql](../labs/011-where-comparison-operators.sql). First inspect the connection target and confirm the Docker instance is disposable. From the repository root:

```powershell
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/011-where-comparison-operators.sql
```

The script starts a read-only transaction, verifies PostgreSQL major version 18 and database name, runs six deterministic queries, and fails closed if its acceptance checks do not match expected results. It ends with `ROLLBACK`.

1. Exact paid-status match: IDs **201, 203, 206**.
2. Inclusive amount threshold `>= 100`: IDs **202, 203, 204, 206**.
3. Strict threshold `> 100`: IDs **203, 206**.
4. Inequality `<> 'paid'`: IDs **202, 205**; NULL excluded.
5. NULL status: ID **204**.
6. Date before November 4: IDs **201, 202, 203**.
7. Acceptance: `acceptance_assertion = 1` and `ROLLBACK` without SQL errors.

**Practice:** Predict results for `amount <= 100` (**201, 202, 204, 205**) and `status IS NOT NULL` (**201, 202, 203, 205, 206**). Change only a disposable copy of the lab to verify. For a data-quality check, calculate the number of orders with NULL status (expected **1**). Do not confuse missing status with an explicitly cancelled order.

**Runtime evidence required for certification:** retain UTC timestamp, script SHA/commit, exact command, verified isolated Docker endpoint, `SELECT version()`, stdout/stderr, exit code, and any remediation. Expected outputs printed in a tutorial are **not** execution evidence.

## 4. Troubleshooting, portability, and DBRE/SRE guardrails (50–55 minutes)

| Symptom | Likely cause | Safe diagnostic |
|---|---|---|
| No rows for `status = NULL` | NULL comparison is UNKNOWN | Use `IS NULL` |
| Missing 204 from `status <> 'paid'` | NULL is excluded | Handle missingness explicitly |
| 100-value row absent | Used `>` rather than `>=` | Review inclusive boundary |
| Date filter gives wrong rows | Text/date implicit conversion | Use explicit DATE literal or CAST |
| Unexpected row order | No ORDER BY | Sort on stable ID |
| Version guard fails | Wrong server/database | Stop; verify local disposable endpoint |
| Query unexpectedly slow on real data | Low-selectivity filter or missing suitable access path | Investigate EXPLAIN in approved environment; never run an unbounded experiment in production |

**Data engineering:** explicit boundary predicates are essential for incremental extracts, reconciliation windows, and avoiding missing/duplicate records. **DBRE/SRE:** a `WHERE` clause is not a safety guarantee for write statements; production changes require change control, preview counts, transaction/rollback planning, and verified scope. This chapter runs **SELECT only**. Never use production credentials or sensitive datasets. Do not extrapolate tiny CTE performance to production tables.

**Portability:** `SELECT`, `WHERE`, comparison operators, `IS NULL`, and `ORDER BY` are broadly portable. The lab's `::numeric`, `current_database()`, `current_setting()`, `BEGIN READ ONLY`, and environment assertion are PostgreSQL-specific. Vendor collation, implicit casting, Boolean handling, and date/time semantics may differ.

## 5. Review and answers (55–60 minutes)

1. When does `WHERE` keep a row? **Only when its predicate is TRUE.**
2. Difference between `>` and `>=`? **The latter includes the boundary.**
3. Portable not-equal operator? **`<>`.**
4. Does `NULL <> 'paid'` evaluate TRUE? **No, UNKNOWN.**
5. How do you find missing status? **`status IS NULL`.**
6. Why add `ORDER BY`? **To guarantee displayed row ordering.**
7. What qualifies for `amount = 100`? **Orders 202 and 204.**
8. Why avoid production for this lab? **Even read-only examples can use resources or expose data; isolated execution is required.**

## References and navigation

- [PostgreSQL 18 SELECT / WHERE](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 comparison functions and operators](https://www.postgresql.org/docs/18/functions-comparison.html)
- [PostgreSQL 18 value expressions](https://www.postgresql.org/docs/18/sql-expressions.html)
- [PostgreSQL 18 date/time types](https://www.postgresql.org/docs/18/datatype-datetime.html)
- [PostgreSQL 18 psql](https://www.postgresql.org/docs/18/app-psql.html)

**Next: Chapter 012 — AND, OR, NOT, and Boolean Precedence.** That chapter builds compound predicates on this foundation.
