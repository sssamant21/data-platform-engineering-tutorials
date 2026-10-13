# Chapter 033 — Hands-on DBRE/SRE Index Maintenance Lab

**PostgreSQL:** 18. **Target:** disposable local database only. **Never run this fixture or failure injection in production.** Use a dedicated database and verify your connection before starting. SQL scripts drop only schema `ch033`, but they intentionally destroy any pre-existing schema with that name.

## 1. Run from repository root

```bash
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/033-setup.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/033-investigate.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/033-cleanup.sql
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
