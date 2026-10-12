-- Disposable Chapter 020 metadata collector; no signals or application data.
\set ON_ERROR_STOP on
\pset pager off
BEGIN READ ONLY;
SET LOCAL statement_timeout = '5s';
SET LOCAL lock_timeout = '1s';
SET LOCAL TIME ZONE 'UTC';
WITH actors AS MATERIALIZED (
  SELECT pid, backend_start, datname, usename, application_name,
         state, xact_start, query_start, state_change,
         wait_event_type, wait_event
  FROM pg_stat_activity
  WHERE datname = 'ops_lab' AND backend_type = 'client backend'
    AND application_name IN ('c020_A','c020_B','c020_C')
  ORDER BY pid LIMIT 20
)
SELECT clock_timestamp() AS sampled_at, *,
       clock_timestamp() - xact_start AS transaction_age,
       pg_blocking_pids(pid) AS direct_blockers
FROM actors ORDER BY pid;
WITH actors AS MATERIALIZED (
  SELECT pid FROM pg_stat_activity
  WHERE datname = 'ops_lab' AND backend_type = 'client backend'
    AND application_name IN ('c020_A','c020_B','c020_C')
  ORDER BY pid LIMIT 20
), edges AS (
  SELECT DISTINCT a.pid AS waiter_pid, b.blocker_pid
  FROM actors a
  CROSS JOIN LATERAL unnest(pg_blocking_pids(a.pid)) AS b(blocker_pid)
)
SELECT e.*, s.backend_start AS blocker_start, s.datname AS blocker_database,
       s.usename AS blocker_role, s.application_name AS blocker_application,
       s.backend_type AS blocker_type, s.state AS blocker_state,
       CASE WHEN e.blocker_pid = 0 THEN 'prepared transaction: investigate coordinator'
            WHEN a.pid IS NULL THEN 'outside actor set: investigate separately'
            ELSE 'lab actor: review owner and impact' END AS review_boundary
FROM edges e
LEFT JOIN pg_stat_activity s ON s.pid = e.blocker_pid
LEFT JOIN actors a ON a.pid = e.blocker_pid
ORDER BY waiter_pid, blocker_pid;
COMMIT;
