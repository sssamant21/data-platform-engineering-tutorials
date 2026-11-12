# 093 — B-tree Indexes and Common Index Access Patterns

**Part 10 — SQL Performance & Query Optimization** · **60 minutes** · **PostgreSQL 18 baseline** · **Audience:** data engineers, analysts, DBRE/SRE

[Master TOC](../MASTER-TOC.md) · [Index](../README.md) · [Read-only lab](../labs/093-btree-index-access-patterns.sql) · [Previous: 092](092-table-scans-index-scans-row-estimates-and-selectivity.md) · Next: 094 — Composite indexes and column order (planned)

## 1. Objectives and prerequisites (0–5 minutes)

After this chapter you can explain how B-tree indexes support equality, range, and ordered access; interpret Index Scan, Index Only Scan and Bitmap Index Scan; distinguish planner estimates from measurements; and justify an index change with a safe, reproducible baseline. Complete [091](091-read-execution-plans-with-explain.md) and [092](092-table-scans-index-scans-row-estimates-and-selectivity.md).

**Scenario:** a fictional order service serves point lookups and daily order reports. Indexing every column is not a safe strategy: each index consumes disk, increases write work, and requires maintenance.

## 2. B-tree essentials and portability (5–15 minutes)

A B-tree keeps sorted index keys with references to table rows. PostgreSQL's default index method is B-tree. It supports operators in the relevant operator class, typically equality and ordered comparisons (`=`, `<`, `<=`, `>`, `>=`), as well as ordered retrieval. For a range predicate, an index can avoid scanning unrelated keys; it does not guarantee a faster query. Selectivity, table size, row width, cache, visibility, physical locality, and planner costs all matter.

| Access path | Typical behavior | Caveat |
|---|---|---|
| Sequential scan | Read table pages, test predicate | Often fastest for tiny tables or large result sets |
| Index scan | Navigate index and fetch qualifying heap tuples | Heap fetches can dominate random I/O |
| Index-only scan | Return values available in index | Visibility map may still require heap fetches |
| Bitmap index + heap scan | Build row-location bitmap, visit heap pages | Sorting may still be required; lossy pages may recheck |
| Backward index scan | Traverse B-tree in reverse order | Useful for compatible `ORDER BY ... DESC` |

**Portable concepts:** `WHERE`, `ORDER BY`, and `CREATE INDEX` are broadly supported; actual index access and physical implementation are vendor-specific. **PostgreSQL-specific:** `USING btree`, `EXPLAIN (FORMAT TEXT)`, `pg_indexes`, index-only visibility rules, and `CREATE INDEX CONCURRENTLY`. SQL Server clustered/nonclustered indexes, MySQL InnoDB secondary indexes, Snowflake micro-partition pruning, and BigQuery clustering differ. Do not assume an equivalent B-tree access path in cloud warehouses.

A B-tree index on `order_id` is a plausible candidate for `WHERE order_id = 42`. An index on `created_at` may help a narrow date range or matching sort. A predicate `DATE(created_at) = DATE '2026-11-01'` generally cannot directly use a plain index on `created_at` as a simple range condition; use an explicit half-open timestamp range, or evaluate an approved expression index. Timestamp/time-zone semantics must be verified.

## 3. Guided SQL examples (15–30 minutes)

### A. Exact lookup and range filters

```sql
-- Portable SQL concept, against a hypothetical persisted orders table:
SELECT order_id, amount
FROM orders
WHERE order_id = 42;

SELECT order_id, created_at
FROM orders
WHERE created_at >= TIMESTAMP '2026-11-01 00:00:00'
  AND created_at <  TIMESTAMP '2026-11-02 00:00:00'
ORDER BY created_at;
```

A single-column B-tree index on `created_at` could support the range and order. An index on `order_id` could support equality. Neither index is guaranteed to be chosen; the example table is conceptual and is **not** created by the read-only lab.

### B. Inspect estimated plans without running the query

```sql
-- PostgreSQL 18; safe only on an approved, known table:
EXPLAIN (FORMAT TEXT, COSTS ON)
SELECT order_id FROM orders WHERE order_id = 42;
```

Plain `EXPLAIN` returns a *plan estimate*, not actual timings or row counts. If an index exists, the planner may still choose Seq Scan. `EXPLAIN ANALYZE` **executes** the statement and may be costly or change data for DML. Never run it indiscriminately on production.

### C. Index definition is a change, not part of this lab

```sql
-- Illustration ONLY; do not run against shared or production databases.
-- CREATE INDEX orders_created_at_idx ON orders (created_at);
```

On PostgreSQL, a normal `CREATE INDEX` can block writes while building; `CREATE INDEX CONCURRENTLY` has different transaction restrictions, extra scans, operational costs, and possible invalid-index cleanup. Both require a reviewed migration, capacity check, and rollback. Index design should follow actual workload patterns and measurements.

