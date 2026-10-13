\set ON_ERROR_STOP on
SELECT current_setting('server_version') AS server_version,
 pg_is_in_recovery() AS is_standby,
 current_setting('data_checksums') AS data_checksums;
SELECT name,setting,unit,context,pending_restart
FROM pg_settings
WHERE name IN ('wal_level','max_wal_senders','max_replication_slots',
 'archive_mode','archive_command','archive_library','archive_timeout',
 'full_page_writes','wal_keep_size') ORDER BY name;
SELECT spcname,pg_tablespace_location(oid) AS location
FROM pg_tablespace ORDER BY spcname;
SELECT archived_count,last_archived_wal,last_archived_time,
 failed_count,last_failed_wal,last_failed_time
FROM pg_stat_archiver;
SELECT datname,pg_size_pretty(pg_database_size(oid)) AS size
FROM pg_database WHERE datallowconn ORDER BY pg_database_size(oid) DESC;
