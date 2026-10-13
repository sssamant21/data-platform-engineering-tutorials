\set ON_ERROR_STOP on
SELECT current_setting('server_version') AS server_version,
 pg_is_in_recovery() AS is_standby,clock_timestamp() AS inspected_at;
SELECT name,setting,unit,context,pending_restart
FROM pg_settings
WHERE name IN ('wal_level','wal_keep_size','max_slot_wal_keep_size',
 'max_replication_slots','max_wal_senders','max_wal_size','archive_mode')
ORDER BY name;
SELECT slot_name,slot_type,plugin,database,active,active_pid,
 restart_lsn,confirmed_flush_lsn,catalog_xmin,wal_status,safe_wal_size,
 inactive_since,invalidation_reason,
 CASE WHEN NOT pg_is_in_recovery() AND restart_lsn IS NOT NULL
 THEN pg_wal_lsn_diff(pg_current_wal_lsn(),restart_lsn) END AS retained_wal_bytes
FROM pg_replication_slots ORDER BY slot_name;
SELECT application_name,state,sync_state,sent_lsn,write_lsn,flush_lsn,replay_lsn,
 write_lag,flush_lag,replay_lag
FROM pg_stat_replication;
SELECT wal_records,wal_fpi,wal_bytes,stats_reset FROM pg_stat_wal;
SELECT archived_count,last_archived_time,failed_count,last_failed_time
FROM pg_stat_archiver;
