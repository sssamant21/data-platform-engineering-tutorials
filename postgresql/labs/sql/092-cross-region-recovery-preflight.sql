-- Chapter 092 read-only PostgreSQL 18 backup and DR preflight.
SELECT current_database() AS database_name,current_setting('server_version') AS version,
 pg_is_in_recovery() AS is_standby,clock_timestamp() AS inspected_at;
SELECT name,setting,unit,context,pending_restart
FROM pg_settings WHERE name IN
 ('wal_level','archive_mode','archive_command','archive_library',
  'archive_timeout','max_wal_senders','max_replication_slots',
  'max_slot_wal_keep_size','wal_keep_size','full_page_writes')
ORDER BY name;
SELECT archived_count,last_archived_wal,last_archived_time,
 failed_count,last_failed_wal,last_failed_time,stats_reset
FROM pg_stat_archiver;
SELECT wal_records,wal_bytes,stats_reset FROM pg_stat_wal;
SELECT slot_name,slot_type,active,restart_lsn,confirmed_flush_lsn,
 wal_status,safe_wal_size FROM pg_replication_slots;
SELECT application_name,state,sync_state,sent_lsn,flush_lsn,replay_lsn
FROM pg_stat_replication;
SELECT datname,pg_database_size(oid) AS database_bytes
FROM pg_database WHERE datallowconn ORDER BY database_bytes DESC;
