-- Chapter 085 read-only production change baseline; run per database/node.
SELECT current_database() AS database_name,current_setting('server_version') AS version,
 pg_is_in_recovery() AS is_standby,clock_timestamp() AS inspected_at;
SELECT extname,extversion FROM pg_extension ORDER BY extname;
SELECT name,setting,unit,source,context,pending_restart
FROM pg_settings WHERE name IN
 ('log_min_duration_statement','shared_buffers','max_connections',
 'work_mem','shared_preload_libraries','wal_level','ssl')
ORDER BY name;
SELECT sourcefile,sourceline,name,setting,applied,error
FROM pg_file_settings ORDER BY sourcefile,sourceline;
SELECT datname,age(datfrozenxid) AS xid_age
FROM pg_database ORDER BY xid_age DESC;
SELECT schemaname,relname,n_live_tup,n_dead_tup,last_autovacuum,last_autoanalyze
FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 20;
SELECT application_name,state,sync_state,sent_lsn,replay_lsn
FROM pg_stat_replication;
SELECT slot_name,slot_type,active,restart_lsn FROM pg_replication_slots;
SELECT archived_count,last_archived_time,failed_count,last_failed_time
FROM pg_stat_archiver;
SELECT pid,usename,state,wait_event_type,wait_event,
 now()-xact_start AS transaction_age
FROM pg_stat_activity WHERE xact_start IS NOT NULL ORDER BY xact_start LIMIT 20;
