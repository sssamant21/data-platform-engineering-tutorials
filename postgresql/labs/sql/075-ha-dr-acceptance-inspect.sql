-- Chapter 075 read-only PostgreSQL 18 HA/DR inspection; run on each node.
SELECT current_setting('server_version') AS version,
 pg_is_in_recovery() AS is_standby,
 current_setting('synchronous_commit') AS synchronous_commit,
 current_setting('synchronous_standby_names') AS synchronous_standby_names,
 clock_timestamp() AS inspected_at;
SELECT application_name,state,sync_state,sent_lsn,write_lsn,flush_lsn,replay_lsn
FROM pg_stat_replication;
SELECT status,receive_start_lsn,latest_end_lsn FROM pg_stat_wal_receiver;
SELECT slot_name,slot_type,active,restart_lsn,wal_status,safe_wal_size
FROM pg_replication_slots;
SELECT archived_count,last_archived_time,failed_count,last_failed_time
FROM pg_stat_archiver;
SELECT pid,application_name,state,wait_event_type,wait_event
FROM pg_stat_activity WHERE wait_event='SyncRep';
