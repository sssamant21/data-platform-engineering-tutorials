-- Chapter 115 — portability contract: PostgreSQL 18-specific executable test
-- Synthetic CTEs only. No persistent writes. Not a cross-vendor runtime test.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/115-portable-sql-dialect-testing.sql
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
  IF current_database() <> 'sql_tutorials' THEN
    RAISE EXCEPTION 'Disposable sql_tutorials database required; got %', current_database();
  END IF;
  IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999 THEN
    RAISE EXCEPTION 'PostgreSQL 18 required; got %', current_setting('server_version');
  END IF;
END
$guard$;

-- Portable-style aggregate: expected East (2,1,40), West (2,2,80).
WITH orders(order_id, region, amount) AS (
  VALUES (101,'East',40.00::numeric), (102,'East',NULL::numeric),
         (103,'West',60.00::numeric), (104,'West',20.00::numeric)
)
SELECT region, COUNT(*) AS rows_seen, COUNT(amount) AS known_amounts,
       SUM(COALESCE(amount,0)) AS total_amount
FROM orders GROUP BY region ORDER BY region;

-- FETCH is standard-style; LIMIT is PostgreSQL-supported; both should return 101,102,103.
WITH orders(order_id,region) AS (
 VALUES (101,'East'),(102,'East'),(103,'West'),(104,'West')
)
SELECT order_id FROM orders ORDER BY region,order_id FETCH FIRST 3 ROWS ONLY;

WITH orders(order_id,region) AS (
 VALUES (101,'East'),(102,'East'),(103,'West'),(104,'West')
)
SELECT order_id FROM orders ORDER BY region,order_id LIMIT 3;

-- Fail closed: exact row-level, duplicate-aware comparison, plus numeric/count assertions.
DO $assert$
DECLARE mismatch_count integer; total_count integer; known_count integer;
        null_count integer; grand_total numeric; lower_matches integer;
        ilike_matches integer; pagination_mismatches integer;
BEGIN
 WITH orders(order_id,region,amount) AS (
   VALUES (101,'East',40.00::numeric),(102,'East',NULL::numeric),
          (103,'West',60.00::numeric),(104,'West',20.00::numeric)
 ), actual AS (
   SELECT region,COUNT(*)::integer AS n,COUNT(amount)::integer AS known,
          SUM(COALESCE(amount,0)) AS total FROM orders GROUP BY region
 ), expected(region,n,known,total) AS (
   VALUES ('East',2,1,40.00::numeric),('West',2,2,80.00::numeric)
 ), mismatch AS (
   (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
   UNION ALL
   (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
 ), standard_page AS (
   SELECT order_id FROM orders ORDER BY region,order_id FETCH FIRST 3 ROWS ONLY
 ), vendor_page AS (
   SELECT order_id FROM orders ORDER BY region,order_id LIMIT 3
 ), expected_page(order_id) AS (VALUES (101),(102),(103)),
 page_mismatch AS (
   (SELECT * FROM standard_page EXCEPT ALL SELECT * FROM expected_page)
   UNION ALL (SELECT * FROM expected_page EXCEPT ALL SELECT * FROM standard_page)
   UNION ALL (SELECT * FROM vendor_page EXCEPT ALL SELECT * FROM expected_page)
   UNION ALL (SELECT * FROM expected_page EXCEPT ALL SELECT * FROM vendor_page)
 )
 SELECT (SELECT count(*) FROM mismatch),
        (SELECT count(*) FROM orders),
        (SELECT count(amount) FROM orders),
        (SELECT count(*) FROM orders WHERE amount IS NULL),
        (SELECT sum(coalesce(amount,0)) FROM orders),
        (SELECT count(*) FROM orders WHERE lower(region)=lower('east')),
        (SELECT count(*) FROM orders WHERE region ILIKE 'east'),
        (SELECT count(*) FROM page_mismatch)
 INTO mismatch_count,total_count,known_count,null_count,grand_total,
      lower_matches,ilike_matches,pagination_mismatches;
 IF (mismatch_count,total_count,known_count,null_count,grand_total,
     lower_matches,ilike_matches,pagination_mismatches)
    IS DISTINCT FROM (0,4,3,1,120.00::numeric,2,2,0) THEN
   RAISE EXCEPTION 'Chapter 115 contract failed: mismatch %, rows %, known %, null %, total %, lower %, ilike %, page %',
     mismatch_count,total_count,known_count,null_count,grand_total,
     lower_matches,ilike_matches,pagination_mismatches;
 END IF;
 RAISE NOTICE 'Chapter 115 calculated contract matched: 4 rows, 3 known, 1 NULL, total 120, case matches 2/2, page 101/102/103, 0 mismatches';
END
$assert$;
ROLLBACK;
