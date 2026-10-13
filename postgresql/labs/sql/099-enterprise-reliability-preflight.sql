-- Chapter 099 read-only PostgreSQL 18 enterprise reliability preflight.
SELECT clock_timestamp() AS sampled_at,current_database() AS database_name,
 current_setting('server_version') AS version,pg_is_in_recovery() AS is_standby;
SELECT name,setting,unit,pending_restart
FROM pg_settings WHERE name IN ('max_connections','shared_buffers','autovacuum',
 'archive_mode','wal_level','max_replication_slots','max_slot_wal_keep_size','ssl')
ORDER BY name;
SELECT datname,numbackends,xact_commit,xact_rollback,deadlocks,temp_bytes,
 blks_read,blks_hit,stats_reset FROM pg_stat_database
WHERE datname=current_database();
SELECT state,wait_event_type,wait_event,count(*) AS sessions
FROM pg_stat_activity WHERE datname=current_database()
GROUP BY state,wait_event_type,wait_event ORDER BY sessions DESC;
SELECT schemaname,relname,n_live_tup,n_dead_tup,last_autovacuum,
 pg_total_relation_size(relid) AS total_bytes
FROM pg_stat_user_tables ORDER BY total_bytes DESC LIMIT 25;
SELECT application_name,state,sync_state,sent_lsn,flush_lsn,replay_lsn
FROM pg_stat_replication;
SELECT status,sender_host,latest_end_lsn,latest_end_time FROM pg_stat_wal_receiver;
SELECT slot_name,slot_type,active,wal_status,safe_wal_size FROM pg_replication_slots;
SELECT archived_count,last_archived_time,failed_count,last_failed_time
FROM pg_stat_archiver;
SELECT datname,age(datfrozenxid) AS xid_age FROM pg_database ORDER BY xid_age DESC;
-- Supplement SQL with cloud, application, backup/restore, security and DR evidence.
