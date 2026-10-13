# Chapter 032 — Composite, Partial, Expression and Covering Indexes

**Audience:** DBRE and SRE only. **Baseline:** PostgreSQL 18. **Outcome:** design and verify targeted B-tree indexes while controlling write, storage and deployment risk.

## 1. Start with workload evidence

Capture representative SQL, bind values, predicate selectivity, ORDER BY, LIMIT, write frequency, current plans, buffer activity and service objectives. Inspect existing indexes and constraints before proposing a new one. Chapter 031 covers access-method selection; this chapter covers B-tree key and predicate design.

## 2. Composite indexes

A composite index on `(tenant_id, created_at DESC)` can serve tenant equality plus time-range filtering and compatible ordering:

```sql
CREATE INDEX orders_tenant_created_idx
ON orders (tenant_id, created_at DESC);
```

Leading-column constraints generally narrow the scanned range most effectively. PostgreSQL 18 can sometimes use skip scan when a leading column is unconstrained, but its value depends on distinct counts and planner cost. Do not claim that a missing leading predicate makes every composite index unusable. Evaluate equality, range and ordering together. Avoid redundant indexes until read/write costs have been measured.

## 3. Partial indexes

A partial index stores only rows satisfying a fixed predicate:

```sql
CREATE INDEX orders_open_tenant_created_idx
ON orders (tenant_id, created_at DESC)
WHERE status = 'open';
```

The planner must establish that the query predicate implies the index predicate. A generic prepared plan for `status = $1` cannot assume the parameter always equals `'open'`. Test representative custom and generic plans and application SQL. Partial indexes are not a replacement for partitioning and do not automatically accelerate queries that lack their predicate.

## 4. Expression indexes

An expression index supports predicates written in a matching form:

```sql
CREATE INDEX users_lower_email_idx ON users ((lower(email)));
SELECT * FROM users WHERE lower(email) = 'a@example.test';
```

Collation and function semantics matter. Expression computation and maintenance can increase INSERT and non-HOT UPDATE work. Do not use a lowercased email index as a uniqueness guarantee unless it is declared UNIQUE and the business semantics justify it. Review existing constraints before adding one.

## 5. Covering indexes and index-only scans

```sql
CREATE INDEX orders_tenant_created_cover_idx
ON orders (tenant_id, created_at DESC) INCLUDE (amount);
```

INCLUDE columns are payload, not search keys. B-tree uniqueness applies to key columns, not INCLUDE payload. An index-only scan additionally depends on visibility-map state; a matching covering index does not guarantee zero heap fetches. Inspect `Heap Fetches` in `EXPLAIN (ANALYZE, BUFFERS)`. Wide payload columns increase index size and may exceed tuple-size limits; included columns also prevent B-tree deduplication. Prefer narrow payloads.

## 6. Design and lifecycle matrix

| Design | Read benefit | Principal operational risk |
|---|---|---|
| Composite | Filters and ordering in one access path | Key-order mismatch, write amplification |
| Partial | Smaller targeted index for stable predicate | Planner cannot prove implication |
| Expression | Avoids repeated full scans for computed predicates | Expression upkeep and matching semantics |
| Covering | May reduce heap reads | Index bloat, visibility-dependent heap fetches |

Inspect `pg_indexes`, `pg_index`, `pg_stat_user_indexes`, `pg_relation_size` and `pg_stat_user_tables` with a defined statistics window. A zero scan count alone does not justify dropping an index. Use `CREATE INDEX CONCURRENTLY` for an approved low-blocking rollout when appropriate; it cannot run in a transaction block, may wait for transactions, and failed builds can leave invalid indexes. Inspect validity and dependencies before rollback.

## 7. Hands-on lab

Run [Chapter 032 lab](../labs/032-composite-partial-expression-and-covering-indexes-lab.md). It creates an isolated fixture, captures baseline plans, tests four designs, demonstrates prepared-plan limitations, compares heap fetches and index sizes, and cleans up its schema.

### Acceptance

- Record matching query shape and correct result counts.
- Compare default-planner plans, elapsed time and shared buffer activity.
- Explain the predicate implication requirement and generic-plan caveat.
- Demonstrate why INCLUDE does not guarantee heap-free access.
- Document storage, write, WAL, locking, rollback and maintenance risks.
- Never treat one synthetic execution as a production performance guarantee.

**Validation:** Authoring and structural review only; PostgreSQL 18 runtime execution pending.

## Official PostgreSQL 18 references

- [Multicolumn indexes](https://www.postgresql.org/docs/18/indexes-multicolumn.html)
- [Partial indexes](https://www.postgresql.org/docs/18/indexes-partial.html)
- [Indexes on expressions](https://www.postgresql.org/docs/18/indexes-expressional.html)
- [Index-only scans](https://www.postgresql.org/docs/18/indexes-index-only-scans.html)
- [CREATE INDEX](https://www.postgresql.org/docs/18/sql-createindex.html)
- [EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)

**Next:** Chapter 033 — Index Build, Reindex and Concurrent Maintenance.
