-- PG18 read-only observer, preferably lab_observer with pg_monitor.
-- Scope: Chapter 017 fixtures and two actor labels; no session query text.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
SELECT clock_timestamp() AS observed_at,current_database(),current_user,
       inet_server_addr(),inet_server_port(),pg_is_in_recovery();
SELECT id,units FROM c017_iso.counter ORDER BY id;
SELECT id,on_call FROM c017_iso.roster ORDER BY id;
SELECT count(*) FILTER (WHERE on_call) AS on_call_count,
       count(*) FILTER (WHERE on_call)>=1 AS roster_invariant
FROM c017_iso.roster;
SELECT pid,application_name,state,backend_xid,backend_xmin,
       wait_event_type,wait_event,clock_timestamp()-xact_start AS transaction_age,
       pg_blocking_pids(pid) AS blocking_pids
FROM pg_stat_activity
WHERE datname=current_database() AND application_name IN ('chapter017-A','chapter017-B')
ORDER BY application_name,pid;
SELECT pid,locktype,mode,granted,relation::regclass AS relation,page,tuple
FROM pg_locks WHERE pid IN
 (SELECT pid FROM pg_stat_activity WHERE datname=current_database()
  AND application_name IN ('chapter017-A','chapter017-B'))
ORDER BY pid,locktype,mode;
COMMIT;
