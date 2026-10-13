-- Chapter 087 read-only workload baseline; run before/after each phase.
SELECT current_database() AS database_name,current_setting('server_version') AS version,
 pg_is_in_recovery() AS is_standby,clock_timestamp() AS sample_time;
SELECT datname,numbackends,xact_commit,xact_rollback,blks_read,blks_hit,
 tup_returned,tup_fetched,tup_inserted,tup_updated,tup_deleted,
 temp_files,temp_bytes,deadlocks,stats_reset
FROM pg_stat_database WHERE datname=current_database();
SELECT state,wait_event_type,wait_event,count(*) AS sessions
FROM pg_stat_activity WHERE datname=current_database()
GROUP BY state,wait_event_type,wait_event ORDER BY sessions DESC;
SELECT schemaname,relname,n_live_tup,n_dead_tup,seq_scan,idx_scan
FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 20;
SELECT wal_records,wal_fpi,wal_bytes,stats_reset FROM pg_stat_wal;
SELECT application_name,state,sync_state,sent_lsn,replay_lsn
FROM pg_stat_replication;
SELECT slot_name,slot_type,active,restart_lsn FROM pg_replication_slots;
SELECT pg_database_size(current_database()) AS database_bytes;
