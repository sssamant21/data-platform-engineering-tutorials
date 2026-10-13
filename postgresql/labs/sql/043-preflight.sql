\set ON_ERROR_STOP on
SELECT current_database(),current_user,current_setting('server_version') AS version;
SELECT name,setting,unit FROM pg_settings WHERE name IN ('wal_level','max_wal_senders','max_replication_slots','archive_mode','full_page_writes') ORDER BY name;
SELECT slot_name,slot_type,active,restart_lsn FROM pg_replication_slots;
SELECT archived_count,last_archived_time,failed_count,last_failed_time FROM pg_stat_archiver;
SELECT pid,phase,backup_total,backup_streamed FROM pg_stat_progress_basebackup;
