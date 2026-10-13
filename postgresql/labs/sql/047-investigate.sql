\set ON_ERROR_STOP on
SELECT current_database(),current_user,current_setting('server_version') AS server_version;
SELECT name,setting,unit FROM pg_settings
WHERE name IN ('max_slot_wal_keep_size','wal_keep_size','max_wal_size','idle_replication_slot_timeout','archive_mode')
ORDER BY name;
SELECT slot_name,slot_type,active,active_pid,restart_lsn,confirmed_flush_lsn,
 wal_status,safe_wal_size,inactive_since,invalidation_reason,xmin,catalog_xmin,
 CASE WHEN restart_lsn IS NOT NULL THEN
 pg_wal_lsn_diff(pg_current_wal_lsn(),restart_lsn) END AS estimated_retained_bytes
FROM pg_replication_slots ORDER BY slot_name;
SELECT application_name,state,sync_state,sent_lsn,write_lsn,flush_lsn,replay_lsn
FROM pg_stat_replication;
SELECT archived_count,failed_count,last_archived_time,last_failed_time FROM pg_stat_archiver;
