\set ON_ERROR_STOP on
SELECT current_setting('server_version') AS server_version,
 current_setting('synchronous_commit') AS synchronous_commit,
 current_setting('synchronous_standby_names') AS synchronous_standby_names,
 pg_is_in_recovery() AS is_standby,clock_timestamp() AS inspected_at;
SELECT name,setting,source,context,pending_restart
FROM pg_settings
WHERE name IN ('synchronous_commit','synchronous_standby_names',
 'wal_level','max_wal_senders','max_replication_slots')
ORDER BY name;
SELECT application_name,client_addr,state,sync_priority,sync_state,
 sent_lsn,write_lsn,flush_lsn,replay_lsn,write_lag,flush_lag,replay_lag
FROM pg_stat_replication ORDER BY application_name;
SELECT pid,application_name,state,wait_event_type,wait_event,
 clock_timestamp()-xact_start AS transaction_age
FROM pg_stat_activity
WHERE wait_event='SyncRep' OR backend_type='walsender'
ORDER BY pid;
SELECT slot_name,slot_type,active,restart_lsn,wal_status,safe_wal_size
FROM pg_replication_slots ORDER BY slot_name;
