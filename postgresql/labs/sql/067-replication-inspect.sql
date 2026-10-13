\set ON_ERROR_STOP on
SELECT current_setting('server_version') AS server_version,
 pg_is_in_recovery() AS is_standby,
 clock_timestamp() AS inspected_at;
SELECT name,setting,unit,context,pending_restart
FROM pg_settings
WHERE name IN ('wal_level','max_wal_senders','max_replication_slots',
 'wal_keep_size','max_slot_wal_keep_size','hot_standby',
 'synchronous_commit','synchronous_standby_names')
ORDER BY name;
SELECT application_name,client_addr,state,sync_state,
 sent_lsn,write_lsn,flush_lsn,replay_lsn,write_lag,flush_lag,replay_lag
FROM pg_stat_replication;
SELECT slot_name,slot_type,active,restart_lsn,wal_status,safe_wal_size
FROM pg_replication_slots;
SELECT status,receive_start_lsn,latest_end_lsn
FROM pg_stat_wal_receiver;
SELECT pg_last_wal_receive_lsn() AS receive_lsn,
 pg_last_wal_replay_lsn() AS replay_lsn,
 pg_last_xact_replay_timestamp() AS last_replayed_commit;
