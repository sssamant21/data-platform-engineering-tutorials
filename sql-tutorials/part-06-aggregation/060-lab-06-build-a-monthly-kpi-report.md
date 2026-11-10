# 060 — Lab 06: Build a Monthly KPI Report

**Part 06 — Aggregation, Grouping & Reporting** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBRE/SRE.

**Prerequisites:** [051 — aggregates](051-count-sum-avg-min-and-max.md), [052 — grouping grain](052-group-by-and-aggregation-grain.md), [053 — WHERE versus HAVING](053-having-versus-where.md), [054 — conditional aggregation](054-conditional-aggregation-with-case-and-filter.md), [055 — time buckets](055-date-based-grouping-and-time-buckets.md), [057 — safe division](057-numeric-rounding-ratios-and-safe-division.md), [059 — pivoting](059-pivoting-and-unpivoting-portable-and-vendor-features.md).

> **Safety boundary:** Synthetic events only. The [companion SQL lab](../labs/060-lab-06-monthly-kpi-report.sql) creates a TEMP table inside a transaction and rolls back. Run it only against a separately verified disposable PostgreSQL **18** server and database named `sql_tutorials`. A matching name and version are **not proof** of isolation. Do not use production credentials or endpoints.

## 1. Objectives and 60-minute agenda (5 minutes)

At completion you can (1) define a monthly KPI's grain and time zone; (2) calculate counts and weighted acceptance rates; (3) break down throughput by source system with portable conditional aggregation; (4) prevent divide-by-zero and accidental join fan-out; (5) reconcile monthly and grand totals; (6) explain how to preserve operational evidence.

| Activity | Minutes |
|---|---:|
| Objectives, prerequisites, safety | 5 |
| Metric definitions and SQL portability | 10 |
| Guided report walkthrough | 15 |
| Isolated hands-on lab and exercises | 20 |
| Troubleshooting and checks | 5 |
| Review questions and answers | 5 |

**Scenario:** An ingestion service loads synthetic API and file batches. A monthly DBRE/SRE dashboard must show batch counts, accepted/rejected records, processed records, acceptance percentage, and source-specific volume. The **input grain** is one batch. The **output grain** is one calendar month in UTC. These are *batch-reported record counts*, not distinct entities; do not infer unique customers or events.

## 2. Metric contract and dialects (10 minutes)

- `processed = accepted + rejected`; accepted/rejected are nonnegative integer counts.
- `acceptance_pct = 100 × SUM(accepted) / SUM(processed)`. This is a **weighted** percentage. Do **not** average batch percentages or monthly percentages.
- Zero processed records yields `NULL` (undefined rate), not 0% or 100%. `NULLIF(denominator,0)` prevents division errors.
- Report month is derived from `received_at` in **UTC**, using a half-open reporting window: `>= start AND < next_start`. A batch at exactly midnight February 1 belongs to February.
- The source-system allowlist is `api` and `file`. Unknown categories must be investigated rather than silently omitted.
- Report counts use `COUNT(*)`; source breakdowns use `SUM(CASE WHEN ... THEN ... ELSE 0 END)`.

**Portable SQL:** `COUNT`, `SUM`, `CASE`, `GROUP BY`, `ROUND`, `NULLIF`, `COALESCE` and `WHERE` are widely supported; explicit numeric typing and timestamp expressions vary by engine. **PostgreSQL 18-specific:** `date_trunc('month', received_at AT TIME ZONE 'UTC')::date`, `TIMESTAMPTZ`, `DO` assertions, `CREATE TEMP TABLE ... ON COMMIT DROP`, `SET LOCAL`, and psql `\\set`. Snowflake uses `DATE_TRUNC` with different time-zone handling; BigQuery commonly uses `DATE_TRUNC(DATE(timestamp,'UTC'), MONTH)`; SQL Server commonly uses `DATETRUNC(month,...)` (supported versions only). Validate dialect behavior rather than copy/pasting blindly.

