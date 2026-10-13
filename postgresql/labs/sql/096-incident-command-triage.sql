-- Chapter 096 read-only PostgreSQL 18 incident triage.
SELECT current_database() AS database_name,current_setting('server_version') AS version,
 pg_is_in_recovery() AS is_standby,clock_timestamp() AS sampled_at;
SELECT datname,numbackends,xact_commit,xact_rollback,deadlocks,temp_bytes,
 blks_read,blks_hit,stats_reset FROM pg_stat_database
WHERE datname=current_database();
SELECT pid,usename,application_name,client_addr,state,wait_event_type,
 wait_event,backend_type,clock_timestamp()-xact_start AS transaction_age,
 clock_timestamp()-query_start AS query_age,pg_blocking_pids(pid) AS blocking_pids,
 left(query,160) AS query_sample
FROM pg_stat_activity WHERE datname=current_database()
ORDER BY xact_start NULLS LAST LIMIT 50;
SELECT locktype,mode,granted,count(*) AS sessions
FROM pg_locks GROUP BY locktype,mode,granted ORDER BY sessions DESC;
SELECT application_name,state,sync_state,sent_lsn,flush_lsn,replay_lsn,
 write_lag,flush_lag,replay_lag FROM pg_stat_replication;
SELECT status,sender_host,latest_end_lsn,latest_end_time FROM pg_stat_wal_receiver;
SELECT slot_name,slot_type,active,wal_status,safe_wal_size FROM pg_replication_slots;
SELECT archived_count,last_archived_time,failed_count,last_failed_time
FROM pg_stat_archiver;
SELECT wal_bytes,stats_reset FROM pg_stat_wal;
-- Requires appropriate monitoring privileges to see other users' activity.
-- Do not execute pg_cancel_backend or pg_terminate_backend from this script.
