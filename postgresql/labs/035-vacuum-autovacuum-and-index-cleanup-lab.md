# Chapter 035 — Hands-on DBRE/SRE VACUUM Lab
**V02-B destructive cleanup gate:** Cleanup is deliberately blocked until the operator passes the exact database name, the PostgreSQL 18 cluster system identifier, and the chapter token `035-DROP`. On the **same disposable target** used by this lab, first run `SELECT current_database(), system_identifier FROM pg_control_system();`, examine the reported values and verify the instance is truly disposable. Manually replace `REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID` in the cleanup command. The system identifier alone does not prove that an environment is safe; never execute this cleanup on production or shared staging. These guards are not a substitute for reviewing ownership and dependencies.


**PostgreSQL 18. Disposable database only.** Setup refuses an existing schema; separately confirmed cleanup drops `ch035` and its objects. Do not run on production/shared staging.

## Commands

```bash
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/035-setup.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/035-investigate.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -v expected_db=postgres -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID -v confirm_cleanup=035-DROP -f postgresql/labs/sql/035-cleanup.sql
```

`VACUUM` must execute outside a transaction block; use psql rather than a migration wrapper. Capture terminal output as evidence. Statistics updates can lag and auto-vacuum may run independently, so results are not deterministic.

## Six investigations

1. **Baseline:** record database identity, table/index sizes, row count, stats reset and current autovacuum settings.
2. **Thresholds:** inspect the configured trigger settings; apply a lab-only per-table threshold and record its `reloptions`.
3. **Churn:** update and delete a bounded row set; inspect estimated dead tuples, HOT counters and index sizes.
4. **Progress:** observe `pg_stat_progress_vacuum` from a second session during maintenance if time permits; short operations may be missed.
5. **Maintenance:** run `VACUUM (VERBOSE, ANALYZE, INDEX_CLEANUP AUTO)`; compare estimates and sizes; explain why files may not shrink.
6. **Freeze safety:** capture database/table XID age and oldest active transaction metadata; **do not** simulate wraparound or disable autovacuum.

## Evidence table

| Phase | Dead tuples estimate | Table/index bytes | XID age | Vacuum timestamp | Progress/waits | Interpretation |
|---|---|---|---|---|---|---|
| Baseline | | | | | | |
| After churn | | | | | | |
| After VACUUM | | | | | | |

## Optional observer

```sql
SELECT pid, relid::regclass, phase, heap_blks_total, heap_blks_scanned,
       heap_blks_vacuumed, index_vacuum_count
FROM pg_stat_progress_vacuum
WHERE relid='ch035.events'::regclass;
```

**Pass:** describe safe autovacuum tuning and rollback; distinguish estimated statistics from physical bytes; observe or explain absence of progress rows; verify the schema is removed. **Runtime verification:** pending.
