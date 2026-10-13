\set ON_ERROR_STOP on
SELECT current_setting('server_version') AS version,
 current_setting('max_connections') AS max_connections,
 current_setting('superuser_reserved_connections') AS superuser_reserved,
 current_setting('reserved_connections') AS reserved_connections;
SELECT datname,usename,application_name,state,count(*) AS sessions
FROM pg_stat_activity GROUP BY 1,2,3,4 ORDER BY sessions DESC;
SELECT pid,datname,usename,application_name,state,wait_event_type,wait_event,
 now()-xact_start AS transaction_age,
 now()-query_start AS query_age
FROM pg_stat_activity
WHERE backend_type='client backend' AND pid<>pg_backend_pid()
ORDER BY xact_start NULLS LAST LIMIT 30;
SELECT a.pid AS blocked_pid,unnest(pg_blocking_pids(a.pid)) AS blocker_pid,
 a.datname,a.usename,a.wait_event_type,a.wait_event
FROM pg_stat_activity a WHERE cardinality(pg_blocking_pids(a.pid))>0
ORDER BY a.pid LIMIT 30;
