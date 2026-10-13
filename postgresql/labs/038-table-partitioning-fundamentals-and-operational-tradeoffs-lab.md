# Chapter 038 — Table Partitioning Hands-on Lab

**PostgreSQL 18 · Disposable database only · Runtime verification pending.** Run against a local lab instance. The scripts operate on schema `ch038`; verify the schema is lab-owned before cleanup.

## Commands

```bash
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/038-setup.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/038-investigate.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/038-cleanup.sql
```

Do not wrap a concurrent detach in a transaction block. This lab uses ordinary DETACH/ATTACH on an isolated small table; it is not a production retention procedure.

## Exercises

1. Confirm server version and cluster/database identity; inspect the existing schema before running setup.
2. Create a partitioned parent and January, February, March 2026 child tables.
3. Insert 9,000 synthetic events spanning the three months; inspect row routing with `tableoid::regclass`.
4. Inspect `pg_inherits`, partition bounds and parent/child index definitions.
5. Compare `EXPLAIN (ANALYZE, BUFFERS)` for a February-only predicate against an unbounded query; record scanned partitions and planning/execution time.
6. Demonstrate a safe February partition detach and reattach; validate that the row count and routing are unchanged. Do **not** drop retained data.
7. Inspect leaf table statistics, ANALYZE the parent and record pruning/maintenance implications.
8. Remove only the lab-owned schema after verifying no non-lab objects exist.

## Acceptance matrix

| Check | Expected |
|---|---|
| Parent | `PARTITION BY RANGE(event_time)` |
| Bounds | Three non-overlapping monthly partitions |
| Routing | Rows map to correct month |
| Pruning | February filter excludes unrelated leaf scans |
| Detached table | Still exists as ordinary table |
| Reattach | Parent count and routing restored |
| Cleanup | Lab schema absent |

## Troubleshooting

If inserts fail with no partition found, inspect date bounds and timezone. If pruning is absent, inspect predicate and EXPLAIN; a plan can change with row count and optimizer choices. If ATTACH fails, check bounds, constraints and conflicting rows. Avoid attempting the exercise in shared environments.

**Evidence:** Save before/after EXPLAIN output, partition catalog queries, row counts, commands and cleanup confirmation. **Runtime:** pending.
