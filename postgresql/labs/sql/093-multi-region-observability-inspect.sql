-- Chapter 093 read-only PostgreSQL 18 multi-region DR inspection.
SELECT current_database() AS database_name,current_setting('server_version') AS version,
 pg_is_in_recovery() AS is_standby,clock_timestamp() AS sampled_at;
SELECT application_name,client_addr,state,sync_state,
 sent_lsn,write_lsn,flush_lsn,replay_lsn,write_lag,flush_lag,replay_lag
FROM pg_stat_replication;
SELECT status,sender_host,slot_name,receive_start_lsn,
 written_lsn,flushed_lsn,latest_end_lsn,latest_end_time
FROM pg_stat_wal_receiver;
SELECT slot_name,slot_type,active,restart_lsn,wal_status,safe_wal_size
FROM pg_replication_slots;
SELECT archived_count,last_archived_time,failed_count,last_failed_time,stats_reset
FROM pg_stat_archiver;
SELECT wal_bytes,stats_reset FROM pg_stat_wal;
SELECT datname,numbackends,xact_commit,xact_rollback,deadlocks,temp_bytes,stats_reset
FROM pg_stat_database WHERE datname=current_database();
SELECT state,wait_event_type,wait_event,count(*) AS sessions
FROM pg_stat_activity WHERE datname=current_database()
GROUP BY state,wait_event_type,wait_event ORDER BY sessions DESC;
-- Primary-only: SELECT pg_current_wal_lsn();
-- Standby-only: SELECT pg_last_wal_receive_lsn(),pg_last_wal_replay_lsn();
