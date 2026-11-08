# Chapter 008 — Aliases, Expressions, Literals, and Calculated Columns

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: 007](007-select-fundamentals-retrieve-rows-and-columns.md) · [Next: 009](009-data-types-null-and-explicit-type-conversion.md) (planned)  
> **Audience:** SQL beginners, analysts, data engineers, application engineers, DBREs/SREs · **Duration:** 60 minutes · **Baseline:** PostgreSQL 18  
> **Publication:** Authored; independent editorial review and PostgreSQL 18 runtime validation pending.

## Outcomes and prerequisites (5 minutes)

By the end, you can explain column and table aliases, distinguish literals from column references, build arithmetic and string expressions, calculate a derived column without modifying stored data, recognize NULL and numeric pitfalls, and verify calculations using a read-only lab.

Read [Chapter 007](007-select-fundamentals-retrieve-rows-and-columns.md) first. For live exercises, use the isolated PostgreSQL 18 environment in [Chapter 003](003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md). Do not run labs against production or with privileged credentials.

| Minutes | Segment | Outcome |
|---:|---|---|
| 0–5 | Goals and safety | Know what will run |
| 5–15 | Aliases, literals, expressions | Read SQL expressions |
| 15–30 | Worked examples | Predict computed outputs |
| 30–50 | Hands-on lab | Execute and assert read-only results |
| 50–55 | Troubleshooting | Identify numeric and alias pitfalls |
| 55–60 | Knowledge check | Explain and apply concepts |

## 1. Aliases, literals, and expressions (10 minutes)

An **alias** is a name assigned in a query to an output expression or input relation; it does not rename the underlying database column or table. Use `AS` for clarity:

```sql
SELECT 120.00 AS subtotal_usd,
       120.00 * 0.10 AS tax_usd;
```

Expected: one row, `subtotal_usd=120.00`, `tax_usd=12.0000` (format and numeric scale can depend on the expression and client).

An **expression** computes a value: `quantity * unit_price`, `price - discount`, or `first_name || ' ' || last_name`. A **literal** is a value written directly in the query, such as `12`, `'paid'`, `TRUE`, or `NULL`. Single quotes denote string literals; double quotes in PostgreSQL denote identifiers. A column reference such as `amount_usd` is not a literal.

An expression is evaluated for each qualifying input row. A computed result is **not stored** just because it appears in `SELECT`. Storing it requires a separate schema or write decision, outside this lab.

### Column aliases versus table aliases

```sql
WITH orders(order_id, amount_usd) AS (
  VALUES (7001, 120.00::numeric(10,2))
)
SELECT o.order_id AS id,
       o.amount_usd AS amount
FROM orders AS o;
```

Expected: `id=7001`, `amount=120.00`. Here `o` is a relation alias; `id` and `amount` are output aliases. Aliases are particularly useful in joins, reports, and queries with similarly named columns.

**Scope warning:** In PostgreSQL, a SELECT-list alias can be used in `ORDER BY`, but generally not in the same query level's `WHERE` clause. To filter by a calculated alias, use a subquery or CTE. Aliases are not a substitute for parameterized SQL or access controls.

## 2. Worked examples (15 minutes)

All examples use fictional retail orders. Amounts are `numeric`, not binary floating-point, to avoid rounding surprises in monetary calculations.

### A — Calculated amount

```sql
WITH items(order_id, quantity, unit_price_usd) AS (
  VALUES (7001, 2, 19.95::numeric(10,2)),
         (7002, 3, 10.00::numeric(10,2))
)
SELECT order_id, quantity * unit_price_usd AS line_total_usd
FROM items ORDER BY order_id;
```

| order_id | line_total_usd |
|---:|---:|
| 7001 | 39.90 |
| 7002 | 30.00 |

### B — Discount and parentheses

```sql
SELECT (100.00::numeric(10,2) - 10.00::numeric(10,2))
       * 2 AS discounted_total_usd;
```

Expected `180.00`. Parentheses are essential: `100 - 10 * 2` would be `80`, not `180`.

### C — String concatenation

```sql
SELECT 'Ava' || ' ' || 'Patel' AS display_name;
```

Expected `Ava Patel`. The `||` concatenation operator is supported in PostgreSQL and standard SQL, but portability details vary; some platforms provide `CONCAT` or different behavior around NULL.

### D — Reusing a calculated value safely

```sql
WITH items(order_id, quantity, unit_price_usd) AS (
  VALUES (7001, 2, 19.95::numeric(10,2)),
         (7002, 3, 10.00::numeric(10,2))
), totals AS (
  SELECT order_id, quantity * unit_price_usd AS line_total_usd
  FROM items
)
SELECT order_id, line_total_usd
FROM totals
WHERE line_total_usd >= 35.00
ORDER BY order_id;
```

