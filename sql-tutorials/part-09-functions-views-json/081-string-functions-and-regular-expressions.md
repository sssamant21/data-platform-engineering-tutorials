# 081 — String Functions and Regular Expressions

**Part 09 — SQL Objects, Functions & Semi-Structured Data | 60 minutes | Beginner-friendly | PostgreSQL 18 lab**

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Executable SQL lab](../labs/081-string-functions-and-regular-expressions.sql) · [Previous: 080](../part-08-window-functions/080-lab-08-produce-an-analytical-customer-activity-report.md) · [Next: 082](../MASTER-TOC.md#part-09--sql-objects-functions--semi-structured-data)

## 1. Outcomes and prerequisites (0–5 minutes)

By the end, you can normalize strings without silently changing identifiers, use `TRIM`, `LOWER`, `UPPER`, `LENGTH`, `SUBSTRING`, `REPLACE` and `POSITION`, recognize PostgreSQL regular-expression operators, validate rather than blindly repair malformed records, and reconcile cleaned results with their source rows.

Prerequisites: [Chapter 015 — LIKE](../part-02-filtering/015-like-wildcard-matching-and-dialect-specific-ilike.md), [Chapter 056 — Text transformations](../part-06-aggregation/056-text-transformations-for-reporting.md), and a **disposable PostgreSQL 18** database named `sql_tutorials`. This chapter advances from basic reporting transformations to explicit data-quality contracts and regex-based classification.

| Minutes | Activity |
|---|---|
| 0–5 | Outcomes, safe environment and data contracts |
| 5–15 | Portable string functions and NULL semantics |
| 15–30 | Worked cleaning and regex examples |
| 30–50 | Read-only PostgreSQL lab and exercises |
| 50–55 | Reconciliation, troubleshooting and operational safeguards |
| 55–60 | Review answers and next chapter |

## 2. Why text cleaning matters (5–10 minutes)

An ingestion pipeline may receive `'  Alice@Example.COM  '`, `'alice@example.com'`, or `NULL`. A canonical form can help with matching, but **canonicalization is not proof of identity**: distinct users can share email aliases or case-sensitive identifiers. Keep the raw value and a separately derived normalized value; never silently rewrite the system of record. Define which characters may be removed, which alphabet/collation is expected, and what constitutes an invalid value. Synthetic examples here deliberately avoid real customer data.

## 3. Common SQL string operations (10–15 minutes)

| Function | Example | Expected result | Portability |
|---|---|---|---|
| `TRIM` | `TRIM('  abc  ')` | `abc` | Widely portable |
| `LOWER` | `LOWER('ABC')` | `abc` | Widely portable; collation affects case mapping |
| `UPPER` | `UPPER('abc')` | `ABC` | Widely portable |
| `CHAR_LENGTH` | `CHAR_LENGTH('abc')` | `3` | SQL-standard character count |
| `SUBSTRING` | `SUBSTRING('AB123' FROM 3 FOR 3)` | `123` | SQL-standard form; vendor alternatives exist |
| `POSITION` | `POSITION('@' IN 'a@b')` | `2` | SQL-standard form |
| `REPLACE` | `REPLACE('a-b','-','_')` | `a_b` | Common but check vendor syntax |
| `COALESCE` | `COALESCE(NULL,'missing')` | `missing` | SQL-standard; use only for display, not to erase unknowns |

`TRIM` without an explicit character set removes ordinary spaces, not every kind of Unicode whitespace. `CHAR_LENGTH` counts characters, not UTF-8 bytes; PostgreSQL `OCTET_LENGTH` counts bytes. `LOWER(NULL)` returns `NULL`. SQL concatenation `||` is standard, but SQL Server often uses `+`; `CONCAT` and its NULL behavior differ among vendors.

## 4. Worked example: retain raw and normalized fields (15–22 minutes)

The `VALUES` table is synthetic and exists only for the query:

```sql
WITH incoming(record_id, raw_email) AS (
  VALUES (1, '  Alice@Example.COM  '),
         (2, 'bob@example.org'),
         (3, NULL::text)
)
SELECT record_id, raw_email,
       LOWER(TRIM(raw_email)) AS normalized_email,
       CHAR_LENGTH(TRIM(raw_email)) AS trimmed_chars
FROM incoming
ORDER BY record_id;
```

| record_id | normalized_email | trimmed_chars |
|---:|---|---:|
| 1 | alice@example.com | 17 |
| 2 | bob@example.org | 15 |
| 3 | NULL | NULL |

This is a transformation, **not** a full email-validation algorithm. Do not infer deliverability from a regex match.

## 5. PostgreSQL-specific regular expressions (22–30 minutes)

`LIKE` is appropriate for simple prefix/suffix searches. PostgreSQL adds POSIX-style regex operators: `~` (case-sensitive match), `~*` (case-insensitive match), `!~` and `!~*` (negative matches), plus `REGEXP_REPLACE`. These operators and the exact regex syntax are **not portable SQL**.

```sql
WITH input(code) AS (
  VALUES ('EVT-0042'), ('evt-0042'), ('BAD42')
)
SELECT code,
       code ~ '^EVT-[0-9]{4}$' AS exact_format,
       code ~* '^EVT-[0-9]{4}$' AS case_insensitive_format,
       REGEXP_REPLACE(code, '[0-9]', 'X', 'g') AS masked
FROM input;
```

| code | exact_format | case_insensitive_format | masked |
|---|---|---|---|
| EVT-0042 | true | true | EVT-XXXX |
| evt-0042 | false | true | evt-XXXX |
| BAD42 | false | false | BADXX |

`^` and `$` anchor the full string; `[0-9]{4}` requires exactly four ASCII digits. `g` makes PostgreSQL replace all matches, not just the first. Regex is useful for **format screening**, not authorization or semantic validation. For arbitrary user-supplied patterns, bound input size and query time; complex expressions can consume substantial CPU.

## 6. Data engineering example: classify ingestion IDs (30–35 minutes)

```sql
WITH raw(batch_id, external_code) AS (
 VALUES (1, ' EVT-0042 '), (2, 'EVT-0100'), (3, 'BAD42'), (4, NULL::text)
), cleaned AS (
 SELECT batch_id, external_code, TRIM(external_code) AS code FROM raw
)
SELECT batch_id, code,
       CASE WHEN code IS NULL THEN 'missing'
            WHEN code ~ '^EVT-[0-9]{4}$' THEN 'valid'
            ELSE 'invalid' END AS quality_status
FROM cleaned ORDER BY batch_id;
```

Expected statuses: batch 1 valid, 2 valid, 3 invalid, 4 missing. Preserve rejected rows for remediation. A production pipeline should track accepted, rejected, missing, and duplicate counts separately and reconcile their sum to the incoming row count.

## 7. Hands-on PostgreSQL 18 lab (35–50 minutes)

Run only in an isolated local or disposable database. Inspect the connection first:

```bash
psql -X -d sql_tutorials -c "SELECT current_database(), current_user, current_setting('server_version');"
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/081-string-functions-and-regular-expressions.sql
```

The SQL file begins `BEGIN READ ONLY`, sets transaction-local timeouts, checks database name and PostgreSQL major version, uses only synthetic `VALUES` CTEs, asserts exact output with bidirectional `EXCEPT ALL`, and ends with `ROLLBACK`. A successful run must show `fail_closed_acceptance = 1`. **This is a designed acceptance check, not evidence that it has been executed.**

Practice on a *copy* of the SQL, updating the expected rows before rerunning: (1) add `'  EVT-0007 '` and verify trimming; (2) change `'evt-0042'` to uppercase and compare `~` with `~*`; (3) add `NULL` and explain why `NULL ~ pattern` is not false; (4) compare `CHAR_LENGTH` with `OCTET_LENGTH` for `'é'` in a UTF-8 database; (5) explain why `REGEXP_REPLACE` should not be used to conceal an invalid source identifier.

## 8. Troubleshooting and operational guardrails (50–55 minutes)

| Symptom | Explanation and response |
|---|---|
| A visually blank value remains after `TRIM` | It may contain tabs/nonbreaking spaces; inspect character codes and define a deliberate whitespace policy |
| `NULL` disappears from a `WHERE code ~ ...` filter | The predicate evaluates to unknown; classify missing values explicitly with `IS NULL` |
| Unexpected regex matches | Check anchors, case sensitivity, escaping and collation; test both positive and negative examples |
| Different case-folding across environments | Unicode and collation settings vary; define and test the canonicalization contract |
| Slow regex scans | Test on a bounded synthetic dataset; enforce `statement_timeout`, inspect `EXPLAIN` in approved nonproduction only |
| Acceptance fails | Compare actual and expected multisets; do not bypass version/database guards or weaken assertions |
| Wrong server or database | Stop immediately; never run with production credentials or against production endpoints |

**DBRE/SRE:** read-only does not mean resource-free. Regex filters on large tables can cause expensive scans, and expression indexes are vendor-specific and require separate change review. **Data engineering:** retain raw source fields, document deduplication policy, and monitor rejected-record rates. **Security:** never build regex or SQL strings by concatenating untrusted input; parameterize SQL and restrict accepted regex patterns.

## 9. Review questions and answers (55–60 minutes)

**Q1. Does `LOWER(TRIM(x))` validate an email?** No; it only transforms the string.

**Q2. What does `CHAR_LENGTH(NULL)` return?** `NULL`, not zero.

**Q3. Why use `^...$` anchors?** To require the whole string to match the intended format, rather than matching a substring.

**Q4. What is the difference between `~` and `~*`?** PostgreSQL regex case-sensitive versus case-insensitive matching.

**Q5. Why keep `raw_email` after normalization?** For lineage, debugging, audits and correction of normalization mistakes.

**Q6. Can a passing manual expected-output review be called PostgreSQL 18 runtime validation?** No; runtime validation requires actual execution on an isolated PostgreSQL 18 instance and retained evidence.

## 10. References and next milestone

- [PostgreSQL 18 — String Functions and Operators](https://www.postgresql.org/docs/18/functions-string.html)
- [PostgreSQL 18 — Pattern Matching](https://www.postgresql.org/docs/18/functions-matching.html)
- [PostgreSQL 18 — Character Types](https://www.postgresql.org/docs/18/datatype-character.html)
- [PostgreSQL 18 — Transaction Isolation / Read-only Transactions](https://www.postgresql.org/docs/18/sql-set-transaction.html)
- [Next: 082 — Dates, Intervals, Timestamps, and Time Zones](../MASTER-TOC.md#part-09--sql-objects-functions--semi-structured-data)

**Validation status:** Authored; targeted static reasoning only. Independent editorial review, comprehensive parser-based SQL/link QA, and isolated PostgreSQL 18 runtime execution with reproducible evidence remain pending.
