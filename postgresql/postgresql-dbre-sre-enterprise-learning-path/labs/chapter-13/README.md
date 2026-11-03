# Chapter 13 Lab — Observe Dead Tuples and Run Safe Routine VACUUM

**Platform:** Windows 11 PowerShell + Docker Desktop (Linux containers) · **Reference database:** PostgreSQL 17  
**Status:** Authored only; commands have **not** been executed against a live PostgreSQL runtime.  
**Duration:** 30-minute guided exercise within the chapter's 60-minute session.

[Chapter 13](../../chapters/13-vacuum-autovacuum-bloat-and-maintenance.md) · [Learning path](../../README.md)

## 0. Preconditions, isolation and guardrails (5 minutes)

This lab creates **one isolated disposable container** named `pg-maint-ch13`. It does not use any Chapter 01–12 containers, host ports, cloud resources, production data or production credentials.

In Windows PowerShell:

```powershell
docker version
docker info --format '{{.OSType}}'
docker ps -a --filter "name=pg-maint-ch13"
```

Expected: Docker daemon available and OSType `linux`; no existing container with that name. **If the name exists, STOP and inspect; do not overwrite, reuse or delete an unknown resource.**

All values below are synthetic. The demonstration password is for this private disposable container only. Never copy it to production or put real credentials in source control.

## 1. Start PostgreSQL 17 (3 minutes)

```powershell
docker run -d --name pg-maint-ch13 -e POSTGRES_PASSWORD=TrainingOnly_Ch13_ChangeMe postgres:17
docker exec pg-maint-ch13 pg_isready -U postgres -d postgres
docker exec pg-maint-ch13 psql -U postgres -d postgres -c "SELECT current_database(), current_user, current_setting('server_version') AS version, pg_is_in_recovery();"
```

Expected: readiness accepts connections; database is `postgres`, user is `postgres`, server major version is 17, recovery is false. If initialization is still running, wait briefly and retry readiness. The container publishes **no host TCP port**.

Connect interactively:

```powershell
docker exec -it pg-maint-ch13 psql -U postgres -d postgres
```

Unless noted otherwise, the remaining SQL commands run **inside this psql session** and should be executed in order.

## 2. Baseline autovacuum settings and XID horizon (4 minutes)

```sql
SELECT current_database(), current_user, pg_is_in_recovery();
SHOW autovacuum;
SHOW track_counts;
SHOW autovacuum_vacuum_threshold;
SHOW autovacuum_vacuum_scale_factor;
SHOW autovacuum_vacuum_insert_threshold;
SHOW autovacuum_vacuum_insert_scale_factor;
SHOW autovacuum_freeze_max_age;

SELECT datname, age(datfrozenxid) AS xid_age,
       mxid_age(datminmxid) AS multixact_age
FROM pg_database
ORDER BY xid_age DESC;
```

Expected: autovacuum and track_counts ordinarily `on` in the default image. XID/multixact ages vary. **Do not change freeze or autovacuum settings in this lab.**

## 3. Create a synthetic churn table (4 minutes)

On a first-time empty lab container:

```sql
CREATE TABLE public.maintenance_ch13 (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_status TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO public.maintenance_ch13 (event_status, payload)
SELECT 'new', repeat(md5(g::text), 8)
FROM generate_series(1, 20000) AS g;

ANALYZE public.maintenance_ch13;

SELECT count(*) AS live_rows FROM public.maintenance_ch13;
SELECT pg_size_pretty(pg_total_relation_size('public.maintenance_ch13')) AS total_size_before;
```

Expected: 20,000 live rows. The size varies with storage, indexes and TOAST decisions. `ANALYZE` updates planner statistics; it does not remove dead tuples.

**Idempotency:** If the table already exists, do not rerun CREATE/INSERT blindly. Inspect it, then use a new disposable container name for a clean exercise if appropriate.

## 4. Generate UPDATE/DELETE churn (4 minutes)

```sql
UPDATE public.maintenance_ch13
SET event_status = 'processed',
    payload = payload || '-v2'
WHERE event_id % 2 = 0;

DELETE FROM public.maintenance_ch13
WHERE event_id % 10 = 1;

SELECT count(*) AS remaining_rows,
       count(*) FILTER (WHERE event_status='processed') AS processed_rows
FROM public.maintenance_ch13;
```

