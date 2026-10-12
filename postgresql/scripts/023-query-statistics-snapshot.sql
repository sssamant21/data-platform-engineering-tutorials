-- PG18, extension installed in public. psql -X -qAt -v source_id=...
-- Scoped to connected database and lab_app; NO QUERY TEXT and no resets.
\set ON_ERROR_STOP on
\set QUIET on
\if :{?source_id}
\else
  \echo 'Missing verified source_id'
  SELECT 1/0;
\endif
BEGIN READ ONLY;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
SET LOCAL TIME ZONE 'UTC';
WITH entries AS MATERIALIZED (
 SELECT s.userid::bigint, s.dbid::bigint, s.queryid::text, s.toplevel,
        s.stats_since, s.calls, s.total_exec_time, s.rows,
        s.shared_blks_hit, s.shared_blks_read, s.temp_blks_written
 FROM public.pg_stat_statements(false) s
 WHERE s.dbid=(SELECT oid FROM pg_database WHERE datname=current_database())
   AND s.userid=(SELECT oid FROM pg_roles WHERE rolname='lab_app')
 ORDER BY s.queryid, s.toplevel LIMIT 201
), info AS MATERIALIZED (
 SELECT dealloc, stats_reset FROM public.pg_stat_statements_info
)
SELECT jsonb_build_object(
 'schema_version',1, 'source_id',:'source_id',
 'server_addr',inet_server_addr()::text, 'server_port',inet_server_port(),
 'server_version_num',current_setting('server_version_num')::integer,
 'postmaster_start',pg_postmaster_start_time(), 'in_recovery',pg_is_in_recovery(),
 'database_oid',(SELECT oid::bigint FROM pg_database WHERE datname=current_database()),
 'role_oid',(SELECT oid::bigint FROM pg_roles WHERE rolname='lab_app'),
 'extension_version',(SELECT extversion FROM pg_extension WHERE extname='pg_stat_statements'),
 'policy',jsonb_build_object('compute_query_id',current_setting('compute_query_id'),
   'track',current_setting('pg_stat_statements.track'),
   'track_utility',current_setting('pg_stat_statements.track_utility'),
   'track_planning',current_setting('pg_stat_statements.track_planning')),
 'sampled_at',clock_timestamp(), 'global_reset',info.stats_reset, 'dealloc',info.dealloc,
 'truncated',(SELECT count(*)>200 FROM entries),
 'entries',COALESCE((SELECT jsonb_agg(to_jsonb(e)) FROM entries e),'[]'::jsonb)
) FROM info;
COMMIT;
