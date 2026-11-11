# 069 — Refactor Complex SQL for Readability and Correctness

**Part 07 — Subqueries, CTEs & Set Operations** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBREs/SREs.

**Prerequisite:** [068 — INTERSECT and EXCEPT](068-intersect-and-except.md). **Next:** [070 — Lab 07: multi-level organizational hierarchy](../MASTER-TOC.md#part-07--subqueries-ctes--set-operations).

> **Safety:** All examples use fictional inline data. Run the [PostgreSQL 18 read-only lab](../labs/069-refactor-complex-sql.sql) only on an independently confirmed disposable instance named `sql_tutorials`. Database/version checks cannot establish isolation. Never connect with production credentials.

## 1. Learning objectives and schedule (5 minutes)

You will learn to name the business grain, split long queries into meaningful stages, prevent join fan-out, compare old and new results in both directions, handle NULLs and integer division, and distinguish readability improvements from measured performance gains.

| Activity | Minutes |
|---|---:|
| Outcomes, safety and grain | 5 |
| Refactoring principles and SQL portability | 10 |
| Guided original/refactored examples | 15 |
| Hands-on isolated lab | 20 |
| Troubleshooting and acceptance | 5 |
| Review questions and answers | 5 |

**Scenario:** Six fictional ingestion batches record accepted and rejected rows. The report requires **one row per region**, total accepted, rejected, processed, and a weighted acceptance percentage. We must not accidentally average per-batch percentages or multiply records by joining to a one-to-many alert table.

## 2. Concepts: make correctness visible (10 minutes)

Before rewriting, record a **contract**: input columns, filtering, output grain, output types, NULL policy, ordering, and expected values. A CTE (`WITH`) names a query stage, not a guarantee of materialization or improved speed. Choose names such as `batch_source`, `validated_batches`, and `region_totals`, rather than `a`, `b`, `tmp1`. Keep the number of stages purposeful.

A reliable refactoring sequence:

1. Freeze the original query and capture a baseline of rows, totals, and representative edge cases.
2. Identify each relation's grain and join cardinality. A batch-to-alert join can multiply batch measures.
3. Move reusable expressions into named CTEs; apply filters deliberately before aggregation.
4. Use `COALESCE` only when the business meaning of missing data is defined. Do not silently turn unknown metrics into zero.
5. Compare **both directions** of old/new output using `EXCEPT` and separately compare row counts; standard `EXCEPT` removes duplicates, so for duplicate-sensitive outputs use `EXCEPT ALL` where supported, or compare grouped multiplicities.
6. Check numerical reconciliation and NULL behavior. Benchmark with the same inputs and environment; never assume a CTE is faster.

**Portable SQL:** `WITH`, `CASE`, `GROUP BY`, `NULLIF`, `COALESCE`, `UNION ALL`, and `EXCEPT` are broadly standard, subject to vendor support. The inline `VALUES` relation and its column-alias syntax can differ across systems. PostgreSQL-specific lab syntax includes `::numeric`, `BEGIN READ ONLY`, `SET LOCAL`, `NULLS LAST`, and `psql` meta-commands. PostgreSQL 18 may inline side-effect-free CTEs; `MATERIALIZED` / `NOT MATERIALIZED` are PostgreSQL-specific controls. Review actual plans rather than assuming execution order.

## 3. Walkthrough: original and refactored queries (15 minutes)

Our source rows are `(batch_id,region,channel,accepted,rejected)`:

| Batch | Region | Channel | Accepted | Rejected |
|---:|---|---|---:|---:|
| 1 | East | api | 80 | 20 |
| 2 | East | file | 40 | 10 |
| 3 | West | api | 60 | 0 |
| 4 | West | file | 30 | 10 |
| 5 | East | api | 20 | 0 |
| 6 | West | file | 10 | 20 |

### Before: correct but crowded

```sql
WITH batches(batch_id, region, channel, accepted, rejected) AS (
 VALUES (1,'East','api',80,20),(2,'East','file',40,10),
        (3,'West','api',60,0),(4,'West','file',30,10),
        (5,'East','api',20,0),(6,'West','file',10,20)
)
SELECT region, SUM(accepted) AS accepted,
       SUM(rejected) AS rejected,
       SUM(accepted + rejected) AS processed,
       ROUND(100.0 * SUM(accepted)
             / NULLIF(SUM(accepted + rejected),0),2) AS acceptance_pct
FROM batches
GROUP BY region
ORDER BY region;
```

**Expected:** East `140,30,170,82.35`; West `100,30,130,76.92`. Across regions: accepted 240, rejected 60, processed 300; **weighted** acceptance is `80.00%`. The simple mean of the two region percentages is **not** the global acceptance percentage.

### After: stages communicate the contract

```sql
WITH batches(batch_id, region, channel, accepted, rejected) AS (
 VALUES (1,'East','api',80,20),(2,'East','file',40,10),
        (3,'West','api',60,0),(4,'West','file',30,10),
        (5,'East','api',20,0),(6,'West','file',10,20)
),
validated_batches AS (
 SELECT batch_id, region, accepted, rejected,
        accepted + rejected AS processed
 FROM batches
 WHERE accepted >= 0 AND rejected >= 0
),
region_totals AS (
 SELECT region, SUM(accepted) AS accepted,
        SUM(rejected) AS rejected, SUM(processed) AS processed
 FROM validated_batches
 GROUP BY region
)
SELECT region, accepted, rejected, processed,
       ROUND(100.0 * accepted / NULLIF(processed,0),2) AS acceptance_pct
FROM region_totals
ORDER BY region;
```

This example's values are all valid; **the filter is a policy choice** and would change results if invalid rows existed. For real pipelines, quarantine and count rejected-invalid input instead of quietly dropping it. Prefer a separate quality assertion proving no invalid rows before treating the rewrite as equivalent.

### Common wrong rewrite: alert fan-out

If batch 1 has two alert records, `JOIN alerts USING(batch_id)` produces two copies of batch 1. Summing batch measures after this join inflates totals. For a Boolean “has alert” condition, use `EXISTS`; for alert counts, pre-aggregate alerts **per batch** before joining. Never fix incorrect fan-out with an unexplained `DISTINCT`.

## 4. Hands-on lab (20 minutes)

Run [069-refactor-complex-sql.sql](../labs/069-refactor-complex-sql.sql) in an independently verified disposable PostgreSQL 18 database:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/069-refactor-complex-sql.sql
```

The script uses `BEGIN READ ONLY`, local timeouts, synthetic `VALUES`, explicit database/version checks, a two-way set comparison, count/totals assertions, and `ROLLBACK`. It creates no persistent objects.

**Exercises:**

1. Run original and staged queries; predict two region rows and exact values above.
2. Check that `old EXCEPT new` and `new EXCEPT old` each produce zero rows.
3. Explain why `COUNT(*)` must also be checked when using distinct set comparisons.
4. Add a second alert for batch 1 to a *scratch copy* of the fixture. Compare a direct join with `EXISTS` and identify the overcount.
5. Add an invalid negative accepted value in a scratch copy. Observe that the validation filter changes the dataset; design a separate rejected-input count.
6. Explain why a query with `NULLIF(processed,0)` returns NULL rather than failing on a zero denominator.

**Expected acceptance:** six batches, two regions, accepted 240, rejected 60, processed 300, East 82.35%, West 76.92%, overall 80.00%, zero differences in both directions, and all Boolean assertions true. These are **statically derived expectations**, not runtime evidence.

## 5. Troubleshooting and operational safeguards (5 minutes)

| Symptom | Likely cause | Safe investigation |
|---|---|---|
| Totals increase after refactor | One-to-many join fan-out | Compare input/output row counts and join key multiplicities |
| New rows missing | Filter moved or NULL predicate changed | Compare old/new sets in both directions; count excluded rows |
| Percentages disagree | Averaged ratios instead of weighted totals | Divide total accepted by total processed |
| Results match but ordering differs | No final ORDER BY | Sort final output explicitly |
| Query slower | Different optimizer choices or repeated evaluation | Inspect `EXPLAIN` on isolated data; do not assume CTE improves performance |
| Set comparison misses duplicates | Distinct `EXCEPT` | Use `EXCEPT ALL` when supported or compare grouped row frequencies |

DBRE/SRE review checklist: establish isolated endpoint, use least privilege, record query and schema versions, baseline row counts and totals, review the plan before and after, set timeouts, and preserve test evidence. Never benchmark with intrusive `EXPLAIN ANALYZE` against production without approval; it executes the query.

## 6. Review questions with answers (5 minutes)

**Q1. Does splitting SQL into CTEs guarantee better performance?** No; CTEs primarily improve organization, and optimizer behavior varies.

**Q2. Why compare both directions of `EXCEPT`?** To detect rows present only in either version.

**Q3. Why are distinct set comparisons insufficient for bag semantics?** They can hide differing duplicate multiplicities.

**Q4. How do you prevent double-counting batch metrics after joining alerts?** Use `EXISTS` for presence or aggregate alerts to batch grain before joining.

**Q5. What is the overall acceptance percentage?** `240 / 300 × 100 = 80.00%`; do not average the two regional percentages.

**Q6. Can you claim PostgreSQL 18 validation from reviewing the SQL text?** No; run on an isolated PostgreSQL 18 instance and retain reproducible output and version evidence.

## References and next step

- [PostgreSQL 18 — WITH queries](https://www.postgresql.org/docs/18/queries-with.html)
- [PostgreSQL 18 — Combining queries](https://www.postgresql.org/docs/18/queries-union.html)
- [PostgreSQL 18 — Aggregate functions](https://www.postgresql.org/docs/18/functions-aggregate.html)
- [PostgreSQL 18 — EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)
- [Chapter 070 — Lab 07](../MASTER-TOC.md#part-07--subqueries-ctes--set-operations) — apply refactoring to a hierarchical query.

**Publication state:** authored material; independent editorial review, comprehensive syntax/link QA, and isolated PostgreSQL 18 runtime acceptance pending.
