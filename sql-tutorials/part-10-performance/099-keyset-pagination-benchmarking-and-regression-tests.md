# 099 — Keyset Pagination, Benchmarking, and Regression Tests

**Part 10 — SQL Performance & Query Optimization** · **60 minutes** · **PostgreSQL 18 baseline** · **Audience:** data engineers, DBRE/SRE, application developers

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Read-only PostgreSQL 18 lab](../labs/099-keyset-pagination-benchmark-regression.sql) · [Previous: 098](098-optimize-joins-aggregations-and-subqueries.md) · Next: 100 — Lab 10: baseline, tune, and remeasure a slow query (planned)

## 1. Objectives and prerequisites (0–5 minutes)

After this lesson you can: explain why large OFFSET values can be costly; write a deterministic keyset query with a unique tie-breaker; handle forward page boundaries and NULLs; distinguish benchmark noise from improvement; and create correctness regression checks before accepting a query rewrite. Review [018 — LIMIT/OFFSET](../part-02-filtering/018-limit-offset-fetch-and-top-across-dialects.md), [091 — EXPLAIN](091-read-execution-plans-with-explain.md), [094 — composite indexes](094-composite-indexes-and-column-order.md), and [098 — query rewrites](098-optimize-joins-aggregations-and-subqueries.md).

**Scenario:** A synthetic operations dashboard lists events newest first. A user browses many pages while new events arrive. Data engineers need stable ordering; DBREs must assess query cost and correctness.

## 2. Pagination fundamentals (5–15 minutes)

**OFFSET pagination (portable SQL):** ORDER BY event_time DESC, event_id DESC OFFSET 3 ROWS FETCH NEXT 3 ROWS ONLY. PostgreSQL also supports LIMIT 3 OFFSET 3. An OFFSET of N generally requires processing or skipping N earlier qualifying rows; an index does not make deep skips free. OFFSET can shift page boundaries when concurrent inserts or deletes occur.

**Keyset / seek pagination (portable comparison):** Retain the final row's complete ordering key. For descending, non-NULL event_time and unique event_id:

```sql
SELECT event_id, event_time, event_type
FROM events
WHERE event_time < :last_time
   OR (event_time = :last_time AND event_id < :last_id)
ORDER BY event_time DESC, event_id DESC
FETCH FIRST 3 ROWS ONLY;
```

`:last_time` and `:last_id` are application-bound parameters, **not** literal psql syntax. PostgreSQL supports row-value comparison `(event_time, event_id) < ($1, $2)` for compatible non-NULL types; the expanded OR form is more broadly portable. Always match comparison direction to ORDER BY direction. A nonunique timestamp alone loses tied rows. Define explicit NULL positioning or normalize to a non-NULL sort key before using tuple comparisons. A unique, immutable tie-breaker is essential.

**Index design:** In a physical PostgreSQL table, a candidate index is `(event_time DESC, event_id DESC)` for this ordering. An index is not created by the read-only lab. Evaluate filters, covering needs, storage/write overhead, and actual plans before proposing a production index.

**Consistency caveat:** Keyset avoids the classic duplicate/skip caused by offset shifts, but it is **not a snapshot guarantee** across requests. Updates to ordering keys, deletions, and newly inserted older-key rows can change what appears. For exact export consistency, use a bounded immutable dataset, a persisted export watermark plus appropriate versioning, or an approved consistent-snapshot design; do not keep a long-lived production transaction open for user pagination.

## 3. Worked synthetic example (15–30 minutes)

| event_id | event_time (UTC) | event_type |
|---:|---|---|
| 109 | 2026-11-01 12:05 | alert |
| 108 | 2026-11-01 12:04 | info |
| 107 | 2026-11-01 12:04 | alert |
| 106 | 2026-11-01 12:03 | info |
| 105 | 2026-11-01 12:02 | alert |
| 104 | 2026-11-01 12:02 | info |
| 103 | 2026-11-01 12:01 | alert |
| 102 | 2026-11-01 12:00 | info |
| 101 | 2026-11-01 11:59 | alert |

Sorted descending by (event_time, event_id), page 1 is **109,108,107**, cursor (12:04,107). Page 2 is **106,105,104**, cursor (12:02,104). Page 3 is **103,102,101**. Ties at 12:04 and 12:02 are handled correctly.

```sql
-- PostgreSQL 18 demonstration: synthetic rows, no persistent tables.
WITH events(event_id,event_time) AS (
 VALUES (109,timestamp '2026-11-01 12:05'),
        (108,timestamp '2026-11-01 12:04'),
        (107,timestamp '2026-11-01 12:04'),
        (106,timestamp '2026-11-01 12:03'),
        (105,timestamp '2026-11-01 12:02'),
        (104,timestamp '2026-11-01 12:02'),
        (103,timestamp '2026-11-01 12:01'),
        (102,timestamp '2026-11-01 12:00'),
        (101,timestamp '2026-11-01 11:59')
)
SELECT event_id,event_time
FROM events
WHERE (event_time,event_id) < (timestamp '2026-11-01 12:04',107)
ORDER BY event_time DESC,event_id DESC
LIMIT 3;
```

