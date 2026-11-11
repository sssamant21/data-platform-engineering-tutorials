# 068 — INTERSECT and EXCEPT (MINUS in some systems)

**Part 07 — Subqueries, CTEs & Set Operations** · **60 minutes** · **Audience:** beginners, data engineers, DBREs and SREs.

**Prerequisite:** [067 — UNION versus UNION ALL](067-union-versus-union-all.md). **Next:** [069 — Refactor complex SQL](../MASTER-TOC.md#part-07--subqueries-ctes--set-operations).

> **Safety:** Only fictional inline values. Use the [PostgreSQL 18 read-only lab](../labs/068-intersect-except-set-operations.sql) on an independently verified disposable instance. Never use production credentials. Database name and version guards alone cannot prove isolation.

## 1. Objectives and schedule (5 minutes)

After this lesson you can identify shared rows with `INTERSECT`, left-only rows with `EXCEPT`, explain duplicate and NULL handling, reason about directionality, and apply set operations to ingestion reconciliation without deleting data.

| Activity | Minutes |
|---|---:|
| Outcomes and safety | 5 |
| Concepts and dialects | 10 |
| Guided examples | 15 |
| Hands-on lab | 20 |
| Validation and troubleshooting | 5 |
| Review answers | 5 |

**Scenario:** A fictional source feed contains event IDs `101,102,102,103,104,NULL`; a fictional warehouse snapshot contains `102,103,105,NULL`. A NULL is an *unknown event ID*, not a real event key. We retain it to demonstrate set semantics, then exclude it in a production-style key reconciliation.

## 2. Concepts and portability (10 minutes)

`INTERSECT` returns distinct complete rows present in both queries. `EXCEPT` returns distinct complete rows in the **left** query but absent from the right. Reverse the inputs to investigate warehouse-only records. Both operations default to duplicate elimination; matching NULL positions count as *not distinct* for set operations, unlike `NULL = NULL` in a WHERE predicate.

```sql
SELECT event_id FROM source_feed
INTERSECT
SELECT event_id FROM warehouse_feed;

SELECT event_id FROM source_feed
EXCEPT
SELECT event_id FROM warehouse_feed;
```

Both arms must have the same number of columns with compatible positional types. Compare the *same business grain* (usually stable event IDs), not unrelated projected measurements. An `ORDER BY` on the final result is needed for deterministic display. Parenthesize mixed set operations to express intended precedence; PostgreSQL binds `INTERSECT` more tightly than `UNION` and `EXCEPT`.

**Portable SQL:** `INTERSECT` and `EXCEPT` are standard SQL features, although dialect/version support differs. PostgreSQL 18 supports `INTERSECT ALL` and `EXCEPT ALL`, which preserve multiplicity according to minimum and positive count differences respectively. These `ALL` variants are not universally available. Oracle uses `MINUS` as a synonym for `EXCEPT` in supported versions; check the target version. SQL Server supports `INTERSECT` and `EXCEPT`, but not the `ALL` forms. MySQL 8.0.31+ supports `INTERSECT` and `EXCEPT`; older versions require alternative patterns. Test the target dialect rather than assuming portability.

**NULL warning:** `NOT IN (subquery)` can yield UNKNOWN when the subquery contains NULL; `EXCEPT` uses set comparison semantics. For keyed anti-matching, `NOT EXISTS` is often a readable alternative, with explicit NULL-key policies.

## 3. Guided examples (15 minutes)

The examples use CTEs as synthetic, ephemeral fixtures:

```sql
WITH source_feed(event_id) AS (
 VALUES (101), (102), (102), (103), (104), (NULL::integer)
), warehouse_feed(event_id) AS (
 VALUES (102), (103), (105), (NULL::integer)
)
SELECT event_id FROM source_feed
INTERSECT
SELECT event_id FROM warehouse_feed
ORDER BY event_id NULLS LAST;
```

**Expected:** 3 rows: `102,103,NULL`. The duplicate 102 collapses.

Change `INTERSECT` to `EXCEPT`: **expected source-only** `101,104` (2 rows). Reverse source and warehouse arms: **expected warehouse-only** `105` (1 row). Neither operation proves whether an event is lost, delayed, filtered, or intentionally excluded; it only compares the snapshots.

### Duplicate-aware reconciliation

```sql
WITH source_feed(event_id) AS (
 VALUES (101), (102), (102), (103), (104), (NULL::integer)
), warehouse_feed(event_id) AS (
 VALUES (102), (103), (105), (NULL::integer)
)
SELECT event_id FROM source_feed
EXCEPT ALL
SELECT event_id FROM warehouse_feed
ORDER BY event_id NULLS LAST;
```

**Expected:** `101,102,104` (3 rows): the second 102 remains because source contains two copies and warehouse one. `INTERSECT ALL` yields `102,103,NULL` (3 rows). `EXCEPT ALL` in the reverse direction yields `105` (1 row).

### Operational key policy

For ingestion reconciliation, first exclude or quarantine unknown IDs with `WHERE event_id IS NOT NULL`, then compare distinct IDs. Keep separate metrics for NULL IDs and duplicate counts; do not silently erase them. In this fixture, source has 6 raw rows, 5 known-key rows, 4 distinct known IDs, and 1 NULL; warehouse has 4 raw rows, 3 known-key rows, 3 distinct known IDs, and 1 NULL.

## 4. Hands-on lab (20 minutes)

Execute [068 SQL lab](../labs/068-intersect-except-set-operations.sql) with `psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/068-intersect-except-set-operations.sql`, after verifying the endpoint is disposable and PostgreSQL 18. No credentials are embedded. The script starts a read-only transaction, applies local timeouts, checks database/version, runs queries and fail-closed assertions, then rolls back.

1. Predict the distinct intersection: **102, 103, NULL**.
2. Predict source-only and warehouse-only distinct IDs: **101/104** and **105**.
3. Predict source `EXCEPT ALL` warehouse: **101/102/104**.
4. Modify a scratch copy to add a second `(103)` to warehouse. Predict that distinct set results stay unchanged; `INTERSECT ALL` remains 3 rows because source has only one 103.
5. Exclude NULL keys from both sides. Confirm intersection **102/103**, source-only **101/104**, warehouse-only **105**; report unknown-key counts separately.

**Acceptance:** Every Boolean check is true, and the assertion query returns `1`. These are **predicted**, not runtime-observed, outcomes.

## 5. Troubleshooting and DBRE/SRE safeguards (5 minutes)

| Symptom | Cause | Safe response |
|---|---|---|
| Unexpected missing duplicate | Default set semantics are distinct | Compare `ALL` variants or `GROUP BY` counts |
| Wrong side of discrepancy | `EXCEPT` is directional | Run both directions, label clearly |
| NULL appears as shared | NULLs are not distinct for set comparison | Quarantine unknown IDs, track separately |
| Different results between dialects | Unsupported `ALL` / `MINUS` syntax | Check version, rewrite with counts |
| Type or column mismatch | Positional schema incompatibility | Explicitly select/cast aligned columns |
| Inconsistent snapshots | Feeds captured at different cutoffs | Compare same watermark and snapshot scope |

Never infer deletions or trigger repair jobs from one set difference. Confirm ingestion lag, CDC ordering, time windows, retention, and event-key uniqueness. On large tables, inspect plans and resource impact in staging before operational use. The lab performs no writes.

## 6. Review questions and answers (5 minutes)

1. **What does INTERSECT return?** Distinct complete rows common to both inputs.
2. **Is EXCEPT symmetric?** No; switching sides changes the answer.
3. **How are NULLs treated?** Corresponding NULLs compare as not distinct during set duplicate elimination.
4. **Why might EXCEPT ALL retain 102?** Source contains two 102s and warehouse one, leaving one unmatched occurrence.
5. **Can a discrepancy prove data loss?** No; watermark differences, lag and filtering may explain it.
6. **Why compare event IDs rather than all columns?** The business key defines reconciliation grain; different metadata could make identical events look different.

## References and navigation

- [PostgreSQL 18 — Combining Queries](https://www.postgresql.org/docs/18/queries-union.html)
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — VALUES](https://www.postgresql.org/docs/18/sql-values.html)
- [MySQL 8.0 — INTERSECT](https://dev.mysql.com/doc/refman/8.0/en/intersect.html)
- [Master TOC](../MASTER-TOC.md) · [SQL Tutorials README](../README.md)

**Validation status:** Authored; targeted static arithmetic and syntax inspection only. Independent editorial review, comprehensive automated link/SQL checks, and actual isolated PostgreSQL 18 runtime execution remain pending.
