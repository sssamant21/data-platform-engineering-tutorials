\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout='3s';
SET LOCAL lock_timeout='500ms';
SET LOCAL stats_fetch_consistency='snapshot';
SELECT jsonb_build_object(
  'schema_version',1,
  'captured_at',clock_timestamp(),
  'server_version_num',current_setting('server_version_num')::integer,
  'postmaster_start',pg_postmaster_start_time(),
  'database_oid',(SELECT oid FROM pg_database WHERE datname=current_database()),
  'observer_pid',pg_backend_pid(),
  'observer_settings',jsonb_build_object(
    'track_io_timing',current_setting('track_io_timing'),
    'track_wal_io_timing',current_setting('track_wal_io_timing'),
    'work_mem',current_setting('work_mem'),
    'hash_mem_multiplier',current_setting('hash_mem_multiplier'),
    'shared_buffers',current_setting('shared_buffers')),
  'activity',COALESCE((
    SELECT jsonb_agg(to_jsonb(a) ORDER BY a.pid)
    FROM (
      SELECT pid,backend_start,leader_pid,backend_type,application_name,
             state,wait_event_type,wait_event,
             EXTRACT(epoch FROM clock_timestamp()-query_start) AS query_age_seconds,
             EXTRACT(epoch FROM clock_timestamp()-xact_start) AS xact_age_seconds
      FROM pg_stat_activity
      WHERE datname=current_database() AND pid<>pg_backend_pid()
    ) a),'[]'::jsonb),
  'database_stats',(
    SELECT jsonb_build_object(
      'stats_reset',stats_reset,'blks_read',blks_read,'blks_hit',blks_hit,
      'temp_files',temp_files,'temp_bytes',temp_bytes,
      'blk_read_time',blk_read_time,'blk_write_time',blk_write_time,
      'deadlocks',deadlocks)
    FROM pg_stat_database WHERE datname=current_database()),
  'io',COALESCE((
    SELECT jsonb_agg(to_jsonb(i) ORDER BY backend_type,object,context)
    FROM pg_stat_io i),'[]'::jsonb),
  'checkpointer',(SELECT to_jsonb(c) FROM pg_stat_checkpointer c),
  'wal',(SELECT to_jsonb(w) FROM pg_stat_wal w)
);
COMMIT;
