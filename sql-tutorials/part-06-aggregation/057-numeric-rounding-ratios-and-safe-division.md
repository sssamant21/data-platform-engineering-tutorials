# 057 — Numeric Rounding, Ratios, and Safe Division

**Part 06 — Aggregation, Grouping & Reporting** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBRE/SRE · **Lab target:** PostgreSQL 18

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Previous: 056](056-text-transformations-for-reporting.md) · [SQL lab](../labs/057-numeric-rounding-ratios-safe-division.sql) · [Next: 058 (planned)](../MASTER-TOC.md)

## 1. Objectives and prerequisites (5 minutes)

After this lesson you can: (1) distinguish integer, exact numeric and floating-point arithmetic; (2) round display values without corrupting intermediate calculations; (3) build percentages and ratios using safe division; (4) explain NULL versus zero denominators; (5) reconcile group-level metrics with source totals. Prerequisites: [051 aggregates](051-count-sum-avg-min-and-max.md), [052 aggregation grain](052-group-by-and-aggregation-grain.md), and [054 conditional aggregation](054-conditional-aggregation-with-case-and-filter.md).

**Scenario:** A fictional data platform tracks ingestion batches with accepted and rejected records. Data engineers need acceptance percentages; DBRE/SRE teams must distinguish a zero-volume batch from a failed batch and avoid misleading KPI dashboards.

## 2. Concepts and portability (10 minutes)

A **ratio** divides one measure by another. A **percentage** is that ratio multiplied by 100. The denominator must match the intended grain and population: `accepted / (accepted + rejected)` measures accepted records among processed records, not among all records ever received.

| Pattern | Purpose | Caution |
|---|---|---|
| `CAST(a AS DECIMAL(18,4)) / b` | Exact decimal ratio | Precision/scale rules vary by engine |
| `a / NULLIF(b, 0)` | Avoid division-by-zero exception | Returns NULL when b is zero (or NULL) |
| `ROUND(value, 2)` | Present two decimal places | Dialects differ in midpoint and float handling |
| `COALESCE(ratio, 0)` | Explicit zero-fill policy | Hides undefined ratios unless justified |
| `SUM(a) / NULLIF(SUM(b),0)` | Weighted aggregate ratio | Different from `AVG(a/b)` |

**Portable core:** `CAST`, `DECIMAL`, `NULLIF`, `COALESCE`, `SUM`, `CASE`, and `ROUND` are broadly available. However integer division differs across platforms; PostgreSQL `5 / 2` (integers) yields `2`, whereas `5::numeric / 2` yields `2.5`. PostgreSQL `::numeric` is shorthand, not portable; use `CAST(... AS DECIMAL(...))` for cross-dialect examples. PostgreSQL `ROUND(numeric, integer)` supports decimal scale; floating-point rounding and tie-breaking can differ by engine. Avoid binary floating point for monetary reconciliation.

## 3. Guided walkthrough (15 minutes)

The isolated lab uses five synthetic ingestion batches:

| Batch | Pipeline | Accepted | Rejected | Expected acceptance |
|---|---|---:|---:|---:|
| 1 | claims | 80 | 20 | 80.00% |
| 2 | claims | 45 | 5 | 90.00% |
| 3 | events | 0 | 0 | NULL (no records) |
| 4 | events | 30 | 10 | 75.00% |
| 5 | events | 9 | 1 | 90.00% |

**A. Compute a row-level rate.** The following expression prevents division by zero and preserves exact decimal arithmetic:

```sql
SELECT batch_id,
       accepted_count + rejected_count AS processed_count,
       ROUND(100.0 * accepted_count
             / NULLIF(accepted_count + rejected_count, 0), 2) AS acceptance_pct
FROM ch057_batches
ORDER BY batch_id;
```

The batch with zero processed records has a **NULL**, not 0% or 100%. A NULL ratio means *undefined*; a valid 0% means there were processed records but none accepted.

**B. Aggregate with the correct weight.** Summing accepted and processed counts *before* division produces the true pipeline rate:

```sql
SELECT pipeline,
       SUM(accepted_count) AS accepted,
       SUM(accepted_count + rejected_count) AS processed,
       ROUND(100.0 * SUM(accepted_count)
             / NULLIF(SUM(accepted_count + rejected_count), 0), 2) AS acceptance_pct
FROM ch057_batches
GROUP BY pipeline ORDER BY pipeline;
```

Expected: claims **125/150 = 83.33%**, events **39/50 = 78.00%**. Overall **164/200 = 82.00%**. The unweighted average of batch percentages is **83.75%** across the four nonempty batches, which is *not* the overall acceptance rate. This is a common dashboard error.

**C. Separate reporting precision from source precision.** `ROUND(100.0 * accepted / processed, 2)` rounds a percentage for presentation. Preserve original integer counts and compute unrounded ratios for comparisons; rounding each row before aggregating can accumulate error.