Expected: 10,000 updated rows; 2,000 deleted rows; **18,000 remaining** and **10,000 processed**. The DELETE selects odd IDs, so it does not remove any of the even-ID updated rows.

Conceptually, UPDATE produces old row versions, while DELETE makes deleted row versions obsolete once no snapshot needs them. The exact physical tuple state and number of removable versions can vary.

## 5. Inspect estimates, sizes and vacuum history (4 minutes)

```sql
SELECT pg_sleep(1);
SELECT pg_stat_clear_snapshot();

SELECT relname, n_live_tup, n_dead_tup,
       n_tup_ins, n_tup_upd, n_tup_del, n_tup_hot_upd,
       last_vacuum, last_autovacuum, last_analyze, last_autoanalyze
FROM pg_stat_user_tables
WHERE schemaname = 'public' AND relname = 'maintenance_ch13';

SELECT pg_size_pretty(pg_relation_size('public.maintenance_ch13')) AS heap_size,
       pg_size_pretty(pg_indexes_size('public.maintenance_ch13')) AS indexes_size,
       pg_size_pretty(pg_total_relation_size('public.maintenance_ch13')) AS total_size;

SELECT relname, reloptions
FROM pg_class
WHERE oid = 'public.maintenance_ch13'::regclass;

SELECT pid, relid::regclass AS relation, phase,
       heap_blks_total, heap_blks_scanned, heap_blks_vacuumed
FROM pg_stat_progress_vacuum
WHERE datname = current_database();
```

Expected: cumulative insert/update/delete counters and size values; the dead-tuple estimate **may be positive or already low/zero** if autovacuum or page cleanup ran. A short-lived VACUUM may finish before the progress query, leaving zero rows. These are valid observations.

**Why:** PostgreSQL's cumulative statistics update asynchronously, and the background autovacuum worker can race with a small demonstration workload. Do not disable autovacuum to manufacture a dead-tuple count.

## 6. Perform routine VACUUM (3 minutes)

**Safety checkpoint:** Confirm the `psql` prompt is connected to `postgres` inside `pg-maint-ch13`. Run this only in the disposable lab, and not within an explicit `BEGIN`/`COMMIT` transaction block.

```sql
SELECT current_database(), pg_is_in_recovery();
VACUUM (VERBOSE, ANALYZE) public.maintenance_ch13;
```

Expected: `VACUUM` succeeds; VERBOSE messages may report scanned pages, dead tuples, indexes and freeze information. `VACUUM` cannot run inside a transaction block. If the session is in an aborted transaction, issue `ROLLBACK;` and confirm lab identity before retrying.

**Do not run `VACUUM FULL`.** It rewrites the table, requires an ACCESS EXCLUSIVE lock, and needs additional disk space. This lab tests ordinary VACUUM only.

## 7. Verify and interpret the result (3 minutes)

```sql
SELECT pg_stat_clear_snapshot();

SELECT relname, n_live_tup, n_dead_tup,
       last_vacuum, vacuum_count,
       last_autovacuum, autovacuum_count,
       last_analyze
FROM pg_stat_user_tables
WHERE schemaname='public' AND relname='maintenance_ch13';

SELECT count(*) AS remaining_rows FROM public.maintenance_ch13;

SELECT pg_size_pretty(pg_total_relation_size('public.maintenance_ch13')) AS total_size_after;

SELECT c.relname,
       age(c.relfrozenxid) AS relation_xid_age,
       mxid_age(c.relminmxid) AS relation_multixact_age
FROM pg_class AS c
WHERE c.oid='public.maintenance_ch13'::regclass;
```

Expected: **18,000 live application rows**. The last manual vacuum timestamp and/or vacuum count should reflect this operation once stats become visible; if not, wait briefly and query again. `n_dead_tup` should often decrease but is not an exact invariant. **Do not require total relation size to shrink**: reclaimed space is normally reusable inside the relation.

## 8. Diagnose a hypothetical production symptom (5 minutes)

Scenario: a high-churn production table grows steadily; dashboard shows increasing dead-tuple estimates, autovacuum activity and query latency.

Write a short DBRE/SRE assessment covering:

