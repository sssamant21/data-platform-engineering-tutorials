-- Chapter 016 — DISTINCT and duplicate handling.
-- Run ONLY in an independently verified disposable PostgreSQL 18 lab.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/016-distinct-duplicate-handling.sql
-- Synthetic inline rows only; no persistent DDL or DML.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials'
 AND current_setting('server_version_num')::integer >= 180000
 AND current_setting('server_version_num')::integer < 190000
 THEN 1 ELSE 0 END AS environment_assertion;

-- Unique projected regions: East, West, NULL (NULL last).
WITH orders(region) AS (
 VALUES ('East'::text),('West'),('East'),('East'),(NULL::text),('West')
)
SELECT DISTINCT region FROM orders ORDER BY region NULLS LAST;

-- Counts: all_rows=6, non_null_regions=5, unique_non_null_regions=2.
WITH orders(region) AS (
 VALUES ('East'::text),('West'),('East'),('East'),(NULL::text),('West')
)
SELECT COUNT(*) AS all_rows, COUNT(region) AS non_null_regions,
       COUNT(DISTINCT region) AS unique_non_null_regions
FROM orders;

-- Multiple orders for one customer are legitimate, not necessarily duplicates.
WITH orders(customer_id) AS (VALUES (101),(102),(101),(103),(104),(105))
SELECT customer_id, COUNT(*) AS order_count
FROM orders GROUP BY customer_id HAVING COUNT(*) > 1 ORDER BY customer_id;
-- Expected: 101 | 2

-- Fail-closed acceptance of exact expected counts and groups.
WITH orders(order_id,customer_id,region,status,amount) AS (
 VALUES (1,101,'East'::text,'paid'::text,100.00::numeric),
        (2,102,'West','paid',80.00),
        (3,101,'East','paid',25.00),
        (4,103,'East','pending',40.00),
        (5,104,NULL::text,'paid',60.00),
        (6,105,'West','paid',90.00)
), checks AS (
 SELECT
  (SELECT COUNT(*) FROM orders) = 6 AS row_count,
  (SELECT COUNT(region) FROM orders) = 5 AS nonnull_count,
  (SELECT COUNT(DISTINCT region) FROM orders) = 2 AS region_count,
  (SELECT COUNT(*) FROM (SELECT DISTINCT region FROM orders) d) = 3 AS categories,
  (SELECT COUNT(*) FROM (SELECT DISTINCT region,status FROM orders) d) = 4 AS pairs,
  (SELECT COUNT(DISTINCT customer_id) FROM orders) = 5 AS customers,
  (SELECT COUNT(DISTINCT order_id) FROM orders) = 6 AS unique_order_ids,
  (SELECT array_agg(customer_id ORDER BY customer_id) FROM
    (SELECT customer_id FROM orders GROUP BY customer_id HAVING COUNT(*) > 1) d)
    = ARRAY[101] AS repeated_customer,
  (SELECT COUNT(*) FROM orders WHERE region IS NULL) = 1 AS missing_region
)
SELECT 1 / CASE WHEN row_count AND nonnull_count AND region_count AND categories
 AND pairs AND customers AND unique_order_ids AND repeated_customer
 AND missing_region THEN 1 ELSE 0 END AS acceptance_assertion
FROM checks;
ROLLBACK;
