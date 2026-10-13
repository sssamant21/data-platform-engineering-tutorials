\set ON_ERROR_STOP on
SELECT current_database(),current_user,current_setting('server_version') AS version;
SELECT name,setting,source,pending_restart FROM pg_settings
WHERE name IN ('wal_level','archive_mode','archive_command','archive_library','archive_timeout','full_page_writes','max_wal_senders') ORDER BY name;
SELECT archived_count,last_archived_wal,last_archived_time,failed_count,last_failed_wal,last_failed_time,stats_reset FROM pg_stat_archiver;
SELECT pg_current_wal_lsn() AS current_lsn,pg_walfile_name(pg_current_wal_lsn()) AS current_segment;
SELECT slot_name,slot_type,active,restart_lsn FROM pg_replication_slots;
