-- PostgreSQL 18. Invoke psql -X -qAt -v ON_ERROR_STOP=1 -v source_id=...
-- One JSON sample for the CONNECTED database. Read-only, no server counter reset.
\set ON_ERROR_STOP on
\set QUIET on
\if :{?source_id}
\else
  \echo 'Missing verified source_id'
  SELECT 1/0;
\endif
BEGIN READ ONLY;
SET LOCAL statement_timeout = '5s';
SET LOCAL lock_timeout = '1s';
SET LOCAL TIME ZONE 'UTC';
SET LOCAL stats_fetch_consistency = 'snapshot';
WITH d AS MATERIALIZED (
  SELECT datid, datname, stats_reset, numbackends, xact_commit, xact_rollback,
         blks_read, blks_hit, temp_files, temp_bytes, deadlocks
  FROM pg_stat_database WHERE datname = current_database()
)
SELECT jsonb_build_object(
  'schema_version', 1,
  'source_id', :'source_id',
  'server_addr', inet_server_addr()::text,
  'server_port', inet_server_port(),
  'server_version_num', current_setting('server_version_num')::integer,
  'postmaster_start', pg_postmaster_start_time(),
  'in_recovery', pg_is_in_recovery(),
  'database_oid', d.datid::bigint,
  'database_name', d.datname,
  'track_counts', current_setting('track_counts'),
  'stats_reset', d.stats_reset,
  'snapshot_at', pg_stat_get_snapshot_timestamp(),
  'sampled_at', clock_timestamp(),
  'gauges', jsonb_build_object('numbackends', d.numbackends),
  'counters', jsonb_build_object(
    'xact_commit', d.xact_commit, 'xact_rollback', d.xact_rollback,
    'blks_read', d.blks_read, 'blks_hit', d.blks_hit,
    'temp_files', d.temp_files, 'temp_bytes', d.temp_bytes, 'deadlocks', d.deadlocks)
) FROM d;
COMMIT;
