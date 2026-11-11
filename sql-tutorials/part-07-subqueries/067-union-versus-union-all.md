# 067 — UNION versus UNION ALL

**Part 07 — Subqueries, CTEs & Set Operations** · **60 minutes** · **Audience:** SQL beginners, data engineers, DBREs and SREs.

**Prerequisite:** [066 — Recursive CTEs and Hierarchical Queries](066-recursive-ctes-and-hierarchical-queries.md). **Next:** 068 — INTERSECT and EXCEPT.

> **Safety:** All examples use fictional ingestion measurements defined inline. Run the [read-only PostgreSQL 18 lab](../labs/067-union-versus-union-all.sql) only against an independently verified disposable PostgreSQL 18 instance. Never use production credentials. A database-name or version check alone cannot establish isolation.

## 1. Outcomes and 60-minute agenda (5 minutes)

By the end, you can combine compatible query results, distinguish bag semantics from deduplication, predict how NULL and duplicate rows behave, explain why an ORDER BY applies to the final combined result, and choose safe ingestion and reconciliation patterns.

| Activity | Minutes |
|---|---:|
| Objectives, synthetic scenario, safety | 5 |
| Set operators and portability | 10 |
| Guided examples and expected output | 15 |
| Hands-on exercises | 20 |
| Validation, troubleshooting | 5 |
| Review questions and answers | 5 |

**Scenario:** Two fictional telemetry feeds report processed record counts by region and channel. The feeds may overlap; some events are repeated. A DBRE/SRE wants both an event-preserving audit and a distinct-row inventory. These are *different questions*.

## 2. Concepts and syntax (10 minutes)

`UNION ALL` concatenates rows from both inputs, preserving duplicates. `UNION` removes duplicate **complete output rows**; it does not deduplicate by a business key unless the selected columns define that key. Both operators require the same number of columns and compatible data types in corresponding positions. Column names come from the first query in PostgreSQL; align aliases and explicit casts where needed.

```sql
SELECT region, channel, processed FROM first_feed
UNION ALL
SELECT region, channel, processed FROM second_feed;

SELECT region, channel, processed FROM first_feed
UNION
SELECT region, channel, processed FROM second_feed;
```

**Portable SQL:** `UNION` and `UNION ALL` are widely supported standard SQL. SQL rows have multiset ("bag") semantics by default. For set-operation duplicate elimination, two rows with NULLs in the same positions are considered duplicates, unlike `NULL = NULL` in a WHERE predicate. Do not assume that either operator preserves input order. Add a final `ORDER BY` for presentation.

**PostgreSQL-specific lab details:** `VALUES` CTE fixtures, `::integer` casts, `BEGIN READ ONLY`, `SET LOCAL`, and `psql` directives are used for safe isolated exercises. Other engines vary in casting and transaction syntax. `UNION` may require sorting or hashing to remove duplicates, but the optimizer can choose different plans. Do not claim `UNION ALL` is always faster without measurement.

## 3. Guided examples (15 minutes)

### A. Define the synthetic feeds

```sql
WITH api(region, channel, processed) AS (
 VALUES ('East','api',40), ('West','api',30),
        ('East','api',40), ('North','api',NULL::integer)
), file_feed(region, channel, processed) AS (
 VALUES ('East','file',40), ('West','file',20),
        ('South','file',10), ('North','api',NULL::integer)
)
SELECT region, channel, processed FROM api
UNION ALL
SELECT region, channel, processed FROM file_feed
ORDER BY region, channel, processed NULLS LAST;
```

**Expected:** 8 rows. `('East','api',40)` occurs twice; `('North','api',NULL)` occurs twice. `SUM(processed)` is 180 because SUM ignores NULL. The ordering clause `NULLS LAST` is PostgreSQL-supported syntax and is not uniformly portable.

### B. Deduplicate full rows

Replace `UNION ALL` with `UNION` in the previous query. **Expected:** 6 rows; East/api/40 and North/api/NULL each appear once. The numeric sum is 140. Neither result is automatically "correct": the two East/api/40 records might be distinct real events with identical measurements, while the North rows may be duplicate ingestion.

### C. Count the difference without losing evidence

```sql
WITH api(region, channel, processed) AS (
 VALUES ('East','api',40), ('West','api',30),
        ('East','api',40), ('North','api',NULL::integer)
), file_feed(region, channel, processed) AS (
 VALUES ('East','file',40), ('West','file',20),
        ('South','file',10), ('North','api',NULL::integer)
), combined AS (
 SELECT region,channel,processed FROM api
 UNION ALL
 SELECT region,channel,processed FROM file_feed
)
SELECT region,channel,processed,COUNT(*) AS occurrences
FROM combined
GROUP BY region,channel,processed
HAVING COUNT(*) > 1
ORDER BY region,channel;
```

