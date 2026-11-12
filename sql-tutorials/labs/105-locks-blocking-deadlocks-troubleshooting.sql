-- 105: observational locks + fictional wait-for graph; no contention or backend intervention.
-- Run ONLY in disposable PostgreSQL 18 database sql_tutorials.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
  IF current_database() <> 'sql_tutorials' THEN
    RAISE EXCEPTION 'Disposable database sql_tutorials required; got %', current_database();
  END IF;
  IF current_setting('server_version_num')::integer / 10000 <> 18 THEN
    RAISE EXCEPTION 'PostgreSQL 18 required; got %', current_setting('server_version');
  END IF;
END
$guard$;

-- Current session only. Count and modes depend on environment.
SELECT locktype, mode, granted, count(*) AS observed_locks
FROM pg_locks WHERE pid = pg_backend_pid()
GROUP BY locktype, mode, granted ORDER BY locktype, mode, granted;

-- Entirely synthetic graph. IDs are invented; no actual sessions are touched.
WITH edges(waiter,blocker) AS (
 VALUES (101,102),(102,101),(103,104),(105,104),(106,107)
)
SELECT waiter, blocker,
       EXISTS (SELECT 1 FROM edges reverse_edge
               WHERE reverse_edge.waiter = edges.blocker
                 AND reverse_edge.blocker = edges.waiter) AS direct_cycle
FROM edges ORDER BY waiter;

WITH edges(waiter,blocker) AS (
 VALUES (101,102),(102,101),(103,104),(105,104),(106,107)
), classified AS (
 SELECT waiter,blocker,
        EXISTS (SELECT 1 FROM edges e2
                WHERE e2.waiter = e.blocker AND e2.blocker = e.waiter) AS in_cycle
 FROM edges e
)
SELECT count(*) AS edges,
       count(*) FILTER (WHERE in_cycle) AS cycle_participants,
       count(*) FILTER (WHERE NOT in_cycle) AS noncycle_waiters,
       count(DISTINCT blocker) FILTER (WHERE NOT in_cycle) AS noncycle_blocker_ids
FROM classified;

DO $assert$
DECLARE missing_count integer; extra_count integer;
BEGIN
  WITH edges(waiter,blocker) AS (
    VALUES (101,102),(102,101),(103,104),(105,104),(106,107)
  ), classified AS (
    SELECT e.waiter,e.blocker,
           EXISTS (SELECT 1 FROM edges r
                   WHERE r.waiter=e.blocker AND r.blocker=e.waiter) AS in_cycle
    FROM edges e
  ), actual(metric,n) AS (
    SELECT 'edges', count(*)::bigint FROM classified
    UNION ALL SELECT 'cycle_participants', count(*)::bigint FROM classified WHERE in_cycle
    UNION ALL SELECT 'noncycle_waiters', count(*)::bigint FROM classified WHERE NOT in_cycle
    UNION ALL SELECT 'noncycle_blocker_ids', count(DISTINCT blocker)::bigint FROM classified WHERE NOT in_cycle
  ), expected(metric,n) AS (
    VALUES ('edges',5::bigint),('cycle_participants',2::bigint),
           ('noncycle_waiters',3::bigint),('noncycle_blocker_ids',2::bigint)
  ), missing AS (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual),
     extra AS (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
  SELECT (SELECT count(*) FROM missing),(SELECT count(*) FROM extra)
  INTO missing_count,extra_count;
  IF missing_count <> 0 OR extra_count <> 0 THEN
    RAISE EXCEPTION '105 synthetic graph assertions failed: missing %, extra %',
      missing_count,extra_count;
  END IF;
  RAISE NOTICE '105 synthetic graph assertions passed (5 edges, 2 cycle participants, 3 noncycle waiters, 2 noncycle blockers)';
END
$assert$;
ROLLBACK;
