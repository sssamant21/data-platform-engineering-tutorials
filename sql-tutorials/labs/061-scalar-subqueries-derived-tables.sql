-- 061 Scalar subqueries and derived tables; synthetic, read-only PostgreSQL 18 lab.
-- Run ONLY against a separately verified disposable PostgreSQL 18 database.
-- psql -X -v ON_ERROR_STOP=1 -f sql-tutorials/labs/061-scalar-subqueries-derived-tables.sql
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
-- These checks identify version/database, NOT whether an endpoint is isolated.
SELECT current_database() AS database_name, current_setting('server_version') AS pg_version,
       inet_server_addr() AS server_ip, inet_server_port() AS server_port;
-- Intentionally fails when the connected server is not PostgreSQL 18.
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer
                  BETWEEN 180000 AND 189999 THEN 1 ELSE 0 END AS version_guard;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials' THEN 1 ELSE 0 END AS database_guard;
-- Query A: scalar subquery, one average applied to six batch rows.
SELECT b.batch_id, b.region, b.processed
FROM (VALUES (1,'East',100),(2,'East',50),(3,'West',40),
             (4,'West',60),(5,'North',20),(6,'North',30))
     AS b(batch_id,region,processed)
WHERE b.processed > (
  SELECT AVG(x.processed)
  FROM (VALUES (100),(50),(40),(60),(20),(30)) AS x(processed)
)
ORDER BY b.batch_id;
-- Expected: 1 East 100; 4 West 60.
-- Query B: derived table, one row per region.
SELECT regional.region, regional.total_processed
FROM (
 SELECT b.region, SUM(b.processed) AS total_processed
 FROM (VALUES (1,'East',100),(2,'East',50),(3,'West',40),
              (4,'West',60),(5,'North',20),(6,'North',30))
      AS b(batch_id,region,processed)
 GROUP BY b.region
) AS regional
WHERE regional.total_processed > 50
ORDER BY regional.total_processed DESC, regional.region;
-- Expected: East 150; West 100.
SELECT (SELECT AVG(v.processed)
        FROM (VALUES (100),(50),(40),(60),(20),(30)) AS v(processed))
       AS overall_average;
-- Expected: 50.
SELECT (SELECT v.n FROM (VALUES (1)) AS v(n) WHERE v.n=99) AS no_match;
-- Expected: NULL.
-- Deterministic assertions: every column should be true.
WITH batches(batch_id,region,processed) AS (
 VALUES (1,'East',100),(2,'East',50),(3,'West',40),
        (4,'West',60),(5,'North',20),(6,'North',30)
), regional AS (
 SELECT region, SUM(processed) AS total_processed
 FROM batches GROUP BY region
), selected_batches AS (
 SELECT batch_id FROM batches
 WHERE processed > (SELECT AVG(processed) FROM batches)
), selected_regions AS (
 SELECT region,total_processed FROM regional WHERE total_processed > 50
)
SELECT
 (SELECT COUNT(*)=6 AND SUM(processed)=300 FROM batches) AS fixture_ok,
 (SELECT AVG(processed)=50 FROM batches) AS average_ok,
 (SELECT COUNT(*)=2 AND MIN(batch_id)=1 AND MAX(batch_id)=4
  FROM selected_batches) AS scalar_filter_ok,
 (SELECT COUNT(*)=3 AND SUM(total_processed)=300 FROM regional) AS grain_ok,
 (SELECT COUNT(*)=2 AND SUM(total_processed)=250
  FROM selected_regions) AS derived_filter_ok,
 (SELECT COUNT(*)=1 FROM selected_regions
  WHERE region='East' AND total_processed=150) AS east_ok,
 (SELECT COUNT(*)=1 FROM selected_regions
  WHERE region='West' AND total_processed=100) AS west_ok,
 ((SELECT n FROM (VALUES (1)) AS v(n) WHERE n=99) IS NULL) AS empty_scalar_ok;
ROLLBACK;
-- Static expected results only; no runtime validation implied.
