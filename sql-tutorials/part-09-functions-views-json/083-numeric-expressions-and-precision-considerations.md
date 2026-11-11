# 083 — Numeric Expressions and Precision Considerations

**Part 09 — SQL Objects, Functions & Semi-Structured Data | 60 minutes | PostgreSQL 18**

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [SQL lab](../labs/083-numeric-expressions-precision.sql) · [Previous: 082](082-dates-intervals-timestamps-and-time-zones.md) · [Next: 084](../MASTER-TOC.md#part-09--sql-objects-functions--semi-structured-data)

## 1. Learning objectives and agenda (0–5 minutes)

By the end, distinguish exact decimal arithmetic from binary floating-point, choose a numeric type for money and measurements, avoid accidental integer division and division by zero, explain rounding order, and reconcile totals at a declared data grain. Prerequisites: [009 — Data types](../part-01-fundamentals/009-data-types-null-and-explicit-type-conversion.md), [051 — Aggregates](../part-06-aggregation/051-count-sum-avg-min-and-max.md), and an **isolated PostgreSQL 18** database named `sql_tutorials`.

| Minutes | Activity |
|---|---|
| 0–5 | Objectives and lab safety |
| 5–15 | Exact and approximate types, operators |
| 15–30 | Worked reconciliation examples |
| 30–50 | Hands-on synthetic lab and exercises |
| 50–55 | Troubleshooting, portability and safety |
| 55–60 | Review questions and answers |

## 2. Numeric types and SQL semantics (5–15 minutes)

| Type | What it means | Engineering use |
|---|---|---|
| `SMALLINT`, `INTEGER`, `BIGINT` | Exact signed whole numbers, bounded range | Counts, sequence IDs; consider overflow |
| `NUMERIC(p,s)` / `DECIMAL(p,s)` | Exact decimal with declared precision and scale | Currency and financial reconciliation |
| `NUMERIC` | Exact decimal with no declared precision/scale | Intermediate exact calculations |
| `REAL`, `DOUBLE PRECISION` | Approximate binary floating point | Scientific measurements, telemetry where tolerance is explicit |

**Precision** is the maximum significant decimal digits in `NUMERIC(p,s)`; **scale** is the number of fractional decimal digits. For example, `NUMERIC(10,2)` can represent values up to 99,999,999.99, subject to sign. PostgreSQL rounds values when coercing them to a declared scale; an out-of-range value raises an error. Some SQL engines implement `DECIMAL` precision and overflow rules differently.

**Portable concepts:** `DECIMAL`, `NUMERIC`, `CAST`, `ROUND`, `ABS`, `COALESCE`, `NULLIF`, `SUM`, and `AVG` are widely available, but function overloads, rounding ties, integer division, overflow, and implicit conversions differ. In PostgreSQL, `ROUND(numeric, integer)` is supported, while the two-argument `ROUND(double precision, integer)` is not: cast to `numeric` when deliberate decimal rounding is needed. `NUMERIC` rounds ties away from zero in PostgreSQL; do not assume every engine does.

## 3. Worked examples (15–30 minutes)

### A. Exact decimal versus approximate floating point

```sql
SELECT (0.1::numeric + 0.2::numeric = 0.3::numeric) AS exact_match,
       (0.1::double precision + 0.2::double precision
         = 0.3::double precision) AS float_match;
```

Expected in PostgreSQL 18: `exact_match = true`, `float_match = false` on normal IEEE-754 binary floating-point implementations. Avoid equality tests on approximate measurements; use an explicitly justified tolerance, and be alert to relative versus absolute error.

### B. Integer division, explicit casts and safe denominators

```sql
SELECT 5 / 2 AS truncated_integer_quotient,
       5::numeric / 2 AS exact_quotient,
       ROUND(5::numeric / NULLIF(2, 0), 2) AS safe_ratio,
       5::numeric / NULLIF(0, 0) AS undefined_ratio;
```

Expected: `2`, `2.5`, `2.50`, `NULL`. In PostgreSQL, dividing two integers truncates toward zero. `NULLIF(denominator, 0)` prevents division by zero by producing `NULL`; the consumer must distinguish undefined from a legitimate zero. Never replace undefined ratios with zero without a documented reporting rule.

### C. Round each line or round the total?

Synthetic invoice-line amounts (already stored as exact `numeric`): `19.995`, `10.005`, `0.100`; a fourth line has `NULL` amount.

```sql
WITH lines(line_id, amount) AS (
  VALUES (1, 19.995::numeric), (2, 10.005::numeric),
         (3, 0.100::numeric), (4, NULL::numeric)
)
SELECT COUNT(*) AS line_count,
       COUNT(amount) AS measured_count,
       SUM(amount) AS raw_total,
       ROUND(SUM(amount), 2) AS round_after_sum,
       SUM(ROUND(amount, 2)) AS sum_after_round
FROM lines;
```

Expected: `4`, `3`, `30.100`, `30.10`, `30.11`. This one-cent difference is a **business rule**, not a SQL defect. The correct method depends on whether the source of truth is rounded invoice lines or an unrounded aggregate. Keep both values and the calculation policy in audit evidence.

### D. Precision and explicit presentation

```sql
SELECT ROUND(-1.235::numeric, 2) AS negative_tie,
       CAST(12.345 AS NUMERIC(8,2)) AS scaled_value,
       ABS(-7::numeric) AS magnitude;
```

Expected PostgreSQL results: `-1.24`, `12.35`, `7`. Formatting is not storage: avoid converting numeric columns to strings before numeric sorting or aggregation.

## 4. Hands-on PostgreSQL 18 lab (30–50 minutes)

Use a disposable lab instance only. The script uses inline synthetic `VALUES` and does **not** create, update, or delete tables. Run from the repository root:

```bash
psql -X -d sql_tutorials -c "SELECT current_database(), current_setting('server_version');"
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/083-numeric-expressions-precision.sql
```

The script begins a **read-only transaction**, sets transaction-local timeouts, checks the database name and PostgreSQL major version, computes exact results, and uses bidirectional `EXCEPT ALL` to compare actual and expected rows. A fail-closed assertion causes a nonzero exit on a mismatch; the final `ROLLBACK` leaves no persistent state. **The script is authored but has not been executed on PostgreSQL 18 as part of this publication.**

Exercises (do not modify the canonical lab):

1. Add a synthetic `0.005::numeric` line in a scratch `WITH` query. Predict the new raw total (`30.105`), rounded-total (`30.11`) and sum-of-rounded-lines (`30.12`).
2. Change `5 / 2` to `5::numeric / 2`. Explain why the result changes from `2` to `2.5`.
3. Write a read-only check that counts missing amounts: `COUNT(*) - COUNT(amount)`; expected `1`.
4. Model a success ratio for a service with zero requests using `successful::numeric / NULLIF(requests, 0)`; expected `NULL`, not 0% or 100%.

**Acceptance:** Confirm the database/version guards pass, `exact_match` is true, the three reconciliation totals match, the bidirectional difference count is zero, and the script exits successfully after rollback. Capture PostgreSQL version, command, exit status, and output in a future runtime QA evidence file; do not call it validated until then.

## 5. Troubleshooting, portability and safety (50–55 minutes)

- **Unexpected truncation:** inspect operand types; cast *before* division, not only after it.
- **Unexpected one-cent difference:** inspect whether rounding occurs per line, per tax category, or after aggregation. Never silently alter financial rules.
- **Unexpected NULL:** `SUM` ignores NULL; `COUNT(*)` counts rows, `COUNT(column)` counts non-NULL values. `SUM` of an all-NULL group is NULL.
- **Unexpected float comparison:** binary float is approximate; choose an error tolerance based on domain requirements.
- **Numeric overflow:** verify the maximum value and scale for stored `NUMERIC(p,s)`, and consider accumulator capacity. PostgreSQL `SUM(integer)` returns `bigint`; `SUM(bigint)` returns `numeric`.
- **DBRE/SRE guardrails:** do not use production credentials or live billing/healthcare data; do not rewrite financial records to make aggregates match. Use read-only queries, bounded timeouts, and source-to-target reconciliation with a documented rounding policy. For telemetry, record units and sampling grain.

## 6. Review questions and answers (55–60 minutes)

1. **Which type is generally appropriate for exact currency?** `NUMERIC/DECIMAL` with a documented precision and scale; integer minor units can also be suitable under a documented policy.
2. **Why does `5 / 2` return `2` in PostgreSQL?** Both operands are integers, so integer division truncates.
3. **Why can rounding before summation differ from rounding afterward?** Each rounded line introduces a separate rounding step; the example differs by 0.01.
4. **How can you prevent a divide-by-zero exception?** Use `NULLIF(denominator, 0)`, and handle the resulting NULL explicitly.
5. **Is `double precision` safe for exact money equality?** No. Binary floating point cannot exactly represent many decimal fractions.
6. **What evidence is required before marking the lab runtime-validated?** An actual isolated PostgreSQL 18 execution with captured version, command, exit code, output and assertions.

## References

- [PostgreSQL 18 — Numeric Types](https://www.postgresql.org/docs/18/datatype-numeric.html)
- [PostgreSQL 18 — Mathematical Functions and Operators](https://www.postgresql.org/docs/18/functions-math.html)
- [PostgreSQL 18 — Aggregate Functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [PostgreSQL 18 — Type Conversion](https://www.postgresql.org/docs/18/typeconv.html)
- [Chapter 084 — JSON and semi-structured SQL queries](../MASTER-TOC.md#part-09--sql-objects-functions--semi-structured-data)

**Validation status:** Authored/published; targeted static inspection and manual expected-output reasoning. Independent editorial review, comprehensive automated SQL syntax/link QA, and isolated PostgreSQL 18 runtime validation **pending**.
