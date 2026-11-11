-- Chapter 069: refactor SQL without changing the business result.
-- Synthetic inline data only. Run on independently verified disposable PostgreSQL 18.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
SELECT current_database() AS database_name, current_setting('server_version') AS server_version,
       inet_server_addr() AS server_ip, inet_server_port() AS server_port;
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer BETWEEN 180000 AND 189999 THEN 1 ELSE 0 END AS version_guard;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials' THEN 1 ELSE 0 END AS database_guard;

-- Original report: expected East (140,30,170,82.35), West (100,30,130,76.92).
WITH batches(batch_id,region,channel,accepted,rejected) AS (
 VALUES (1,'East','api',80,20),(2,'East','file',40,10),
        (3,'West','api',60,0),(4,'West','file',30,10),
        (5,'East','api',20,0),(6,'West','file',10,20)
)
SELECT region, SUM(accepted) AS accepted, SUM(rejected) AS rejected,
       SUM(accepted+rejected) AS processed,
       ROUND(100.0*SUM(accepted)/NULLIF(SUM(accepted+rejected),0),2) AS acceptance_pct
FROM batches GROUP BY region ORDER BY region;

-- Staged refactor with explicitly named intermediate grains.
WITH batches(batch_id,region,channel,accepted,rejected) AS (
 VALUES (1,'East','api',80,20),(2,'East','file',40,10),
        (3,'West','api',60,0),(4,'West','file',30,10),
        (5,'East','api',20,0),(6,'West','file',10,20)
), validated_batches AS (
 SELECT batch_id,region,accepted,rejected,accepted+rejected AS processed
 FROM batches WHERE accepted>=0 AND rejected>=0
), region_totals AS (
 SELECT region,SUM(accepted) AS accepted,SUM(rejected) AS rejected,
        SUM(processed) AS processed FROM validated_batches GROUP BY region
)
SELECT region,accepted,rejected,processed,
       ROUND(100.0*accepted/NULLIF(processed,0),2) AS acceptance_pct
FROM region_totals ORDER BY region;

-- Check two-way equality, counts, expected region totals and weighted global totals.
-- EXCEPT ALL detects differences in duplicate multiplicity (PostgreSQL 18).
WITH batches(batch_id,region,channel,accepted,rejected) AS (
 VALUES (1,'East','api',80,20),(2,'East','file',40,10),
        (3,'West','api',60,0),(4,'West','file',30,10),
        (5,'East','api',20,0),(6,'West','file',10,20)
), original AS (
 SELECT region,SUM(accepted) AS accepted,SUM(rejected) AS rejected,
        SUM(accepted+rejected) AS processed,
        ROUND(100.0*SUM(accepted)/NULLIF(SUM(accepted+rejected),0),2) AS acceptance_pct
 FROM batches GROUP BY region
), validated_batches AS (
 SELECT batch_id,region,accepted,rejected,accepted+rejected AS processed
 FROM batches WHERE accepted>=0 AND rejected>=0
), refactor_totals AS (
 SELECT region,SUM(accepted) AS accepted,SUM(rejected) AS rejected,
        SUM(processed) AS processed FROM validated_batches GROUP BY region
), refactored AS (
 SELECT region,accepted,rejected,processed,
        ROUND(100.0*accepted/NULLIF(processed,0),2) AS acceptance_pct
 FROM refactor_totals
), old_only AS (
 SELECT * FROM original EXCEPT ALL SELECT * FROM refactored
), new_only AS (
 SELECT * FROM refactored EXCEPT ALL SELECT * FROM original
), checks AS (
 SELECT
  (SELECT COUNT(*)=6 AND SUM(accepted)=240 AND SUM(rejected)=60
          AND SUM(accepted+rejected)=300 FROM batches) AS source_ok,
  (SELECT COUNT(*)=0 FROM batches WHERE accepted<0 OR rejected<0
          OR accepted IS NULL OR rejected IS NULL) AS input_quality_ok,
  (SELECT COUNT(*)=2 FROM original) AS original_grain_ok,
  (SELECT COUNT(*)=2 FROM refactored) AS refactored_grain_ok,
  (SELECT COUNT(*)=0 FROM old_only) AS old_only_empty,
  (SELECT COUNT(*)=0 FROM new_only) AS new_only_empty,
  (SELECT accepted=140 AND rejected=30 AND processed=170 AND acceptance_pct=82.35
          FROM refactored WHERE region='East') AS east_ok,
  (SELECT accepted=100 AND rejected=30 AND processed=130 AND acceptance_pct=76.92
          FROM refactored WHERE region='West') AS west_ok,
  (SELECT SUM(accepted)=240 AND SUM(rejected)=60 AND SUM(processed)=300
          AND ROUND(100.0*SUM(accepted)/NULLIF(SUM(processed),0),2)=80.00
          FROM refactored) AS weighted_total_ok
)
SELECT * FROM checks;

-- Fail closed: one false or unknown check aborts execution with division-by-zero.
WITH batches(batch_id,region,channel,accepted,rejected) AS (
 VALUES (1,'East','api',80,20),(2,'East','file',40,10),
        (3,'West','api',60,0),(4,'West','file',30,10),
        (5,'East','api',20,0),(6,'West','file',10,20)
), original AS (
 SELECT region,SUM(accepted) accepted,SUM(rejected) rejected,
 SUM(accepted+rejected) processed,
 ROUND(100.0*SUM(accepted)/NULLIF(SUM(accepted+rejected),0),2) acceptance_pct
 FROM batches GROUP BY region
), valid AS (
 SELECT region,accepted,rejected,accepted+rejected processed FROM batches
 WHERE accepted>=0 AND rejected>=0
), totals AS (
 SELECT region,SUM(accepted) accepted,SUM(rejected) rejected,
 SUM(processed) processed FROM valid GROUP BY region
), revised AS (
 SELECT region,accepted,rejected,processed,
 ROUND(100.0*accepted/NULLIF(processed,0),2) acceptance_pct FROM totals
), diff AS (
 SELECT * FROM original EXCEPT ALL SELECT * FROM revised
), reverse_diff AS (
 SELECT * FROM revised EXCEPT ALL SELECT * FROM original
)
SELECT 1 / CASE WHEN
 (SELECT COUNT(*)=6 AND SUM(accepted)=240 AND SUM(rejected)=60 FROM batches)
 AND (SELECT COUNT(*)=0 FROM batches WHERE accepted<0 OR rejected<0 OR accepted IS NULL OR rejected IS NULL)
 AND (SELECT COUNT(*)=2 FROM original)
 AND (SELECT COUNT(*)=2 FROM revised)
 AND (SELECT COUNT(*)=0 FROM diff)
 AND (SELECT COUNT(*)=0 FROM reverse_diff)
 AND (SELECT COUNT(*)=1 FROM revised WHERE region='East' AND accepted=140 AND rejected=30 AND processed=170 AND acceptance_pct=82.35)
 AND (SELECT COUNT(*)=1 FROM revised WHERE region='West' AND accepted=100 AND rejected=30 AND processed=130 AND acceptance_pct=76.92)
 AND (SELECT SUM(accepted)=240 AND SUM(rejected)=60 AND SUM(processed)=300
       AND ROUND(100.0*SUM(accepted)/NULLIF(SUM(processed),0),2)=80.00 FROM revised)
 THEN 1 ELSE 0 END AS acceptance_guard;
ROLLBACK;
