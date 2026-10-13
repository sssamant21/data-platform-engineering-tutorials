\set ON_ERROR_STOP on
SELECT current_setting('server_version') AS version,
 current_setting('max_connections') AS max_connections,
 current_setting('superuser_reserved_connections') AS superuser_reserved,
 current_setting('reserved_connections') AS reserved_connections,
 pg_is_in_recovery() AS is_standby;
SELECT datname,usename,application_name,state,count(*) AS sessions
FROM pg_stat_activity GROUP BY 1,2,3,4 ORDER BY sessions DESC;
SELECT pid,datname,usename,application_name,state,wait_event_type,wait_event,
 now()-xact_start AS transaction_age
FROM pg_stat_activity WHERE xact_start IS NOT NULL
ORDER BY xact_start LIMIT 20;
SELECT datname,numbackends,xact_commit,xact_rollback,deadlocks
FROM pg_stat_database ORDER BY numbackends DESC;