### D. Synthetic lookup without any persistent index

```sql
WITH orders(order_id, amount) AS (
  VALUES (101, 12.00::numeric), (102, 25.00::numeric),
         (103, 8.00::numeric), (104, 40.00::numeric),
         (105, 15.00::numeric)
)
SELECT order_id, amount FROM orders WHERE order_id = 103;
```

**Expected (reasoned, not executed):** one row, `103 | 8.00`. This illustrates a selective lookup, **not** index usage: inline `VALUES` has no persistent index.

## 4. Hands-on lab (30–50 minutes)

**Environment:** isolated PostgreSQL 18 database named `sql_tutorials`, with disposable credentials. See [Chapter 003](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md).

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/093-btree-index-access-patterns.sql
```

The [SQL lab](../labs/093-btree-index-access-patterns.sql) uses five fictional orders in CTEs, a read-only transaction, PostgreSQL 18/database guards, local timeouts, a plain estimated `EXPLAIN`, exact multiset assertions and rollback. It never creates an index or table.

1. Predict the exact lookup for order 103 and the range `order_id >= 102 AND order_id < 105`.
2. Run the lab; check the displayed rows and the final assertion result.
3. Explain why a `VALUES` plan cannot demonstrate a B-tree index scan.
4. Identify which hypothetical persistent-table indexes might help equality lookup, date-range filtering, and ordered retrieval.
5. Sketch an *isolated* benchmark proposal: representative row count and skew, realistic write rate, index storage, `EXPLAIN (ANALYZE, BUFFERS)` under approved limits, p50/p95 timings, and a rollback strategy.

**Expected results (manually calculated):**

| Query | Result |
|---|---|
| `order_id = 103` | `103, 8.00` |
| `102 <= order_id < 105` | IDs `102, 103, 104` |
| Range count and sum | `3`, `73.00` |
| All orders | `5`, `100.00` |

Exact plan operators and costs are deliberately **not** asserted.

## 5. Troubleshooting and operational safety (50–55 minutes)

| Symptom | Investigation |
|---|---|
| Planner chooses Seq Scan | Check table size, selectivity, stats, index availability, and estimated heap I/O |
| Index Scan unexpectedly slow | Look for random heap reads, high matching-row fraction, cache effects, and concurrency |
| Index Only Scan has Heap Fetches | Visibility map may not mark all pages all-visible |
| Index not used with a transformed column | Check expression, implicit cast, collation, and operator class |
| Sort remains despite index | Verify requested sort order, filters, multiple keys, and whether planner prefers another access path |
| Lab guard fails | Confirm PostgreSQL major version 18 and isolated database name; do not bypass guard |

**Guardrails:** never create indexes or change planner settings in production as part of this tutorial. Use synthetic data, least-privilege disposable accounts, approved changes, free-space estimates, lock monitoring, write-latency baselines, and a rollback plan. The lab has no persisted objects and runs under `BEGIN READ ONLY`. Avoid posting sensitive query parameters or execution plans publicly.

## 6. Review questions with answers (55–60 minutes)

1. **Does a B-tree guarantee an Index Scan?** No. The optimizer chooses a costed access path.
2. **When might Seq Scan win?** Small tables or broad filters with many qualifying rows.
3. **What does Index Only Scan mean?** Required columns are available in the index, but heap visibility checks can still occur.
4. **Can a B-tree support `ORDER BY`?** Often yes, when the index ordering and query requirements align.
5. **What is the cost of extra indexes?** Storage, write amplification, WAL, and maintenance overhead.
6. **Why not infer performance from five CTE rows?** They have no persisted index or realistic storage and distribution.
7. **What does plain EXPLAIN prove?** Only the planner's estimated strategy for that query and environment.

## References and next chapter

- [PostgreSQL 18 — Index Types](https://www.postgresql.org/docs/18/indexes-types.html)
- [PostgreSQL 18 — B-tree Indexes](https://www.postgresql.org/docs/18/btree.html)
- [PostgreSQL 18 — Indexes and ORDER BY](https://www.postgresql.org/docs/18/indexes-ordering.html)
- [PostgreSQL 18 — Index-Only Scans](https://www.postgresql.org/docs/18/indexes-index-only-scans.html)
- [PostgreSQL 18 — Using EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html)
- [PostgreSQL 18 — CREATE INDEX](https://www.postgresql.org/docs/18/sql-createindex.html)

**Next:** Chapter 094 — Composite indexes and column order.

**Validation status:** Authored; targeted static/manual reasoning only. Independent editorial review, comprehensive parser-based SQL/link QA, and actual isolated PostgreSQL 18 runtime execution with retained evidence remain pending.
