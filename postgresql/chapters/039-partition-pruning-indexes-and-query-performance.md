# Chapter 039 — Partition Pruning, Indexes and Query Performance

**Audience:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Authored; runtime verification pending

## 1. Objectives

Distinguish plan-time pruning from execution-time pruning; interpret `EXPLAIN (ANALYZE, BUFFERS)`; evaluate generic versus custom prepared plans; design partition-local indexes; recognize missing parent statistics and excessive partition counts; and build a safe, evidence-backed query-performance investigation.

## 2. Pruning is not indexing

Partition pruning excludes partitions whose bounds cannot satisfy the query. It is driven by partition constraints and the partition key, not by index existence. Indexes determine access paths *within* remaining partitions. A query can prune correctly but still scan millions of qualifying rows, and an indexed query may still be slow due to heap fetches, poor selectivity, cache misses or planning overhead.

```text
Query predicate on event_time
        |
   Partition pruning
        |
   selected leaf partitions
        |
  local index / bitmap / seq scan
        |
       result
```

## 3. Plan-time and execution-time pruning

**Plan-time:** constant bounds allow irrelevant child relations to be omitted when the plan is built.

**Execution-time:** parameter values available at executor initialization or during nested-loop execution can remove subplans later. In `EXPLAIN`, inspect `Subplans Removed`, child nodes shown as `(never executed)`, and `loops` differences. The absence of a child in a plan can mean it was pruned at planning time. Do not infer failure from a generic plan that lists multiple children without reading actual execution statistics.

```sql
EXPLAIN (ANALYZE, BUFFERS, SETTINGS)
SELECT count(*) FROM ch039.events
WHERE event_time >= timestamptz '2026-02-01 00:00:00+00'
  AND event_time < timestamptz '2026-03-01 00:00:00+00';

EXPLAIN (ANALYZE, BUFFERS, SETTINGS)
SELECT count(*) FROM ch039.events WHERE tenant_id=42;
```

The first query can prune to February. The second lacks the partition key and may scan every month, even when tenant indexes exist.

## 4. Prepared statements and plan caching

Prepared queries may use custom plans or generic plans depending on PostgreSQL's plan-cache decisions. Generic plans can still benefit from execution-time partition pruning. To compare explicitly in a lab:

```sql
SET plan_cache_mode = force_custom_plan;
PREPARE monthly(timestamptz,timestamptz) AS
SELECT count(*) FROM ch039.events WHERE event_time >= $1 AND event_time < $2;
EXPLAIN (ANALYZE, BUFFERS) EXECUTE monthly('2026-02-01+00','2026-03-01+00');
DEALLOCATE monthly;

SET plan_cache_mode = force_generic_plan;
PREPARE monthly(timestamptz,timestamptz) AS
SELECT count(*) FROM ch039.events WHERE event_time >= $1 AND event_time < $2;
EXPLAIN (ANALYZE, BUFFERS) EXECUTE monthly('2026-02-01+00','2026-03-01+00');
DEALLOCATE monthly;
RESET plan_cache_mode;
```

Interpret the *actual* plan and runtime; forced modes are diagnostic experiments, not blanket production tuning recommendations.

## 5. Index design on partitioned tables

A parent `CREATE INDEX` defines a partitioned index and creates matching physical indexes on existing leaf partitions. PostgreSQL has no general-purpose global index spanning all partitions. Choose local index key order from workload predicates, selectivity and ORDER BY. Examples:

```sql
CREATE INDEX events_tenant_time_idx ON ch039.events(tenant_id,event_time DESC);
```

A query with tenant and bounded time filters may use a local index scan. A time-only query may prefer sequential scans if most rows in the selected month qualify. Avoid creating every conceivable index on every partition: each index adds storage, WAL, write amplification and maintenance cost.

For large existing partition hierarchies, building an index concurrently on the partitioned parent is not generally supported directly. A documented operational pattern is to create an invalid parent index with `ON ONLY`, build matching child indexes concurrently, and attach them; review PostgreSQL 18 restrictions and exact DDL in a change plan.

## 6. Statistics, skew and planning overhead

Collect per-leaf stats and parent statistics. Changes to child partitions do not guarantee timely automatic ANALYZE of the partitioned parent. For skewed tenant/date distributions, inspect extended statistics and row estimate errors where applicable.

```sql
ANALYZE ch039.events;

SELECT relid::regclass AS relation, n_live_tup, last_analyze, last_autoanalyze
FROM pg_stat_user_tables
WHERE relid='ch039.events'::regclass
   OR relid IN (SELECT inhrelid FROM pg_inherits
                WHERE inhparent='ch039.events'::regclass);
```

Track `Planning Time`, `Execution Time`, buffers, rows removed by filter, estimated vs actual rows, and leaf count. Too many partitions can increase catalog, lock, memory and planning overhead even when pruning works.

## 7. Production investigation workflow

1. **Baseline:** query text, bind parameter types, plan mode, p50/p95/p99 latency, throughput, CPU/I/O and data distribution.
2. **Inspect:** `EXPLAIN (ANALYZE, BUFFERS, SETTINGS)` on a bounded representative query, mindful that ANALYZE executes the statement.
3. **Confirm pruning:** identify selected partitions, `Subplans Removed`, `never executed` nodes and loops.
4. **Check access paths:** local index definitions, index-only scan visibility, heap fetches and selectivity.
5. **Check statistics:** parent/leaf ANALYZE age, estimates, skew and prepared plan behavior.
6. **Change one variable:** predicate, index or stats, with rollback and storage/WAL budget.
7. **Validate:** compare plans and production-like latency over representative load, including ingest and replica impact.

Avoid forcing planner settings globally or adding indexes without measured benefit.

## 8. Troubleshooting matrix

| Symptom | Evidence | Investigation |
|---|---|---|
| Every partition scanned | Predicate omits key or hides bounds | Rewrite to direct typed key range |
| Generic plan looks broad | Subplans Removed / loops | Verify execution-time pruning |
| Pruning succeeds but slow | Buffers and actual rows | Index/selectivity/heap I/O |
| Estimates far from actual | ANALYZE timestamps, distributions | Parent and leaf stats |
| High planning latency | Many leaf partitions, Planning Time | Revisit granularity and query design |
| Index not used | Selectivity, sort, cost, stats | Benchmark alternatives, avoid forced scans |

## 9. Lab and acceptance

[Chapter 039 lab](../labs/039-partition-pruning-indexes-and-query-performance-lab.md) compares bounded/unbounded predicates, local index behavior, forced generic/custom plans, and statistics refresh. It does not alter production planner settings.

**Pass:** explain plan-time vs execution-time pruning, capture actual child scans and buffers, compare local index paths, and justify a safe optimization with a rollback plan. **Validation:** authored; PostgreSQL 18 runtime pending.

## Official references

- [Partition pruning](https://www.postgresql.org/docs/18/ddl-partitioning.html)
- [EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)
- [Planner configuration](https://www.postgresql.org/docs/18/runtime-config-query.html)
- [PREPARE](https://www.postgresql.org/docs/18/sql-prepare.html)
- [Statistics](https://www.postgresql.org/docs/18/planner-stats.html)

**Next:** Chapter 040 — Partition Lifecycle, Retention and Recovery Project.
