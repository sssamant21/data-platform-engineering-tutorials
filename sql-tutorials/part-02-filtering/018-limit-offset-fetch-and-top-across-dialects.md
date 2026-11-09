# Chapter 018 — LIMIT, OFFSET, FETCH, and TOP Across Dialects

> [Master TOC](../MASTER-TOC.md) · [Learning path](../README.md) · [Previous: 017](017-order-by-and-deterministic-sorting.md) · [Next: 019 (planned)](../MASTER-TOC.md)
>
> **Part 02 — Filtering, Sorting & Conditional Logic** · **60 minutes** · **PostgreSQL 18 lab target**
>
> **Status:** Authored/published; targeted static review only. Independent editorial review, comprehensive SQL syntax checking, and isolated PostgreSQL 18 runtime validation pending.

## Outcomes, prerequisites and agenda (0–5 minutes)

You will limit returned rows, distinguish limiting from filtering, page through results, explain why stable ordering matters, recognize vendor syntax differences, and avoid unsafe high-offset pagination in operational workloads.

**Prerequisites:** [SELECT (007)](../part-01-fundamentals/007-select-fundamentals-retrieve-rows-and-columns.md), [WHERE (011)](011-where-and-comparison-operators.md), [ORDER BY (017)](017-order-by-and-deterministic-sorting.md), and [isolated PostgreSQL 18 setup (003)](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md).

| Minutes | Activity |
|---|---|
| 0–5 | Outcomes and safety |
| 5–15 | Row-limiting syntax and semantics |
| 15–30 | Worked examples and dialect comparison |
| 30–50 | Read-only PostgreSQL 18 lab |
| 50–55 | Troubleshooting and DBRE/SRE guardrails |
| 55–60 | Review questions and answers |

## Key concepts (5–15 minutes)

A row limit caps **returned** rows, not necessarily the rows read or sorted by the database. Without a final `ORDER BY`, the subset is unspecified. With a nonunique sort, tied records may move between pages; always add a unique tie-breaker when repeatability matters. `OFFSET` skips result rows *after* ordering; page 2 of size 2 uses `OFFSET 2`. SQL engines may still scan/sort the skipped rows. Changes between requests can cause duplicates or missing records even with a unique order.

**PostgreSQL/MySQL/SQLite-style:** `ORDER BY event_id LIMIT 2 OFFSET 2`. PostgreSQL supports both `LIMIT` and SQL-standard `OFFSET 2 ROWS FETCH NEXT 2 ROWS ONLY`. `FETCH FIRST 2 ROWS ONLY` is standard syntax; support and exact grammar differ by vendor. **SQL Server:** `SELECT TOP (2) ... ORDER BY event_id`, or `ORDER BY event_id OFFSET 2 ROWS FETCH NEXT 2 ROWS ONLY` (ORDER BY required for OFFSET/FETCH). **Oracle:** `ORDER BY event_id OFFSET 2 ROWS FETCH NEXT 2 ROWS ONLY` on supported versions. **Snowflake:** `LIMIT ... OFFSET ...`; **BigQuery:** `LIMIT ... OFFSET ...`. Do not assume `TOP` is portable. For production SQL, check the target vendor's current documentation.

`FETCH FIRST ... WITH TIES` (where supported) can return **more** rows than the specified count if the final ordering values tie. PostgreSQL 18 supports it with `FETCH`; `LIMIT` does not provide the same syntax. A unique final sort key removes ties, so `WITH TIES` has no additional effect in that case.

## Worked examples (15–30 minutes)

All records are fictional operational events:

| event_id | service | severity | created_at (UTC) |
|---:|---|---:|---|
| 201 | api | 2 | 2026-01-01 09:00 |
| 202 | billing | 1 | 2026-01-01 09:05 |
| 203 | api | 1 | 2026-01-01 09:05 |
| 204 | ingest | 3 | 2026-01-02 10:00 |
| 205 | api | 2 | 2026-01-03 11:00 |
| 206 | billing | 1 | 2026-01-03 12:00 |

### A. First page: oldest two events

```sql
WITH events(event_id, created_at) AS (
 VALUES (201,TIMESTAMP '2026-01-01 09:00'),
        (202,TIMESTAMP '2026-01-01 09:05'),
        (203,TIMESTAMP '2026-01-01 09:05'),
        (204,TIMESTAMP '2026-01-02 10:00'),
        (205,TIMESTAMP '2026-01-03 11:00'),
        (206,TIMESTAMP '2026-01-03 12:00')
)
SELECT event_id FROM events
ORDER BY created_at ASC, event_id ASC
FETCH FIRST 2 ROWS ONLY;
-- Expected: 201, 202.
```

### B. Second page with OFFSET

```sql
WITH events(event_id) AS (VALUES (201),(202),(203),(204),(205),(206))
SELECT event_id FROM events
ORDER BY event_id ASC LIMIT 2 OFFSET 2;
-- Expected: 203, 204.
```

The SQL-standard PostgreSQL alternative is `ORDER BY event_id OFFSET 2 ROWS FETCH NEXT 2 ROWS ONLY`. Offset is zero-based: `OFFSET 0` skips nothing.

### C. Keyset pagination for stable identifiers

```sql
WITH events(event_id) AS (VALUES (201),(202),(203),(204),(205),(206))
SELECT event_id FROM events
WHERE event_id > 202
ORDER BY event_id
FETCH FIRST 2 ROWS ONLY;
-- Expected: 203, 204.
```

