# Chapter 019 — CASE, COALESCE, and NULLIF

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: 018](018-limit-offset-fetch-and-top-across-dialects.md) · [Next: 020 (planned)](../MASTER-TOC.md)
>
> **Part 02 — Filtering, Sorting & Conditional Logic** · **60 minutes** · **PostgreSQL 18 lab target**
>
> **Status:** Authored/published; targeted static reasoning only. Independent editorial review, comprehensive syntax checks and isolated PostgreSQL 18 runtime validation pending.

## Learning outcomes, prerequisites and schedule (0–5 minutes)

By the end, you can classify records with searched and simple `CASE`, supply fallback values with `COALESCE`, prevent division by zero with `NULLIF`, and distinguish missing data from business defaults. You can explain the impact of these expressions on reporting, alerting, data quality and index use.

Prerequisites: [NULL logic (013)](013-null-handling-and-sql-three-valued-logic.md), [Boolean precedence (012)](012-and-or-not-and-boolean-precedence.md), [sorting (017)](017-order-by-and-deterministic-sorting.md), and [isolated lab setup (003)](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md).

| Time | Activity |
|---|---|
| 0–5 | Outcomes, prerequisites, safety |
| 5–15 | Syntax, NULL semantics, type resolution |
| 15–30 | Worked operational examples |
| 30–50 | Read-only SQL lab and practice |
| 50–55 | Troubleshooting and production safeguards |
| 55–60 | Review questions and answers |

## Concepts and portable syntax (5–15 minutes)

**Searched CASE** evaluates predicates in order and returns the result for the first predicate that is TRUE; FALSE and UNKNOWN do not match. **Simple CASE** compares one expression with successive values. Always include `ELSE` when a missing match must be visible; omitting it yields NULL. A simple CASE `WHEN NULL` does not match a NULL expression; use searched `CASE WHEN col IS NULL`.

```sql
CASE WHEN severity = 1 THEN 'critical'
     WHEN severity = 2 THEN 'warning'
     ELSE 'other' END

CASE status WHEN 'ok' THEN 'healthy'
            WHEN 'down' THEN 'unavailable'
            ELSE 'unknown' END
```

`COALESCE(a,b,c)` returns the first **non-NULL** expression; it does not replace empty strings or zero. `NULLIF(a,b)` returns NULL when `a = b` is TRUE; otherwise it returns `a`. Both are standard SQL expressions supported in PostgreSQL 18 and major SQL platforms. Their arguments must have compatible types under the target database's type-resolution rules. Use explicit casts where needed.

```sql
COALESCE(owner_team, 'unassigned')
NULLIF(request_count, 0)
```

A NULL denominator can be used to produce NULL rather than an error: `errors::numeric / NULLIF(request_count,0)` is PostgreSQL syntax because `::numeric` is vendor-specific; portable SQL uses `CAST(errors AS DECIMAL(12,2)) / NULLIF(request_count,0)`. **Important:** NULL means “rate unavailable,” not “zero errors.” If your report chooses a zero fallback, document the business meaning.

PostgreSQL usually evaluates only necessary CASE/COALESCE branches at execution, but planning-time constant folding and aggregate evaluation can still raise errors before CASE protects them. Do not treat CASE as a universal exception handler or a guarantee of evaluation order for arbitrary expressions. See PostgreSQL conditional-expression documentation.

## Worked examples (15–30 minutes)

All rows are invented operational observations:

| event_id | service | severity | owner_team | requests | errors |
|---:|---|---:|---|---:|---:|
| 301 | api | 1 | platform | 100 | 5 |
| 302 | billing | 2 | NULL | 0 | 0 |
| 303 | ingest | NULL | data | 50 | 2 |
| 304 | api | 3 | NULL | 20 | 0 |
| 305 | search | 1 | sre | NULL | 1 |
| 306 | billing | 2 | app | 40 | NULL |

### A. Classify severity, including missing values

```sql
WITH events(event_id,severity) AS
 (VALUES (301,1),(302,2),(303,NULL::integer),(304,3),(305,1),(306,2))
SELECT event_id,
 CASE WHEN severity IS NULL THEN 'unclassified'
      WHEN severity = 1 THEN 'critical'
      WHEN severity = 2 THEN 'warning'
      ELSE 'informational' END AS priority
FROM events ORDER BY event_id;
```

**Expected:** 301 critical; 302 warning; 303 unclassified; 304 informational; 305 critical; 306 warning. PostgreSQL's `NULL::integer` is vendor-specific; use `CAST(NULL AS INTEGER)` for portable SQL.

### B. Display fallback owners without altering source values

```sql
WITH events(event_id,owner_team) AS
 (VALUES (301,'platform'),(302,NULL),(303,'data'),(304,NULL))
SELECT event_id, COALESCE(owner_team,'unassigned') AS display_owner
FROM events ORDER BY event_id;
-- Expected: platform, unassigned, data, unassigned.
```

A display fallback does **not** fix missing ownership. Keep separate data-quality metrics for `owner_team IS NULL`. `COALESCE(owner_team,'')` may conceal missing ownership in dashboards.

### C. Safe error-rate computation

```sql
WITH events(event_id,requests,errors) AS
 (VALUES (301,100,5),(302,0,0),(303,50,2),(304,20,0),
         (305,NULL::integer,1),(306,40,NULL::integer))
SELECT event_id,
 ROUND(100.0 * errors / NULLIF(requests,0),2) AS error_pct
FROM events ORDER BY event_id;
-- Expected: 5.00, NULL, 4.00, 0.00, NULL, NULL.
```

