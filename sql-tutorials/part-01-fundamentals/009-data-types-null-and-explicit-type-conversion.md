# Chapter 009 — Data Types, NULL, and Explicit Type Conversion

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: 008](008-aliases-expressions-literals-and-calculated-columns.md) · [Next: 010](010-lab-01-explore-sample-database-and-write-first-queries.md) (planned)  
> **Audience:** SQL beginners, analysts, data engineers, application engineers, DBRE/SRE · **Duration:** 60 minutes · **Lab baseline:** PostgreSQL 18  
> **Status:** Published content; independent editorial review and PostgreSQL 18 runtime validation pending.

## Learning outcomes and prerequisites (0–5 minutes)

After this chapter you can choose basic SQL data types, distinguish NULL from zero/empty strings, explain why comparisons with NULL need special predicates, convert types explicitly, recognize unsafe casts, and test synthetic data without writing database objects. Complete [Chapter 008](008-aliases-expressions-literals-and-calculated-columns.md) first. Run the [Chapter 003 isolated PostgreSQL 18 lab](003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md) using a non-production account.

| Time | Activity | Deliverable |
|---|---|---|
| 0–5 min | Outcomes, lab safety | Confirm sandbox only |
| 5–15 min | Types and NULL | Choose representations |
| 15–30 min | Worked SQL examples | Predict results |
| 30–50 min | Read-only lab | Run checks and compare output |
| 50–55 min | Troubleshooting | Explain errors and hazards |
| 55–60 min | Review | Answer questions |

## 1. Data types and their meaning (5–15 minutes)

A **data type** determines what values a column or expression can represent and which operations are meaningful. A value that looks numeric is not necessarily stored as a number. A postal code like `'00501'` should be text because leading zeros matter; a monetary amount usually needs exact decimal arithmetic.

| Purpose | Common SQL choice | PostgreSQL 18 note | Operational caution |
|---|---|---|---|
| Whole-number quantity | INTEGER / BIGINT | `integer`, `bigint` | Check range before casting |
| Exact price | DECIMAL(p,s) / NUMERIC(p,s) | `numeric(12,2)` | Agree on currency and rounding |
| Approximate measurement | DOUBLE PRECISION | Binary floating-point | Avoid for exact money |
| Code or identifier | VARCHAR(n), CHARACTER VARYING, TEXT | `text` has no length limit | Never strip leading zeros |
| True/false | BOOLEAN | `true`, `false`, NULL | Unknown is not false |
| Calendar day | DATE | No time-of-day | Separate from timestamp |
| Point in time | TIMESTAMP WITH TIME ZONE | `timestamptz` | Normalize time-zone conventions |

The SQL standard defines several of these types, but type ranges, implicit conversions, timestamp handling and type names differ across engines. PostgreSQL-specific shorthand `value::type` is convenient; `CAST(value AS type)` is the more portable form.

## 2. NULL is missing or unknown, not a value (10–20 minutes)

`NULL` represents absent/unknown information, not zero, `FALSE`, `''` or the literal text `'NULL'`. Standard SQL uses **three-valued logic**: a comparison can evaluate to TRUE, FALSE or UNKNOWN. For example, `NULL = NULL` evaluates to UNKNOWN, not TRUE; in a `WHERE` clause only TRUE rows survive. Use `IS NULL` and `IS NOT NULL` to test missingness. Chapter 013 explores complete truth tables; Chapter 019 introduces `COALESCE`.

```sql
WITH customers(customer_id, email) AS (
  VALUES (101, 'ava@example.invalid'::text),
         (102, NULL::text),
         (103, ''::text)
)
SELECT customer_id, email IS NULL AS missing_email
FROM customers ORDER BY customer_id;
```

Expected: customer 101 = false; 102 = true; 103 = false. An empty string is present but empty in PostgreSQL. **Oracle differs**: an empty character string is generally treated as NULL, so do not assume this distinction is portable.

```sql
SELECT NULL::integer = NULL::integer AS equality_test,
       NULL::integer IS NULL AS missing_test;
```

Expected: `equality_test` displays NULL, `missing_test` is `true`.

## 3. Explicit casts and worked examples (20–30 minutes)

### A. Preserve exact numeric semantics

```sql
SELECT CAST('19.95' AS DECIMAL(10,2)) * 2 AS line_total_usd,
       CAST(1 AS NUMERIC) / 3 AS fractional_ratio;
```

Expected `39.90` and a repeating decimal approximately 0.3333; display scale may vary. In PostgreSQL, integer `1 / 3` returns `0`, so cast before division.

### B. Convert a date with a clear input format

```sql
SELECT CAST('2026-11-08' AS DATE) AS order_date;
```

Expected `2026-11-08`. ISO-style date literals are easier to review than locale-dependent formats. Dates and timestamps are not interchangeable; time-zone interpretation requires deliberate design.

### C. Identify a failed cast without aborting the batch

```sql
WITH input(raw_amount) AS (
 VALUES ('12.50'::text), ('not-a-number'::text), (NULL::text)
)
SELECT raw_amount,
       CASE WHEN raw_amount ~ '^[0-9]+(\\.[0-9]{1,2})?$'
            THEN CAST(raw_amount AS NUMERIC(10,2))
            ELSE NULL::NUMERIC(10,2)
       END AS parsed_amount
FROM input;
```

