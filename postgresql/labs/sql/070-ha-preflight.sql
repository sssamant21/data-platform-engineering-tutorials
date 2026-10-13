\set ON_ERROR_STOP on
SELECT current_setting('server_version') AS server_version,
 pg_is_in_recovery() AS is_standby,clock_timestamp() AS inspected_at,
 current_setting('synchronous_commit') AS synchronous_commit,
 current_setting('synchronous_standby_names') AS synchronous_standby_names;
SELECT application_name,client_addr,state,sync_state,
 sent_lsn,write_lsn,flush_lsn,replay_lsn
FROM pg_stat_replication;
SELECT slot_name,slot_type,active,restart_lsn,wal_status,safe_wal_size
FROM pg_replication_slots ORDER BY slot_name;
SELECT status,receive_start_lsn,latest_end_lsn
FROM pg_stat_wal_receiver;
SELECT pg_last_wal_receive_lsn() AS receive_lsn,
 pg_last_wal_replay_lsn() AS replay_lsn;
SELECT archived_count,last_archived_time,failed_count,last_failed_time
FROM pg_stat_archiver;
SELECT pid,application_name,state,wait_event_type,wait_event,
 clock_timestamp()-xact_start AS xact_age
FROM pg_stat_activity
WHERE xact_start IS NOT NULL ORDER BY xact_start LIMIT 20;
