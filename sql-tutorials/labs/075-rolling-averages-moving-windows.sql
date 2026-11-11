-- 075 — Synthetic moving averages. Read-only. Verify a disposable PG18 endpoint independently.
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

-- Detailed eight-row moving window result.
WITH samples(service,sample_id,sample_time,latency_ms) AS (
 VALUES ('api',1,TIMESTAMP '2026-01-01 09:00',100),
 ('api',2,TIMESTAMP '2026-01-01 09:05',200),
 ('api',3,TIMESTAMP '2026-01-01 09:05',300),
 ('api',4,TIMESTAMP '2026-01-01 09:10',NULL::integer),
 ('api',5,TIMESTAMP '2026-01-01 09:20',500),
 ('file',6,TIMESTAMP '2026-01-01 09:00',40),
 ('file',7,TIMESTAMP '2026-01-01 09:10',80),
 ('file',8,TIMESTAMP '2026-01-01 09:20',120)
), moving AS (
 SELECT service,sample_id,sample_time,latency_ms,
 ROUND(AVG(latency_ms) OVER w,2) AS avg_3_rows,
 COUNT(*) OVER w AS window_rows,
 COUNT(latency_ms) OVER w AS measured_rows
 FROM samples
 WINDOW w AS (
 PARTITION BY service ORDER BY sample_time,sample_id
 ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
 )
), actual AS (
 SELECT service,sample_id,latency_ms,avg_3_rows,window_rows,measured_rows,
 CASE WHEN measured_rows=3 THEN avg_3_rows END AS complete_avg_3
 FROM moving
)
SELECT * FROM actual ORDER BY service,sample_id;

-- Exact two-way multiset acceptance; errors terminate psql with ON_ERROR_STOP.
WITH samples(service,sample_id,sample_time,latency_ms) AS (
 VALUES ('api',1,TIMESTAMP '2026-01-01 09:00',100),
 ('api',2,TIMESTAMP '2026-01-01 09:05',200),
 ('api',3,TIMESTAMP '2026-01-01 09:05',300),
 ('api',4,TIMESTAMP '2026-01-01 09:10',NULL::integer),
 ('api',5,TIMESTAMP '2026-01-01 09:20',500),
 ('file',6,TIMESTAMP '2026-01-01 09:00',40),
 ('file',7,TIMESTAMP '2026-01-01 09:10',80),
 ('file',8,TIMESTAMP '2026-01-01 09:20',120)
), moving AS (
 SELECT service,sample_id,sample_time,latency_ms,
 ROUND(AVG(latency_ms) OVER w,2) AS avg_3_rows,
 COUNT(*) OVER w AS window_rows,
 COUNT(latency_ms) OVER w AS measured_rows
 FROM samples
 WINDOW w AS (
 PARTITION BY service ORDER BY sample_time,sample_id
 ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
 )
), actual AS (
 SELECT service,sample_id,latency_ms,avg_3_rows,window_rows,measured_rows,
 CASE WHEN measured_rows=3 THEN avg_3_rows END AS complete_avg_3
 FROM moving
),
expected(service,sample_id,latency_ms,avg_3_rows,window_rows,measured_rows,complete_avg_3) AS (
 VALUES
 ('api',1,100,100.00::numeric,1::bigint,1::bigint,NULL::numeric),
 ('api',2,200,150.00::numeric,2::bigint,2::bigint,NULL::numeric),
 ('api',3,300,200.00::numeric,3::bigint,3::bigint,200.00::numeric),
 ('api',4,NULL::integer,250.00::numeric,3::bigint,2::bigint,NULL::numeric),
 ('api',5,500,400.00::numeric,3::bigint,2::bigint,NULL::numeric),
 ('file',6,40,40.00::numeric,1::bigint,1::bigint,NULL::numeric),
 ('file',7,80,60.00::numeric,2::bigint,2::bigint,NULL::numeric),
 ('file',8,120,80.00::numeric,3::bigint,3::bigint,80.00::numeric)
), differences AS (
 (SELECT service,sample_id,latency_ms,avg_3_rows,window_rows,measured_rows,complete_avg_3 FROM actual
  EXCEPT ALL SELECT * FROM expected)
 UNION ALL
 (SELECT * FROM expected
  EXCEPT ALL SELECT service,sample_id,latency_ms,avg_3_rows,window_rows,measured_rows,complete_avg_3 FROM actual)
), checks AS (
 SELECT
 (SELECT COUNT(*)=8 FROM actual) AS eight_rows_ok,
 (SELECT COUNT(*)=0 FROM differences) AS exact_rows_ok,
 (SELECT COUNT(*)=2 FROM actual WHERE complete_avg_3 IS NOT NULL) AS strict_window_ok,
 (SELECT COUNT(*)=2 FROM actual WHERE service='api' AND sample_id IN (4,5)
  AND window_rows=3 AND measured_rows=2) AS missing_measurements_ok
)
SELECT *, 1 / CASE WHEN eight_rows_ok AND exact_rows_ok
 AND strict_window_ok AND missing_measurements_ok THEN 1 ELSE 0 END AS fail_closed_acceptance
FROM checks;

-- PostgreSQL 18-specific interval RANGE comparison.
WITH samples(service,sample_id,sample_time,latency_ms) AS (VALUES ('api',1,TIMESTAMP '2026-01-01 09:00',100),
 ('api',2,TIMESTAMP '2026-01-01 09:05',200),
 ('api',3,TIMESTAMP '2026-01-01 09:05',300),
 ('api',4,TIMESTAMP '2026-01-01 09:10',NULL::integer),
 ('api',5,TIMESTAMP '2026-01-01 09:20',500),
 ('file',6,TIMESTAMP '2026-01-01 09:00',40),
 ('file',7,TIMESTAMP '2026-01-01 09:10',80),
 ('file',8,TIMESTAMP '2026-01-01 09:20',120))
SELECT service,sample_id,
 ROUND(AVG(latency_ms) OVER (
 PARTITION BY service ORDER BY sample_time
 RANGE BETWEEN INTERVAL '10 minutes' PRECEDING AND CURRENT ROW
 ),2) AS trailing_10min_avg
FROM samples ORDER BY service,sample_time,sample_id;
ROLLBACK;
