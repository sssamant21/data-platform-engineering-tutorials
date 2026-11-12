# 095 — Partial, Expression, and Covering Indexes

**Part 10 — SQL Performance & Query Optimization** · **60 minutes** · **PostgreSQL 18 baseline** · **Audience:** data engineers, analysts, DBRE/SRE

[Master TOC](../MASTER-TOC.md) · [Index](../README.md) · [Read-only lab](../labs/095-partial-expression-covering-indexes.sql) · [Previous: 094](094-composite-indexes-and-column-order.md) · Next: 096 — Optimizer statistics and PostgreSQL maintenance basics (planned)

## 1. Learning objectives and prerequisites (0–5 minutes)

After this lesson, you can distinguish partial, expression, and covering indexes; identify when a predicate implies a partial-index condition; explain the limitations of index-only scans; propose safe workload measurements; and separate PostgreSQL-specific syntax from portable SQL. Read [091 — EXPLAIN](091-read-execution-plans-with-explain.md), [093 — B-tree indexes](093-btree-indexes-and-common-index-access-patterns.md), and [094 — composite indexes](094-composite-indexes-and-column-order.md).

**Scenario:** A fictional multi-tenant order service frequently queries open orders, searches case-insensitive email addresses, and displays order summaries. The data team wants faster dashboards; DBRE must consider index footprint, write amplification, and visibility-map behavior before approving changes.

## 2. Three index techniques (5–15 minutes)

| Technique | PostgreSQL example (illustrative only) | Main purpose | Key limitation |
|---|---|---|---|
| Partial | `CREATE INDEX ... ON orders (tenant_id, created_at) WHERE status = 'open'` | Index only qualifying rows | Planner must establish that the query implies the index predicate |
| Expression | `CREATE INDEX ... ON customers (lower(email))` | Index a computed search key | Query must use a matching expression; collation/semantics matter |
| Covering | `CREATE INDEX ... ON orders (tenant_id, created_at) INCLUDE (amount, status)` | Store payload columns with search keys | Index-only scans still depend on heap-page visibility; INCLUDE adds size |

**Portable concepts:** `WHERE`, `LOWER`, projected columns, and filtering are broadly supported. **PostgreSQL-specific:** `CREATE INDEX ... WHERE`, expression-index syntax, `INCLUDE`, `EXPLAIN (BUFFERS)`, visibility map, and `CREATE INDEX CONCURRENTLY`. Other engines may have filtered indexes, functional indexes, included columns, or entirely different access methods; check each vendor's exact semantics.

### Partial-index implication and parameterization

A partial index `WHERE status = 'open'` is a candidate for `WHERE status = 'open' AND tenant_id = 10`. A generic prepared plan with `WHERE status = $1` **cannot generally prove** that `$1` always equals `'open'`; PostgreSQL may use a different plan. A custom plan with known parameter values can behave differently. Never promise a partial-index hit without testing actual prepared-statement plan behavior.

Partial indexes can enforce conditional uniqueness, e.g. `CREATE UNIQUE INDEX ... ON users(email) WHERE deleted_at IS NULL`, but uniqueness semantics, NULLs, and migrations require separate design review. They do **not** automatically implement row-level security.

### Expression indexes and correctness

`lower(email) = lower($1)` may use an index on `lower(email)`. A normal index on `email` is not automatically equivalent. Case folding is not a universal identity rule: Unicode, collations, normalization, and business identity policies matter. Do not use an expression index to substitute for an approved canonicalization policy.

### Covering and index-only scans

In PostgreSQL, `INCLUDE` payload columns are stored in leaf index tuples, not used as search keys. A query projecting only indexed keys and payloads **may** qualify for an index-only scan, but PostgreSQL must establish MVCC visibility. When heap pages are not marked all-visible, heap fetches can still occur. `EXPLAIN (ANALYZE, BUFFERS)` on a **disposable isolated database only** can show actual heap fetches; plain `EXPLAIN` shows estimates, not runtime evidence. Payload width and updates can make covering indexes expensive. PostgreSQL B-tree deduplication is not used for indexes with non-key `INCLUDE` columns.

## 3. Guided SQL examples (15–30 minutes)

All DDL below is **documentation only**. The runnable lab does not create an index or persistent table.

```sql
-- PostgreSQL-only examples. DO NOT run against production.
-- CREATE INDEX orders_open_tenant_created_idx
--   ON orders (tenant_id, created_at DESC) WHERE status = 'open';
-- CREATE INDEX customers_lower_email_idx
--   ON customers (lower(email));
-- CREATE INDEX orders_tenant_created_cover_idx
--   ON orders (tenant_id, created_at DESC) INCLUDE (amount, status);
```

A partial index is potentially useful for this query:

```sql
SELECT order_id, amount
FROM orders
WHERE tenant_id = 10 AND status = 'open'
ORDER BY created_at DESC, order_id DESC;
```

The example partial index does **not** guarantee sort elimination for `order_id DESC`, because `order_id` is not a key. An `INCLUDE (order_id)` payload would not fix ordering; the ordering column must be a key. Index eligibility is not a promise that the optimizer will choose it.

Expression-index candidate:

```sql
SELECT customer_id FROM customers
WHERE lower(email) = lower('ALICE@EXAMPLE.TEST');
```

A covering index on `(tenant_id, created_at DESC) INCLUDE (amount, status)` does not cover `order_id` unless that column is already available as an index key/payload; PostgreSQL secondary indexes do not automatically contain every projected column. Compare the actual SELECT list to stored index columns.

### Synthetic walk-through (no persistent objects)

