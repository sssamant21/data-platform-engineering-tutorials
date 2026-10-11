-- PostgreSQL 18 architecture inspection; reads metadata only.
\set ON_ERROR_STOP on
\pset pager off
SET statement_timeout = '5s';
SET lock_timeout = '1s';
SELECT clock_timestamp() AS observed_at, current_database(), current_user,
       current_setting('server_version') AS server_version,
       pg_is_in_recovery() AS in_recovery, pg_backend_pid() AS observer_pid;
SELECT backend_type, state, count(*) AS processes
FROM pg_stat_activity GROUP BY backend_type, state
ORDER BY backend_type, state;
SELECT name, setting, unit, context, source
FROM pg_settings
WHERE name IN ('shared_buffers','wal_buffers','work_mem','hash_mem_multiplier',
 'maintenance_work_mem','autovacuum_work_mem','max_connections','max_wal_size',
 'checkpoint_timeout','checkpoint_completion_target','fsync',
 'synchronous_commit','synchronous_standby_names','data_directory')
ORDER BY name;
SELECT datname, temp_files, temp_bytes, blks_read, blks_hit, stats_reset
FROM pg_stat_database WHERE datname = current_database();
SELECT wal_records, wal_fpi, wal_bytes, wal_buffers_full, stats_reset
FROM pg_stat_wal;
SELECT num_timed, num_requested, write_time, sync_time, buffers_written, stats_reset
FROM pg_stat_checkpointer;
SELECT pg_relation_filepath('pg_catalog.pg_class'::regclass) AS example_catalog_path,
       pg_size_pretty(pg_total_relation_size('pg_catalog.pg_class'::regclass))
       AS example_catalog_total_size;
