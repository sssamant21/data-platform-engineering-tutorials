# 071 — Window-function Anatomy: OVER, PARTITION BY, ORDER BY

**Part 08 — Window Functions & Advanced Analytics** · **60 minutes** · **Audience:** SQL beginners, data engineers, analysts, DBRE/SRE.

**Prerequisites:** [052 — GROUP BY and aggregation grain](../part-06-aggregation/052-group-by-and-aggregation-grain.md), [065 — Common table expressions](../part-07-subqueries/065-common-table-expressions-with.md), and [Master TOC](../MASTER-TOC.md). **Next:** [072 — ROW_NUMBER, RANK, and DENSE_RANK](../MASTER-TOC.md#part-08--window-functions--advanced-analytics).

**Safety:** All example rows are fictional. Run the [PostgreSQL 18 lab](../labs/071-window-function-anatomy.sql) only on an independently confirmed disposable `sql_tutorials` database. It uses inline `VALUES`, a read-only transaction, local timeouts, assertions and `ROLLBACK`. A database-name guard alone cannot establish isolation.

## 1. Outcomes and agenda (5 minutes)

After this lesson, you can explain why window functions preserve row-level detail; distinguish `OVER ()`, `PARTITION BY`, and window `ORDER BY`; calculate per-service and global totals without collapsing rows; recognize default frame surprises; and validate an operational reconciliation report.

| Segment | Minutes |
|---|---:|
| Objectives, prerequisites, safety | 5 |
| Concepts and syntax | 10 |
| Guided examples | 15 |
| Hands-on lab and exercises | 20 |
| Troubleshooting and validation | 5 |
| Review and answers | 5 |

## 2. Core concepts and SQL anatomy (10 minutes)

A **window function** computes a value from a set of rows related to the current output row. Unlike `GROUP BY`, it normally **does not reduce the number of output rows**. The `OVER` clause describes that related set.

```sql
SUM(records) OVER ()                            -- all output rows
SUM(records) OVER (PARTITION BY service)         -- one partition per service
SUM(records) OVER (PARTITION BY service
                   ORDER BY batch_id
                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                                                  -- cumulative sum
```

- `OVER ()` uses the entire window input, so the same grand total appears on every row.
- `PARTITION BY service` divides rows into independent groups **without collapsing them**.
- `ORDER BY batch_id` *inside* `OVER` controls the sequence used by order-sensitive calculations; it **does not guarantee final result ordering**. Add a top-level `ORDER BY`.
- A **window frame** selects a subset of rows within a partition. For cumulative row-by-row sums, spell out `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` instead of relying on a default.
- Window ordering with ties requires care: `RANGE`-style default frames may include peers sharing the same order key, while `ROWS` counts physical rows. Use a unique, deterministic order key when possible.
- `GROUP BY` first aggregates to one row per group; window functions run on the rows available **after** grouping, filtering, and `HAVING` in the same query block. To filter on a window result, compute it in a CTE/subquery, then filter outside.

**Portability:** `OVER`, `PARTITION BY`, window `ORDER BY`, and `ROWS` frames are broadly supported SQL concepts; exact supported functions, frame defaults, and optimizer behavior differ by database. PostgreSQL's `::` cast, `VALUES` CTE conventions, `SET LOCAL`, and `psql` commands in the lab are platform-specific.

## 3. Synthetic operational scenario (15 minutes)

A fictional ingestion platform processes six batches across API and FILE services. The input grain is **one row per batch**, not one row per service.

| batch_id | service | records |
|---:|---|---:|
| 1 | api | 40 |
| 2 | api | 60 |
| 3 | file | 30 |
| 4 | file | 70 |
| 5 | api | 20 |
| 6 | file | 10 |

The total is **230**; API totals **120** and FILE totals **110**. The following query preserves six rows while adding context:

```sql
WITH batches(batch_id, service, records) AS (
  VALUES (1,'api',40),(2,'api',60),(3,'file',30),
         (4,'file',70),(5,'api',20),(6,'file',10)
)
SELECT batch_id, service, records,
       SUM(records) OVER () AS grand_total,
       SUM(records) OVER (PARTITION BY service) AS service_total
FROM batches
ORDER BY batch_id;
```

**Expected output:**

| batch_id | service | records | grand_total | service_total |
|---:|---|---:|---:|---:|
| 1 | api | 40 | 230 | 120 |
| 2 | api | 60 | 230 | 120 |
| 3 | file | 30 | 230 | 110 |
| 4 | file | 70 | 230 | 110 |
| 5 | api | 20 | 230 | 120 |
| 6 | file | 10 | 230 | 110 |

To calculate a running total **per service**, add an explicit frame:

```sql
WITH batches(batch_id, service, records) AS (
  VALUES (1,'api',40),(2,'api',60),(3,'file',30),
         (4,'file',70),(5,'api',20),(6,'file',10)
)
SELECT batch_id, service, records,
       SUM(records) OVER (
         PARTITION BY service ORDER BY batch_id
         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS service_running_total
FROM batches
ORDER BY batch_id;
```

**Expected running totals by batch ID:** 40, 100, 30, 100, 120, 110. They reset when a new service partition begins; the outer display interleaves the services.

**Compare with aggregation:** `SELECT service, SUM(records) FROM batches GROUP BY service` returns **two rows**, not six. Do not join that summary back to batches unless the join key is unique and the output grain is understood.

## 4. Hands-on PostgreSQL 18 lab (20 minutes)

Open [071-window-function-anatomy.sql](../labs/071-window-function-anatomy.sql). From the `sql-tutorials/labs/` directory, after verifying the connection points to an isolated PostgreSQL 18 training instance:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f 071-window-function-anatomy.sql
```

`-X` disables psql startup-file processing; it does not prove endpoint safety. Use a dedicated least-privilege lab role, inspect the server endpoint and credentials, and never use production connections.

1. Predict the global and per-service totals from the six rows before running the SQL.
2. Run the window query and confirm **six** output rows; check that all `grand_total` values are 230.
3. Inspect running totals; check the last API row is 120 and the last FILE row is 110.
4. Compare the two-row grouped summary against the six-row window output. Explain the different grains.
5. Execute the SQL acceptance assertions. A failed check deliberately raises an error, and `ON_ERROR_STOP=1` stops the script.
6. **Stretch:** change the final display ordering to `service, batch_id`. The calculated running totals must not change. Then try `COUNT(*) OVER (PARTITION BY service)` and predict 3 for every row.

**Expected acceptance:** six batches, grand total 230, two services, exact service totals, exact running totals, and no mismatch between the grouped and window-derived per-service totals. These are **statically reasoned expected results**, not proof of PostgreSQL 18 execution.

## 5. Troubleshooting and operational safeguards (5 minutes)

| Symptom | Cause | Response |
|---|---|---|
| Six input rows become two | Used `GROUP BY` instead of a window | Keep detail rows and use `OVER` |
| Running total unexpectedly jumps on tied keys | Default peer-aware frame | Use explicit `ROWS` frame and deterministic tie-breaker |
| Results appear in surprising order | Window `ORDER BY` is not final sorting | Add top-level `ORDER BY` |
| Window result rejected in `WHERE` | Window functions are evaluated after `WHERE` | Compute in CTE then filter outside |
| Slow query on large partitions | Sorting and memory pressure | Review plans, partition cardinality, work memory and spill metrics in staging; avoid unapproved load tests |
| Guard or assertion fails | Wrong endpoint/version or incorrect results | Stop; verify isolation and input contract; never bypass safety checks |

DBRE/SRE use cases include per-tenant workload totals, per-service ingestion volume, rolling telemetry, and duplicate-detection groundwork. Partitioning by a high-cardinality key can be expensive; validate plans and data volume before production adoption. No schema changes or index operations are performed here.

## 6. Review questions with answers (5 minutes)

**Q1. Why use a window function instead of `GROUP BY`?** To retain individual batch rows while attaching aggregate context.

**Q2. What does `OVER ()` mean?** The function sees all rows in its window input, subject to the query's earlier filtering and grouping.

**Q3. Does `ORDER BY` inside `OVER` sort final output?** No; add an outer `ORDER BY`.

**Q4. Why specify `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`?** It makes the cumulative frame explicit and avoids default peer-group surprises.

**Q5. What is the last running total for FILE?** 110, at batch 6.

**Q6. Can a synthetic lab certify production query performance?** No; it demonstrates semantics only. Production readiness requires representative workload testing, review, and approvals.

## 7. References and validation state

- [PostgreSQL 18 — Window functions tutorial](https://www.postgresql.org/docs/18/tutorial-window.html)
- [PostgreSQL 18 — Window function calls and frames](https://www.postgresql.org/docs/18/sql-expressions.html#SYNTAX-WINDOW-FUNCTIONS)
- [PostgreSQL 18 — Window functions reference](https://www.postgresql.org/docs/18/functions-window.html)
- [PostgreSQL 18 — SELECT processing](https://www.postgresql.org/docs/18/sql-select.html)

**Validation classification:** Chapter authored; expected outputs manually reasoned. Independent editorial review, comprehensive automated SQL syntax/link QA, and **actual isolated PostgreSQL 18 runtime validation** remain separate pending gates until evidenced. See [status tracker](../STATUS-TRACKER.md).
