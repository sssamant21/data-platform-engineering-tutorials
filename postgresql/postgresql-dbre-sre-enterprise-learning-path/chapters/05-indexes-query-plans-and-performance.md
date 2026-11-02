# Chapter 05 — Indexes, Query Plans and Performance

**Track:** PostgreSQL Database Engineering (DBRE/SRE) — Enterprise Learning Path  
**Level:** Beginner to intermediate · **Duration:** 60 minutes · **Reference version:** PostgreSQL 17  
**Publication state:** Authored. Runtime lab execution and independent review are **pending**.

[Course home](../README.md) · [Master TOC](../MASTER-TOC.md) · [Chapter 05 lab](../labs/chapter-05/README.md) · [Progress](../STATUS-TRACKER.md)

## 1. Learning outcomes

After this chapter, a DBRE/SRE should be able to:

1. Explain why a query can be slow even when PostgreSQL is healthy.
2. Distinguish sequential, index, index-only, and bitmap heap scans.
3. Read a basic `EXPLAIN (ANALYZE, BUFFERS)` plan, including estimated versus actual rows.
4. Design a B-tree index that supports both equality filtering and an `ORDER BY ... LIMIT` query.
5. Explain partial, expression, and covering indexes without assuming they are universally beneficial.
6. Measure index size and query behavior, and explain the impact of indexes on writes and storage.
7. Propose a safe, evidence-based production change instead of adding indexes indiscriminately.

## 2. 60-minute lesson plan

| Time | Topic | Deliverable |
|---|---|---|
| 0–10 min | Workload patterns and access paths | Identify a candidate query |
| 10–20 min | B-tree, composite, partial, covering, and other index types | Choose an index and justify column order |
| 20–30 min | Query plans, cardinality, buffers, and planner statistics | Interpret a sample plan |
| 30–52 min | [Hands-on lab](../labs/chapter-05/README.md) | Capture before/after plans and index sizes |
| 52–60 min | Production change review and troubleshooting | Complete acceptance checklist |

## 3. Performance starts with the workload

Imagine an application requesting the most recent 20 events for a customer:

```sql
SELECT event_id, customer_id, created_at, amount
FROM perf_lab.events
WHERE customer_id = 42
ORDER BY created_at DESC
LIMIT 20;
```

The performance question is not "does this table have an index?" It is "what access path minimizes work for this specific query, selectivity, sort order, data volume, and hardware?"

Collect the following before proposing changes:

- Query shape and parameters (with sensitive values redacted), execution frequency, and application latency budget.
- Table row count, cardinality of filtered columns, skew, and growth rate.
- Current plan and estimated/actual row counts.
- Buffer reads/hits, sort spills, temporary I/O, and CPU/IO pressure.
- Index inventory, write volume, update patterns, and storage headroom.
- Concurrency and whether a regression began after deployment, statistics drift, or data growth.

An index can improve a read while increasing WAL generation, insert/update cost, storage, backup volume, and future maintenance.

## 4. PostgreSQL access paths

| Plan node | Meaning | When it may be appropriate |
|---|---|---|
| `Seq Scan` | Reads table pages sequentially and applies filters | Small tables or queries returning a large fraction of rows |
| `Index Scan` | Uses index entries to locate heap tuples | Selective predicates and ordered retrieval |
| `Index Only Scan` | Can satisfy projected values from an index | Columns covered and visibility-map conditions favorable |
| `Bitmap Index Scan` + `Bitmap Heap Scan` | Gathers matching tuple locations then visits heap pages | Moderate selectivity or combined index predicates |
| `Sort` | Explicitly sorts rows | No suitable presorted path or sort is cheaper |
| `Nested Loop` / `Hash Join` / `Merge Join` | Different join strategies | Choice depends on cardinality, order, and memory |

**Important:** `Seq Scan` is not automatically a problem. On a tiny table, sequential access may be cheaper than index traversal.

### Common index families

- **B-tree:** default; excellent starting point for equality, ranges, and ordered lookups.
- **Hash:** equality-oriented; B-tree is often preferable for ordinary scalar keys because it also supports range/order patterns.
- **GIN:** useful for arrays, JSONB, and full-text-style inverted lookups with appropriate operators.
- **GiST / SP-GiST:** extensible access methods for specialized data/operator classes.
- **BRIN:** summarizes ranges of heap pages; can be compact for very large tables with useful physical correlation.

