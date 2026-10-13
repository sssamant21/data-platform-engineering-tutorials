-- Chapter 089 read-only PostgreSQL capacity and FinOps preflight.
SELECT current_database() AS database_name,current_setting('server_version') AS version,
 pg_is_in_recovery() AS is_standby,clock_timestamp() AS sampled_at;
SELECT datname,pg_database_size(oid) AS database_bytes
FROM pg_database WHERE datallowconn ORDER BY database_bytes DESC;
SELECT datname,numbackends,xact_commit,xact_rollback,blks_read,blks_hit,
 temp_bytes,deadlocks,stats_reset FROM pg_stat_database ORDER BY datname;
SELECT schemaname,relname,pg_total_relation_size(relid) AS total_bytes,
 pg_indexes_size(relid) AS index_bytes,n_live_tup,n_dead_tup
FROM pg_stat_user_tables ORDER BY total_bytes DESC LIMIT 25;
SELECT state,count(*) AS connections FROM pg_stat_activity GROUP BY state ORDER BY state;
SELECT wal_bytes,wal_records,stats_reset FROM pg_stat_wal;
SELECT slot_name,slot_type,active,restart_lsn,wal_status,safe_wal_size
FROM pg_replication_slots;
SELECT application_name,state,sync_state,sent_lsn,replay_lsn
FROM pg_stat_replication;
SELECT archived_count,last_archived_time,failed_count,last_failed_time
FROM pg_stat_archiver;
