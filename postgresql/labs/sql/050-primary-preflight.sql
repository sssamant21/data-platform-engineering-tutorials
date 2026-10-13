\set ON_ERROR_STOP on
SELECT pg_is_in_recovery() AS in_recovery,current_setting('server_version') AS version,
 current_setting('wal_level') AS wal_level,current_setting('archive_mode') AS archive_mode,
 current_setting('synchronous_commit') AS synchronous_commit,
 current_setting('synchronous_standby_names') AS synchronous_standby_names;
SELECT system_identifier FROM pg_control_system();
SELECT application_name,client_addr,state,sync_state,
 sent_lsn,write_lsn,flush_lsn,replay_lsn,
 pg_wal_lsn_diff(pg_current_wal_lsn(),replay_lsn) AS replay_gap_bytes
FROM pg_stat_replication;
SELECT slot_name,slot_type,active,restart_lsn,wal_status,safe_wal_size FROM pg_replication_slots;
SELECT archived_count,failed_count,last_archived_wal,last_archived_time,
 last_failed_wal,last_failed_time FROM pg_stat_archiver;
