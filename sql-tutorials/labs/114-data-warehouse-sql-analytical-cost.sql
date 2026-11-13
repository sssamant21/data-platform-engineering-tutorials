-- Chapter 114: Data warehouse SQL and analytical cost considerations
-- Synthetic, read-only logic exercise; NOT a cloud billing benchmark.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/114-data-warehouse-sql-analytical-cost.sql
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
DO $guard$
BEGIN
 IF current_database() <> 'sql_tutorials' THEN
   RAISE EXCEPTION 'Disposable sql_tutorials database required, got %', current_database();
 END IF;
 IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999 THEN
   RAISE EXCEPTION 'PostgreSQL 18 required, got %', current_setting('server_version');
 END IF;
END
$guard$;

-- Correct order-grain regional revenue.
WITH orders(order_id,region,amount) AS (
 VALUES (1,'East',40.00::numeric),(2,'East',60.00::numeric),
        (3,'West',30.00::numeric),(4,'West',70.00::numeric)
)
SELECT region,count(*) AS order_count,sum(amount) AS revenue
FROM orders GROUP BY region ORDER BY region;

-- Contrast the correct sum and intentionally incorrect join sum.
WITH orders(order_id,region,amount) AS (
 VALUES (1,'East',40.00::numeric),(2,'East',60.00::numeric),
        (3,'West',30.00::numeric),(4,'West',70.00::numeric)
), lines(line_id,order_id) AS (
 VALUES (11,1),(12,1),(21,2),(31,3),(32,3),(41,4)
)
SELECT (SELECT sum(amount) FROM orders) AS correct_total,
       (SELECT sum(o.amount) FROM orders o JOIN lines l USING(order_id)) AS wrong_join_total;

-- Fail-closed assertions (expected outputs are statically calculated, not observed).
DO $assert$
DECLARE n_orders integer; n_lines integer; east_total numeric; west_total numeric;
        correct_total numeric; wrong_total numeric; mismatch_count integer;
BEGIN
 WITH orders(order_id,region,amount) AS (
  VALUES (1,'East',40.00::numeric),(2,'East',60.00::numeric),
         (3,'West',30.00::numeric),(4,'West',70.00::numeric)
 ), lines(line_id,order_id) AS (
  VALUES (11,1),(12,1),(21,2),(31,3),(32,3),(41,4)
 ), actual AS (
  SELECT region,count(*)::integer AS n,sum(amount) AS revenue
  FROM orders GROUP BY region
 ), expected(region,n,revenue) AS (
  VALUES ('East',2,100.00::numeric),('West',2,100.00::numeric)
 ), mismatch AS (
  (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
  UNION ALL
  (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
 )
 SELECT (SELECT count(*) FROM orders),(SELECT count(*) FROM lines),
        (SELECT revenue FROM actual WHERE region='East'),
        (SELECT revenue FROM actual WHERE region='West'),
        (SELECT sum(amount) FROM orders),
        (SELECT sum(o.amount) FROM orders o JOIN lines l USING(order_id)),
        (SELECT count(*) FROM mismatch)
 INTO n_orders,n_lines,east_total,west_total,correct_total,wrong_total,mismatch_count;
 IF (n_orders,n_lines,east_total,west_total,correct_total,wrong_total,mismatch_count)
    IS DISTINCT FROM (4,6,100.00::numeric,100.00::numeric,200.00::numeric,270.00::numeric,0) THEN
   RAISE EXCEPTION 'Chapter 114 assertion failure: orders %, lines %, east %, west %, correct %, wrong %, mismatches %',
     n_orders,n_lines,east_total,west_total,correct_total,wrong_total,mismatch_count;
 END IF;
 RAISE NOTICE 'Chapter 114 synthetic assertions passed: 4 orders, 6 lines, 200.00 correct, 270.00 wrong, 70.00 overcount, 0 mismatches';
END
$assert$;
ROLLBACK;
