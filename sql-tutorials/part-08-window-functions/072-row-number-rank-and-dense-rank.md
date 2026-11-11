# 072 — ROW_NUMBER, RANK, and DENSE_RANK

**Part 08 — Window Functions & Advanced Analytics** · **60 minutes** · **Audience:** beginners, data engineers, analysts, DBRE/SRE.

**Prerequisites:** [071 — Window-function anatomy](071-window-function-anatomy-over-partition-by-order-by.md), [017 — Deterministic sorting](../part-02-filtering/017-order-by-and-deterministic-sorting.md). **Next:** [073 — LAG and LEAD](../MASTER-TOC.md#part-08--window-functions--advanced-analytics).

**Safety:** Fictional ingestion batches only. The [PostgreSQL 18 read-only lab](../labs/072-row-number-rank-dense-rank.sql) uses inline VALUES, a read-only transaction, local timeouts, fail-closed checks, and ROLLBACK. Run only against an independently verified disposable database with a least-privilege lab account; a database-name check is not proof of isolation.

## 1. Objectives and agenda (5 minutes)

By the end, explain how three ranking functions differ on ties, produce deterministic top-N reports, handle NULL ordering explicitly, and detect unsafe deduplication patterns.

| Segment | Time |
|---|---:|
| Objectives and safeguards | 5 min |
| Concepts and portable syntax | 10 min |
| Guided examples | 15 min |
| Hands-on lab and exercises | 20 min |
| Troubleshooting and validation | 5 min |
| Review with answers | 5 min |

## 2. Core concepts (10 minutes)

Ranking functions return a value for **each input row** without collapsing the row grain. The window `PARTITION BY` restarts rankings within each service; the window `ORDER BY` defines the comparison.

- `ROW_NUMBER()` assigns 1, 2, 3, ... even when sort values tie. Include a unique secondary key for repeatable results.
- `RANK()` gives peers the same rank, leaving gaps after ties: 1, 1, 3.
- `DENSE_RANK()` gives peers the same rank without gaps: 1, 1, 2.
- For `RANK` and `DENSE_RANK`, peers are rows equal on **all window ORDER BY expressions**. Adding `batch_id` to their window ordering breaks score ties and changes their meaning.
- Window `ORDER BY` does not guarantee the final display order; use an outer `ORDER BY`. These ranking functions do not use a custom frame.

**Portable SQL:** All three functions and `OVER (PARTITION BY ... ORDER BY ...)` are widely supported. NULL sort defaults differ by platform. PostgreSQL supports `NULLS LAST`; for more portable explicit behavior, order by `CASE WHEN records IS NULL THEN 1 ELSE 0 END, records DESC` (and append `batch_id` only to the `ROW_NUMBER` ordering).

## 3. Guided scenario and examples (15 minutes)

A fictional ingestion platform tracks eight batches. Grain: **one row per batch**. `records` is a synthetic count; one FILE batch has unknown volume (`NULL`), which is not zero.

| batch_id | service | records |
|---:|---|---:|
| 1 | api | 90 |
| 2 | api | 70 |
| 3 | api | 90 |
| 4 | api | 40 |
| 5 | file | 60 |
| 6 | file | 60 |
| 7 | file | 30 |
| 8 | file | NULL |

The query below uses an explicit NULL-first discriminator and an independent tie-breaker only for row numbering:

```sql
WITH batches(batch_id,service,records) AS (
 VALUES (1,'api',90),(2,'api',70),(3,'api',90),(4,'api',40),
        (5,'file',60),(6,'file',60),(7,'file',30),(8,'file',NULL)
)
SELECT batch_id, service, records,
 ROW_NUMBER() OVER (
   PARTITION BY service
   ORDER BY CASE WHEN records IS NULL THEN 1 ELSE 0 END,
            records DESC, batch_id
 ) AS row_num,
 RANK() OVER (
   PARTITION BY service
   ORDER BY CASE WHEN records IS NULL THEN 1 ELSE 0 END,
            records DESC
 ) AS competition_rank,
 DENSE_RANK() OVER (
   PARTITION BY service
   ORDER BY CASE WHEN records IS NULL THEN 1 ELSE 0 END,
            records DESC
 ) AS dense_rank
FROM batches
ORDER BY service, row_num;
```

**Expected output (reasoned, not runtime-tested):**

| service | batch_id | records | row_num | competition_rank | dense_rank |
|---|---:|---:|---:|---:|---:|
| api | 1 | 90 | 1 | 1 | 1 |
| api | 3 | 90 | 2 | 1 | 1 |
| api | 2 | 70 | 3 | 3 | 2 |
| api | 4 | 40 | 4 | 4 | 3 |
| file | 5 | 60 | 1 | 1 | 1 |
| file | 6 | 60 | 2 | 1 | 1 |
| file | 7 | 30 | 3 | 3 | 2 |
| file | 8 | NULL | 4 | 4 | 3 |

**Top one batch per service:** Compute `ROW_NUMBER` in a CTE and filter `WHERE row_num = 1` outside it. This returns batch IDs **1 and 5**, with the lowest batch ID resolving each tie. **Top scoring ties:** Filter `RANK() = 1` instead; this returns IDs **1, 3, 5, 6**. Neither query changes data.

```sql
WITH batches(batch_id,service,records) AS (
 VALUES (1,'api',90),(2,'api',70),(3,'api',90),(4,'api',40),
        (5,'file',60),(6,'file',60),(7,'file',30),(8,'file',NULL)
), numbered AS (
 SELECT batch_id, service, records,
        ROW_NUMBER() OVER (
          PARTITION BY service
          ORDER BY CASE WHEN records IS NULL THEN 1 ELSE 0 END,
                   records DESC, batch_id
        ) AS rn
 FROM batches
)
SELECT service, batch_id, records
FROM numbered WHERE rn = 1
ORDER BY service;
```

**Important:** Do not use `ROW_NUMBER() = 1` to delete supposed duplicates unless the business key, retention rule, late-arrival policy, and tie-breaker have been independently approved. A ranking query is not evidence that records are safe to remove.

## 4. Hands-on lab (20 minutes)

Open [072-row-number-rank-dense-rank.sql](../labs/072-row-number-rank-dense-rank.sql). Verify the PostgreSQL 18 server endpoint, disposable database, and least-privilege role **before** running:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f 072-row-number-rank-dense-rank.sql
```

1. Predict the API rankings before executing SQL. Explain why batch 2 receives `RANK=3` but `DENSE_RANK=2`.
2. Run the full ranking query and verify eight rows with four per service.
3. Run the top-one query and verify IDs 1 and 5.
4. Run the tied-leader query and verify IDs 1, 3, 5, 6.
5. Verify that the unknown FILE record count sorts last and is not treated as zero.
6. Run the fail-closed acceptance statement; any mismatch must terminate with an error under `ON_ERROR_STOP=1`.
7. **Stretch:** change the outer display order to `batch_id`; verify ranking values do not change. Then add `batch_id` to the `RANK` window `ORDER BY` and explain why tied ranks disappear.

**Expected checks:** eight rows; row numbers 1–4 in each service; API and FILE rank vectors `[1,1,3,4]`; dense-rank vectors `[1,1,2,3]`; exactly two deterministic winners; four tied leaders; one NULL volume; no data modifications.

## 5. Troubleshooting and DBRE/SRE guardrails (5 minutes)

| Symptom | Likely cause | Safe response |
|---|---|---|
| Winner changes across executions | Nonunique `ROW_NUMBER` ordering | Add an approved stable unique tie-breaker |
| Tied ranks unexpectedly disappear | Unique key added to `RANK` order | Rank on the score only; tie-break `ROW_NUMBER` separately |
| `RANK` skips numbers | Competition ranking semantics | Use `DENSE_RANK` if contiguous ranks are required |
| NULL appears as best score | Vendor-specific NULL ordering | Make NULL placement explicit |
| `WHERE row_num=1` fails in same SELECT | Window values not available in WHERE | Use a CTE or derived table |
| Large partitions spill to disk | Sort and memory demand | Inspect `EXPLAIN` and temp-file metrics in approved staging; do not run unapproved production benchmarks |

**Operational uses:** top expensive queries per service, newest event per correlation key, duplicate investigation, and alert prioritization. For “newest” use an event timestamp plus a unique event ID; document late arrivals and time-zone interpretation. Never use synthetic query timings to claim production performance.

## 6. Review questions and answers (5 minutes)

**Q1. Which function assigns a unique ordinal to tied rows?** `ROW_NUMBER`, provided a deterministic total order is specified.

**Q2. Why does API batch 2 have `RANK=3`?** Two preceding batches tie at rank 1, so competition ranking skips rank 2.

**Q3. Why does API batch 2 have `DENSE_RANK=2`?** Dense ranking counts distinct score groups without gaps.

**Q4. How do you retain all highest-scoring tied batches?** Filter `RANK() = 1` in an outer query.

**Q5. Does the window's `ORDER BY` sort displayed rows?** No. Use the final query's `ORDER BY`.

**Q6. What is unsafe about using row numbers for production deduplication?** The selection rule may ignore business identity, concurrent updates, late events, or legitimate ties; review before any deletion.

## 7. References and validation status

- [PostgreSQL 18 — Window functions](https://www.postgresql.org/docs/18/functions-window.html)
- [PostgreSQL 18 — Window tutorial](https://www.postgresql.org/docs/18/tutorial-window.html)
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — Expressions and window syntax](https://www.postgresql.org/docs/18/sql-expressions.html#SYNTAX-WINDOW-FUNCTIONS)

**Status:** Authored and published; expected outputs manually derived. Targeted static review of SQL logic only. Independent editorial review, comprehensive automated link/syntax QA, and **actual isolated PostgreSQL 18 runtime execution** remain pending; no runtime evidence retained.
