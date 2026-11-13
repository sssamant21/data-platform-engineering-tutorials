# 115 — Portable SQL versus Vendor-Specific Syntax and Testing

**Part 12 — Data Engineering, SQL Dialects & Final Projects | Duration: 60 minutes | Audience:** data engineers, analysts, DBREs and SREs.

**Validation state:** Authored content; targeted manual/static inspection only. Independent editorial review, comprehensive parser-based SQL/link QA, and actual isolated PostgreSQL 18 runtime execution **pending**. Expected results are calculated, not observed.

## 1. Objectives and prerequisites (0–5 minutes)

After this lesson, distinguish portable relational semantics from vendor extensions; identify dialect differences in pagination, null handling, upserts, dates, identifiers and types; design a compatibility matrix; and create safe cross-platform regression tests. Prerequisites: [018 — pagination](../part-02-filtering/018-limit-offset-fetch-and-top-across-dialects.md), [036 — UPSERT and MERGE](../part-04-data-modification/036-upsert-and-merge-patterns-across-sql-dialects.md), [107 — reconciliation](../part-11-security-operations/107-data-quality-assertions-and-reconciliation-queries.md), and [114 — warehouse cost](114-data-warehouse-sql-and-analytical-cost-considerations.md).

**Agenda:** objectives 5 min; concepts 10; worked examples 15; hands-on lab 20; troubleshooting 5; review 5.

## 2. What portability actually means (5–15 minutes)

**Portable SQL** means a query's syntax *and semantics* are supported consistently on the target engines. Standards-inspired syntax is a useful starting point, but standards support varies by product and version. A query that parses on two engines may still differ in NULL ordering, collation, rounding, implicit casts, timestamp zones, integer division, or duplicate handling.

| Concern | Portable-first approach | Dialect-specific note |
|---|---|---|
| Row limiting | `ORDER BY ... OFFSET 0 ROWS FETCH NEXT 3 ROWS ONLY` where supported | PostgreSQL/MySQL use `LIMIT`; SQL Server also offers `TOP`; Oracle supports `FETCH` |
| Case-insensitive search | Normalize both sides with `LOWER()`, then compare | PostgreSQL `ILIKE` is an extension; collations affect results |
| Null fallback | `COALESCE(value, 0)` | SQL Server `ISNULL`, Oracle `NVL`, MySQL `IFNULL` differ in type behavior |
| Conditional expression | `CASE WHEN ... THEN ... ELSE ... END` | `IIF` and `DECODE` are not universal |
| Date grouping | Use typed range predicates and platform-specific date bucketing | `DATE_TRUNC`, `TRUNC`, `DATETRUNC` vary |
| Upsert | Separate portable logical specification from implementation | PostgreSQL `ON CONFLICT`, MySQL `ON DUPLICATE KEY UPDATE`, SQL Server/Oracle `MERGE` require vendor review |
| Identifiers | Simple unquoted lowercase names | PostgreSQL double quotes, SQL Server brackets, MySQL backticks; folding and reserved words differ |
| Booleans | Explicit documented mapping | Oracle SQL and SQL Server have version/type differences; `BIT` is not always Boolean |
| Set comparison | `EXCEPT` where supported, or two-direction anti-joins with duplicate counts | Oracle commonly uses `MINUS`; `EXCEPT ALL` availability varies |

**Important:** portability is a tested property of a *specific version matrix*, not a blanket promise. Use parameters rather than string interpolation for user input. Never assume an implicit cast, sort order, or default isolation level is consistent.

## 3. Worked examples and expected results (15–30 minutes)

Use fictional retail orders: (101, East, 40.00), (102, East, NULL), (103, West, 60.00), (104, West, 20.00). The following standard-style CTE is supported by PostgreSQL 18; other vendors may need a different inline row-constructor syntax.

```sql
WITH orders(order_id, region, amount) AS (
  VALUES (101, 'East', 40.00), (102, 'East', NULL),
         (103, 'West', 60.00), (104, 'West', 20.00)
)
SELECT region, COUNT(*) AS row_count,
       COUNT(amount) AS known_amounts,
       SUM(COALESCE(amount, 0)) AS total_amount
FROM orders
GROUP BY region
ORDER BY region;
```

**Calculated output:** East: row_count 2, known_amounts 1, total_amount 40.00; West: 2, 2, 80.00. `COUNT(*)` counts NULL-bearing rows; `COUNT(amount)` does not. If NULL means unknown rather than zero, replacing it with zero may be semantically wrong: document the business rule.

For deterministic pagination, add a unique tie-breaker:

```sql
SELECT order_id, region
FROM orders
ORDER BY region, order_id
OFFSET 0 ROWS FETCH NEXT 3 ROWS ONLY;
```

