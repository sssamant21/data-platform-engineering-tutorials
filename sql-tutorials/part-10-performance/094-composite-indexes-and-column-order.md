# 094 — Composite Indexes and Column Order

**Part 10 — SQL Performance & Query Optimization** · **60 minutes** · **PostgreSQL 18 baseline** · **Audience:** data engineers, analysts, DBRE/SRE

[Master TOC](../MASTER-TOC.md) · [Index](../README.md) · [Read-only lab](../labs/094-composite-indexes-column-order.sql) · [Previous: 093](093-btree-indexes-and-common-index-access-patterns.md) · Next: 095 — Partial, expression, and covering indexes (planned)

## 1. Learning objectives and prerequisites (0–5 minutes)

After this lesson you can: explain composite B-tree key order; match equality, range and ordering predicates to candidate indexes; recognize when a leading-key gap matters; evaluate sort elimination; and propose a safe benchmark before changing a production index. Prerequisites: [091 — EXPLAIN](091-read-execution-plans-with-explain.md), [092 — selectivity](092-table-scans-index-scans-row-estimates-and-selectivity.md), and [093 — B-tree basics](093-btree-indexes-and-common-index-access-patterns.md).

**Scenario:** a fictional commerce service filters orders by tenant, status and creation time. A dashboard retrieves the newest paid orders per tenant. A DBRE must choose between candidate composite indexes without increasing write amplification unnecessarily.

## 2. Concepts: order is a workload decision (5–15 minutes)

A composite index stores multiple key columns in a defined order. PostgreSQL B-tree indexes can support conditions on multiple columns. Equality constraints on leading columns, plus an inequality on the first column without an equality constraint, typically determine how much of the index must be scanned. Conditions on later columns may still be checked at the index and reduce heap visits, but do not always reduce the scanned index range. PostgreSQL 18 also supports **skip scan** in certain cases: it may perform repeated searches over distinct leading-key values when that is cheaper. Therefore, **“the leftmost prefix is always mandatory” is too absolute**; confirm the actual plan and selectivity.

Consider the hypothetical index `(tenant_id, status, created_at DESC)`:

| Query pattern | Candidate fit | Why |
|---|---|---|
| `tenant_id = ? AND status = ? AND created_at >= ?` | Strong candidate | Two leading equalities followed by a date range |
| `tenant_id = ? AND status = ? ORDER BY created_at DESC` | Strong candidate | Matching equality prefix and descending date order |
| `tenant_id = ? AND created_at >= ?` | Depends | Missing status equality; may scan many status groups or use skip scan |
| `status = ?` alone | Often weaker | Leading tenant is unbounded; planner may choose another path |
| `tenant_id = ? ORDER BY created_at DESC` | Not automatically sort-free | Rows are grouped by status before date |
| `status = ? AND tenant_id = ?` | Same equality-prefix potential | Textual WHERE order does **not** dictate index order |

Index design depends on real filter frequency, selectivity, sort direction, LIMIT, joins, and write costs. Put **workload-relevant** equality keys before the first range key; this is a useful starting heuristic, not a universal rule. Choosing tenant first can also support tenant-only access; choosing status first may favor a different workload. For a tenant-scoped newest-orders query without a status predicate, `(tenant_id, created_at DESC)` may be a better index. The planner may choose a sequential scan for small or unselective datasets.

**Portable SQL:** predicates, multi-column `CREATE INDEX`, and `ORDER BY` concepts are broadly shared. **PostgreSQL-specific behavior:** B-tree skip scan, `EXPLAIN` syntax, `INCLUDE`, operator classes, null-ordering options, and index-build concurrency. SQL Server, MySQL, Oracle and analytical warehouses have different physical structures and optimizers; verify their documentation.

## 3. Guided examples (15–30 minutes)

### A. Candidate definitions — illustrative, NOT for execution in this lab

```sql
-- PostgreSQL syntax; requires an approved migration on a real table.
-- CREATE INDEX orders_tenant_status_created_idx
--   ON orders (tenant_id, status, created_at DESC);
-- CREATE INDEX orders_tenant_created_idx
--   ON orders (tenant_id, created_at DESC);
```

These indexes overlap for some workloads but are not interchangeable. Both consume storage and add INSERT/UPDATE/DELETE and WAL costs. Do not build both without workload evidence.

### B. Equality prefix, range, and stable ordering

```sql
-- Conceptual portable query; orders is not created by this chapter.
SELECT order_id, created_at, amount
FROM orders
WHERE tenant_id = 10
  AND status = 'paid'
  AND created_at >= TIMESTAMP '2026-11-01 00:00:00'
  AND created_at < TIMESTAMP '2026-11-03 00:00:00'
ORDER BY created_at DESC, order_id DESC;
```

The composite index above can help narrow the date range, but **does not guarantee** that the complete `ORDER BY created_at DESC, order_id DESC` is satisfied: `order_id` is not an index key. A planner may add a sort or incremental sort. A matching `(tenant_id, status, created_at DESC, order_id DESC)` index could avoid that sort for this predicate pattern, subject to planner choice.

### C. Read estimated plans only

```sql
-- PostgreSQL 18: on an approved, known, hypothetical persisted orders table.
EXPLAIN (FORMAT TEXT, COSTS ON)
SELECT order_id FROM orders
WHERE tenant_id = 10 AND status = 'paid'
ORDER BY created_at DESC;
```

Plain `EXPLAIN` does not execute the SELECT. An inline `VALUES` source in the actual lab has **no index**, so its plan is **not evidence of composite-index performance**. Avoid `EXPLAIN ANALYZE` on unapproved workloads: it executes queries and can consume significant resources.

