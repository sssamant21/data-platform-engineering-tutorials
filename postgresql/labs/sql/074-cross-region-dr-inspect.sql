-- Chapter 074: read-only inspection. Run on each node and label outputs.
SELECT current_setting('server_version') AS version,
 pg_is_in_recovery() AS is_standby,clock_timestamp() AS inspected_at;
SELECT application_name,state,sync_state,sent_lsn,write_lsn,flush_lsn,replay_lsn
FROM pg_stat_replication;
SELECT status,receive_start_lsn,latest_end_lsn FROM pg_stat_wal_receiver;
SELECT slot_name,slot_type,active,restart_lsn,wal_status,safe_wal_size
FROM pg_replication_slots;
SELECT archived_count,last_archived_time,failed_count,last_failed_time
FROM pg_stat_archiver;
SELECT name,setting,source FROM pg_settings
WHERE name IN ('synchronous_commit','synchronous_standby_names',
 'wal_keep_size','max_slot_wal_keep_size','archive_mode') ORDER BY name;
