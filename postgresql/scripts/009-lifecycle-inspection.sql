-- PostgreSQL 18; connect to the intended endpoint as lab_observer.
-- Read-only evidence; no workload or lifecycle changes.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '5s';
SET LOCAL lock_timeout = '1s';

SELECT clock_timestamp() AS observed_at,
       version() AS server_build,
       inet_server_addr() AS server_address,
       inet_server_port() AS server_port,
       current_database() AS database_name,
       current_user AS observer,
       pg_postmaster_start_time() AS postmaster_started_at,
       pg_is_in_recovery() AS is_standby;

SELECT name, setting, unit, source, pending_restart
FROM pg_settings
WHERE name IN ('data_directory', 'port', 'fsync', 'full_page_writes',
               'synchronous_commit', 'synchronous_standby_names',
               'wal_level', 'logging_collector', 'log_destination')
ORDER BY name;

SELECT application_name, state, sync_state,
       sent_lsn, write_lsn, flush_lsn, replay_lsn
FROM pg_stat_replication
ORDER BY application_name;

SELECT status, sender_host, sender_port, slot_name,
       written_lsn, flushed_lsn, latest_end_lsn
FROM pg_stat_wal_receiver;

SELECT datname, numbackends, stats_reset
FROM pg_stat_database
WHERE datname = current_database();

COMMIT;
