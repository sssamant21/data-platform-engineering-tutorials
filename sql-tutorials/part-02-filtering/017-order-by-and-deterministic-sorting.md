# Chapter 017 — ORDER BY and Deterministic Sorting

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: 016](016-distinct-and-duplicate-handling.md) · [Next: 018 (planned)](../MASTER-TOC.md)
>
> **Part 02 — Filtering, Sorting & Conditional Logic** · **60 minutes** · **PostgreSQL 18 lab target**
>
> **Status:** Authored/published; targeted static checks only. Independent editorial review, comprehensive SQL syntax checks and isolated PostgreSQL 18 runtime validation pending.

## Learning objectives and agenda (0–5 minutes)

After this lesson, you can sort a result by one or more keys; choose ascending and descending directions; handle ties, NULLs, text collation and timestamp boundaries; distinguish deterministic ordering from unspecified row order; and apply sorting safely in data engineering and DBRE/SRE queries.

| Minutes | Topic |
|---|---|
| 0–5 | Objectives, prerequisites, safety |
| 5–15 | ORDER BY semantics and portable syntax |
| 15–30 | Worked synthetic examples |
| 30–50 | PostgreSQL 18 read-only lab |
| 50–55 | Troubleshooting and operational safeguards |
| 55–60 | Review questions and answers |

**Prerequisites:** [007 — SELECT](../part-01-fundamentals/007-select-fundamentals-retrieve-rows-and-columns.md), [009 — NULL](../part-01-fundamentals/009-data-types-null-and-explicit-type-conversion.md), [016 — DISTINCT](016-distinct-and-duplicate-handling.md), and [003 — isolated PostgreSQL 18 setup](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md).

## Key concepts and syntax (5–15 minutes)

**Portable SQL:** `ORDER BY expression ASC|DESC` sorts the final query result. `ASC` means ascending and is the default; `DESC` means descending. Specify direction independently for each key: `ORDER BY status ASC, amount DESC, order_id ASC`. The first key determines major groups; later keys resolve ties. An `ORDER BY` without a unique final key can still leave tied rows in unspecified order.

Without an outermost `ORDER BY`, SQL does **not** guarantee row order, even when a table has a primary key or an index. Ordering inside a CTE or subquery does not generally guarantee the final presentation order. A stable final tie-breaker is especially important for pagination, repeatable ETL extracts, incident timelines, and comparison tests.

**NULL portability:** PostgreSQL 18 sorts NULLs last with `ASC` and first with `DESC` by default; other databases differ. PostgreSQL supports `NULLS FIRST` and `NULLS LAST`. A broadly portable explicit alternative is `ORDER BY CASE WHEN resolved_at IS NULL THEN 1 ELSE 0 END, resolved_at ASC, event_id ASC`. Check actual dialect support and collation settings.

**Text sorting:** Case, accents, locale, and collation can change alphabetical ordering. Never assume cross-database bytewise order. PostgreSQL `COLLATE "C"` can provide a byte-oriented comparison for demonstrations; it is not a general cross-platform clause. A timestamp sort is chronological only when values are typed as timestamps, not free-form strings. An alias may be referenced in `ORDER BY` in standard SQL; prefer explicit names over positional `ORDER BY 2` for maintainability.

## Worked examples (15–30 minutes)

These are six **fictional** operational records. `event_id` is unique; `priority` and `created_at` have ties.

| event_id | service | priority | created_at (UTC) | resolved_at (UTC) |
|---:|---|---:|---|---|
| 101 | api | 2 | 2026-01-03 09:00 | NULL |
| 102 | ingest | 1 | 2026-01-03 09:05 | 2026-01-03 10:00 |
| 103 | api | 1 | 2026-01-03 09:05 | NULL |
| 104 | billing | 3 | 2026-01-02 20:00 | 2026-01-03 08:00 |
| 105 | ingest | 1 | 2026-01-03 09:05 | 2026-01-03 11:00 |
| 106 | api | 2 | 2026-01-04 07:00 | NULL |

### A. Sort highest-priority events first, then time and unique ID

In this example **priority 1 is most urgent**. Use ascending priority, ascending time, then ascending unique ID.

```sql
WITH events(event_id, priority, created_at) AS (
 VALUES
 (101,2,TIMESTAMP '2026-01-03 09:00'),
 (102,1,TIMESTAMP '2026-01-03 09:05'),
 (103,1,TIMESTAMP '2026-01-03 09:05'),
 (104,3,TIMESTAMP '2026-01-02 20:00'),
 (105,1,TIMESTAMP '2026-01-03 09:05'),
 (106,2,TIMESTAMP '2026-01-04 07:00')
)
SELECT event_id, priority, created_at
FROM events
ORDER BY priority ASC, created_at ASC, event_id ASC;
-- Expected IDs: 102, 103, 105, 101, 106, 104.
```

Without `event_id`, IDs 102, 103, and 105 tie. The database may return them in different orders after a plan change.

### B. Latest event first

```sql
WITH events(event_id, created_at) AS (
 VALUES (101,TIMESTAMP '2026-01-03 09:00'),
        (102,TIMESTAMP '2026-01-03 09:05'),
        (103,TIMESTAMP '2026-01-03 09:05'),
        (104,TIMESTAMP '2026-01-02 20:00'),
        (105,TIMESTAMP '2026-01-03 09:05'),
        (106,TIMESTAMP '2026-01-04 07:00')
)
SELECT event_id FROM events
ORDER BY created_at DESC, event_id DESC;
-- Expected IDs: 106, 105, 103, 102, 101, 104.
```

