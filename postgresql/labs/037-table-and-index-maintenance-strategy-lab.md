# Chapter 037 — Maintenance Strategy Lab

**PostgreSQL 18. Disposable local environment only. Runtime validation pending.**

## Run

```bash
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/037-setup.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/037-investigate.sql
psql -X -v ON_ERROR_STOP=1 -d postgres -f postgresql/labs/sql/037-cleanup.sql
```

## Exercises

1. Inventory table/index sizes, definitions, dead-tuple estimates and vacuum timestamps.
2. Capture EXPLAIN (ANALYZE, BUFFERS) on a bounded query.
3. Generate synthetic update/delete churn.
4. Compare ANALYZE with VACUUM (ANALYZE) outcomes.
5. Check freeze age, active transactions and replica-slot status.
6. Choose whether to wait, vacuum, analyze, reindex or request a rewrite. Record locks, WAL, disk and rollback requirements.
7. Verify the lab environment is clean.

| Choice | Evidence | Lock risk | Capacity | Recovery plan |
|---|---|---|---|---|
| ANALYZE | | | | |
| VACUUM | | | | |
| REINDEX CONCURRENTLY | | | | |
| VACUUM FULL | | | | |

**Acceptance:** evidence-driven choice and documented risks. **Execution:** pending.