```sql
WITH orders(order_id, tenant_id, status, created_at, amount) AS (
 VALUES
 (101,10,'open',TIMESTAMP '2026-11-01 09:00',20.00::numeric),
 (102,10,'paid',TIMESTAMP '2026-11-01 10:00',30.00::numeric),
 (103,10,'open',TIMESTAMP '2026-11-02 11:00',15.00::numeric),
 (104,20,'open',TIMESTAMP '2026-11-02 12:00',40.00::numeric),
 (105,10,'open',TIMESTAMP '2026-11-03 08:00',25.00::numeric),
 (106,20,'paid',TIMESTAMP '2026-11-03 13:00',10.00::numeric)
)
SELECT order_id, amount FROM orders
WHERE tenant_id = 10 AND status = 'open'
ORDER BY created_at DESC, order_id DESC;
```

**Expected, reasoned:** orders 105 (25.00), 103 (15.00), 101 (20.00). Tenant-10 open amount is 60.00. All open orders total 100.00 across four rows. The inline `VALUES` data have **no physical index**; any estimated plan is a SQL-plan reading exercise, not a benchmark of partial, expression, or covering indexes.

## 4. Hands-on lab (30–50 minutes)

Connect **only** to an isolated PostgreSQL 18 database named `sql_tutorials`, following [Chapter 003](../part-01-fundamentals/003-set-up-sql-lab-postgresql-18-docker-and-sql-clients.md). Use synthetic data and no production credentials.

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/095-partial-expression-covering-indexes.sql
```

The [lab](../labs/095-partial-expression-covering-indexes.sql) begins a read-only transaction, fails closed on unexpected database/version, uses transaction-local timeouts, displays estimated plans, checks exact result multisets in both directions, and rolls back. A `DO` guard is permitted in a read-only transaction when it does not write data.

1. Predict tenant-10 open orders and total before running the lab.
2. Execute the lab and verify the ordered results and assertion notice.
3. Inspect the email-normalization example; explain why `LOWER` is a query expression, not proof of universal email identity.
4. Explain why a partial index with `status = 'open'` cannot be assumed usable for a generic `status = $1` plan.
5. Draft an **unexecuted** benchmark proposal: on a disposable representative dataset, compare baseline, partial, expression, and covering candidates. Capture data volume, skew, index sizes, plan choice, buffer hits/reads, heap fetches, p50/p95 latency, WAL and write overhead. Review with DBRE before any migration.

**Expected results (static reasoning only):**

| Check | Expected |
|---|---|
| Total orders | 6 |
| Open orders, all tenants | 4, amount 100.00 |
| Tenant 10 open orders | 3, amount 60.00 |
| Tenant 10 open IDs, newest first | 105, 103, 101 |
| Case-insensitive `alice@example.test` matches | Customer IDs 1 and 3 |

## 5. Troubleshooting and production safety (50–55 minutes)

| Symptom | What to investigate |
|---|---|
| Planner ignores partial index | Query predicate implication, prepared generic/custom plan, selectivity, index definition, statistics |
| Expression index not used | Expression mismatch, collation, casts, estimated cost, query volume |
| Covering index still reads heap | MVCC visibility map, autovacuum activity, heap fetches, projected columns |
| Slow writes after adding indexes | Index count/width, HOT update eligibility, WAL volume, bloat, cache pressure |
| Unexpected ORDER BY sort | Payload versus key distinction, missing tie-breaker key, direction and NULL order |
| Index creation blocks or fails | Locking, long transactions, disk/WAL capacity, concurrent-build limitations |

**Guardrails:** Do not execute DDL against production from this lesson. For real changes require a change ticket, ownership and approval, representative benchmarks, disk/WAL headroom, locking analysis, rollout window, monitoring and rollback strategy. PostgreSQL `CREATE INDEX CONCURRENTLY` cannot run inside a transaction block and can leave an invalid index after failure; it is **not** used in this lab. For existing live workloads, use approved observation paths and avoid unbounded `EXPLAIN ANALYZE`. Do not infer actual performance from six synthetic rows.

## 6. Review questions and answers (55–60 minutes)

1. **When is a partial index useful?** When a stable, frequently queried subset is substantially smaller than the table and query predicates imply the index predicate.
2. **Does a `lower(email)` index speed up every email comparison?** No. Matching expression and collation semantics, planner choice and query shape matter.
3. **Does `INCLUDE (amount)` help filter on amount as an index key?** No. `INCLUDE` is payload, not a search key.
4. **Does an index-only scan always avoid heap access?** No. MVCC visibility checks may require heap fetches.
5. **Can a generic `status = $1` prepared query always use `WHERE status = 'open'` partial index?** No; the generic plan cannot assume the parameter value.
6. **What evidence is required before claiming performance improvement?** Isolated representative benchmark results, plans, buffer/heap-fetch metrics, latency distributions and write overhead, with version and dataset recorded.

**Next:** Chapter 096 — Optimizer Statistics and PostgreSQL Maintenance Basics.

## References

- [PostgreSQL 18: Partial Indexes](https://www.postgresql.org/docs/18/indexes-partial.html)
- [PostgreSQL 18: Indexes on Expressions](https://www.postgresql.org/docs/18/indexes-expressional.html)
- [PostgreSQL 18: Index-Only Scans and Covering Indexes](https://www.postgresql.org/docs/18/indexes-index-only-scans.html)
- [PostgreSQL 18: EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)
- [PostgreSQL 18: CREATE INDEX](https://www.postgresql.org/docs/18/sql-createindex.html)

**Validation state:** Authored for publication; targeted static/manual reasoning only. Independent editorial review, comprehensive parser-based SQL/link QA and actual isolated PostgreSQL 18 execution are not established by this document.
