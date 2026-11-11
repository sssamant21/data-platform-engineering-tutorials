-- 077: synthetic latency distribution. PostgreSQL 18, disposable database only.
-- Run: psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/077-ntile-percentiles-distribution.sql
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

-- The inline data are fictional. NULL means missing, not zero.
WITH samples(service,event_id,latency_ms) AS (
 VALUES ('api',1,10),('api',2,20),('api',3,20),('api',4,40),
        ('api',5,100),('api',6,NULL::integer),
        ('file',7,5),('file',8,15),('file',9,25),('file',10,35)
), measured AS (
 SELECT * FROM samples WHERE latency_ms IS NOT NULL
)
SELECT service,event_id,latency_ms,
       NTILE(4) OVER (PARTITION BY service ORDER BY latency_ms,event_id) AS quartile,
       RANK() OVER (PARTITION BY service ORDER BY latency_ms) AS latency_rank,
       PERCENT_RANK() OVER (PARTITION BY service ORDER BY latency_ms) AS percent_rank,
       CUME_DIST() OVER (PARTITION BY service ORDER BY latency_ms) AS cume_dist
FROM measured ORDER BY service,latency_ms,event_id;

WITH samples(service,latency_ms) AS (
 VALUES ('api',10),('api',20),('api',20),('api',40),('api',100),
        ('api',NULL::integer),('file',5),('file',15),('file',25),('file',35)
)
SELECT service,COUNT(*) AS total_rows,COUNT(latency_ms) AS measured_rows,
       COUNT(*)-COUNT(latency_ms) AS missing_rows,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_ms) AS p50_cont,
       PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY latency_ms) AS p50_disc,
       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95_cont
FROM samples GROUP BY service ORDER BY service;

-- Compare exact multiset of bucket assignments in both directions.
WITH samples(service,event_id,latency_ms) AS (
 VALUES ('api',1,10),('api',2,20),('api',3,20),('api',4,40),
        ('api',5,100),('api',6,NULL::integer),
        ('file',7,5),('file',8,15),('file',9,25),('file',10,35)
), measured AS (
 SELECT * FROM samples WHERE latency_ms IS NOT NULL
), actual AS (
 SELECT service,event_id,latency_ms,
        NTILE(4) OVER (PARTITION BY service ORDER BY latency_ms,event_id) AS quartile
 FROM measured
), expected(service,event_id,latency_ms,quartile) AS (
 VALUES ('api',1,10,1),('api',2,20,1),('api',3,20,2),
        ('api',4,40,3),('api',5,100,4),
        ('file',7,5,1),('file',8,15,2),('file',9,25,3),('file',10,35,4)
), differences AS (
 (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
 UNION ALL
 (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
), percentiles AS (
 SELECT service, COUNT(*) AS n,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_ms) AS p50_cont,
        PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY latency_ms) AS p50_disc,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95_cont
 FROM measured GROUP BY service
), checks AS (
 SELECT (SELECT COUNT(*)=9 FROM actual) AS row_count_ok,
        (SELECT COUNT(*)=0 FROM differences) AS buckets_ok,
        (SELECT COUNT(*)=1 FROM samples WHERE latency_ms IS NULL) AS missing_ok,
        (SELECT n=5 AND p50_cont=20 AND p50_disc=20 AND abs(p95_cont-88)<0.000001
         FROM percentiles WHERE service='api') AS api_percentiles_ok,
        (SELECT n=4 AND p50_cont=20 AND p50_disc=15 AND abs(p95_cont-33.5)<0.000001
         FROM percentiles WHERE service='file') AS file_percentiles_ok
)
SELECT *, 1 / CASE WHEN row_count_ok AND buckets_ok AND missing_ok
                        AND api_percentiles_ok AND file_percentiles_ok
                   THEN 1 ELSE 0 END AS fail_closed_acceptance
FROM checks;
ROLLBACK;