Expected: `12.50`, NULL, NULL respectively. **PostgreSQL-specific:** the `~` regex operator. This is a deliberately narrow *example* validator, not a general decimal parser: it rejects signs, whitespace, exponent notation and other valid numeric representations; even a matching string can overflow `NUMERIC(10,2)`. For production ETL, validate format, range, locale and error-handling requirements explicitly. SQL Server's `TRY_CAST` and Snowflake's `TRY_TO_DECIMAL` are different vendor-specific alternatives.

### D. NULL in arithmetic

```sql
SELECT 10 + NULL::integer AS unknown_total,
       10 + 0 AS known_total;
```

Expected NULL versus 10. Substituting zero for missing amounts is a business rule, not an automatic SQL correction.

## 4. Hands-on practice (30–50 minutes)

**Lab:** [009-data-types-null-explicit-conversion.sql](../labs/009-data-types-null-explicit-conversion.sql).

From the repository root, using the isolated lab connection configured in Chapter 003:

```powershell
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/009-data-types-null-explicit-conversion.sql
```

The lab requires the database name `sql_tutorials` and PostgreSQL major version 18, starts `BEGIN READ ONLY`, uses only synthetic `VALUES` rows, and finishes with `ROLLBACK`. It does not create or modify tables. Confirm the connection targets a disposable local instance; **do not run against production or use production credentials**.

Practice tasks:

1. Inspect customer 102's NULL email and customer 103's empty email. Expected missing-email flags: true and false.
2. Cast the string `'19.95'` to `NUMERIC(10,2)` and multiply by two. Expected 39.90.
3. Compare integer division `1 / 3` with `ROUND(CAST(1 AS NUMERIC) / 3, 2)`. Expected 0 and 0.33.
4. Parse three synthetic input amounts, including an invalid string. Expected two numeric amounts and one NULL; invalid input is deliberately not cast.
5. Count missing versus empty email values. Expected one of each.
6. Execute the final acceptance assertion. Expected `acceptance_assertion = 1`; a mismatch causes an error with `ON_ERROR_STOP=1`.

**Evidence required for actual runtime acceptance:** record PostgreSQL server version, isolated database identity, exact command, script revision/commit, stdout/stderr, exit code and timestamp in a reproducible QA artifact. Expected outputs printed in documentation are *not* execution evidence.

## 5. Troubleshooting and DBRE/SRE implications (50–55 minutes)

| Symptom | Likely reason | Safe response |
|---|---|---|
| `invalid input syntax for type numeric` | Text is not a valid numeric literal | Profile source data; quarantine bad values before conversion |
| `numeric field overflow` | Precision/scale too narrow | Validate maximum range; revise schema via reviewed change |
| `operator does not exist` | Incompatible operand types | Add an intentional, reviewed `CAST` |
| Missing rows after `WHERE email = NULL` | Comparison evaluates UNKNOWN | Use `email IS NULL` |
| Unexpected zeros in reports | Integer division | Cast operand to NUMERIC |
| Dates differ between systems | Locale or time-zone assumptions | Use documented ISO formats and UTC policy |
| Guard assertion fails | Wrong DB or PostgreSQL version | Stop; reconnect to the isolated PostgreSQL 18 lab |

**Data engineering:** define contracts for nullable fields, reject/accept rules, monetary precision, time zones and invalid source strings before loading. **DBRE/SRE:** unexpected casts can increase query CPU and prevent efficient index usage when applied to indexed columns; investigate plans and statistics rather than changing production schema blindly. For healthcare datasets, use fictional records and do not treat absent clinical values as zero without an approved semantic rule.

## 6. Review questions and answers (55–60 minutes)

1. Is NULL the same as zero? **No; it denotes missing/unknown information.**
2. Does `NULL = NULL` return TRUE? **No; it evaluates to UNKNOWN.**
3. Which predicate finds absent email values? **`email IS NULL`.**
4. Why use `NUMERIC(12,2)` for currency? **Exact decimal arithmetic and explicit scale, subject to business rounding rules.**
5. Why does `1 / 3` differ from `CAST(1 AS NUMERIC) / 3` in PostgreSQL? **Integer division truncates; numeric division retains a fraction.**
6. What does `CAST('bad' AS NUMERIC)` do? **It errors; validate or handle malformed inputs explicitly.**
7. Is PostgreSQL `::numeric` portable SQL? **No; prefer standard `CAST(... AS NUMERIC)` across engines.**

## Dialect notes and authoritative references

- Portable: `CAST`, `IS NULL`, `IS NOT NULL`, `NUMERIC`, `DATE`, and basic Boolean logic; implementations vary.
- PostgreSQL-specific: `::`, `~`, `current_setting`, `VALUES` type inference, and exact numeric/display details.
- [PostgreSQL 18 — Data Types](https://www.postgresql.org/docs/18/datatype.html)
- [PostgreSQL 18 — Type Conversion](https://www.postgresql.org/docs/18/typeconv.html)
- [PostgreSQL 18 — Comparison Functions and Operators](https://www.postgresql.org/docs/18/functions-comparison.html)
- [PostgreSQL 18 — Conditional Expressions](https://www.postgresql.org/docs/18/functions-conditional.html)
- [PostgreSQL 18 — Numeric Types](https://www.postgresql.org/docs/18/datatype-numeric.html)

**Next:** Chapter 010 — Lab 01: Explore the Sample Database and Write First Queries.