**D. Define a missing-data policy.** A zero-volume batch is valid and may indicate no traffic; it is not evidence of success or failure. `COALESCE(acceptance_pct, 0)` may be appropriate for a visualization with an explicit "no data" flag, but it is not mathematically equivalent to a zero acceptance rate. An unexpected NULL count should be investigated rather than silently converted.

## 4. Production and DBRE/SRE safeguards (5 minutes)

- Check the denominator's grain and whether retries, duplicates, late arrivals, or filtered rows change it.
- Enforce nonnegative counts in isolated examples; in production, validate source contracts rather than assuming them.
- Use `NUMERIC/DECIMAL` for exact ratios, especially financial amounts; floating point may introduce representation error.
- Avoid `AVG(rounded_percentage)` for global KPIs; use `SUM(numerator)/SUM(denominator)`.
- For operational alerts, report numerator, denominator, timestamp window, and sample size alongside the percentage. A 100% error rate on one request is not equivalent to 100% on one million requests.
- Do not use production credentials, patient data, or real business data in this lab.

## 5. Hands-on PostgreSQL 18 lab (20 minutes)

**Preflight:** Confirm independently that the target is a disposable isolated PostgreSQL 18 instance, and database `sql_tutorials`. The script checks version and database name, but **these checks alone cannot prove isolation**. Run from a lab-only terminal:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/057-numeric-rounding-ratios-safe-division.sql
```

The [lab file](../labs/057-numeric-rounding-ratios-safe-division.sql) starts a transaction, applies transaction-local statement/lock/idle timeouts, creates a temporary table with synthetic rows, checks detailed expected results using fail-closed assertions, and finishes with `ROLLBACK`.

Practice tasks:

1. Run the lab and record the server version, endpoint, exit code, and output in a private QA evidence location. **No runtime validation is claimed by this chapter.**
2. Compare `5 / 2` with `CAST(5 AS DECIMAL(10,2)) / 2` in PostgreSQL.
3. Explain why batch 3 has a NULL acceptance percentage.
4. Compute acceptance by pipeline and reconcile total accepted/rejected/processed counts.
5. Compare the weighted overall acceptance percentage (82.00%) with the unweighted average of four defined batch percentages (83.75%).
6. Change a synthetic batch in your own disposable copy to have accepted 0, rejected 10; verify that its rate becomes **0%**, not NULL. Restore the fixture before relying on the included assertions.

**Expected report:** claims 125 accepted, 25 rejected, 150 processed, 83.33%; events 39 accepted, 11 rejected, 50 processed, 78.00%; grand total 164 accepted, 36 rejected, 200 processed, 82.00%. The script emits a passing NOTICE only when its checks succeed; a NOTICE printed in source is **not** evidence that it has executed.

## 6. Troubleshooting and correctness checks (5 minutes)

| Symptom | Likely cause | Safe action |
|---|---|---|
| Division by zero | Missing `NULLIF(denominator,0)` | Guard denominator, preserve undefined result |
| Unexpected integer ratio | Integer operands | Cast numerator to exact decimal before division |
| Dashboard differs from source | Averaging percentages instead of weighting counts | Reconcile summed numerator and denominator |
| NULL rate becomes 0 | Unconditional `COALESCE` | Preserve NULL and expose a no-volume indicator |
| Rounded values disagree slightly | Premature rounding or floating point | Retain exact intermediates and round only for display |
| Lab guard rejects server | Wrong major version or database | Stop; inspect endpoint and use isolated PostgreSQL 18 |

**Validation status:** Authored for publication; targeted static reasoning only. Independent editorial review, comprehensive automated SQL/link checks, and actual PostgreSQL 18 runtime execution with retained evidence remain pending.

## 7. Review questions and answers (5 minutes)

1. **Why use `NULLIF(denominator,0)`?** It returns NULL for a zero denominator, preventing a division-by-zero exception.
2. **Is a NULL rate the same as 0%?** No. NULL means undefined or missing; 0% is a defined ratio with a nonzero denominator and zero numerator.
3. **Why isn't `AVG(batch_rate)` the global rate?** It weights batches equally regardless of their processed record counts.
4. **How should monetary ratios be calculated?** Prefer exact decimal types, documented precision, and rounding only at the appropriate reporting boundary.
5. **What should an SRE include with a percentage alert?** Raw numerator and denominator, time window, data freshness, and threshold/sample-size policy.

**Next:** [058 — ROLLUP, CUBE, and GROUPING SETS (planned)](../MASTER-TOC.md).

## References

- [PostgreSQL 18 — Mathematical Functions and Operators](https://www.postgresql.org/docs/18/functions-math.html)
- [PostgreSQL 18 — Numeric Types](https://www.postgresql.org/docs/18/datatype-numeric.html)
- [PostgreSQL 18 — Conditional Expressions (NULLIF, COALESCE)](https://www.postgresql.org/docs/18/functions-conditional.html)
- [PostgreSQL 18 — Aggregate Functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