This second snippet assumes an existing isolated `orders` table and is **illustrative only**, not directly executable by itself. Expected first three IDs from the fictional dataset: 101, 102, 103. PostgreSQL equivalent: `ORDER BY region, order_id LIMIT 3 OFFSET 0`. Do not rely on unspecified NULL ordering or ties.

For a case-insensitive exact comparison, `LOWER(region) = LOWER('east')` is more portable than `region ILIKE 'east'`; however, Unicode case folding and collation still require tests.

**Cross-engine test contract:** assert the same column names and types (after explicit normalization), row counts, ordered IDs, NULL behavior, decimal totals, duplicate multiplicities and error handling. Keep expected results in version control. Do not equate matching aggregate totals with matching rows.

## 4. Hands-on PostgreSQL 18 lab (30–50 minutes)

Run [115 — portability contract lab](../labs/115-portable-sql-dialect-testing.sql) **only** in a disposable PostgreSQL 18 database named `sql_tutorials`:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/115-portable-sql-dialect-testing.sql
```

The lab uses a read-only transaction, synthetic CTEs, version/database checks, transaction-local timeouts, exact bidirectional `EXCEPT ALL` assertions, and rollback. It deliberately demonstrates PostgreSQL-only `ILIKE` alongside a portable-style `LOWER` expression. The assertions and guard block are PostgreSQL-specific, **not** portable SQL.

**Practice:** (1) inspect the four synthetic rows and NULL; (2) compare `COUNT(*)` to `COUNT(amount)`; (3) compare `LOWER` and `ILIKE` results; (4) compare `FETCH FIRST` to `LIMIT` with identical ordering; (5) run the exact-result assertions; (6) draft a portability test matrix for PostgreSQL 18, Snowflake and BigQuery, marking every unexecuted target **not tested**. Optional: change the case predicate to a prefix match and explain why matching rules and index behavior can differ.

**Calculated expected outputs:** 4 orders; 3 known amounts; 1 NULL; East 40.00; West 80.00; overall 120.00; both case-insensitive filters match 2 East orders; both pagination forms return IDs 101, 102, 103; zero assertion mismatches. These are *not* observed PostgreSQL results.

## 5. Troubleshooting and operational guardrails (50–55 minutes)

| Symptom | Likely cause | Safe response |
|---|---|---|
| Syntax error on another engine | `VALUES` CTE, `LIMIT`, `ILIKE`, or cast syntax differs | Rewrite for that engine; record tested version |
| Different first page | Missing unique `ORDER BY` tie-breaker or different NULL ordering | Explicit ordering and NULL policy |
| Totals match but records differ | Offsetting data errors or duplicate multiplicity | Compare normalized keys and rows in both directions |
| Date buckets disagree | Session time zone or timestamp type | Pin time zone and explicit range boundaries |
| Text matching differs | Collation/Unicode behavior | Define case/accent policy and test representative values |
| Migration query is unexpectedly slow | Different optimizer, indexes or data distribution | Inspect each engine's plan and resource limits |

**Safety:** never run cross-engine comparison against production without approval, scoped read-only access and query budgets. Never test `MERGE`, DDL, grants or destructive statements outside an isolated disposable environment. Avoid real customer data, production credentials and copying sensitive query literals into logs. A passing PostgreSQL lab establishes **no** portability certification for MySQL, SQL Server, Oracle, Snowflake or BigQuery.

## 6. Review questions with answers (55–60 minutes)

1. **Does SQL-standard syntax guarantee identical behavior?** No; implementations, collations, types and version support differ.
2. **Why use a unique sort key for pagination?** To make tie ordering deterministic.
3. **How do `COUNT(*)` and `COUNT(column)` differ?** The latter ignores NULL values.
4. **Why is `ILIKE` not portable?** It is PostgreSQL-specific syntax, not universally implemented.
5. **What proves a migration is correct?** Version-scoped tests comparing normalized rows, types, duplicates, NULLs and business totals, plus operational acceptance.

## References and next milestone

- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — Pattern matching](https://www.postgresql.org/docs/18/functions-matching.html)
- [PostgreSQL 18 — Conditional expressions](https://www.postgresql.org/docs/18/functions-conditional.html)
- [SQL Server — SELECT TOP](https://learn.microsoft.com/en-us/sql/t-sql/queries/top-transact-sql)
- [BigQuery — GoogleSQL query syntax](https://cloud.google.com/bigquery/docs/query-syntax)
- [Snowflake — SELECT](https://docs.snowflake.com/en/sql-reference/sql/select)

**Next:** Chapter 116 — PostgreSQL 18 SQL: lab baseline and advanced features (pending publication).
