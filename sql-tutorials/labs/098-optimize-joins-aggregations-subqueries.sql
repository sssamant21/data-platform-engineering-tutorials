-- 098: Optimize joins, aggregations, and subqueries.
-- Synthetic, read-only PostgreSQL 18 exercise; no persistent objects.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/098-optimize-joins-aggregations-subqueries.sql
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout='15s';
SET LOCAL lock_timeout='2s';
SET LOCAL idle_in_transaction_session_timeout='30s';

DO $guard$
BEGIN
 IF current_database() <> 'sql_tutorials' THEN
  RAISE EXCEPTION 'Use isolated sql_tutorials database, not %',current_database();
 END IF;
 IF current_setting('server_version_num')::integer / 10000 <> 18 THEN
  RAISE EXCEPTION 'Requires PostgreSQL 18; found %',current_setting('server_version');
 END IF;
END
$guard$;

-- Estimated plan only: inline data has no physical indexes.
EXPLAIN (COSTS ON)
WITH orders(order_id) AS (VALUES (101),(102),(103)),
payments(order_id,status,amount) AS (
 VALUES (101,'settled',50::numeric),(101,'failed',50::numeric),
        (102,'settled',40::numeric)
)
SELECT o.order_id FROM orders o
WHERE EXISTS (SELECT 1 FROM payments p
 WHERE p.order_id=o.order_id AND p.status='settled');

-- Show corrected one-row-per-order results.
WITH orders(order_id) AS (VALUES (101),(102),(103)),
lines(order_id,line_amount) AS (
 VALUES (101,30::numeric),(101,20::numeric),
        (102,40::numeric),(103,10::numeric)
),
payments(order_id,status,amount) AS (
 VALUES (101,'settled',50::numeric),(101,'failed',50::numeric),
        (102,'settled',40::numeric)
),
line_totals AS (
 SELECT order_id,SUM(line_amount) AS line_total FROM lines GROUP BY order_id
),
settled_totals AS (
 SELECT order_id,SUM(amount) AS settled_total FROM payments
 WHERE status='settled' GROUP BY order_id
)
SELECT o.order_id,l.line_total,COALESCE(p.settled_total,0) AS settled_total
FROM orders o
LEFT JOIN line_totals l USING(order_id)
LEFT JOIN settled_totals p USING(order_id)
ORDER BY o.order_id;

DO $assert$
DECLARE mismatch_count bigint; naive_rows bigint; line_sum numeric; settled_sum numeric;
BEGIN
 WITH orders(order_id) AS (VALUES (101),(102),(103)),
 lines(order_id,line_amount) AS (
  VALUES (101,30::numeric),(101,20::numeric),
         (102,40::numeric),(103,10::numeric)
 ),
 payments(order_id,status,amount) AS (
  VALUES (101,'settled',50::numeric),(101,'failed',50::numeric),
         (102,'settled',40::numeric)
 ),
 line_totals AS (
  SELECT order_id,SUM(line_amount) AS line_total FROM lines GROUP BY order_id
 ),
 settled_totals AS (
  SELECT order_id,SUM(amount) AS settled_total
  FROM payments WHERE status='settled' GROUP BY order_id
 ),
 actual AS (
  SELECT o.order_id,l.line_total,COALESCE(p.settled_total,0) AS settled_total
  FROM orders o LEFT JOIN line_totals l USING(order_id)
  LEFT JOIN settled_totals p USING(order_id)
 ),
 expected(order_id,line_total,settled_total) AS (
  VALUES (101,50::numeric,50::numeric),(102,40::numeric,40::numeric),
         (103,10::numeric,0::numeric)
 ),
 differences AS (
  (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
  UNION ALL
  (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
 ),
 exists_result AS (
  SELECT o.order_id FROM orders o
  WHERE EXISTS (SELECT 1 FROM payments p
   WHERE p.order_id=o.order_id AND p.status='settled')
 ),
 join_distinct AS (
  SELECT DISTINCT o.order_id FROM orders o JOIN payments p USING(order_id)
  WHERE p.status='settled'
 ),
 existence_diff AS (
  (SELECT * FROM exists_result EXCEPT ALL SELECT * FROM join_distinct)
  UNION ALL
  (SELECT * FROM join_distinct EXCEPT ALL SELECT * FROM exists_result)
  UNION ALL
  (SELECT * FROM exists_result EXCEPT ALL SELECT * FROM (VALUES (101),(102)) AS v(order_id))
  UNION ALL
  (SELECT * FROM (VALUES (101),(102)) AS v(order_id) EXCEPT ALL SELECT * FROM exists_result)
 )
 SELECT
  (SELECT count(*) FROM differences)+(SELECT count(*) FROM existence_diff),
  (SELECT count(*) FROM orders o JOIN lines l USING(order_id)
    JOIN payments p USING(order_id)),
  (SELECT SUM(line_total) FROM actual),
  (SELECT SUM(settled_total) FROM actual)
 INTO mismatch_count,naive_rows,line_sum,settled_sum;
 IF mismatch_count <> 0 OR naive_rows <> 5 OR line_sum <> 100 OR settled_sum <> 90 THEN
  RAISE EXCEPTION '098 mismatch=% naive_rows=% line_sum=% settled_sum=%',
    mismatch_count,naive_rows,line_sum,settled_sum;
 END IF;
 RAISE NOTICE '098 assertions passed: naive_rows=%, line_sum=%, settled_sum=%',
   naive_rows,line_sum,settled_sum;
END
$assert$;
ROLLBACK;
