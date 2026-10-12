\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout='3s';
SET LOCAL lock_timeout='500ms';
SELECT clock_timestamp() AS observed_at,pid,backend_start,application_name,
       state,wait_event_type,wait_event,xact_start,query_start,pg_blocking_pids(pid) AS blockers
FROM pg_stat_activity
WHERE datname=current_database()
  AND application_name IN ('c030_blocker','c030_probe')
  AND pid<>pg_backend_pid()
ORDER BY pid;
SELECT clock_timestamp() AS observed_at,l.pid,a.backend_start,l.mode,l.granted
FROM pg_locks l
JOIN pg_stat_activity a ON a.pid=l.pid
WHERE a.datname=current_database()
  AND a.application_name IN ('c030_blocker','c030_probe')
  AND l.locktype='relation'
  AND l.relation='c030_incident.requests'::regclass
ORDER BY l.pid,l.granted,l.mode;
COMMIT;
