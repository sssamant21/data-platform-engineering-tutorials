-- Chapter 001: read-only first-response snapshot.
-- Reference major: PostgreSQL 18. Run in psql, outside a long explicit transaction.
-- Uses current connection credentials. No query text or application data is exported.
\set ON_ERROR_STOP on
\pset pager off
SET statement_timeout = '5s';
SET lock_timeout = '1s';

\echo '=== Identity and instance ==='
SELECT clock_timestamp() AT TIME ZONE 'UTC' AS captured_at_utc,
       current_database() AS database_name,
       current_user AS session_role,
       inet_server_addr() AS server_address,
       inet_server_port() AS server_port,
       current_setting('server_version') AS server_version,
       pg_is_in_recovery() AS in_recovery,
       current_setting('transaction_read_only') AS transaction_read_only,
       pg_postmaster_start_time() AS server_started_at;

\echo '=== Selected settings: values must be read with their units ==='
SELECT name, setting, unit, context, source, pending_restart
FROM pg_settings
WHERE name IN ('max_connections', 'superuser_reserved_connections',
               'reserved_connections', 'shared_buffers', 'work_mem',
               'maintenance_work_mem', 'wal_level', 'archive_mode',
               'autovacuum', 'track_activities', 'track_counts')
ORDER BY name;

\echo '=== Client sessions: ordinary roles can have limited detail visibility ==='
SELECT datname, usename, application_name, state,
       wait_event_type, wait_event, count(*) AS sessions
FROM pg_stat_activity
WHERE backend_type = 'client backend'
GROUP BY datname, usename, application_name, state, wait_event_type, wait_event
ORDER BY sessions DESC, datname, usename
LIMIT 30;

\echo '=== Non-idle client activity, without query text ==='
SELECT pid, datname, usename, application_name, state,
       clock_timestamp() - xact_start AS transaction_age,
       clock_timestamp() - query_start AS query_age,
       wait_event_type, wait_event
FROM pg_stat_activity
WHERE backend_type = 'client backend'
  AND pid <> pg_backend_pid()
  AND state IS DISTINCT FROM 'idle'
ORDER BY xact_start NULLS LAST, query_start NULLS LAST
LIMIT 20;

\echo '=== Database footprints: not filesystem free space ==='
SELECT datname, pg_size_pretty(pg_database_size(oid)) AS database_size
FROM pg_database
WHERE datallowconn
  AND has_database_privilege(oid, 'CONNECT')
ORDER BY pg_database_size(oid) DESC
LIMIT 20;

\echo '=== Database counters: rate calculations require another sample ==='
SELECT datname, numbackends, xact_commit, xact_rollback,
       deadlocks, stats_reset
FROM pg_stat_database
WHERE datname IS NOT NULL
ORDER BY datname
LIMIT 20;
