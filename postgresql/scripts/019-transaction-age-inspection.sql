-- PostgreSQL 18. Metadata only; no cancellation or application-table access.
-- Observer values below are not the target sessions' effective settings.
\set ON_ERROR_STOP on
\pset pager off
BEGIN READ ONLY;
SET LOCAL statement_timeout = '5s';
SET LOCAL lock_timeout = '1s';
SELECT clock_timestamp() AS sampled_at, pid, backend_start,
       datname, usename, application_name, state,
       clock_timestamp() - xact_start AS transaction_age,
       CASE WHEN state = 'active'
            THEN clock_timestamp() - query_start END AS active_statement_age,
       CASE WHEN state LIKE 'idle%'
            THEN clock_timestamp() - state_change END AS idle_age,
       backend_xid, backend_xmin, wait_event_type, wait_event,
       pg_blocking_pids(pid) AS blocking_pids
FROM pg_stat_activity
WHERE datname = current_database()
  AND backend_type = 'client backend'
  AND pid <> pg_backend_pid()
ORDER BY xact_start NULLS LAST, pid
LIMIT 100;
SELECT name, setting, unit, source
FROM pg_settings
WHERE name IN ('statement_timeout', 'lock_timeout',
 'transaction_timeout', 'idle_in_transaction_session_timeout',
 'idle_session_timeout')
ORDER BY name;
COMMIT;
