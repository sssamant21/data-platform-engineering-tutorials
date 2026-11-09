# Chapter 015 — LIKE, Wildcard Matching, and Dialect-Specific ILIKE

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: Chapter 014](014-in-between-and-range-predicates.md) · [Next: Chapter 016 (planned)](../MASTER-TOC.md)
>
> **Part 02 — Filtering, Sorting & Conditional Logic** · **60 minutes** · **PostgreSQL 18 lab target**
>
> **Status:** Authored/published; targeted static review only. Independent editorial review, comprehensive syntax checks, and isolated PostgreSQL 18 runtime validation pending.

## Learning objectives and 60-minute agenda (0–5 min)

By the end, explain the difference between exact equality and pattern matching; use `LIKE`, `NOT LIKE`, `%`, and `_`; escape literal wildcard characters; distinguish PostgreSQL `ILIKE` from portable SQL; reason about NULLs and case sensitivity; and diagnose pattern-based operational filters.

| Minutes | Activity |
|---|---|
| 0–5 | Prerequisites, learning objectives, sandbox identity |
| 5–15 | Syntax, wildcards, NULL, portability |
| 15–30 | Worked examples and expected outputs |
| 30–50 | Read-only lab and practice |
| 50–55 | Troubleshooting, query safety, performance |
| 55–60 | Review questions and answer key |

**Prerequisites:** [Chapter 011](011-where-and-comparison-operators.md), [Chapter 013](013-null-handling-and-sql-three-valued-logic.md), [Chapter 014](014-in-between-and-range-predicates.md), and [PostgreSQL 18 lab setup](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md). Confirm that your endpoint is a disposable, isolated PostgreSQL 18 instance. A database name or version check alone does not prove isolation.

## Concepts (5–15 min)

**Portable SQL:** `column LIKE 'A%'` matches strings beginning with `A`; `%` matches zero or more characters; `_` matches exactly one character. A `LIKE` pattern is anchored to the entire string: `'alpha' LIKE 'ph%'` is FALSE, while `'alpha' LIKE '%ph%'` is TRUE. `NOT LIKE` negates the predicate. If the input is NULL, the predicate evaluates to UNKNOWN; `WHERE` does not retain UNKNOWN rows.

`LIKE` case sensitivity and collation behavior vary across systems. PostgreSQL's `ILIKE` is a **nonstandard PostgreSQL extension** for case-insensitive pattern matching according to the active locale; do not assume all engines support it or that locale/collation results are identical. Portable `LOWER(column) LIKE LOWER(pattern)` is a common alternative but may affect index usage and still depends on collation and Unicode rules. SQL Server, MySQL, SQLite, BigQuery, Snowflake, and Oracle differ in case behavior and available operators; validate with test data on each target.

To search for literal `%` or `_`, define an explicit escape character, e.g. `LIKE '%!%%' ESCAPE '!'` for strings containing a percent sign and `LIKE '%!_%' ESCAPE '!'` for underscores. `ESCAPE` is standard-style syntax, but support and defaults vary. Use parameters for user-supplied patterns; escaping SQL string literals and escaping LIKE wildcards are separate problems.

## Synthetic sample (15–30 min)

| id | customer_code | email | note |
|---:|---|---|---|
| 101 | ALPHA | Ada@Example.test | priority_1 |
| 102 | alpha2 | ben@example.test | 20% discount |
| 103 | BETA | NULL | priorityX1 |
| 104 | A_100 | Cia@Example.test | 100% ready |
| 105 | GAMMA | dan@sample.test | NULL |
| 106 | AL | eve@example.test | regular |

All rows are fictional. These examples are read-only, self-contained, and PostgreSQL-oriented where casts or `ILIKE` appear.

### A. Prefix and suffix

```sql
WITH customers(id, code) AS (
 VALUES (101,'ALPHA'),(102,'alpha2'),(103,'BETA'),
        (104,'A_100'),(105,'GAMMA'),(106,'AL')
)
SELECT id FROM customers WHERE code LIKE 'A%' ORDER BY id;
-- PostgreSQL deterministic C-collation/ASCII example: 101, 104, 106
```

`LIKE '%A'` matches codes ending in capital `A`: **101, 103, 105**. Do not infer stable results across arbitrary collations without testing.

### B. One-character wildcard

```sql
SELECT 'A_100' LIKE 'A_100' AS wildcard_match,
       'AX100' LIKE 'A_100' AS also_matches;
-- TRUE, TRUE: underscore is a wildcard, not a literal underscore
```

### C. Literal underscore and percent sign

```sql
SELECT 'A_100' LIKE 'A!_100' ESCAPE '!' AS literal_underscore,
       '20% discount' LIKE '%!%%' ESCAPE '!' AS contains_percent;
-- TRUE, TRUE
```

### D. Case-insensitive matching (PostgreSQL extension)

