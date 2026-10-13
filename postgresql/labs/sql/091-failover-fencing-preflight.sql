-- Chapter 091 read-only PostgreSQL 18 failover preflight; run on each node.
SELECT current_database() AS database_name,current_setting('server_version') AS version,
 pg_is_in_recovery() AS is_standby,clock_timestamp() AS observed_at;
SELECT application_name,client_addr,state,sync_state,
 sent_lsn,write_lsn,flush_lsn,replay_lsn,write_lag,flush_lag,replay_lag
FROM pg_stat_replication;
SELECT status,sender_host,slot_name,receive_start_lsn,
 written_lsn,flushed_lsn,latest_end_lsn,latest_end_time
FROM pg_stat_wal_receiver;
SELECT slot_name,slot_type,active,restart_lsn,confirmed_flush_lsn,
 wal_status,safe_wal_size FROM pg_replication_slots;
SELECT archived_count,last_archived_time,failed_count,last_failed_time
FROM pg_stat_archiver;
SELECT name,setting,context,pending_restart FROM pg_settings WHERE name IN
 ('wal_level','synchronous_standby_names','max_wal_senders',
  'max_replication_slots','max_slot_wal_keep_size','archive_mode')
ORDER BY name;
-- Run only after verifying server role:
-- Primary: SELECT pg_current_wal_lsn();
-- Standby: SELECT pg_last_wal_receive_lsn(),pg_last_wal_replay_lsn();