Do not select an index family solely from a column's data type; verify operators, operator classes, selectivity, and real plans.

## 5. Composite indexes and leftmost-column design

For the customer timeline query, consider:

```sql
CREATE INDEX idx_events_customer_created
ON perf_lab.events (customer_id, created_at DESC);
```

The first column supports equality filtering. The second helps retrieve matching rows in the required order, potentially avoiding an explicit sort and allowing the executor to stop early at `LIMIT 20`.

A B-tree on `(customer_id, created_at DESC)` is **not generally interchangeable** with `(created_at DESC, customer_id)` for this query. Multicolumn B-tree behavior depends on leading-column conditions and the planner's ability to constrain index ranges; review the PostgreSQL documentation for the version in use.

### Covering indexes and index-only scans

```sql
-- Example only; do not add to the lab on top of the first index by default.
CREATE INDEX idx_events_customer_created_cover
ON perf_lab.events (customer_id, created_at DESC)
INCLUDE (amount);
```

`INCLUDE` stores non-key payload columns that may help satisfy projections. It does **not** guarantee an index-only scan: required columns must be available from the index, and PostgreSQL may need heap visibility checks. In this example, selecting `event_id` would also require it in the index for a true index-only plan. Covering indexes can be much larger and can increase write costs.

### Partial indexes

```sql
CREATE INDEX idx_events_pending_recent
ON perf_lab.events (created_at DESC)
WHERE status = 'pending';
```

A partial index stores only rows satisfying its predicate. It is useful if a query's predicate implies the index predicate and the selected subset is meaningful. Generic prepared plans and parameterization can affect whether a partial index is usable. The lab compares its behavior without assuming a guaranteed plan.

### Expression indexes

An index on `lower(email)` may support case-insensitive lookup if the query uses the corresponding expression, but the business must first define case-normalization rules. Expression indexes increase write work; they are not a substitute for consistent identity semantics.

## 6. Reading EXPLAIN safely

Use `EXPLAIN` to inspect a predicted plan without executing the query. `EXPLAIN (ANALYZE, BUFFERS)` **actually executes it**. In this chapter, all measured statements are bounded, read-only `SELECT` queries against a disposable database.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT event_id, customer_id, created_at, amount
FROM perf_lab.events
WHERE customer_id = 42
ORDER BY created_at DESC
LIMIT 20;
```

A typical pre-index shape might include:

```text
Limit
  -> Sort
       Sort Key: created_at DESC
       -> Seq Scan on events
            Filter: (customer_id = 42)
            Rows Removed by Filter: ...
Planning Time: ...
Execution Time: ...
```

After the index, a possible plan is:

```text
Limit
  -> Index Scan using idx_events_customer_created on events
       Index Cond: (customer_id = 42)
