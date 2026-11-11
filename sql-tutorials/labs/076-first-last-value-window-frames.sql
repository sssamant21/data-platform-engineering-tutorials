-- Chapter 076: FIRST_VALUE, LAST_VALUE and explicit window frames.
-- Synthetic inline rows only. Run with psql -X -v ON_ERROR_STOP=1 -f ... on verified disposable PostgreSQL 18.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
SELECT current_database() AS database_name, current_user AS role_name,
 current_setting('server_version') AS server_version,
 inet_server_addr() AS server_ip, inet_server_port() AS server_port;
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer BETWEEN 180000 AND 189999 THEN 1 ELSE 0 END AS version_guard;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials' THEN 1 ELSE 0 END AS database_guard;

-- Dataset: duplicate event timestamps are resolved with unique event_id.
-- Rows 3 and 4 share a timestamp; row 5 has a NULL metric.
WITH events(service,event_id,event_time,latency_ms) AS (
 VALUES
 ('api',1,TIMESTAMP '2026-01-01 09:00',100),
 ('api',2,TIMESTAMP '2026-01-01 09:05',200),
 ('api',3,TIMESTAMP '2026-01-01 09:10',300),
 ('api',4,TIMESTAMP '2026-01-01 09:10',400),
 ('api',5,TIMESTAMP '2026-01-01 09:20',NULL::integer),
 ('file',6,TIMESTAMP '2026-01-01 09:00',50),
 ('file',7,TIMESTAMP '2026-01-01 09:15',70),
 ('file',8,TIMESTAMP '2026-01-01 09:30',90)
), actual AS (
 SELECT service,event_id,latency_ms,
 FIRST_VALUE(event_id) OVER w_full AS first_id,
 LAST_VALUE(event_id) OVER w_running AS last_so_far_id,
 LAST_VALUE(event_id) OVER w_full AS final_id,
 FIRST_VALUE(latency_ms) OVER w_full AS first_latency,
 LAST_VALUE(latency_ms) OVER w_full AS final_latency
 FROM events
 WINDOW
 w_running AS (PARTITION BY service ORDER BY event_time,event_id
   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW),
 w_full AS (PARTITION BY service ORDER BY event_time,event_id
   ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
)
SELECT * FROM actual ORDER BY service,event_id;

-- Bidirectional multiset comparison and fail-closed acceptance.
WITH events(service,event_id,event_time,latency_ms) AS (
 VALUES
 ('api',1,TIMESTAMP '2026-01-01 09:00',100),
 ('api',2,TIMESTAMP '2026-01-01 09:05',200),
 ('api',3,TIMESTAMP '2026-01-01 09:10',300),
 ('api',4,TIMESTAMP '2026-01-01 09:10',400),
 ('api',5,TIMESTAMP '2026-01-01 09:20',NULL::integer),
 ('file',6,TIMESTAMP '2026-01-01 09:00',50),
 ('file',7,TIMESTAMP '2026-01-01 09:15',70),
 ('file',8,TIMESTAMP '2026-01-01 09:30',90)
), actual AS (
 SELECT service,event_id,latency_ms,
 FIRST_VALUE(event_id) OVER w_full AS first_id,
 LAST_VALUE(event_id) OVER w_running AS last_so_far_id,
 LAST_VALUE(event_id) OVER w_full AS final_id,
 FIRST_VALUE(latency_ms) OVER w_full AS first_latency,
 LAST_VALUE(latency_ms) OVER w_full AS final_latency
 FROM events
 WINDOW
 w_running AS (PARTITION BY service ORDER BY event_time,event_id
   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW),
 w_full AS (PARTITION BY service ORDER BY event_time,event_id
   ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
), expected(service,event_id,latency_ms,first_id,last_so_far_id,final_id,first_latency,final_latency) AS (
 VALUES
 ('api',1,100,1,1,5,100,NULL::integer),
 ('api',2,200,1,2,5,100,NULL::integer),
 ('api',3,300,1,3,5,100,NULL::integer),
 ('api',4,400,1,4,5,100,NULL::integer),
 ('api',5,NULL::integer,1,5,5,100,NULL::integer),
 ('file',6,50,6,6,8,50,90),
 ('file',7,70,6,7,8,50,90),
 ('file',8,90,6,8,8,50,90)
), differences AS (
 (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
 UNION ALL
 (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
), checks AS (
 SELECT (SELECT COUNT(*)=8 FROM actual) AS row_count_ok,
        (SELECT COUNT(*)=0 FROM differences) AS exact_results_ok,
        (SELECT COUNT(*)=5 FROM actual WHERE service='api' AND final_latency IS NULL) AS null_preserved_ok,
        (SELECT COUNT(*)=8 FROM actual WHERE last_so_far_id=event_id) AS running_frame_ok
)
SELECT *, 1 / CASE WHEN row_count_ok AND exact_results_ok
 AND null_preserved_ok AND running_frame_ok THEN 1 ELSE 0 END AS fail_closed_acceptance
FROM checks;
ROLLBACK;
