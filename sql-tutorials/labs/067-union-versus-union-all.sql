-- Chapter 067: UNION versus UNION ALL. Synthetic, read-only PostgreSQL 18 lab.
-- Verify endpoint isolation independently; database/version guards do not prove it.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
SELECT current_database() AS database_name,
       current_setting('server_version') AS server_version,
       inet_server_addr() AS server_ip, inet_server_port() AS server_port;
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer BETWEEN 180000 AND 189999 THEN 1 ELSE 0 END AS version_guard;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials' THEN 1 ELSE 0 END AS database_guard;

-- Expect 8 rows, sum 180. Two identical East/api rows and two North/api NULL rows.
WITH api(region,channel,processed) AS (
 VALUES ('East','api',40),('West','api',30),('East','api',40),('North','api',NULL::integer)
), file_feed(region,channel,processed) AS (
 VALUES ('East','file',40),('West','file',20),('South','file',10),('North','api',NULL::integer)
), combined AS (
 SELECT region,channel,processed FROM api
 UNION ALL
 SELECT region,channel,processed FROM file_feed
)
SELECT region,channel,processed FROM combined ORDER BY region,channel,processed NULLS LAST;

-- Expect 6 distinct rows, sum 140.
WITH api(region,channel,processed) AS (
 VALUES ('East','api',40),('West','api',30),('East','api',40),('North','api',NULL::integer)
), file_feed(region,channel,processed) AS (
 VALUES ('East','file',40),('West','file',20),('South','file',10),('North','api',NULL::integer)
), distinct_rows AS (
 SELECT region,channel,processed FROM api
 UNION
 SELECT region,channel,processed FROM file_feed
)
SELECT region,channel,processed FROM distinct_rows ORDER BY region,channel,processed NULLS LAST;

-- Expect East/api/40 = 2, North/api/NULL = 2.
WITH api(region,channel,processed) AS (
 VALUES ('East','api',40),('West','api',30),('East','api',40),('North','api',NULL::integer)
), file_feed(region,channel,processed) AS (
 VALUES ('East','file',40),('West','file',20),('South','file',10),('North','api',NULL::integer)
), combined AS (
 SELECT region,channel,processed FROM api
 UNION ALL
 SELECT region,channel,processed FROM file_feed
)
SELECT region,channel,processed,COUNT(*) AS occurrences
FROM combined GROUP BY region,channel,processed
HAVING COUNT(*)>1 ORDER BY region,channel;

-- Deterministic acceptance; every column must be TRUE.
WITH api(region,channel,processed) AS (
 VALUES ('East','api',40),('West','api',30),('East','api',40),('North','api',NULL::integer)
), file_feed(region,channel,processed) AS (
 VALUES ('East','file',40),('West','file',20),('South','file',10),('North','api',NULL::integer)
), all_rows AS (
 SELECT region,channel,processed FROM api
 UNION ALL
 SELECT region,channel,processed FROM file_feed
), distinct_rows AS (
 SELECT region,channel,processed FROM api
 UNION
 SELECT region,channel,processed FROM file_feed
), duplicates AS (
 SELECT region,channel,processed,COUNT(*) AS n
 FROM all_rows GROUP BY region,channel,processed HAVING COUNT(*)>1
), checks AS (
 SELECT
 (SELECT COUNT(*)=8 AND SUM(processed)=180 AND COUNT(processed)=6 FROM all_rows) AS all_ok,
 (SELECT COUNT(*)=6 AND SUM(processed)=140 AND COUNT(processed)=5 FROM distinct_rows) AS distinct_ok,
 (SELECT COUNT(*)=2 AND SUM(n)=4 FROM duplicates) AS duplicate_groups_ok,
 (SELECT n=2 FROM duplicates WHERE region='East' AND channel='api' AND processed=40) AS east_ok,
 (SELECT n=2 FROM duplicates WHERE region='North' AND channel='api' AND processed IS NULL) AS north_null_ok
)
SELECT * FROM checks;

-- Fail closed with nonzero psql exit on any unexpected result.
WITH api(region,channel,processed) AS (
 VALUES ('East','api',40),('West','api',30),('East','api',40),('North','api',NULL::integer)
), file_feed(region,channel,processed) AS (
 VALUES ('East','file',40),('West','file',20),('South','file',10),('North','api',NULL::integer)
), all_rows AS (
 SELECT region,channel,processed FROM api UNION ALL
 SELECT region,channel,processed FROM file_feed
), distinct_rows AS (
 SELECT region,channel,processed FROM api UNION
 SELECT region,channel,processed FROM file_feed
), duplicates AS (
 SELECT region,channel,processed,COUNT(*) AS n FROM all_rows
 GROUP BY region,channel,processed HAVING COUNT(*)>1
)
SELECT 1 / CASE WHEN
 (SELECT COUNT(*)=8 AND SUM(processed)=180 AND COUNT(processed)=6 FROM all_rows)
 AND (SELECT COUNT(*)=6 AND SUM(processed)=140 AND COUNT(processed)=5 FROM distinct_rows)
 AND (SELECT COUNT(*)=2 AND SUM(n)=4 FROM duplicates)
 AND (SELECT n=2 FROM duplicates WHERE region='East' AND channel='api' AND processed=40)
 AND (SELECT n=2 FROM duplicates WHERE region='North' AND channel='api' AND processed IS NULL)
 THEN 1 ELSE 0 END AS acceptance_guard;
ROLLBACK;
