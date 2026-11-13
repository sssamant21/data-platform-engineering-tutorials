-- Chapter 111: OLTP versus OLAP query design
-- Synthetic-only read-only exercise; intended for disposable PostgreSQL 18 sql_tutorials.
-- Run with: psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/111-oltp-versus-olap-query-design.sql
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
  IF current_database() <> 'sql_tutorials' THEN
    RAISE EXCEPTION 'Wrong database: expected sql_tutorials, got %', current_database();
  END IF;
  IF current_setting('server_version_num')::integer < 180000
     OR current_setting('server_version_num')::integer >= 190000 THEN
    RAISE EXCEPTION 'Requires PostgreSQL 18, got %', current_setting('server_version');
  END IF;
END
$guard$;

-- Selective OLTP-style lookup (not an index benchmark).
WITH orders(order_id, customer_id, region, amount) AS (
  VALUES (1001,11,'East',40.00::numeric), (1002,12,'West',25.00::numeric),
         (1003,11,'East',35.00::numeric), (1004,13,'West',50.00::numeric),
         (1005,14,'East',20.00::numeric)
)
SELECT order_id, customer_id, amount FROM orders WHERE order_id = 1002;

-- OLAP-style report at region grain.
WITH orders(order_id, customer_id, region, amount) AS (
  VALUES (1001,11,'East',40.00::numeric), (1002,12,'West',25.00::numeric),
         (1003,11,'East',35.00::numeric), (1004,13,'West',50.00::numeric),
         (1005,14,'East',20.00::numeric)
)
SELECT region, count(*) AS order_count, sum(amount) AS revenue
FROM orders GROUP BY region ORDER BY region;

-- Exact assertions: 5 orders, 7 lines, 170.00 totals, fan-out 260.00.
-- Line amounts: 1001 (15+25), 1002 (25), 1003 (35), 1004 (20+30), 1005 (20).
DO $assert$
DECLARE
  n_orders integer; n_lines integer;
  header_total numeric; line_total numeric; naive_total numeric;
  mismatch_count integer;
BEGIN
  WITH orders(order_id, region, amount) AS (
    VALUES (1001,'East',40.00::numeric), (1002,'West',25.00::numeric),
           (1003,'East',35.00::numeric), (1004,'West',50.00::numeric),
           (1005,'East',20.00::numeric)
  ), lines(order_id, line_id, amount) AS (
    VALUES (1001,1,15.00::numeric), (1001,2,25.00::numeric),
           (1002,1,25.00::numeric), (1003,1,35.00::numeric),
           (1004,1,20.00::numeric), (1004,2,30.00::numeric),
           (1005,1,20.00::numeric)
  )
  SELECT (SELECT count(*) FROM orders), (SELECT count(*) FROM lines),
         (SELECT sum(amount) FROM orders), (SELECT sum(amount) FROM lines),
         (SELECT sum(o.amount) FROM orders o JOIN lines l USING(order_id))
  INTO n_orders, n_lines, header_total, line_total, naive_total;

  IF (n_orders,n_lines,header_total,line_total,naive_total)
     IS DISTINCT FROM (5,7,170.00::numeric,170.00::numeric,260.00::numeric) THEN
    RAISE EXCEPTION 'Unexpected totals: orders %, lines %, header %, line %, joined %',
      n_orders,n_lines,header_total,line_total,naive_total;
  END IF;

  WITH orders(region, amount) AS (
    VALUES ('East',40.00::numeric), ('West',25.00::numeric),
           ('East',35.00::numeric), ('West',50.00::numeric), ('East',20.00::numeric)
  ), actual AS (
    SELECT region, count(*) AS n, sum(amount) AS revenue FROM orders GROUP BY region
  ), expected(region,n,revenue) AS (
    VALUES ('East',3::bigint,95.00::numeric),('West',2::bigint,75.00::numeric)
  ), differences AS (
    (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
    UNION ALL
    (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
  )
  SELECT count(*) INTO mismatch_count FROM differences;

  IF mismatch_count <> 0 THEN
    RAISE EXCEPTION 'Region reconciliation mismatch count: %', mismatch_count;
  END IF;
  RAISE NOTICE 'Chapter 111 synthetic assertions passed: 5 orders, 7 lines, totals 170.00, naive join 260.00, 0 region mismatches';
END
$assert$;

ROLLBACK;