Keyset pagination uses the last observed ordering key instead of counting skipped rows. For a compound order, carry *all* sort keys in the cursor and use a matching lexicographic predicate (for example, PostgreSQL `(created_at, event_id) > (:last_created_at, :last_event_id)`). Parameter placeholders here are illustrative; bind values using the client's parameter API, not string concatenation. Keyset pagination is usually more efficient for deep pages when a suitable index exists, but it does **not** itself create a fixed snapshot across requests.

### D. WITH TIES is not a fixed-size page

```sql
WITH events(event_id, severity) AS (
 VALUES (201,2),(202,1),(203,1),(204,3),(205,2),(206,1)
)
SELECT event_id, severity FROM events
ORDER BY severity ASC
FETCH FIRST 2 ROWS WITH TIES;
-- PostgreSQL expected: three rows (202, 203, 206), order among them unspecified.
```

Because all three severity-1 records tie, the result has three rows. Never assert a particular order within tied values.

## Hands-on lab (30–50 minutes)

Run [018 SQL lab](../labs/018-limit-offset-fetch-top.sql) **only after independently verifying** a disposable PostgreSQL 18 instance named `sql_tutorials`. The script's database/version assertion is a second-line safeguard, not evidence of isolation.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/018-limit-offset-fetch-top.sql
```

The lab uses only synthetic inline `VALUES`, `BEGIN READ ONLY`, a local timeout, and `ROLLBACK`. It verifies both `LIMIT/OFFSET` and `OFFSET/FETCH`, first-page and cursor-based results, and `WITH TIES`. **Expected** outputs: `environment_assertion = 1` and `acceptance_assertion = 1`. These are not observed execution results.

**Practice and solutions:**

1. Return the first three IDs ascending. **Answer:** 201, 202, 203 (`ORDER BY event_id FETCH FIRST 3 ROWS ONLY`).
2. Return page 3 with two rows per page. **Answer:** 205, 206 (`LIMIT 2 OFFSET 4`).
3. Return the next two after ID 204. **Answer:** 205, 206 (`WHERE event_id > 204 ORDER BY event_id LIMIT 2`).
4. What happens with `LIMIT 0`? **Answer:** Zero rows returned.
5. What does `OFFSET 100` return from six rows? **Answer:** No rows.
6. Is `LIMIT 2` without `ORDER BY` deterministic? **Answer:** No.
7. Does `FETCH FIRST 2 ROWS WITH TIES` always return two? **Answer:** No.
8. Can a page drift between separate requests? **Answer:** Yes, concurrent inserts/deletes and changing sort values can shift results.

## Troubleshooting and operational safety (50–55 minutes)

| Symptom | Explanation | Safe response |
|---|---|---|
| Different first rows between runs | No outer ORDER BY | Add deterministic sort and unique tie-breaker |
| Duplicate or missing rows between pages | Concurrent changes or unstable ordering | Use keyset for suitable workflows; consider snapshot requirements |
| High OFFSET gets slow | Database may process skipped rows | Prefer indexed keyset access; benchmark in isolation |
| TOP rejected by PostgreSQL | Vendor-specific T-SQL syntax | Use LIMIT or FETCH |
| OFFSET/FETCH rejected by SQL Server | Missing ORDER BY or incompatible version | Add ORDER BY and check supported syntax |
| WITH TIES returns too many rows | Ties at boundary | Use ONLY for fixed maximum page size |
| Query is slow despite LIMIT | Filtering/sorting may process many rows | Inspect a safe EXPLAIN and cap workload |

**DBRE/SRE guidance:** A row limit is not a resource limit. Never use a tutorial query against production without approval; set statement timeouts and inspect access paths for large tables. For audit exports, define a stable time window, a unique order and a consistent-snapshot strategy where required. Use UTC timestamps with explicit types, not ambiguous strings. Never embed production credentials or real patient data. Avoid `SELECT *` in application paging contracts. For large ETL backfills, use checkpoints and idempotency rather than relying on OFFSET through a changing source.

## Review questions and answers (55–60 minutes)

1. Is LIMIT part of every SQL dialect? **No.**
2. Which form is closer to SQL-standard row limiting? **FETCH FIRST/NEXT.**
3. What does OFFSET count? **Rows skipped after sorting.**
4. Why append a unique ID to ORDER BY? **To break ties deterministically.**
5. Is TOP portable to PostgreSQL? **No; it is T-SQL syntax.**
6. Can LIMIT reduce a costly scan to a cheap operation automatically? **No.**
7. What is keyset pagination? **Filtering after the last observed ordering key.**
8. Does keyset alone guarantee snapshot consistency? **No.**
9. Can WITH TIES exceed the requested number? **Yes.**
10. What constitutes runtime validation? **Actual execution on isolated PostgreSQL 18 with retained reproducible evidence.**

## References and next lesson

- [PostgreSQL 18 — LIMIT and OFFSET](https://www.postgresql.org/docs/18/queries-limit.html)
- [PostgreSQL 18 — SELECT / FETCH](https://www.postgresql.org/docs/18/sql-select.html)
- [SQL Server — SELECT TOP](https://learn.microsoft.com/en-us/sql/t-sql/queries/top-transact-sql)
- [SQL Server — ORDER BY OFFSET/FETCH](https://learn.microsoft.com/en-us/sql/t-sql/queries/select-order-by-clause-transact-sql)
- [Oracle — SELECT](https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/SELECT.html)
- [Chapter 019 — CASE, COALESCE, NULLIF (planned)](../MASTER-TOC.md)
