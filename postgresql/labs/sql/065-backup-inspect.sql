\set ON_ERROR_STOP on
SELECT current_setting('server_version') AS server_version,
 current_setting('TimeZone') AS timezone,
 pg_is_in_recovery() AS is_standby;
SELECT name,setting,unit,context,pending_restart
FROM pg_settings
WHERE name IN ('wal_level','archive_mode','archive_command','archive_library',
 'archive_timeout','full_page_writes','max_wal_senders','wal_keep_size')
ORDER BY name;
SELECT archived_count,last_archived_wal,last_archived_time,
 failed_count,last_failed_wal,last_failed_time,stats_reset
FROM pg_stat_archiver;
SELECT datname,pg_size_pretty(pg_database_size(oid)) AS database_size
FROM pg_database WHERE datallowconn ORDER BY pg_database_size(oid) DESC;
