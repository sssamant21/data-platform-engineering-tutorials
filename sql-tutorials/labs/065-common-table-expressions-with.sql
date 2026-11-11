-- 065 — Common Table Expressions (WITH), synthetic read-only PostgreSQL 18 lab
-- Independently verify disposable endpoint. Database/version guards do not prove isolation.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
SELECT current_database() AS database_name, current_setting('server_version') AS server_version,
       inet_server_addr() AS server_ip, inet_server_port() AS server_port;
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
                THEN 1 ELSE 0 END AS version_guard;
SELECT 1 / CASE WHEN current_database()='sql_tutorials' THEN 1 ELSE 0 END AS database_guard;

-- Expected batch processed: 100,50,60,40,20,30.
WITH batches(batch_id,source,accepted,rejected) AS (
 VALUES (1,'api',80,20),(2,'api',40,10),(3,'file',60,0),
        (4,'file',30,10),(5,'api',20,0),(6,'file',10,20)
), per_batch AS (
 SELECT batch_id,source,accepted,rejected,accepted+rejected AS processed FROM batches
)
SELECT batch_id,source,processed FROM per_batch ORDER BY batch_id;

-- Expected api (3,140,30,170,82.35); file (3,100,30,130,76.92).
WITH batches(batch_id,source,accepted,rejected) AS (
 VALUES (1,'api',80,20),(2,'api',40,10),(3,'file',60,0),
        (4,'file',30,10),(5,'api',20,0),(6,'file',10,20)
), per_batch AS (
 SELECT batch_id,source,accepted,rejected,accepted+rejected AS processed FROM batches
), per_source AS (
 SELECT source,COUNT(*) AS batch_count,SUM(accepted) AS accepted,
        SUM(rejected) AS rejected,SUM(processed) AS processed
 FROM per_batch GROUP BY source
)
SELECT source,batch_count,accepted,rejected,processed,
       ROUND(100.0*accepted/NULLIF(processed,0),2) AS acceptance_pct
FROM per_source ORDER BY source;

-- All flags must be true.
WITH batches(batch_id,source,accepted,rejected) AS (
 VALUES (1,'api',80,20),(2,'api',40,10),(3,'file',60,0),
        (4,'file',30,10),(5,'api',20,0),(6,'file',10,20)
), per_batch AS (
 SELECT batch_id,source,accepted,rejected,accepted+rejected AS processed FROM batches
), per_source AS (
 SELECT source,COUNT(*) AS batch_count,SUM(accepted) AS accepted,
        SUM(rejected) AS rejected,SUM(processed) AS processed
 FROM per_batch GROUP BY source
), checks AS (
 SELECT
 (SELECT COUNT(*)=6 AND SUM(accepted)=240 AND SUM(rejected)=60 AND SUM(processed)=300 FROM per_batch) AS totals_ok,
 (SELECT array_agg(processed ORDER BY batch_id)=ARRAY[100,50,60,40,20,30] FROM per_batch) AS batch_ok,
 (SELECT COUNT(*)=2 FROM per_source) AS sources_ok,
 (SELECT accepted=140 AND rejected=30 AND processed=170 AND batch_count=3
         AND ROUND(100.0*accepted/NULLIF(processed,0),2)=82.35
  FROM per_source WHERE source='api') AS api_ok,
 (SELECT accepted=100 AND rejected=30 AND processed=130 AND batch_count=3
         AND ROUND(100.0*accepted/NULLIF(processed,0),2)=76.92
  FROM per_source WHERE source='file') AS file_ok,
 (SELECT ROUND(100.0*SUM(accepted)/NULLIF(SUM(processed),0),2)=80.00 FROM per_source) AS weighted_ok,
 (SELECT array_agg(batch_id ORDER BY batch_id)=ARRAY[1,2,3]
  FROM per_batch WHERE processed>=50) AS filtered_ok
)
SELECT * FROM checks;

-- Fail closed: no silent acceptance if a core result changes.
WITH batches(batch_id,source,accepted,rejected) AS (
 VALUES (1,'api',80,20),(2,'api',40,10),(3,'file',60,0),
        (4,'file',30,10),(5,'api',20,0),(6,'file',10,20)
), per_batch AS (
 SELECT batch_id,source,accepted,rejected,accepted+rejected AS processed FROM batches
), per_source AS (
 SELECT source,SUM(accepted) AS accepted,SUM(rejected) AS rejected,
        SUM(processed) AS processed FROM per_batch GROUP BY source
)
SELECT 1 / CASE WHEN
 (SELECT COUNT(*)=6 AND SUM(accepted)=240 AND SUM(rejected)=60 AND SUM(processed)=300 FROM per_batch)
 AND (SELECT COUNT(*)=2 FROM per_source)
 AND (SELECT processed=170 FROM per_source WHERE source='api')
 AND (SELECT processed=130 FROM per_source WHERE source='file')
 AND (SELECT ROUND(100.0*SUM(accepted)/NULLIF(SUM(processed),0),2)=80.00 FROM per_source)
 THEN 1 ELSE 0 END AS acceptance_guard;
ROLLBACK;
-- Static expected results only; actual PG18 execution evidence pending.
