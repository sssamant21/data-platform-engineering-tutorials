# Chapter 040 — Partition Lifecycle, Retention and Recovery Lab
**V02-B destructive cleanup gate:** Cleanup is deliberately blocked until the operator passes the exact database name, the PostgreSQL 18 cluster system identifier, and the chapter token `040-DROP`. On the **same disposable target** used by this lab, first run `SELECT current_database(), system_identifier FROM pg_control_system();`, examine the reported values and verify the instance is truly disposable. Manually replace `REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID` in the cleanup command. The system identifier alone does not prove that an environment is safe; never execute this cleanup on production or shared staging. These guards are not a substitute for reviewing ownership and dependencies.


**PostgreSQL 18. Disposable database only. Runtime execution pending.** Use an isolated database. The scripts use a dedicated schema `ch040` and must not be executed against production or shared staging.

## Run from repository root

```bash
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/040-setup.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/040-investigate.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -v expected_db=postgres -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID -v confirm_cleanup=040-DROP -f postgresql/labs/sql/040-cleanup.sql
```

## Exercises

1. Inspect partition bounds, row counts and local indexes.
2. Provision April 2026 ahead of ingestion and insert an event into the new partition.
3. Insert a late-arriving January event and verify routing.
4. Compare EXPLAIN for a February-only query against an unbounded query.
5. Record January row count; detach January and verify that its standalone table still holds all rows.
6. Reattach January using the original bounds and compare total counts and routing.
7. Independently verify an archive by restoring into a separate disposable database before marking archival acceptance. This archive test is an operator-controlled extension, not automated by the SQL scripts.
8. Complete cleanup after verifying the lab schema is exclusively owned by the exercise.

## Acceptance

| Check | Expected |
|---|---|
| Future partition | April exists and accepts events |
| Late arrival | January row routed correctly |
| Pruning | February filter excludes unrelated partitions |
| Detach | January data preserved in standalone table |
| Recovery | Reattach restores parent visibility and counts |
| Archive | Independent restore test documented |
| Cleanup | Lab objects removed |

**Stop conditions:** unexpected locks, mismatched row counts, missing backups, unapproved deletion or replica risk. **Runtime validation:** pending.