### D. Synthetic result set

```sql
WITH orders(tenant_id, order_id, status, created_at, amount) AS (
 VALUES
 (10,101,'paid',TIMESTAMP '2026-11-01 09:00',20.00::numeric),
 (10,102,'pending',TIMESTAMP '2026-11-01 10:00',15.00::numeric),
 (10,103,'paid',TIMESTAMP '2026-11-02 11:00',30.00::numeric),
 (20,104,'paid',TIMESTAMP '2026-11-02 12:00',40.00::numeric),
 (10,105,'paid',TIMESTAMP '2026-11-03 08:00',50.00::numeric),
 (20,106,'failed',TIMESTAMP '2026-11-01 13:00',10.00::numeric)
)
SELECT order_id, amount
FROM orders
WHERE tenant_id = 10 AND status = 'paid'
  AND created_at >= TIMESTAMP '2026-11-01'
  AND created_at < TIMESTAMP '2026-11-03'
ORDER BY created_at DESC, order_id DESC;
```

**Expected (manually reasoned):** order 103 (30.00), then 101 (20.00). Order 105 is outside the exclusive upper bound. Order 104 belongs to another tenant.

## 4. Hands-on lab (30–50 minutes)

Use only a disposable PostgreSQL 18 database named `sql_tutorials`, following [003 — lab setup](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md). From the repository root:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/094-composite-indexes-column-order.sql
```

The [read-only lab](../labs/094-composite-indexes-column-order.sql) has a fail-closed database/version guard, synthetic inline rows, estimated EXPLAIN, transaction-local timeouts, exact bidirectional multiset checks, and ROLLBACK. No table or index is created.

1. Predict which two tenant-10 paid orders fall in the half-open November 1–3 range.
2. Execute the lab, compare ordered rows and aggregates, and confirm the assertions pass without errors.
3. Rewrite the hypothetical index to optimize tenant-10 newest orders **regardless of status**. Explain why the status-middle index may not preserve date ordering.
4. Explain whether swapping `tenant_id = 10 AND status = 'paid'` in the WHERE clause changes the usable index key order. It does not.
5. Propose an isolated benchmark with representative volume and skew: compare no index, `(tenant_id, status, created_at DESC)`, and `(tenant_id, created_at DESC)`; record plans, p50/p95 latency, buffer reads, index size, write overhead, and regression cases. Require an approved migration and rollback plan before any real deployment.

**Expected results (reasoned, not runtime-validated):**

| Check | Expected |
|---|---|
| Total synthetic orders | 6 |
| Tenant 10 paid orders (all dates) | 3; revenue 100.00 |
| Tenant 10 paid orders in Nov 1–3 half-open range | 2; revenue 50.00 |
| Ordered IDs in date range | 103, 101 |
| Tenant 20 paid orders | 1; revenue 40.00 |

The lab intentionally does not assert a plan operator, index usage, cost, or timing.

## 5. Troubleshooting and DBRE/SRE guardrails (50–55 minutes)

| Symptom | Check |
|---|---|
| Index ignored | Table size, row estimates, stats freshness, selectivity, planner costs, parameter values |
| Unexpected Sort | Equality prefix, remaining key order, tie-breaker keys, direction, NULL ordering |
| Later-column filter scans many keys | Missing equality on an earlier column; inspect skip-scan feasibility and alternatives |
| Slow write workload after indexing | Index count/size, WAL, page splits, updates, vacuum and replication impact |
| Different tenant performance | Skew, parameter-sensitive plans, correlation and per-tenant cardinality |
| Lab refuses to run | Use isolated database `sql_tutorials` and PostgreSQL major 18; never disable guards |

**Safety:** This lesson does not authorize production DDL, planner toggles, or benchmarks. Production `CREATE INDEX` can block writes; `CREATE INDEX CONCURRENTLY` has restrictions, additional work, and invalid-index failure modes. Seek DBRE change approval, capacity and lock checks, maintenance/rollback strategy, and application latency baselines. Never use real customer data or production credentials.

## 6. Review questions with answers (55–60 minutes)

1. **Why does composite index order matter?** It determines grouping and useful search/order prefixes.
2. **Does WHERE predicate text order matter?** No; the optimizer interprets predicates independently of their textual order.
3. **Can PostgreSQL 18 use a later key without a leading equality?** Sometimes, including skip scan; cost and data distribution determine usefulness.
4. **Can `(tenant_id,status,created_at)` satisfy tenant-only `ORDER BY created_at` without sorting?** Not generally: status partitions the date ordering.
5. **Why include an order-ID tie-breaker?** To make pagination and results deterministic when timestamps tie.
6. **Does a six-row VALUES lab prove index speed?** No; it has no physical index or realistic I/O.
7. **What must be measured before index rollout?** Read and write latency, plans, buffers, size, locks, WAL, and regressions.

## References and next milestone

- [PostgreSQL 18 — Multicolumn Indexes](https://www.postgresql.org/docs/18/indexes-multicolumn.html)
- [PostgreSQL 18 — Indexes and ORDER BY](https://www.postgresql.org/docs/18/indexes-ordering.html)
- [PostgreSQL 18 — Index Types](https://www.postgresql.org/docs/18/indexes-types.html)
- [PostgreSQL 18 — Using EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html)
- [PostgreSQL 18 — CREATE INDEX](https://www.postgresql.org/docs/18/sql-createindex.html)

**Next:** 095 — Partial, expression, and covering indexes.

**Validation status:** Authored with targeted static/manual reasoning. Independent editorial review, comprehensive automated parser-based SQL/link QA, and actual isolated PostgreSQL 18 runtime validation with retained evidence remain pending.
