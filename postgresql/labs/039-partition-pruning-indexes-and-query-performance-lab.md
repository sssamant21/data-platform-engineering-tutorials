# Chapter 039 — Partition Pruning, Indexes and Query Performance Lab
**V02-B destructive cleanup gate:** Cleanup is deliberately blocked until the operator passes the exact database name, the PostgreSQL 18 cluster system identifier, and the chapter token `039-DROP`. On the **same disposable target** used by this lab, first run `SELECT current_database(), system_identifier FROM pg_control_system();`, examine the reported values and verify the instance is truly disposable. Manually replace `REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID` in the cleanup command. The system identifier alone does not prove that an environment is safe; never execute this cleanup on production or shared staging. These guards are not a substitute for reviewing ownership and dependencies.


**PostgreSQL 18 · Disposable local database only · Runtime verification pending.** The scripts use a dedicated schema `ch039`. Confirm it does not contain existing work before setup or cleanup.

## Execute from repository root

```bash
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/039-setup.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/039-investigate.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -v expected_db=postgres -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID -v confirm_cleanup=039-DROP -f postgresql/labs/sql/039-cleanup.sql
```

## Investigation steps

1. Inspect server version, partition bounds, leaf indexes and row counts.
2. Run `EXPLAIN (ANALYZE, BUFFERS, SETTINGS)` for a February-only time range.
3. Run a tenant-only predicate without time bounds and identify how many partitions are visited.
4. Compare tenant-plus-time predicates with local index access.
5. Compare `force_custom_plan` and `force_generic_plan` for a prepared time-range query; record `Subplans Removed`, `never executed` and loop counts.
6. Refresh parent statistics and compare planning and execution time.
7. Complete a production recommendation with index write-cost, WAL, storage and rollback implications.

## Evidence matrix

| Query | Selected partitions | Plan time | Execution time | Shared buffers | Index access |
|---|---|---|---|---|---|
| February range | | | | | |
| Tenant only | | | | | |
| Tenant + February | | | | | |
| Prepared custom | | | | | |
| Prepared generic | | | | | |

**Acceptance:** correctly identify pruning versus local index selection, show parameter-plan effects without assuming a generic plan is bad, and remove only the lab schema. **Runtime:** pending.
