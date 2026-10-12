-- PG18 metadata only. psql -X -qAt -v source_id=...; no application-table access.
\set ON_ERROR_STOP on
\set QUIET on
\if :{?source_id}
\else
  \echo 'Missing source identity'
  SELECT 1/0;
\endif
BEGIN READ ONLY;
SET LOCAL statement_timeout='3s';
SET LOCAL lock_timeout='500ms';
SET LOCAL TIME ZONE 'UTC';
SET LOCAL stats_fetch_consistency='snapshot';
WITH candidates AS MATERIALIZED (
 SELECT pid, backend_start, usename, application_name, state, xact_start,
        query_start, state_change, wait_event_type, wait_event, query_id::text,
        backend_xid::text, backend_xmin::text
 FROM pg_stat_activity
 WHERE datname=current_database() AND backend_type='client backend'
   AND pid<>pg_backend_pid()
 ORDER BY xact_start NULLS LAST, pid LIMIT 51
), selected AS MATERIALIZED (
 SELECT * FROM candidates ORDER BY xact_start NULLS LAST,pid LIMIT 50
), observed AS MATERIALIZED (
 SELECT s.*, clock_timestamp()-s.xact_start AS transaction_age,
        CASE WHEN s.state='active' THEN clock_timestamp()-s.query_start END AS active_age,
        CASE WHEN s.state LIKE 'idle%' THEN clock_timestamp()-s.state_change END AS idle_age,
        pg_blocking_pids(s.pid) AS all_blockers
 FROM selected s
), sessions AS (
 SELECT o.pid, o.backend_start, o.usename, o.application_name, o.state,
        o.xact_start, o.query_start, o.state_change, o.wait_event_type, o.wait_event,
        o.query_id, o.backend_xid, o.backend_xmin, o.transaction_age, o.active_age, o.idle_age,
        ARRAY(SELECT DISTINCT b FROM unnest(o.all_blockers) b ORDER BY b LIMIT 20) AS blocker_pids,
        cardinality(o.all_blockers)>20 AS blocker_array_may_be_clipped
 FROM observed o
), db AS MATERIALIZED (
 SELECT datid,datname,stats_reset,numbackends,xact_commit,xact_rollback,
        blks_read,blks_hit,temp_files,temp_bytes,deadlocks
 FROM pg_stat_database WHERE datname=current_database()
)
SELECT jsonb_build_object(
 'schema_version',1,'source_id',:'source_id','sampled_at',clock_timestamp(),
 'server_addr',inet_server_addr()::text,'server_port',inet_server_port(),
 'server_version_num',current_setting('server_version_num')::integer,
 'postmaster_start',pg_postmaster_start_time(),'in_recovery',pg_is_in_recovery(),
 'database',to_jsonb(db),
 'observer_settings',(SELECT jsonb_object_agg(name,jsonb_build_object('setting',setting,'unit',unit))
  FROM pg_settings WHERE name IN ('track_counts','track_activities','track_io_timing',
    'track_wal_io_timing','max_connections','shared_buffers','work_mem')),
 'session_cohort_clipped',(SELECT count(*)>50 FROM candidates),
 'sessions',COALESCE((SELECT jsonb_agg(to_jsonb(s)) FROM sessions s),'[]'::jsonb),
 'prepared_transactions_in_database',(SELECT count(*) FROM pg_prepared_xacts WHERE database=current_database()),
 'limitations','Dynamic observations can change; no query text; source identity is caller-verified.'
) FROM db;
COMMIT;
