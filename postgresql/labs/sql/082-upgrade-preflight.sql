-- Chapter 082 read-only PostgreSQL upgrade preflight.
-- Run separately in every database; capture source/target versions.
SELECT current_database() AS database_name, current_setting('server_version') AS version,
 current_setting('server_version_num') AS version_num,clock_timestamp() AS inspected_at;
SELECT datname,pg_encoding_to_char(encoding) AS encoding,datcollate,datctype,
 datcollversion FROM pg_database WHERE datallowconn ORDER BY datname;
SELECT extname,extversion FROM pg_extension ORDER BY extname;
SELECT name,setting,pending_restart FROM pg_settings
WHERE name IN ('shared_preload_libraries','wal_level','archive_mode','archive_command',
 'max_replication_slots','max_wal_senders','ssl','password_encryption')
ORDER BY name;
SELECT slot_name,slot_type,active,restart_lsn
FROM pg_replication_slots ORDER BY slot_name;
SELECT application_name,state,sync_state,sent_lsn,replay_lsn
FROM pg_stat_replication;
SELECT archived_count,last_archived_time,failed_count,last_failed_time
FROM pg_stat_archiver;
SELECT schemaname,tablename,policyname,cmd FROM pg_policies
ORDER BY schemaname,tablename,policyname;
