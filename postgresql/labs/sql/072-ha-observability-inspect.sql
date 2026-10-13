\set ON_ERROR_STOP on
SELECT current_setting('server_version') AS server_version,
 pg_is_in_recovery() AS is_standby,clock_timestamp() AS inspected_at;
SELECT name,setting,source,context,pending_restart
FROM pg_settings
WHERE name IN ('wal_level','max_wal_senders','max_replication_slots',
 'synchronous_commit','synchronous_standby_names','wal_keep_size')
ORDER BY name;
SELECT application_name,client_addr,state,sync_state,
 sent_lsn,write_lsn,flush_lsn,replay_lsn,write_lag,flush_lag,replay_lag
FROM pg_stat_replication ORDER BY application_name;
SELECT status,receive_start_lsn,latest_end_lsn
FROM pg_stat_wal_receiver;
SELECT slot_name,slot_type,active,restart_lsn,wal_status,safe_wal_size
FROM pg_replication_slots ORDER BY slot_name;
SELECT archived_count,last_archived_time,failed_count,last_failed_time
FROM pg_stat_archiver;
SELECT pid,application_name,state,wait_event_type,wait_event,
 clock_timestamp()-xact_start AS transaction_age
FROM pg_stat_activity
WHERE wait_event='SyncRep' OR backend_type='walsender'
ORDER BY pid;