Expected: 106, 105, 104. Row constructors and LIMIT here are PostgreSQL syntax; standard FETCH FIRST can replace LIMIT. Never concatenate untrusted cursor text into SQL: bind typed parameters and validate cursor structure.

## 4. Hands-on lab (30–50 minutes)

Run only on an **isolated disposable PostgreSQL 18** database named `sql_tutorials`, with a nonproduction role:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/099-keyset-pagination-benchmark-regression.sql
```

The [lab](../labs/099-keyset-pagination-benchmark-regression.sql) checks the database name and major version, starts a read-only transaction, sets local timeouts, uses inline synthetic values, shows an **estimated** EXPLAIN plan, and asserts three pages and exact equivalence with OFFSET on a *fixed* dataset. It rolls back. Expected notice: `099 assertions passed: 9 rows, 3 pages, no mismatch`. If an assertion fails, psql exits nonzero with ON_ERROR_STOP.

**Practice A:** Change page size to 2 in a scratch copy, derive four full pages plus one final row, and verify no duplicates. **Practice B:** Remove the event_id tie-breaker and explain which tied event may be lost. **Practice C:** Insert a hypothetical new event at 12:06 *between requests* on paper; explain why OFFSET page 2 can repeat a row while the original keyset cursor continues below its boundary.

### Benchmark design, not benchmark results

Record PostgreSQL version, hardware/instance class, row count, index definitions, query parameters, cache state, concurrency, query plans, and at least several repetitions of each candidate. In an **approved isolated performance environment**, compare `EXPLAIN (ANALYZE, BUFFERS, SETTINGS)` with timing distributions (median and p95), returned row counts, and logical/physical I/O. ANALYZE executes the statement; never run it against unsafe writes or uncontrolled production workloads. Use representative larger datasets: the nine-row teaching fixture cannot establish a performance win. Warm-cache and cold-cache runs answer different questions; do not clear production caches to manufacture a cold run. Compare under equivalent conditions, account for noise, and report regressions.

| Evidence | Baseline OFFSET | Candidate keyset |
|---|---|---|
| PostgreSQL version and dataset | Record | Same |
| Exact query and parameters | Record | Record |
| Rows and result semantics | Assert | Assert |
| Plan and buffers | Capture | Capture |
| Median/p95 over repeated runs | Measure | Measure |
| Concurrency and cache state | Record | Match or explain |
| Decision | — | Accept only if correctness holds and measured improvement is meaningful |

## 5. Validation, troubleshooting, and safety (50–55 minutes)

- **Missing/duplicate rows:** verify unique total ordering, tie-breaker direction, bound cursor types, and concurrent mutations. OFFSET and keyset are equivalent only against a fixed ordered dataset for this exercise.
- **Slow deep pages:** inspect filter selectivity, ORDER BY/index compatibility, row estimates, buffers, and sort spills. Keyset can still be slow with unsuitable predicates or no useful index.
- **Wrong page after NULL:** define NULL policy explicitly; tuple comparisons with NULL produce unknown results.
- **No index scan in lab:** inline VALUES rows have no physical index. The lab's estimated plan teaches inspection, not index speed.
- **Guardrails:** read-only transaction, synthetic values, database/version guard, short timeouts, no DDL/DML, no production credentials. Never claim performance improvement from theoretical complexity or a tiny sample.

## 6. Review questions with answers (55–60 minutes)

1. **Why include event_id after event_time?** To establish deterministic ordering across equal timestamps.
2. **What cursor follows page 1?** (2026-11-01 12:04, 107).
3. **Why can deep OFFSET be expensive?** The engine still processes/skips preceding qualifying rows.
4. **Does keyset ensure a consistent snapshot across HTTP requests?** No; it provides a boundary, not cross-request MVCC snapshot consistency.
5. **Can the lab prove keyset is faster?** No; it tests correctness on nine synthetic rows and displays an estimated plan.
6. **What must precede a production index change?** Workload evidence, read/write tradeoff analysis, change approval, rollback strategy, and post-change measurement.

## References

- [PostgreSQL 18 — LIMIT and OFFSET](https://www.postgresql.org/docs/18/queries-limit.html)
- [PostgreSQL 18 — ORDER BY](https://www.postgresql.org/docs/18/queries-order.html)
- [PostgreSQL 18 — Row constructor comparison](https://www.postgresql.org/docs/18/functions-comparisons.html#ROW-WISE-COMPARISON)
- [PostgreSQL 18 — EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)
- [PostgreSQL 18 — Multicolumn indexes](https://www.postgresql.org/docs/18/indexes-multicolumn.html)

**Validation state:** Authored material; targeted static/manual review only. Independent editorial review, comprehensive static QA, and isolated PostgreSQL 18 runtime execution with retained evidence are **pending**.
