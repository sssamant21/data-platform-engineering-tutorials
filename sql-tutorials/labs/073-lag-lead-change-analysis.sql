-- Chapter 073: LAG and LEAD for change analysis. Synthetic inline data only.
-- Requires an independently verified disposable PostgreSQL 18 database.
-- A database-name guard is not proof that the endpoint is isolated.
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

-- Row-by-row navigation; gaps are actual elapsed minutes, not row counts.
WITH observations(service,event_id,observed_at,records) AS (
 VALUES
 ('api',1,TIMESTAMP '2026-01-01 09:00:00',100),
 ('api',2,TIMESTAMP '2026-01-01 09:05:00',130),
 ('api',3,TIMESTAMP '2026-01-01 09:10:00',NULL::integer),
 ('api',4,TIMESTAMP '2026-01-01 09:15:00',125),
 ('file',5,TIMESTAMP '2026-01-01 09:00:00',50),
 ('file',6,TIMESTAMP '2026-01-01 09:05:00',50),
 ('file',7,TIMESTAMP '2026-01-01 09:10:00',80),
 ('file',8,TIMESTAMP '2026-01-01 09:20:00',70)
), neighbors AS (
 SELECT service,event_id,observed_at,records,
        LAG(records) OVER w AS previous_records,
        LEAD(records) OVER w AS next_records,
        LAG(observed_at) OVER w AS previous_at,
        LAG(event_id) OVER w AS previous_event_id
 FROM observations
 WINDOW w AS (PARTITION BY service ORDER BY observed_at,event_id)
)
SELECT service,event_id,records,previous_records,next_records,
       records - previous_records AS change_from_previous,
       EXTRACT(EPOCH FROM (observed_at - previous_at))/60 AS minutes_since_previous,
       previous_event_id
FROM neighbors
ORDER BY service,observed_at,event_id;

-- Fail-closed full-result reconciliation with explicit expected rows.
WITH observations(service,event_id,observed_at,records) AS (
 VALUES
 ('api',1,TIMESTAMP '2026-01-01 09:00:00',100),
 ('api',2,TIMESTAMP '2026-01-01 09:05:00',130),
 ('api',3,TIMESTAMP '2026-01-01 09:10:00',NULL::integer),
 ('api',4,TIMESTAMP '2026-01-01 09:15:00',125),
 ('file',5,TIMESTAMP '2026-01-01 09:00:00',50),
 ('file',6,TIMESTAMP '2026-01-01 09:05:00',50),
 ('file',7,TIMESTAMP '2026-01-01 09:10:00',80),
 ('file',8,TIMESTAMP '2026-01-01 09:20:00',70)
), neighbors AS (
 SELECT service,event_id,observed_at,records,
        LAG(records) OVER w AS previous_records,
        LEAD(records) OVER w AS next_records,
        LAG(observed_at) OVER w AS previous_at,
        LAG(event_id) OVER w AS previous_event_id
 FROM observations
 WINDOW w AS (PARTITION BY service ORDER BY observed_at,event_id)
), actual AS (
 SELECT service,event_id,records,previous_records,next_records,
        records - previous_records AS delta,
        EXTRACT(EPOCH FROM (observed_at - previous_at))/60 AS gap_minutes,
        previous_event_id
 FROM neighbors
), expected(service,event_id,records,previous_records,next_records,delta,gap_minutes,previous_event_id) AS (
 VALUES
 ('api',1,100, NULL::integer,130,NULL::integer,NULL::numeric,NULL::integer),
 ('api',2,130,100,NULL::integer,30,5::numeric,1),
 ('api',3,NULL::integer,130,125,NULL::integer,5::numeric,2),
 ('api',4,125,NULL::integer,NULL::integer,NULL::integer,5::numeric,3),
 ('file',5,50,NULL::integer,50,NULL::integer,NULL::numeric,NULL::integer),
 ('file',6,50,50,80,0,5::numeric,5),
 ('file',7,80,50,70,30,5::numeric,6),
 ('file',8,70,80,NULL::integer,-10,10::numeric,7)
), differences AS (
 (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
 UNION ALL
 (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
), checks AS (
 SELECT
 (SELECT COUNT(*)=8 FROM actual) AS eight_rows_ok,
 (SELECT COUNT(*)=2 FROM (SELECT service FROM actual GROUP BY service HAVING COUNT(*)=4) s) AS partition_counts_ok,
 (SELECT COUNT(*)=1 FROM actual WHERE service='file' AND event_id=8 AND delta=-10 AND gap_minutes=10) AS drop_and_gap_ok,
 (SELECT COUNT(*)=1 FROM actual WHERE event_id=6 AND delta=0) AS zero_delta_ok,
 (SELECT COUNT(*)=1 FROM actual WHERE event_id=4 AND previous_event_id=3 AND previous_records IS NULL) AS null_predecessor_ok,
 (SELECT COUNT(*)=0 FROM differences) AS exact_results_ok
)
SELECT *, 1 / CASE WHEN eight_rows_ok AND partition_counts_ok AND drop_and_gap_ok
 AND zero_delta_ok AND null_predecessor_ok AND exact_results_ok THEN 1 ELSE 0 END AS fail_closed_acceptance
FROM checks;
ROLLBACK;
