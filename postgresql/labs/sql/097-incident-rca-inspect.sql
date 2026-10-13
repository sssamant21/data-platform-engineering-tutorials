-- Chapter 097 read-only PostgreSQL 18 incident diagnosis.
SELECT clock_timestamp() AS sampled_at,current_database() AS database_name,
 current_setting('server_version') AS version,pg_is_in_recovery() AS is_standby;
SELECT pid,usename,application_name,state,wait_event_type,wait_event,
 clock_timestamp()-xact_start AS xact_age,
 clock_timestamp()-query_start AS query_age,
 pg_blocking_pids(pid) AS blocking_pids,left(query,180) AS query_sample
FROM pg_stat_activity WHERE datname=current_database()
ORDER BY xact_start NULLS LAST LIMIT 60;
SELECT locktype,mode,granted,count(*) AS count
FROM pg_locks GROUP BY locktype,mode,granted ORDER BY count DESC;
SELECT datname,numbackends,xact_commit,xact_rollback,deadlocks,temp_bytes,
 stats_reset FROM pg_stat_database WHERE datname=current_database();
SELECT state,wait_event_type,wait_event,count(*) AS sessions
FROM pg_stat_activity WHERE datname=current_database()
GROUP BY state,wait_event_type,wait_event ORDER BY sessions DESC;
-- Use pg_monitor or approved privileges for full cross-user visibility.
-- Do not terminate or cancel sessions from this script.