The `100.0` literal ensures noninteger arithmetic in PostgreSQL. For strict portability, cast to an appropriate DECIMAL type. The final NULL for event 306 is due to unknown errors, not zero requests. Do not silently convert it to 0%.

### D. Detect unknown and zero separately

```sql
WITH events(event_id,requests) AS (VALUES (301,100),(302,0),(305,NULL::integer))
SELECT event_id,
 CASE WHEN requests IS NULL THEN 'missing'
      WHEN requests = 0 THEN 'zero'
      ELSE 'positive' END AS volume_status
FROM events ORDER BY event_id;
-- Expected: 301 positive, 302 zero, 305 missing.
```

**Data engineering:** In an ELT pipeline, preserve original nullable values and publish a derived status column rather than overwriting missing data. **DBRE/SRE:** Classify alert records explicitly so a NULL metric does not accidentally fall into the healthy bucket.

## Hands-on lab (30–50 minutes)

Use [Chapter 019 SQL lab](../labs/019-case-coalesce-nullif.sql) only on an **independently confirmed disposable PostgreSQL 18** database called `sql_tutorials`. The database-name/version assertion is an additional safeguard, not proof that a database is disposable.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/019-case-coalesce-nullif.sql
```

The lab is a read-only transaction with synthetic inline `VALUES`, a local statement timeout, explicit assertions and `ROLLBACK`. **Expected (not observed)** output: `environment_assertion = 1` and `acceptance_assertion = 1`; the six ordered result rows should match examples A–C. A failed assertion causes division by zero and, with `ON_ERROR_STOP=1`, exits nonzero.

**Practice tasks (solutions):**

1. Mark severity 1 as `P1`, 2 as `P2`, everything else as `other`. **Answer:** `CASE WHEN severity=1 THEN 'P1' WHEN severity=2 THEN 'P2' ELSE 'other' END`; NULL becomes other unless separately handled.
2. Treat NULL severity as `missing`. **Answer:** add `WHEN severity IS NULL THEN 'missing'` before the numeric checks.
3. Display missing owner as `unassigned`. **Answer:** `COALESCE(owner_team,'unassigned')`.
4. Count missing owners. **Answer:** `COUNT(*) FILTER (WHERE owner_team IS NULL)` in PostgreSQL; portable alternative `SUM(CASE WHEN owner_team IS NULL THEN 1 ELSE 0 END)`. Expected: 2.
5. Compute rate for event 302. **Answer:** NULL, because denominator is zero.
6. Compute rate for event 304. **Answer:** 0.00%.
7. Explain event 306's NULL rate. **Answer:** errors are missing; do not assume zero.
8. Replace a zero denominator with NULL. **Answer:** `NULLIF(requests,0)`.
9. Why is `CASE severity WHEN NULL THEN ...` wrong? **Answer:** NULL is not equal to NULL.
10. How do you get a portable numeric cast? **Answer:** `CAST(errors AS DECIMAL(12,2))`.

## Troubleshooting and safeguards (50–55 minutes)

| Symptom | Cause | Safe resolution |
|---|---|---|
| Missing values unexpectedly become 'other' | NULL comparison is UNKNOWN | Add explicit `IS NULL` branch |
| Division by zero | Unprotected zero denominator | Use `NULLIF(denominator,0)` |
| Error rate is NULL | Missing numerator/denominator or zero denominator | Track distinct data-quality causes |
| CASE type mismatch | Incompatible result branch types | Use explicit compatible casts |
| COALESCE still returns blank | Empty string is not NULL in PostgreSQL | Decide whether `NULLIF(TRIM(col),'')` fits the business rule |
| CASE fails to prevent constant error | Planning-time simplification | Avoid invalid constants; do not use CASE as exception handling |
| Query plan changes after wrapping indexed column | Expression may inhibit ordinary index matching | Test with safe EXPLAIN in isolation; avoid blanket rewrites |

**Safety:** Never execute lab SQL with production credentials or against a production database. Do not alter tables, roles, or indexes. Confirm isolation before running; use `psql -X -v ON_ERROR_STOP=1` so assertion failures are not ignored. For data pipelines, keep raw NULLs, document any imputation, validate numeric precision, and add data-quality checks. For monitoring, separate “zero,” “unknown,” and “not applicable” rather than assigning the same severity.

## Review questions and answers (55–60 minutes)

1. What does CASE return if no WHEN matches and ELSE is absent? **NULL.**
2. Which WHEN wins if multiple searched predicates are true? **The first matching WHEN.**
3. Does `severity = NULL` detect missing values? **No; use IS NULL.**
4. What does COALESCE return? **The first non-NULL argument.**
5. Does COALESCE replace empty strings in PostgreSQL? **No.**
6. What does `NULLIF(0,0)` return? **NULL.**
7. What does `NULLIF(5,0)` return? **5.**
8. Does a NULL rate imply zero errors? **No.**
9. Is `::numeric` portable SQL? **No; use CAST for portability.**
10. Does publishing the SQL lab prove runtime correctness? **No; isolated PostgreSQL 18 execution with retained evidence is required.**

## References and next chapter

- [PostgreSQL 18 — Conditional Expressions](https://www.postgresql.org/docs/18/functions-conditional.html)
- [PostgreSQL 18 — Type Conversion](https://www.postgresql.org/docs/18/typeconv.html)
- [PostgreSQL 18 — Comparison Functions and NULL](https://www.postgresql.org/docs/18/functions-comparison.html)
- [PostgreSQL 18 — psql](https://www.postgresql.org/docs/18/app-psql.html)
- [Next: 020 — Lab 02, filter and rank operational records (planned)](../MASTER-TOC.md)
