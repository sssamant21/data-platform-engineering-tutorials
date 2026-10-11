-- PG18 read-only inspection; lab_observer has pg_monitor.
-- Three actor labels only. No query text, fixture reads or backend signaling.
-- Avoid reading the locked fixture: queued/held AccessExclusive can block even observers.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
SELECT clock_timestamp() AS observed_at,current_database(),current_user,
       inet_server_addr(),inet_server_port(),pg_is_in_recovery();
-- Timeout settings below belong to this observer, not remote actor sessions.
SELECT name,setting,unit,context FROM pg_settings
WHERE name IN ('deadlock_timeout','lock_timeout','statement_timeout',
               'log_lock_waits','max_locks_per_transaction')
ORDER BY name;
SELECT pid,application_name,usename,backend_start,state,
       wait_event_type,wait_event,backend_xid,backend_xmin,
       clock_timestamp()-xact_start AS transaction_age,
       clock_timestamp()-query_start AS current_or_last_statement_age,
       pg_blocking_pids(pid) AS blocking_pids
FROM pg_stat_activity
WHERE datname=current_database()
  AND application_name IN ('chapter018-A','chapter018-B','chapter018-C')
ORDER BY application_name,pid;

-- Each pg_blocking_pids array is sampled once in this graph query.
-- Paths stop at cycles, prepared PID 0, an external node or depth eight.
WITH RECURSIVE actors AS MATERIALIZED (
 SELECT pid,application_name,pg_blocking_pids(pid) AS blockers
 FROM pg_stat_activity WHERE datname=current_database()
  AND application_name IN ('chapter018-A','chapter018-B','chapter018-C')
), walk(start_pid,waiting_pid,blocking_pid,depth,path,cycle) AS (
 SELECT a.pid,a.pid,b.pid,1,ARRAY[a.pid,b.pid],b.pid=a.pid
 FROM actors a CROSS JOIN LATERAL
  (SELECT DISTINCT pid FROM unnest(a.blockers) AS u(pid)) b
 UNION ALL
 SELECT w.start_pid,a.pid,b.pid,w.depth+1,w.path||b.pid,b.pid=ANY(w.path)
 FROM walk w JOIN actors a ON a.pid=w.blocking_pid
 CROSS JOIN LATERAL
  (SELECT DISTINCT pid FROM unnest(a.blockers) AS u(pid)) b
 WHERE w.depth<8 AND NOT w.cycle AND w.blocking_pid<>0
)
SELECT w.start_pid,w.waiting_pid,w.blocking_pid,w.depth,w.path,w.cycle,
       s.application_name AS originating_waiter,
       b.application_name AS blocker_label,b.usename AS blocker_login,
       CASE WHEN w.cycle THEN 'cycle observed'
            WHEN w.blocking_pid=0 THEN 'prepared transaction: investigate ownership'
            WHEN e.pid IS NULL THEN 'outside sampled actor scope'
            WHEN cardinality(e.blockers)=0 THEN 'root candidate in sampled graph'
            WHEN w.depth=8 THEN 'depth limit'
            ELSE 'intermediate blocker' END AS interpretation
FROM walk w
LEFT JOIN actors s ON s.pid=w.start_pid
LEFT JOIN actors e ON e.pid=w.blocking_pid
LEFT JOIN pg_stat_activity b ON b.pid=w.blocking_pid
ORDER BY w.start_pid,w.depth,w.blocking_pid;

SELECT l.pid,l.locktype,l.mode,l.granted,l.fastpath,l.waitstart,
       l.database,
       CASE WHEN l.database=0 OR l.database=(SELECT oid FROM pg_database WHERE datname=current_database())
            THEN l.relation::regclass::text
            ELSE l.relation::text END AS relation_or_oid,
       l.page,l.tuple,l.transactionid,l.virtualxid,l.virtualtransaction
FROM pg_locks l WHERE l.pid IN
 (SELECT pid FROM pg_stat_activity WHERE datname=current_database()
  AND application_name IN ('chapter018-A','chapter018-B','chapter018-C'))
ORDER BY l.pid,l.granted,l.locktype,l.mode;
SELECT datname,deadlocks,stats_reset FROM pg_stat_database WHERE datname=current_database();
SELECT count(*) AS prepared_transaction_count FROM pg_prepared_xacts;
SELECT transaction,prepared,owner,database FROM pg_prepared_xacts
ORDER BY prepared LIMIT 20;
COMMIT;
