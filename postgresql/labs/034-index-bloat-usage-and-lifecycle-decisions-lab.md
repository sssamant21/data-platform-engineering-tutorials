# Chapter 034 — Hands-on Index Bloat, Usage and Lifecycle Lab

**Baseline:** PostgreSQL 18. **Safety:** disposable local database only; setup and cleanup destroy schema `ch034`. Do not run on production or shared staging.

## Execute

```bash
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/034-setup.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/034-investigate.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/034-cleanup.sql
```

Use `psql` directly; `VACUUM` in the investigation must run outside a transaction block. Save output to an evidence log if required. The script uses `pg_stat_clear_snapshot()` to avoid a stale statistics snapshot; asynchronous statistics propagation can still make deltas lag.

## Six investigations

1. **Inventory and dependency:** capture `pg_index` validity, primary/unique flags, index definitions and sizes. Confirm the primary key is not an optional index.
2. **Usage baseline:** collect stats reset time, `idx_scan`, `idx_tup_read`, `idx_tup_fetch` and representative EXPLAIN plans.
3. **Write churn:** update a bounded subset and delete a bounded subset; compare row estimates, table/index sizes, HOT counters and query plans.
4. **Maintenance:** run `VACUUM (ANALYZE)`; inspect new sizes and dead tuple estimates. Do not assume VACUUM shrinks the index file.
5. **Redundancy review:** compare two indexes with a shared leading column, including their ordering semantics and write/storage tradeoffs.
6. **Lifecycle exercise:** remove only a lab-owned non-constraint index concurrently, then recreate it concurrently and verify its definition and validity.

## Expected behavior

The planner may prefer sequential scans on synthetic data; stats can lag; disk size may stay constant after deletes/VACUUM. These are valid observations, not failures. The lab does not prove physical bloat or production benefits of REINDEX.

## Evidence worksheet

| Stage | Time/reset | Index | idx_scan delta | Bytes | Plan/buffers | HOT/dead rows | Decision |
|---|---|---|---|---|---|---|---|
| Before churn | | | | | | | |
| After churn | | | | | | | |
| After VACUUM | | | | | | | |
| After lifecycle | | | | | | | |

**Pass:** retain constraint index; correctly interpret stats reset/window; record index size and plans; execute and verify the lab-only concurrent drop/recreate; clean up `ch034`.

**Status:** Authored; PostgreSQL 18 runtime verification pending.