## 3. Worked example and expected output (15 minutes)

The lab fixture contains eight batches:

| ID | UTC timestamp | Source | Accepted | Rejected |
|---:|---|---|---:|---:|
| 1 | Jan 05 10:00 | api | 90 | 10 |
| 2 | Jan 31 23:59 | file | 40 | 10 |
| 3 | Feb 01 00:00 | api | 60 | 20 |
| 4 | Feb 15 12:00 | file | 20 | 0 |
| 5 | Mar 01 00:00 | api | 95 | 5 |
| 6 | Mar 20 15:00 | file | 45 | 5 |
| 7 | Mar 21 09:00 | api | 0 | 0 |
| 8 | Mar 31 23:59 | file | 30 | 10 |

**Main query** (after running fixture setup from the lab; the full script executes it automatically):

```sql
SELECT date_trunc('month', received_at AT TIME ZONE 'UTC')::date AS month_start,
       COUNT(*) AS batches,
       SUM(accepted) AS accepted,
       SUM(rejected) AS rejected,
       SUM(accepted + rejected) AS processed,
       ROUND(100.0 * SUM(accepted)
             / NULLIF(SUM(accepted + rejected), 0), 2) AS acceptance_pct,
       SUM(CASE WHEN source_system = 'api'
                THEN accepted + rejected ELSE 0 END) AS api_processed,
       SUM(CASE WHEN source_system = 'file'
                THEN accepted + rejected ELSE 0 END) AS file_processed
FROM ch060_batches
WHERE received_at >= TIMESTAMPTZ '2026-01-01 00:00+00'
  AND received_at <  TIMESTAMPTZ '2026-04-01 00:00+00'
GROUP BY 1
ORDER BY 1;
```

| month_start | batches | accepted | rejected | processed | acceptance_pct | api_processed | file_processed |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-01-01 | 2 | 130 | 20 | 150 | 86.67 | 100 | 50 |
| 2026-02-01 | 2 | 80 | 20 | 100 | 80.00 | 80 | 20 |
| 2026-03-01 | 4 | 170 | 20 | 190 | 89.47 | 100 | 90 |
| **Grand total** | **8** | **380** | **60** | **440** | **86.36** | **280** | **160** |

The grand-total acceptance rate is **380 / 440 × 100 = 86.36%**, *not* the average of the three rounded monthly percentages. The grand-total row is a **separate reconciliation calculation**, not a fourth row emitted by the main query. Each month must satisfy `accepted + rejected = processed = api_processed + file_processed`.

**Common incorrect query:** `AVG(100.0 * accepted / NULLIF(accepted+rejected,0))` averages batch percentages, gives a different answer when batch sizes vary, and excludes zero-sized batches. This is not the contractual KPI.

## 4. Hands-on capstone (20 minutes)

1. Confirm that the endpoint is a disposable PostgreSQL 18 instance under your control. Verify Docker/container identity, host, port, database, and login **outside** the SQL script; never assume `sql_tutorials` is safe solely by name.
2. Open [the SQL lab](../labs/060-lab-06-monthly-kpi-report.sql) and inspect its entire contents before execution. It sets `ON_ERROR_STOP`, begins a transaction, uses local timeouts, checks version/database, creates a temporary table, inserts eight synthetic rows, runs the monthly and overall queries, performs deterministic assertions, and rolls back.
3. Run with psql, pointing explicitly at the isolated endpoint (adapt the host/port to your own disposable instance):

   ```bash
   psql -X -h 127.0.0.1 -p 5432 -U lab_user -d sql_tutorials \
     -v ON_ERROR_STOP=1 -f sql-tutorials/labs/060-lab-06-monthly-kpi-report.sql
   ```

   Do not assume port 5432 is isolated. Use only an endpoint independently confirmed as a disposable lab. Avoid passwords on command lines.
