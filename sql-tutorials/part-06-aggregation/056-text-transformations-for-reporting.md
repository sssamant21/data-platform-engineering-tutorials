# 056 — Text Transformations for Reporting

**Part 06 — Aggregation, Grouping & Reporting** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBRE/SRE · **Lab target:** PostgreSQL 18

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Previous: 055](055-date-based-grouping-and-time-buckets.md) · [SQL lab](../labs/056-text-transformations-for-reporting.sql) · [Next: 057 (planned)](../MASTER-TOC.md)

## 1. Learning objectives and prerequisites (5 minutes)

After this lesson, you can (1) normalize text labels before grouping; (2) distinguish TRIM, UPPER, LOWER, REPLACE, LENGTH, and concatenation; (3) preserve NULL semantics; (4) identify normalization collisions and Unicode/collation risks; (5) reconcile a report against its raw source. Review [051 — aggregates](051-count-sum-avg-min-and-max.md), [052 — grouping grain](052-group-by-and-aggregation-grain.md), and [054 — conditional aggregation](054-conditional-aggregation-with-case-and-filter.md).

**Scenario:** A fictional payment-ingestion pipeline receives region and status labels with inconsistent case and padding. The data team needs trustworthy KPIs; the DBRE/SRE team must detect unexpected label drift without modifying original records.

## 2. Concepts and SQL portability (10 minutes)

Text normalization converts multiple equivalent *representations* into one agreed reporting key. It must not silently assert that semantically different values are equivalent. For example, `' North '` and `'north'` may represent the same region under a documented case-insensitive policy, but `'US'` and `'us'` might be distinct identifiers in another system.

| Operation | Typical use | Important limitation |
|---|---|---|
| `TRIM(text)` | Remove leading/trailing ordinary spaces | Does not necessarily remove tabs, nonbreaking spaces, or internal whitespace |
| `UPPER(text)`, `LOWER(text)` | Canonical case for controlled labels | Locale, collation, and Unicode behavior vary |
| `REPLACE(text, old, new)` | Replace exact substrings | Not a fuzzy or regex match |
| `CHAR_LENGTH(text)` | Count characters | Different from bytes; grapheme clusters can be multiple characters |
| `COALESCE(text, 'UNKNOWN')` | Display NULL with an explicit label | May conflate actual value 'UNKNOWN' with missing data |
| `CONCAT(...)` | Build display labels | NULL behavior differs by dialect; portable `||` is NULL-propagating in PostgreSQL |

**Portable SQL:** `TRIM`, `UPPER`, `LOWER`, `REPLACE`, `CHAR_LENGTH`, `COALESCE`, and `CASE` are broadly supported, though function signatures, case folding, collation, and concatenation differ. PostgreSQL `BTRIM`, `REGEXP_REPLACE`, `INITCAP`, `OCTET_LENGTH`, and `||` semantics should be treated as dialect-sensitive. SQL Server commonly uses `+` or `CONCAT`; MySQL `CONCAT` propagates NULL; PostgreSQL `concat` ignores NULL arguments. Validate behavior on each target platform.

## 3. Guided walkthrough: normalize before grouping (15 minutes)

The lab creates six synthetic payment events with `region_raw`, `status_raw`, and `amount`:

| ID | Raw region | Raw status | Amount |
|---|---|---|---:|
| 1 | `'  North  '` | `'  CAPTURED '` | 20.00 |
| 2 | `'north'` | `'captured'` | 30.00 |
| 3 | `' SOUTH '` | `' Pending '` | 15.00 |
| 4 | `'South'` | `'CAPTURED'` | 40.00 |
| 5 | NULL | `'captured'` | 10.00 |
| 6 | `'  West  '` | NULL | 5.00 |

**Step A — inspect before transforming.** A raw `GROUP BY region_raw` produces separate North and South groups. This is a *data-quality observation*, not proof that all similarly spelled values should be merged.

**Step B — normalize in a CTE, then aggregate.**

```sql
WITH normalized AS (
  SELECT event_id,
         COALESCE(UPPER(TRIM(region_raw)), 'UNKNOWN') AS region,
         COALESCE(UPPER(TRIM(status_raw)), 'UNKNOWN') AS status,
         amount
  FROM ch056_payments
)
SELECT region, COUNT(*) AS events, SUM(amount) AS total
FROM normalized
GROUP BY region
ORDER BY region;
```

Expected region report:

| Region | Events | Total |
|---|---:|---:|
| NORTH | 2 | 50.00 |
| SOUTH | 2 | 55.00 |
| UNKNOWN | 1 | 10.00 |
| WEST | 1 | 5.00 |

The report must reconcile to **6 events and 120.00**. The normalized status report has **CAPTURED: 4 events / 100.00; PENDING: 1 / 15.00; UNKNOWN: 1 / 5.00**.

**Step C — build a readable label without changing keys.**

```sql
SELECT event_id,
       'REGION=' || COALESCE(UPPER(TRIM(region_raw)), 'UNKNOWN')
       || '; STATUS=' || COALESCE(UPPER(TRIM(status_raw)), 'UNKNOWN') AS display_label
FROM ch056_payments ORDER BY event_id;
```

For event 1, expected `REGION=NORTH; STATUS=CAPTURED`; for event 5, `REGION=UNKNOWN; STATUS=CAPTURED`. Concatenation is for presentation; store source fields separately for lineage and auditability.

**Step D — detect variants and missing values.**

