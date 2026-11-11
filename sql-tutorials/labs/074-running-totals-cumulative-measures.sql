-- Chapter 074: Running totals and cumulative measures; synthetic rows only.
-- Verify an isolated disposable PostgreSQL 18 endpoint and least-privilege role independently.
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

-- Complete ordered cumulative results.
WITH batches(service,batch_id,event_time,records) AS (
 VALUES ('api',1,TIMESTAMP '2026-01-01 09:00',20),
 ('api',2,TIMESTAMP '2026-01-01 09:05',30),
 ('api',3,TIMESTAMP '2026-01-01 09:05',10),
 ('api',4,TIMESTAMP '2026-01-01 09:10',40),
 ('file',5,TIMESTAMP '2026-01-01 09:00',15),
 ('file',6,TIMESTAMP '2026-01-01 09:05',NULL::integer),
 ('file',7,TIMESTAMP '2026-01-01 09:10',25)
), calculated AS (
 SELECT service,batch_id,event_time,records,
 SUM(records) OVER (PARTITION BY service ORDER BY event_time,batch_id
 ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_records,
 COUNT(records) OVER (PARTITION BY service ORDER BY event_time,batch_id
 ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS known_measurements,
 SUM(records) OVER (PARTITION BY service) AS service_total
 FROM batches
)
SELECT service,batch_id,records,running_records,known_measurements,service_total,
 ROUND(100.0 * running_records / NULLIF(service_total,0),2) AS cumulative_pct
FROM calculated ORDER BY service,event_time,batch_id;

-- Exact bidirectional multiset comparison; any difference stops psql.
WITH batches(service,batch_id,event_time,records) AS (
 VALUES ('api',1,TIMESTAMP '2026-01-01 09:00',20),
 ('api',2,TIMESTAMP '2026-01-01 09:05',30),
 ('api',3,TIMESTAMP '2026-01-01 09:05',10),
 ('api',4,TIMESTAMP '2026-01-01 09:10',40),
 ('file',5,TIMESTAMP '2026-01-01 09:00',15),
 ('file',6,TIMESTAMP '2026-01-01 09:05',NULL::integer),
 ('file',7,TIMESTAMP '2026-01-01 09:10',25)
), calculated AS (
 SELECT service,batch_id,event_time,records,
 SUM(records) OVER (PARTITION BY service ORDER BY event_time,batch_id
 ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_records,
 COUNT(records) OVER (PARTITION BY service ORDER BY event_time,batch_id
 ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS known_measurements,
 SUM(records) OVER (PARTITION BY service) AS service_total
 FROM batches
), actual AS (
 SELECT service,batch_id,records,running_records,known_measurements,service_total,
 ROUND(100.0 * running_records / NULLIF(service_total,0),2) AS cumulative_pct
 FROM calculated
), expected(service,batch_id,records,running_records,known_measurements,service_total,cumulative_pct) AS (
 VALUES
 ('api',1,20,20::bigint,1::bigint,100::bigint,20.00::numeric),
 ('api',2,30,50::bigint,2::bigint,100::bigint,50.00::numeric),
 ('api',3,10,60::bigint,3::bigint,100::bigint,60.00::numeric),
 ('api',4,40,100::bigint,4::bigint,100::bigint,100.00::numeric),
 ('file',5,15,15::bigint,1::bigint,40::bigint,37.50::numeric),
 ('file',6,NULL::integer,15::bigint,1::bigint,40::bigint,37.50::numeric),
 ('file',7,25,40::bigint,2::bigint,40::bigint,100.00::numeric)
), differences AS (
 (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
 UNION ALL
 (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
), checks AS (
 SELECT
 (SELECT COUNT(*)=7 FROM actual) AS seven_rows_ok,
 (SELECT COUNT(*)=0 FROM differences) AS exact_rows_ok,
 (SELECT COUNT(*)=1 FROM actual WHERE batch_id=6 AND records IS NULL AND running_records=15 AND known_measurements=1) AS missing_measurement_ok,
 (SELECT COUNT(*)=2 FROM actual WHERE cumulative_pct=100.00 AND batch_id IN (4,7)) AS final_totals_ok
)
SELECT *, 1 / CASE WHEN seven_rows_ok AND exact_rows_ok
 AND missing_measurement_ok AND final_totals_ok THEN 1 ELSE 0 END AS fail_closed_acceptance
FROM checks;
ROLLBACK;
