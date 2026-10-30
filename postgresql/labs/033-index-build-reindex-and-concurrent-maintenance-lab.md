# Chapter 033 — Hands-on DBRE/SRE Index Maintenance Lab
**V02-B destructive cleanup gate:** Cleanup is deliberately blocked until the operator passes the exact database name, the PostgreSQL 18 cluster system identifier, and the chapter token `033-DROP`. On the **same disposable target** used by this lab, first run `SELECT current_database(), system_identifier FROM pg_control_system();`, examine the reported values and verify the instance is truly disposable. Manually replace `REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID` in the cleanup command. The system identifier alone does not prove that an environment is safe; never execute this cleanup on production or shared staging. These guards are not a substitute for reviewing ownership and dependencies.


**PostgreSQL:** 18. **Target:** disposable local database only. **Never run this fixture or failure injection in production.** Use a dedicated database and verify your connection before starting. Setup now refuses an existing `ch033` schema; the separately confirmed cleanup destroys that schema.

## 1. Run from repository root

```bash
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/033-setup.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/033-investigate.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -v expected_db=postgres -v expected_system_id=REPLACE_WITH_OBSERVED_LAB_SYSTEM_ID -v confirm_cleanup=033-DROP -f postgresql/labs/sql/033-cleanup.sql
```

The investigation script uses psql's `\\set ON_ERROR_STOP off` for **one intentional unique-index failure**, then restores strict error handling. Run it with `psql`, not a migration framework or transaction-wrapping client.

## 2. Investigation sequence

1. **Baseline:** record database identity, existing indexes, row counts and initial query plan.
2. **Regular build:** create customer index; observe size and plan. Explain the write-blocking risk.
3. **Concurrent build:** create time index outside a transaction; observe validity and record whether a separate observer session caught progress.
4. **Concurrent reindex:** rebuild time index; verify the same logical index remains valid.
5. **Failure injection:** attempt a UNIQUE concurrent index on deliberately duplicated `status`; capture the expected failure and inspect the invalid artifact. Do not use this technique on shared systems.
6. **Recovery:** only if the exact invalid lab artifact is present, drop it concurrently; verify no invalid indexes remain.

## 3. Optional observer session

Open a second `psql` session while the investigation runs and repeat:

```sql
SELECT pid, command, phase, blocks_done, blocks_total,
       lockers_done, lockers_total, current_locker_pid
FROM pg_stat_progress_create_index
WHERE relid = 'ch033.orders'::regclass;
```

Small builds may finish before you observe a row. That is not a test failure. For concurrency/wait testing, use separate coordinated sessions and bounded transactions; never simulate blockers on production.

## 4. Evidence and acceptance

| Operation | Start/end | Lock or wait evidence | Index valid/ready | Index bytes | WAL/replica impact | Decision |
|---|---|---|---|---|---|---|
| Regular build | | | | | | |
| Concurrent build | | | | | | |
| Concurrent reindex | | | | | | |
| Expected failure | | | | | | |
| Invalid-index cleanup | | | | | | |

Pass when the intentional unique build fails for duplicates, the invalid index is observed, cleanup succeeds, and all remaining indexes are valid. Record explain plans, timings and operational tradeoffs; do not claim synthetic performance gains generalize to production.

**Status:** Authored; PostgreSQL 18 runtime verification pending.