Expected: only `7001 / 39.90`. The CTE gives the computed value a name that the outer query can filter.

### E — Rounding a ratio

```sql
SELECT ROUND(1::numeric / 3, 2) AS ratio;
```

Expected `0.33`. PostgreSQL integer division differs from numeric division: `1 / 3` with integer operands yields `0`. Cast intentionally when fractional results matter. Division by zero raises an error; Chapter 019 covers `NULLIF` as one safeguard.

## 3. Hands-on lab (20 minutes)

**File:** [008-aliases-expressions-calculated-columns.sql](../labs/008-aliases-expressions-calculated-columns.sql)

Run only against the isolated `sql_tutorials` database from Chapter 003:

```powershell
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/008-aliases-expressions-calculated-columns.sql
```

The path assumes execution from the repository root. If you are inside `sql-tutorials/`, omit that prefix. Use a lab account with appropriate read-only access. The script checks PostgreSQL major version 18 and the expected database name, begins a read-only transaction, uses only in-query `VALUES` data, and rolls back at the end.

**Exercises:**

1. Predict the `id` and `amount` aliases in the table-alias example.
2. Compute `quantity * unit_price_usd` for orders 7001 and 7002. Expected: 39.90 and 30.00.
3. Add a 10% discount using `ROUND(line_total_usd * 0.90, 2)`. Expected: 35.91 and 27.00.
4. Filter on a calculated total via a CTE. Expected: only order 7001 for a threshold of 35.00.
5. Confirm a numeric division result of 0.33, and a concatenated display name of `Ava Patel`.
6. Run the included acceptance assertion. An unexpected result deliberately fails the query and, with `ON_ERROR_STOP=1`, stops `psql`.

**Lab acceptance:** all expected results match; no persistent objects are created or changed; the script exits successfully. Record `SELECT version();`, run time, exit code, and any discrepancies when performing independent runtime validation. Do not mark the chapter runtime-validated from the documented expected results alone.

## 4. Troubleshooting and DBRE/SRE considerations (5 minutes)

| Symptom | Cause | Safe correction |
|---|---|---|
| `column "line_total_usd" does not exist` in WHERE | SELECT alias is not visible to WHERE at the same query level | Wrap the expression in a CTE or repeat it |
| `column does not exist` after aliasing a relation | Original relation name used after `FROM orders AS o` | Qualify with `o.column_name` |
| Decimal output looks wrong | Integer division or floating-point arithmetic | Use explicit `numeric` casts and test rounding |
| Concatenated result is NULL | NULL input with `||` | Consider `COALESCE` (Chapter 019) |
| Division by zero | Unchecked denominator | Validate inputs; use safe division design |
| Query fails environment assertion | Wrong database or server version | Reconnect to isolated PostgreSQL 18 lab |

**Production implications:** A calculated output column is not a persisted source of truth. Application and data engineering teams should agree on rounding rules, currency units, and where transformations belong. DBRE/SREs should assess CPU-intensive expressions, result size, and expression-based filtering when investigating performance. Avoid presenting display aliases as guaranteed API contracts without integration tests.

## 5. Knowledge check (5 minutes)

1. Does `AS revenue` rename a physical column?
2. What is the difference between `'amount_usd'` and `amount_usd`?
3. What is `2 * 19.95`?
4. Why might `WHERE line_total_usd > 35` fail if `line_total_usd` is defined in the same SELECT?
5. What is the result of `ROUND(1::numeric / 3, 2)`?

**Answers:** (1) No, it names a query output. (2) A string literal versus a column reference. (3) 39.90. (4) WHERE generally cannot see a same-level SELECT alias; use a CTE. (5) 0.33.

## Dialect notes and references

- PostgreSQL-specific: `::numeric` cast shorthand; use `CAST(value AS DECIMAL(10,2))` for more portable syntax.
- Standard SQL includes `AS`, arithmetic expressions, `CAST`, and `||`; exact type inference, concatenation and NULL semantics vary among engines.
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — Value Expressions](https://www.postgresql.org/docs/18/sql-expressions.html)
- [PostgreSQL 18 — Mathematical Functions](https://www.postgresql.org/docs/18/functions-math.html)
- [PostgreSQL 18 — String Functions](https://www.postgresql.org/docs/18/functions-string.html)

**Next:** Chapter 009 — Data types, NULL, and explicit type conversion.