Planning Time: ...
Execution Time: ...
```

These are **illustrative shapes**, not observed results. The planner may choose a different plan depending on statistics, table size, cost parameters, cache state, and data distribution.

### What to read first

| Field | Interpretation | Caution |
|---|---|---|
| `cost=...` | Planner's relative estimated cost | Not elapsed milliseconds |
| `rows=...` | Estimated rows at a node | May differ from actual rows due to statistics or correlation |
| `actual ... rows=... loops=...` | Measured rows and execution loops | Per-loop reporting requires care |
| `Rows Removed by Filter` | Rows examined but rejected by filter | Often signals extra work |
| `Buffers: shared hit` | PostgreSQL shared-buffer accesses served from shared memory | Not proof of zero storage work overall |
| `Buffers: shared read` | Pages read into shared buffers | Can be served by OS cache; not necessarily physical disk I/O |
| `Sort Method` | How a sort was performed | External merge can indicate temp-file usage |
| `Planning Time` / `Execution Time` | Server-side plan and execution time | Does not represent end-to-end application p95 latency |

The planner uses table statistics collected by `ANALYZE`, plus cost estimates, to choose a plan. Compare actual versus estimated cardinality before changing cost parameters. Avoid disabling scan methods or altering cluster-wide settings to force a demonstration.

## 7. Index lifecycle and DBRE operational responsibilities

### Change design

1. Establish baseline query plans, application SLOs, and write/IO metrics.
2. Confirm whether an existing index already supports the query.
3. Propose the smallest useful index and estimate additional disk/WAL footprint.
4. Test against production-like row counts and realistic data skew in staging.
5. Review DDL locking, deployment timing, and rollback with the application owner.
6. Use `CREATE INDEX CONCURRENTLY` for appropriate production cases **after** understanding its restrictions and operational costs. It cannot run inside a transaction block and can leave an invalid index on failure.
7. Monitor query latency, CPU, storage, index growth, replication lag, and write amplification.
8. Remove redundant indexes only after workload-based review and an approved change.

### Index-use metrics

`pg_stat_user_indexes` and `pg_stat_all_indexes` expose cumulative index-use counters. A low `idx_scan` count alone is **not sufficient** to delete an index: it may support a rare critical query, constraints, or disaster-recovery workflow. Statistics may reset and do not show all business criticality.

### PostgreSQL platform distinctions

- **Bare metal/VM:** DBRE may own OS and storage bottlenecks in addition to query design.
- **AWS RDS:** DBRE uses permitted PostgreSQL views and managed metrics; superuser/OS access is constrained.
- **Kubernetes:** inspect database plans alongside CPU throttling, storage latency, persistent-volume behavior, and operator settings.

The logical indexing principles remain the same, but deployment controls and telemetry differ.

## 8. Hands-on lab

Complete [Chapter 05 lab](../labs/chapter-05/README.md). It creates an isolated `training_ch05` database with synthetic events, captures before/after query plans, adds a composite B-tree index, optionally tests a partial index, and inspects index size and usage.

The lab deliberately avoids changing server-wide planner parameters or dropping existing resources.

## 9. Troubleshooting playbook

| Observation | Possible explanation | Evidence / safe next step |
|---|---|---|
| Index exists but Seq Scan chosen | Table small, query unselective, or index not suitable | Check selectivity, `ANALYZE`, and actual plan |
| Estimated rows differ sharply from actual | Stale/inadequate statistics or correlated columns | Review `pg_stats`, data skew, and statistics strategy |
| Sort spills to disk | Workload size exceeds sort memory budget | Review `Sort Method` and temp I/O; avoid global `work_mem` changes |
| Query fast in psql but slow in app | Network, pooling, concurrency, parameter values | Compare end-to-end tracing and sampled query plans |
| Index size grows unexpectedly | Many indexes, write churn, wide payloads | Inventory index sizes and write/update patterns |
| Latency worsens after new index | Added write overhead, changed plan, resource contention | Compare before/after under representative load and use approved rollback |
| Low `idx_scan` | Rare workload or stats reset | Validate business use before considering deletion |

## 10. Acceptance checklist

- [ ] Explain why a sequential scan can be optimal.
- [ ] Read a plan and identify estimated versus actual rows.
- [ ] Explain `shared hit` and `shared read` without conflating them with physical disk metrics.
- [ ] Show a candidate composite index and justify column order.
- [ ] Demonstrate baseline and indexed plans in a disposable database.
- [ ] Explain why index-only scans depend on projection and visibility.
- [ ] Describe the write/storage tradeoffs of adding indexes.
- [ ] Inventory index sizes and use counters.
- [ ] Provide a staged production change proposal with monitoring and rollback.
- [ ] Keep actual runtime verification and independent approval explicitly pending until evidence exists.

## 11. Official PostgreSQL 17 references

- [Using EXPLAIN](https://www.postgresql.org/docs/17/using-explain.html)
- [Indexes](https://www.postgresql.org/docs/17/indexes.html)
- [Multicolumn Indexes](https://www.postgresql.org/docs/17/indexes-multicolumn.html)
- [Partial Indexes](https://www.postgresql.org/docs/17/indexes-partial.html)
- [Index-Only Scans and Covering Indexes](https://www.postgresql.org/docs/17/indexes-index-only-scans.html)
- [Examining Index Usage](https://www.postgresql.org/docs/17/indexes-examine.html)
- [ANALYZE](https://www.postgresql.org/docs/17/sql-analyze.html)
- [CREATE INDEX](https://www.postgresql.org/docs/17/sql-createindex.html)

**Next:** Chapter 06 — PostgreSQL on Bare Metal.