1. Which metrics distinguish table growth from actual physical bloat?
2. What evidence would show a long transaction holding back cleanup?
3. How do autovacuum thresholds relate to the table's estimated row count?
4. How would you assess I/O, locks, WAL volume and change-window impact before a manual vacuum?
5. Why is `VACUUM FULL` not an automatic first response?
6. Which teams approve maintenance and what constitutes a safe rollback/stop condition?
7. What would you monitor afterward to prevent recurrence?

**Example safe read-only diagnostic for an incident:**

```sql
SELECT pid, usename, datname, state,
       now() - xact_start AS xact_age,
       age(backend_xmin) AS xmin_age
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
ORDER BY xact_start;

SELECT datname, age(datfrozenxid) AS xid_age
FROM pg_database
ORDER BY xid_age DESC;
```

Do not terminate sessions, drop slots or change global autovacuum settings as part of this training.

## 9. Acceptance and evidence checklist

- [ ] Confirmed local container identity and PostgreSQL 17.
- [ ] Captured baseline autovacuum settings and XID age.
- [ ] Inserted 20,000 synthetic rows, updated 10,000, deleted 2,000.
- [ ] Verified exactly 18,000 remaining rows.
- [ ] Queried table statistics and understood estimates may lag.
- [ ] Captured table/index/total relation sizes before and after.
- [ ] Executed ordinary `VACUUM (VERBOSE, ANALYZE)` outside a transaction.
- [ ] Inspected last vacuum time/count and relation XID horizon.
- [ ] Explained why physical storage may not decrease.
- [ ] Completed a risk-aware maintenance assessment.
- [ ] Stored sanitized **actual** outputs separately if executed; do not mark the lab validated based on expected results.

**Current status:** Not executed; no independent review, staging certification or production readiness approval.

## 10. Troubleshooting

| Symptom | Likely explanation | Safe action |
|---|---|---|
| Docker daemon unavailable | Docker Desktop or Linux engine stopped | Start local engine; rerun preflight |
| Container name exists | Prior lab or unrelated resource | Inspect identity; do not delete automatically |
| Relation already exists | Lab rerun | Inspect existing data; choose a new isolated lab for a clean run |
| Dead tuple estimate is zero | Autovacuum ran or stats lagged | Check last_autovacuum and counters; do not disable autovacuum |
| VACUUM rejected inside transaction | Explicit transaction block is open | End it safely with COMMIT/ROLLBACK; rerun standalone |
| Relation size unchanged | Space became internally reusable | Evaluate future reuse and bloat evidence, not size alone |
| Progress view empty | Vacuum finished or not running | Use last_vacuum and logs/metrics for completed work |
| Unexpected row count | Wrong database, repeated workload or manual changes | Verify database identity; stop before destructive resets |

## 11. Optional cleanup — deliberate and isolated

Exit `psql` with `\q`. Keep the container if you want to preserve lab evidence. **Only when finished and after confirming that the exact disposable Chapter 13 container is yours**, you may stop it:

```powershell
docker inspect --format '{{.Name}} {{.Config.Image}}' pg-maint-ch13
docker stop pg-maint-ch13
```

To permanently remove **this dedicated lab container and all its ephemeral data**, run the following only after confirming no needed evidence remains:

```powershell
docker rm -v pg-maint-ch13
```

This is destructive to the container's unmounted data and is **never** an instruction to remove production or another chapter's container. No host ports or named volumes are created by this lab. The official PostgreSQL 17 image declares a data volume, so Docker may create an anonymous volume; `docker rm -v` removes anonymous volumes attached to this verified disposable container. Do not prune unrelated volumes.

## Official references

- [PostgreSQL 17: Routine Vacuuming](https://www.postgresql.org/docs/17/routine-vacuuming.html)
- [PostgreSQL 17: VACUUM](https://www.postgresql.org/docs/17/sql-vacuum.html)
- [PostgreSQL 17: Autovacuum Configuration](https://www.postgresql.org/docs/17/runtime-config-autovacuum.html)
- [PostgreSQL 17: Monitoring Statistics](https://www.postgresql.org/docs/17/monitoring-stats.html)
- [PostgreSQL 17: Progress Reporting](https://www.postgresql.org/docs/17/progress-reporting.html)