```sql
SELECT 'alpha2' ILIKE 'AL%' AS case_insensitive,
       'alpha2' LIKE 'AL%' AS case_sensitive;
-- TRUE, FALSE under the lab's deterministic C collation
```

### E. NULL-aware exclusion

```sql
SELECT NULL::text NOT LIKE 'A%' AS unknown_result,
       COALESCE(NULL::text NOT LIKE 'A%', FALSE) AS explicit_false;
-- NULL, FALSE
```

If missing emails must be audited, use `email IS NULL` separately. Do not silently interpret missing values as a nonmatch or as an ordinary exception.

### F. Operational pattern filtering

An SRE inspecting synthetic incident labels might use `incident_code LIKE 'DB-%'` to select database incidents, but should not equate this prefix with authoritative ownership metadata. Confirm case rules, label normalization, and expected IDs before using the result to drive alerts, reports, or retention decisions.

## Hands-on lab (30–50 min)

Run [015 SQL lab](../labs/015-like-wildcards-ilike.sql) only after verifying the container/server is an isolated training instance:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/015-like-wildcards-ilike.sql
```

The script begins a read-only transaction, sets a short statement timeout and deterministic collation on test expressions, checks PostgreSQL 18 and database name, creates only inline `VALUES` datasets, displays examples, checks exact ID arrays, and rolls back. **Expected** `environment_assertion = 1` and `acceptance_assertion = 1` with exit code zero; these are acceptance criteria, **not a claim that the lab has been run**.

Practice independently (20 min):

1. Find codes starting with uppercase `A` using `LIKE`. Expected IDs **101, 104, 106**.
2. Find codes starting with `al` regardless of case using PostgreSQL `ILIKE 'al%'`. Expected **101, 102, 106**.
3. Find notes containing a **literal** percent sign. Expected **102, 104**.
4. Find codes containing a literal underscore. Expected **104**.
5. Find notes matching `priority_1` with wildcard underscore. Expected **101, 103**; then escape the underscore to match only **101**.
6. Find missing emails separately with `IS NULL`. Expected **103**.
7. Use `NOT LIKE 'A%'` on codes with the lab's C collation. Expected **102, 103, 105**.

## Troubleshooting, performance and safety (50–55 min)

| Symptom | Likely cause | Safe action |
|---|---|---|
| `LIKE 'AL%'` misses lowercase values | Case-sensitive comparison | Confirm collation; use `ILIKE` in PostgreSQL if intended |
| Too many matches for `A_100` | `_` means any single character | Use `ESCAPE` and a literal underscore |
| Percent sign is not matched literally | `%` is a wildcard | Use explicit `ESCAPE` |
| Missing values vanish | NULL yields UNKNOWN | Inspect `IS NULL` separately |
| Query scans too much data | Leading `%...` often prevents ordinary B-tree prefix use | Inspect `EXPLAIN` on sandbox; consider appropriate indexing/search design |
| Cross-platform mismatch | Different collations, locale or `ILIKE` support | Run portability tests against each engine |

**DBRE/SRE guardrails:** A prefix pattern may use an index in some PostgreSQL configurations with appropriate operator classes and collation; a leading wildcard often requires different indexing (e.g. PostgreSQL `pg_trgm`) for scale. Do not create extensions or indexes in this read-only lab. Avoid executing unbounded `LIKE '%...%'` queries against large production tables without a plan and workload review. Never use unreviewed pattern filters to determine records for `UPDATE`, `DELETE`, or automated cleanup. Parameterize SQL; separately escape user-supplied `%`, `_`, and your chosen escape character when literal matching is required.

## Review questions and answers (55–60 min)

1. What does `%` match? **Zero or more characters.**
2. What does `_` match? **Exactly one character.**
3. Is `LIKE '%ph%'` a substring search? **Yes, for this simple pattern.**
4. Does `LIKE 'ph%'` match `alpha`? **No.**
5. Is `ILIKE` portable standard SQL? **No, it is PostgreSQL-specific.**
6. What is the result of `NULL LIKE '%'`? **UNKNOWN (SQL NULL).**
7. How do you search for literal `_`? **Use an explicit `ESCAPE` character.**
8. Does `NOT LIKE` include NULL rows? **No.**
9. Why might `LIKE '%error%'` be expensive? **Leading wildcard often prevents ordinary B-tree prefix indexing.**
10. What proves runtime acceptance? **Actual execution on an isolated PostgreSQL 18 instance with reproducible logs and reviewer evidence.**

## References

- [PostgreSQL 18 pattern matching](https://www.postgresql.org/docs/18/functions-matching.html)
- [PostgreSQL 18 collations](https://www.postgresql.org/docs/18/collation.html)
- [PostgreSQL 18 indexes and operator classes](https://www.postgresql.org/docs/18/indexes-opclass.html)
- [PostgreSQL 18 pg_trgm](https://www.postgresql.org/docs/18/pgtrgm.html)
- [Next: Chapter 016 — DISTINCT and duplicate handling (planned)](../MASTER-TOC.md)