4. Compare all three month rows with the table above. The overall totals must be **8 / 380 / 60 / 440 / 86.36**. The zero-sized batch 7 must show a **NULL** batch acceptance percentage.
5. Confirm the psql process exit code is zero and the script ends with `ROLLBACK`. A success notice is only an execution assertion **when captured from a real run**; its presence in the source is not evidence.
6. **Exercises:** (A) explain why the February 1 midnight batch is excluded from January; (B) derive the March file total (90); (C) explain why the March batch count is 4 even though one batch has zero records; (D) design a data-quality alert for a new source system `stream`; (E) explain why the report should not join raw batch rows to a one-to-many error-detail table before aggregation.

**Expected exercise answers:** (A) half-open UTC time buckets; (B) 50 + 40; (C) `COUNT(*)` counts batches, not processed records; (D) reject/quarantine unknown source categories or add an explicit unknown bucket and reconcile totals; (E) one-to-many joins multiply batch-level counts, so aggregate detail first or report at a consistent grain.

## 5. Troubleshooting, correctness, and operational guardrails (5 minutes)

| Symptom | Cause | Safe investigation |
|---|---|---|
| `division by zero` | Missing `NULLIF` | Inspect denominator; zero-processed batches should yield NULL |
| Monthly totals exceed source totals | Join fan-out or overlapping windows | Recheck grain and time bounds; compare source and grouped sums |
| Missing/extra month | UTC versus local-time grouping | Inspect timezone and midnight boundary rows |
| NULL/zero confusion | Empty aggregates or zero-sized batches | State the KPI contract explicitly; do not silently fill missing values |
| Query blocked | Wrong version or database | Stop; verify endpoint identity and use the correct disposable lab |
| Script exits nonzero | Failed assertion, syntax, permissions, timeout | Preserve error output, diagnose, rerun only in isolated lab |

**DBRE/SRE acceptance checklist:** Record PostgreSQL version, host/port/container identity, command, UTC timestamp, SQL file commit, stdout/stderr, exit code, assertion results, and rollback evidence. Avoid capturing secrets. Verify that the eight fixture rows were never persisted. A transaction rollback is not a substitute for verifying that the target is nonproduction. For larger data, examine index access, aggregation memory, scan cost, and query plan in a separately approved performance exercise; do not run load tests against production.

## 6. Review questions with answers (5 minutes)

**Q1. What is the output grain?** One UTC calendar month, not one batch.

**Q2. Why use `SUM(accepted)/SUM(processed)`?** It weights by actual processed volume, avoiding misleading averages of rates.

**Q3. What does a NULL percentage for batch 7 mean?** Zero records were processed; the ratio is mathematically undefined.

**Q4. Why use `CASE` for source breakdowns?** Conditional sums provide broadly portable fixed-category pivoting and make category accounting explicit.

**Q5. What is needed before claiming PostgreSQL 18 runtime validation?** Actual execution on an independently verified isolated PostgreSQL 18 instance with reproducible version/endpoint evidence, successful assertions, exit code, and rollback proof.

## References and next chapter

- [PostgreSQL 18 — Aggregate functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [PostgreSQL 18 — Date/time functions](https://www.postgresql.org/docs/18/functions-datetime.html)
- [PostgreSQL 18 — Conditional expressions](https://www.postgresql.org/docs/18/functions-conditional.html)
- [PostgreSQL 18 — Transactions](https://www.postgresql.org/docs/18/tutorial-transactions.html)
- [SQL Tutorials master TOC](../MASTER-TOC.md) · [Status tracker](../STATUS-TRACKER.md)

**Next:** Chapter 061 — Scalar Subqueries and Derived Tables (Part 07).

**Publication is not runtime certification:** This chapter provides an executable candidate and statically reasoned expected outputs. Independent editorial review, comprehensive automated SQL syntax/link checks, and actual isolated PostgreSQL 18 runtime acceptance remain separate pending gates.