```sql
SELECT UPPER(TRIM(region_raw)) AS normalized_region,
       COUNT(*) AS rows_in_group,
       COUNT(DISTINCT region_raw) AS raw_spellings
FROM ch056_payments
WHERE region_raw IS NOT NULL
GROUP BY UPPER(TRIM(region_raw))
ORDER BY normalized_region;
```

Expected: NORTH and SOUTH each have 2 raw spellings; WEST has 1. Also inspect `COUNT(*) FILTER (WHERE region_raw IS NULL)` (PostgreSQL-specific aggregate filter) to measure missing values separately. If the literal string `'UNKNOWN'` is valid source data, group NULL separately or use an explicit `is_missing` flag to avoid collisions.

## 4. Edge cases and reporting correctness

- `TRIM('  A B  ')` yields `'A B'`; internal spaces remain. `REPLACE('A-B','-',' ')` yields `'A B'`, but do not use such replacements without an approved mapping.
- `TRIM('   ')` yields the empty string, **not NULL** in PostgreSQL. If blank means missing, use `NULLIF(TRIM(region_raw),'')` before `COALESCE`. The lab uses a NULL-only fixture and illustrates this policy separately.
- `CHAR_LENGTH('é')` counts characters, while `OCTET_LENGTH('é')` counts bytes in UTF-8 (typically 2). Unicode normalization (NFC/NFD), collation, and locale can affect comparisons and uniqueness. Do not assume `LOWER` solves accent, whitespace, or Unicode equivalence.
- Normalizing in `WHERE UPPER(TRIM(column)) = ...` may prevent use of an ordinary index on the raw column. Prefer prevalidated canonical columns or an appropriately reviewed expression index for real workloads; never add indexes in production as part of a tutorial.
- `COUNT(DISTINCT region_raw)` ignores NULL and uses the database's equality/collation semantics. A canonicalized label can merge distinct source spellings: preserve raw values and track the number of variants.

## 5. Hands-on lab (20 minutes)

**Preflight:** verify the endpoint is a disposable, isolated PostgreSQL **18.x** instance, and that the database is `sql_tutorials`. Never use production credentials or real patient/customer data. A matching database name alone does not prove isolation. The lab checks version and database, sets transaction-local timeouts, creates a temporary table only, asserts expected results, and rolls back.

From the repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/056-text-transformations-for-reporting.sql
```

Lab tasks: (1) inspect raw values; (2) produce normalized region and status totals; (3) count raw variants per canonical region; (4) create a display label; (5) run assertions; (6) confirm the rollback. Practice independently on a disposable copy: add a blank `region_raw` value and compare `COALESCE(TRIM(...),'UNKNOWN')` with `COALESCE(NULLIF(TRIM(...),''),'UNKNOWN')`; explain why they differ. Adjust expected counts in your own copy when adding data.

**Expected outputs:** 6 source events / 120.00; four normalized regions (NORTH 2/50.00, SOUTH 2/55.00, UNKNOWN 1/10.00, WEST 1/5.00); three statuses (CAPTURED 4/100.00, PENDING 1/15.00, UNKNOWN 1/5.00); 2 raw variants each for NORTH and SOUTH; all assertions pass. Save the executed command, server version and host identity, captured stdout/stderr, exit code, and evidence that the transaction rolled back. A script's expected result is **not** runtime validation.

## 6. Troubleshooting and DBRE/SRE safeguards (5 minutes)

| Symptom | Likely cause | Safe action |
|---|---|---|
| NORTH appears twice | Raw padding/case | Inspect raw spellings and approved normalization policy |
| UNKNOWN unexpectedly large | NULL/blank source values | Separate missing, blank, and literal UNKNOWN categories |
| Sum changed after normalization | Join fan-out or filtering | Reconcile `COUNT(*)` and `SUM(amount)` before and after |
| Case conversion surprises | Locale/collation | Test representative Unicode and dialect behavior |
| Query slowed down | Function on filtered/indexed column | Examine a safe `EXPLAIN`; assess canonical storage/index strategy |
| SQL fails on another engine | Dialect-specific concatenation/regex | Check vendor function docs and test isolated dialect fixtures |

**Safety:** Do not rewrite raw source values merely to make a report look clean. Version the mapping rules, log unexpected labels, and retain an audit path from raw to normalized keys. Keep all practice in the isolated synthetic lab.

## 7. Review questions and answers (5 minutes)

1. **Why normalize before GROUP BY?** Equivalent representations otherwise split into separate report groups.
2. **Does TRIM remove every whitespace character?** No; ordinary TRIM primarily removes specified edge characters, typically spaces.
3. **Does UPPER guarantee Unicode equivalence?** No; case folding, normalization, and collations differ.
4. **Why keep raw labels?** To audit source quality, diagnose collisions, and reverse incorrect mappings.
5. **What happens when TRIM sees only spaces?** PostgreSQL returns an empty string; use NULLIF if policy treats it as missing.
6. **What is the essential reconciliation check?** Event count and amount total must remain 6 and 120.00 after grouping.

## 8. References and next milestone

- [PostgreSQL 18 — String Functions and Operators](https://www.postgresql.org/docs/18/functions-string.html)
- [PostgreSQL 18 — Collation Support](https://www.postgresql.org/docs/18/collation.html)
- [PostgreSQL 18 — Conditional Expressions](https://www.postgresql.org/docs/18/functions-conditional.html)
- [Chapter 057 — Numeric rounding, ratios, and safe division (Master TOC)](../MASTER-TOC.md)

**Validation state:** authored for publication; targeted manual static reasoning only. Independent editorial review, comprehensive automated SQL syntax/link checks, and actual isolated PostgreSQL 18 runtime evidence remain pending.
