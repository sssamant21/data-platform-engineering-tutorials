# Chapter 013 — NULL Handling and SQL Three-Valued Logic

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: Chapter 012](012-and-or-not-and-boolean-precedence.md) · [Next: Chapter 014 (planned)](../MASTER-TOC.md)
>
> **Part 02 — Filtering, Sorting & Conditional Logic** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBRE/SRE
>
> **Status:** Authored/published. Targeted static inspection performed; independent editorial review, full SQL syntax verification and actual isolated PostgreSQL 18 runtime acceptance pending.

## Outcomes and agenda (0–5 minutes)

After this chapter, you can distinguish missing values from empty strings and zero; evaluate TRUE/FALSE/UNKNOWN; use `IS NULL`, `IS NOT NULL`, and `IS [NOT] DISTINCT FROM`; reason about `NOT IN` with NULL; and implement safe data-quality filters.

| Minutes | Activity |
|---|---|
| 0–5 | Prerequisites, safety and objectives |
| 5–15 | NULL semantics and truth tables |
| 15–30 | Worked queries and expected results |
| 30–50 | Hands-on read-only lab and exercises |
| 50–55 | Troubleshooting, portability and operational safeguards |
| 55–60 | Review questions with answers |

**Prerequisites:** [Chapter 009](../part-01-fundamentals/009-data-types-null-and-explicit-type-conversion.md), [Chapter 012](012-and-or-not-and-boolean-precedence.md), and [Chapter 003 lab setup](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md). Verify independently that the PostgreSQL 18 endpoint is a disposable sandbox; a database-name guard alone does not prove isolation.

## 1. Concepts and portable SQL (5–15 minutes)

`NULL` represents an absent/unknown value, **not** the number zero, Boolean FALSE, or an empty text value. Ordinary comparisons involving NULL (including `NULL = NULL` and `NULL <> 5`) yield **UNKNOWN**, not TRUE or FALSE. In a `WHERE` clause, only TRUE qualifies a row; FALSE and UNKNOWN do not.

| A | B | A AND B | A OR B |
|---|---|---|---|
| TRUE | UNKNOWN | UNKNOWN | TRUE |
| FALSE | UNKNOWN | FALSE | UNKNOWN |
| UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |

`NOT UNKNOWN` is UNKNOWN. Use `IS NULL` or `IS NOT NULL` to test presence. `COALESCE(x, fallback)` returns the first non-NULL expression but does **not** distinguish genuinely known fallback values from imputed ones; preserve the original NULL indicator when quality matters.

`IS DISTINCT FROM` is a null-safe comparison in PostgreSQL and the SQL standard: `NULL IS DISTINCT FROM NULL` is FALSE, while `NULL IS DISTINCT FROM 'paid'` is TRUE. `IS NOT DISTINCT FROM` provides null-safe equality. Other databases differ in support or syntax; check dialect documentation.

**Important anti-pattern:** `value NOT IN (1, NULL)` cannot evaluate TRUE for a nonmatching non-NULL value, because the NULL comparison is UNKNOWN. For a nullable exclusion set, explicitly remove NULLs or use a carefully correlated `NOT EXISTS` query. Also, `COUNT(*)` counts all rows while `COUNT(column)` counts non-NULL values.

## 2. Worked examples (15–30 minutes)

All examples use **synthetic, inline data**, so no persistent tables are needed. The linked lab repeats the examples and includes fail-closed checks.

### A. Identify missing statuses

```sql
WITH orders(order_id, status, amount) AS (
  VALUES (401, 'paid', 25.00::numeric),
         (402, NULL::text, 0.00::numeric),
         (403, 'pending', NULL::numeric),
         (404, '', 10.00::numeric),
         (405, 'paid', NULL::numeric),
         (406, NULL::text, 80.00::numeric)
)
SELECT order_id FROM orders
WHERE status IS NULL ORDER BY order_id;
-- Expected: 402, 406
```

`status = NULL` is incorrect: its result is UNKNOWN for every row. The empty string at order 404 is **not** NULL in PostgreSQL (Oracle treats empty character strings differently).

### B. Show UNKNOWN explicitly

```sql
SELECT NULL::text = 'paid' AS ordinary_equality,
       NULL::text IS NOT DISTINCT FROM NULL::text AS null_safe_equality,
       NULL::text IS DISTINCT FROM 'paid' AS null_safe_difference;
-- Expected: NULL (displayed blank by default in psql), TRUE, TRUE
```

### C. Compare NOT with a null-aware predicate

```sql
WITH orders(order_id, status) AS (
  VALUES (401, 'paid'::text), (402, NULL::text),
         (403, 'pending'::text), (404, ''::text),
         (405, 'paid'::text), (406, NULL::text)
)
SELECT order_id FROM orders
WHERE status IS DISTINCT FROM 'paid' ORDER BY order_id;
-- Expected: 402, 403, 404, 406
```

`WHERE NOT (status = 'paid')` returns **403, 404** only, excluding NULL statuses.

### D. Counts and fallback display

```sql
WITH amounts(amount) AS (
  VALUES (25.00::numeric), (0.00::numeric), (NULL::numeric),
         (10.00::numeric), (NULL::numeric), (80.00::numeric)
)
SELECT COUNT(*) AS all_rows, COUNT(amount) AS known_amounts,
       COUNT(*) - COUNT(amount) AS missing_amounts,
       SUM(amount) AS known_sum
FROM amounts;
-- Expected: 6 | 4 | 2 | 115.00
```

`SUM` ignores NULL inputs. `COALESCE(amount, 0)` may be useful for presentation, but it changes the meaning of an unknown amount and should not silently replace missing financial data.

