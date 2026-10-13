\set ON_ERROR_STOP on
SELECT current_database(),current_user,current_setting('server_version') AS server_version;
SELECT name,setting,source,pending_restart FROM pg_settings
WHERE name IN ('archive_mode','archive_command','archive_library','archive_timeout','wal_level','max_wal_senders') ORDER BY name;
SELECT archived_count,last_archived_wal,last_archived_time,
 failed_count,last_failed_wal,last_failed_time,stats_reset
FROM pg_stat_archiver;
SELECT slot_name,slot_type,active,restart_lsn,
 pg_wal_lsn_diff(pg_current_wal_lsn(),restart_lsn) AS retained_bytes
FROM pg_replication_slots WHERE restart_lsn IS NOT NULL;
SELECT pid,phase,backup_total,backup_streamed
FROM pg_stat_progress_basebackup;
SELECT clock_timestamp() AS sampled_at;