**Expected:** East/api/40 has 2 occurrences; North/api/NULL has 2. This is a **duplicate-row investigation**, not proof that either pair should be deleted.

### D. Provenance and business keys

If the requirement is to preserve *source evidence*, add `source_system` and a stable event identifier to the inputs before combining. Then use `UNION ALL` and investigate event IDs, arrival times, and source-specific deduplication rules. Adding a source label changes which rows are duplicates under `UNION`; it is not a substitute for defining a canonical event key.

For operational reporting, reconcile input counts and totals before any deduplication. `COUNT(*)` counts NULL-bearing rows; `COUNT(processed)` does not. If the business measure is event volume, never use `UNION` merely to make the result smaller.

## 4. Hands-on lab (20 minutes)

Run [the complete lab SQL](../labs/067-union-versus-union-all.sql) through `psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/067-union-versus-union-all.sql` using a **verified disposable endpoint**. Supply your own isolated connection parameters; do not embed passwords in scripts. The lab checks PostgreSQL major version and database name, applies transaction-local timeouts, uses only inline synthetic data, fails closed if assertions fail, and rolls back.

1. Predict `UNION ALL` row count and sum before executing: **8 and 180**.
2. Predict `UNION` row count and sum: **6 and 140**.
3. Find repeated complete rows: **two groups**, each occurring twice.
4. Add a `source_system` column to both SELECT arms and observe how provenance changes deduplication. Explain why it cannot identify duplicate business events by itself.
5. Change one `East/api/40` measurement to 41 in a scratch copy of the inline fixture; predict that the distinct row count increases to **7** while `UNION ALL` stays at **8**. Restore the original fixture for the acceptance checks.

**Acceptance:** Every Boolean check in the SQL lab must be true and the fail-closed assertion must complete without error. This is a *specified expected result*, not a claim that the lab has been executed.

## 5. Troubleshooting and operational guardrails (5 minutes)

| Symptom | Likely cause | Safe response |
|---|---|---|
| Different column-count error | SELECT arms have different widths | Align column count and order |
| Type resolution error | Incompatible positional types | Cast explicitly to agreed types |
| Rows unexpectedly disappear | `UNION` removes identical full rows | Use `UNION ALL` for event preservation |
| NULL rows collapse | Set operators treat matching NULL positions as duplicates | Preserve event keys and source metadata |
| Results appear in different order | No final deterministic ORDER BY | Sort final combined result with tie-breakers |
| Query uses more CPU/memory | Duplicate elimination may sort/hash | Compare plans and row counts in isolation; no production benchmarking |

Avoid `SELECT *` in production set operations: schema changes can shift positional alignment. Confirm column semantics, not just compatible types. Never use this lesson as authorization to remove production records.

## 6. Review questions with answers (5 minutes)

1. **Does UNION ALL remove duplicate rows?** No, it preserves all rows.
2. **Does UNION deduplicate by event ID?** Only if the selected full-row projection uniquely represents that event ID; otherwise it compares all selected output columns.
3. **Why do two North/api/NULL rows collapse under UNION?** Duplicate elimination treats NULLs in corresponding positions as not distinct.
4. **Can either operator guarantee output order?** No. Use a final ORDER BY.
5. **Why is UNION risky for an ingestion audit?** Different legitimate events can share identical selected values, silently reducing counts and sums.
6. **When might UNION be appropriate?** When the explicit requirement is a distinct set of complete projected rows, and deduplication semantics have been reviewed.

## References and next lesson

- [PostgreSQL 18 — Combining Queries: UNION, INTERSECT, EXCEPT](https://www.postgresql.org/docs/18/queries-union.html)
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — VALUES](https://www.postgresql.org/docs/18/sql-values.html)
- [PostgreSQL 18 — Sorting Rows](https://www.postgresql.org/docs/18/queries-order.html)
- [Master TOC](../MASTER-TOC.md) · [Part 07 next: 068 — INTERSECT and EXCEPT](../MASTER-TOC.md#part-07--subqueries-ctes--set-operations)

**Validation status:** Authored for publication; targeted static arithmetic/semantic review only. Independent editorial review, comprehensive syntax/link QA, and actual isolated PostgreSQL 18 runtime validation remain pending until separately evidenced.