### E. NOT IN hazard

```sql
SELECT 3 NOT IN (1, NULL) AS unsafe_result,
       3 NOT IN (1, 2) AS safe_result;
-- Expected: NULL | TRUE
```

A NULL in a subquery's exclusion column can cause the same issue. Check nullable keys and design anti-joins with explicit business semantics.

### F. Data-quality exception report

```sql
WITH orders(order_id, status, amount) AS (
  VALUES (401, 'paid', 25.00::numeric),
         (402, NULL::text, 0.00::numeric),
         (403, 'pending', NULL::numeric),
         (404, '', 10.00::numeric),
         (405, 'paid', NULL::numeric),
         (406, NULL::text, 80.00::numeric)
)
SELECT order_id,
       CASE WHEN status IS NULL THEN 'missing_status'
            WHEN status = '' THEN 'blank_status'
            WHEN amount IS NULL THEN 'missing_amount'
            ELSE 'ok' END AS quality_flag
FROM orders ORDER BY order_id;
-- Expected: 401 ok; 402 missing_status; 403 missing_amount;
--           404 blank_status; 405 missing_amount; 406 missing_status
```

The `CASE` order is intentional: a row can have multiple defects; this example assigns one prioritized label. A comprehensive quality pipeline should track independent flags.

## 3. Hands-on lab (30–50 minutes)

Use [013 SQL lab](../labs/013-null-three-valued-logic.sql). Confirm Docker points to your **isolated** PostgreSQL 18 sandbox, not a shared or production endpoint. Run:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/013-null-three-valued-logic.sql
```

The script opens `BEGIN READ ONLY`, checks database/version, runs examples and exact-result assertions, and ends with `ROLLBACK`. It creates no tables and uses no credentials in the file. A nonzero exit status means the exercise did not pass.

**Practice tasks:** (1) Change the missing-status filter to `IS NOT NULL` (expected IDs 401, 403, 404, 405). (2) Compare `status <> 'paid'` with `status IS DISTINCT FROM 'paid'` and explain the difference. (3) Add a `COUNT(amount)` and missing-value percentage to a reporting query; keep the denominator `COUNT(*)`. (4) Test `NOT IN (1, NULL)` and explain why no matching non-NULL candidate qualifies. (5) Design two independent quality flags rather than the prioritized `CASE` above.

**Acceptance criteria:** script exits zero, the environment assertion is 1, the final acceptance assertion is 1, and every expected ID set and count matches. These are *specified* outcomes, not claims of completed execution.

## 4. Troubleshooting, portability, and operational safety (50–55 minutes)

| Symptom | Likely cause | Safer response |
|---|---|---|
| `= NULL` returns no rows | UNKNOWN comparison | Use `IS NULL` |
| `NOT IN` unexpectedly returns none | Nullable exclusion list | Filter NULLs explicitly or use null-aware `NOT EXISTS` |
| Missing-value rate is understated | `COUNT(column)` excludes NULLs | Compare against `COUNT(*)` |
| Empty string appears missing | Dialect-specific semantics | Validate source-specific behavior |
| Fallback masks missing data | `COALESCE` conflates missing and actual zero | Retain separate missingness flag |
| Query fails environment assertion | Wrong DB/version or inaccessible server | Stop; verify isolated endpoint before rerun |

**Portable concepts:** `IS NULL`, `IS NOT NULL`, `COALESCE`, `CASE`, `COUNT`, `NOT IN` and three-valued logic are standard SQL concepts. **PostgreSQL-specific lab syntax:** `::type`, `BEGIN READ ONLY`, `current_database()`, `current_setting()`, and array comparisons. SQL standard `IS [NOT] DISTINCT FROM` is not uniformly implemented across vendors. Oracle empty-string behavior and MySQL's `<=>` null-safe equality differ from PostgreSQL.

**DBRE/SRE guardrails:** never interpret NULL as “inactive” without a data contract; quantify missingness before reconciliation; never run exploratory filters as a production `DELETE`/`UPDATE` predicate without review. Check row counts and sampled exception IDs before changing pipelines. The lab is read-only, but endpoint verification is still mandatory.

**Runtime evidence required before certification:** UTC timestamp, Git commit SHA and SQL hash, independently verified isolated host/container, PostgreSQL version and image digest, exact `psql` command, stdout/stderr, exit code, and reviewer sign-off.

## 5. Review questions with answers (55–60 minutes)

1. Is NULL the same as zero? **No.**
2. What does `NULL = NULL` return? **UNKNOWN.**
3. Which WHERE results retain rows? **TRUE only.**
4. What is `NOT UNKNOWN`? **UNKNOWN.**
5. How do you find missing statuses? **`status IS NULL`.**
6. Does `COUNT(status)` include NULLs? **No.**
7. What does `COUNT(*)` include? **All rows.**
8. Why can `NOT IN` be hazardous? **A NULL in its comparison set can produce UNKNOWN for nonmatches.**
9. What is null-safe equality in PostgreSQL? **`IS NOT DISTINCT FROM`.**
10. Why keep a missingness flag with COALESCE? **To avoid confusing imputed values with observed values.**

## References and next chapter

- [PostgreSQL 18 comparison functions and NULL semantics](https://www.postgresql.org/docs/18/functions-comparison.html)
- [PostgreSQL 18 logical operators](https://www.postgresql.org/docs/18/functions-logical.html)
- [PostgreSQL 18 conditional expressions](https://www.postgresql.org/docs/18/functions-conditional.html)
- [PostgreSQL 18 aggregate functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [Chapter 014 — IN, BETWEEN, and range predicates (planned)](../MASTER-TOC.md)