### C. Unresolved records first, NULL placement explicitly controlled

```sql
WITH events(event_id, resolved_at) AS (
 VALUES (101,NULL::timestamp),
        (102,TIMESTAMP '2026-01-03 10:00'),
        (103,NULL::timestamp),
        (104,TIMESTAMP '2026-01-03 08:00'),
        (105,TIMESTAMP '2026-01-03 11:00'),
        (106,NULL::timestamp)
)
SELECT event_id, resolved_at
FROM events
ORDER BY CASE WHEN resolved_at IS NULL THEN 0 ELSE 1 END,
         resolved_at ASC, event_id ASC;
-- Expected IDs: 101, 103, 106, 104, 102, 105.
```

Here NULL represents *unresolved*, a business rule, not an assumption that NULL always means “first.” In PostgreSQL, `ORDER BY resolved_at ASC NULLS FIRST, event_id ASC` produces the same ordering for this dataset. Be explicit when a business workflow depends on NULL placement.

### D. Sorting is not deduplication

`ORDER BY service, created_at` changes presentation, not row count. For a report requiring one record per service, first define the correct grain and a tie-breaking rule; do not assume sorting alone selects one winner. Similarly, `ORDER BY` inside a CTE does not guarantee the outer query's final order.

## Hands-on lab (30–50 minutes)

Use [Chapter 017 SQL lab](../labs/017-order-by-deterministic-sorting.sql) against an **independently verified disposable** PostgreSQL 18 database. The name/version check in the script is a second-line guard, not proof of isolation.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/017-order-by-deterministic-sorting.sql
```

The script uses `BEGIN READ ONLY`, `SET LOCAL statement_timeout`, synthetic `VALUES` data, explicit assertions and `ROLLBACK`. Expected outputs are `environment_assertion = 1` and `acceptance_assertion = 1`; these are **not observed runtime results**.

Practice tasks and answer key:

1. Sort events by priority (1 first), creation time and unique ID. **Answer:** 102, 103, 105, 101, 106, 104.
2. Sort newest events first and break timestamp ties by highest ID. **Answer:** 106, 105, 103, 102, 101, 104.
3. List unresolved events first, then resolved by oldest resolution time. **Answer:** 101, 103, 106, 104, 102, 105.
4. Sort by service name in PostgreSQL `COLLATE "C"`, then ID. **Answer:** 101, 103, 106 (api), 104 (billing), 102, 105 (ingest).
5. Sort by priority descending, then ID ascending. **Answer:** 104, 101, 106, 102, 103, 105.
6. Remove the final unique key from a sort. **Answer:** Tied rows have no guaranteed relative order; do not assert an exact sequence.
7. Compare a NULL-first CASE expression with PostgreSQL `NULLS FIRST`. **Answer:** They agree for the supplied data.
8. Confirm sorting does not change the six-row count. **Answer:** Six input and output rows.

## Troubleshooting, performance and DBRE/SRE safety (50–55 minutes)

| Symptom | Cause | Safe response |
|---|---|---|
| Rows move between repeated runs | Missing unique tie-breaker | Add stable, unique final sort key |
| NULLs appear in an unexpected position | Dialect-specific default | Use explicit CASE or supported NULLS FIRST/LAST |
| Text sort differs between systems | Collation/locale differences | Record collation and test representative values |
| Sorting appears slow | Sort can consume memory or spill to disk | Inspect EXPLAIN on synthetic data; cap workload |
| A CTE appears sorted but final result changes | Outer order not guaranteed | Put ORDER BY in outermost SELECT |
| Pagination repeats/skips rows | Ties or changing dataset | Use stable order and consistent snapshot; see Chapter 018/099 |

**Operational guardrails:** A read-only query can still use substantial CPU, memory and temporary disk. Do not run an unbounded sort on production tables as an exercise. Use synthetic bounded inputs, statement timeouts and approved environments. Indexes may sometimes satisfy an `ORDER BY`, but the planner is not required to use them. Do not interpret a particular physical plan as an ordering contract. For audit and incident evidence, include timestamps with an explicit timezone convention (UTC here), stable event IDs and query predicates. No production credentials, endpoints, or real records.

## Review questions and answers (55–60 minutes)

1. Does a SELECT without ORDER BY have a guaranteed order? **No.**
2. What is the default sort direction? **ASC.**
3. Does DESC on the first key apply to later keys? **No, each key has its own direction.**
4. Why append a unique event ID? **To make ties deterministic.**
5. Is NULL placement identical across SQL engines? **No.**
6. How can NULL placement be made broadly portable? **ORDER BY CASE WHEN col IS NULL THEN ... END, col.**
7. Does ORDER BY remove duplicate rows? **No.**
8. Is a CTE's internal ORDER BY enough to guarantee final output order? **No.**
9. Why might text order differ between databases? **Different collations.**
10. What is required to claim PostgreSQL 18 runtime validation? **Execute on isolated PostgreSQL 18 and retain reproducible evidence.**

## References

- [PostgreSQL 18 — Sorting Rows (ORDER BY)](https://www.postgresql.org/docs/18/queries-order.html)
- [PostgreSQL 18 — SELECT](https://www.postgresql.org/docs/18/sql-select.html)
- [PostgreSQL 18 — Collation Support](https://www.postgresql.org/docs/18/collation.html)
- [PostgreSQL 18 — EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)
- [Chapter 018 — LIMIT, OFFSET, FETCH, TOP (planned)](../MASTER-TOC.md)
