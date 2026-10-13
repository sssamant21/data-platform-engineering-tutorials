-- Chapter 084 read-only maintenance preflight; run in the target database.
SELECT current_database() AS database_name,current_setting('server_version') AS version,
 pg_is_in_recovery() AS is_standby,clock_timestamp() AS inspected_at;
SELECT datname,age(datfrozenxid) AS xid_age
FROM pg_database ORDER BY xid_age DESC;
SELECT schemaname,relname,n_live_tup,n_dead_tup,
 last_vacuum,last_autovacuum,last_analyze,last_autoanalyze
FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 20;
SELECT pid,datname,usename,state,wait_event_type,wait_event,
 now()-xact_start AS transaction_age
FROM pg_stat_activity WHERE xact_start IS NOT NULL
ORDER BY xact_start LIMIT 20;
SELECT pid,relid::regclass AS relation,phase,
 heap_blks_total,heap_blks_scanned,heap_blks_vacuumed
FROM pg_stat_progress_vacuum;
SELECT slot_name,slot_type,active,restart_lsn FROM pg_replication_slots;
SELECT archived_count,last_archived_time,failed_count,last_failed_time
FROM pg_stat_archiver;
