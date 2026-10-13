-- Chapter 088 read-only storage and lifecycle inspection.
SELECT current_database() AS database_name,current_setting('server_version') AS version,
 clock_timestamp() AS inspected_at;
SELECT datname,pg_database_size(oid) AS database_bytes
FROM pg_database WHERE datallowconn ORDER BY database_bytes DESC;
SELECT schemaname,relname,pg_table_size(relid) AS table_bytes_including_toast,
 pg_indexes_size(relid) AS index_bytes,
 pg_total_relation_size(relid) AS total_bytes,
 n_live_tup,n_dead_tup,last_vacuum,last_autovacuum,last_analyze,last_autoanalyze
FROM pg_stat_user_tables ORDER BY total_bytes DESC LIMIT 25;
SELECT schemaname,tablename,indexname,pg_relation_size(indexrelid) AS index_bytes
FROM pg_indexes i JOIN pg_stat_user_indexes s
 ON i.schemaname=s.schemaname AND i.tablename=s.relname AND i.indexname=s.indexrelname
 ORDER BY index_bytes DESC LIMIT 25;
SELECT datname,age(datfrozenxid) AS xid_age FROM pg_database ORDER BY xid_age DESC;
SELECT pid,relid::regclass AS relation,phase,heap_blks_total,heap_blks_scanned
FROM pg_stat_progress_vacuum;
SELECT wal_records,wal_bytes,stats_reset FROM pg_stat_wal;
SELECT slot_name,slot_type,active,restart_lsn,wal_status,safe_wal_size
FROM pg_replication_slots;
SELECT archived_count,last_archived_time,failed_count,last_failed_time
FROM pg_stat_archiver;
