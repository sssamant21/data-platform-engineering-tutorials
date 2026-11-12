-- 093: B-tree indexes and common index access patterns
-- Isolated PostgreSQL 18 only; read-only, synthetic VALUES, no persistent objects.
-- psql client required for ON_ERROR_STOP.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
  IF current_database() <> 'sql_tutorials' THEN
    RAISE EXCEPTION 'Expected isolated sql_tutorials database, found %', current_database();
  END IF;
  IF current_setting('server_version_num')::integer / 10000 <> 18 THEN
    RAISE EXCEPTION 'Expected PostgreSQL 18, found %', current_setting('server_version');
  END IF;
END
$guard$;

-- Plain EXPLAIN estimates a plan over inline rows; it cannot show a real index scan.
EXPLAIN (FORMAT TEXT, COSTS ON)
SELECT order_id, amount
FROM (VALUES (101,12.00::numeric),(102,25.00::numeric),
             (103,8.00::numeric),(104,40.00::numeric),
             (105,15.00::numeric)) AS o(order_id,amount)
WHERE order_id = 103;

-- Point lookup: expected one row (103, 8.00).
WITH orders(order_id,amount) AS (
 VALUES (101,12.00::numeric),(102,25.00::numeric),
        (103,8.00::numeric),(104,40.00::numeric),
        (105,15.00::numeric)
)
SELECT order_id, amount FROM orders WHERE order_id = 103 ORDER BY order_id;

-- Half-open range: expected IDs 102, 103, 104 and sum 73.00.
WITH orders(order_id,amount) AS (
 VALUES (101,12.00::numeric),(102,25.00::numeric),
        (103,8.00::numeric),(104,40.00::numeric),
        (105,15.00::numeric)
)
SELECT order_id, amount
FROM orders WHERE order_id >= 102 AND order_id < 105 ORDER BY order_id;

-- Fail closed: verify exact result multisets, including duplicates.
DO $assert$
DECLARE discrepancy_count integer;
BEGIN
  WITH orders(order_id,amount) AS (
    VALUES (101,12.00::numeric),(102,25.00::numeric),
           (103,8.00::numeric),(104,40.00::numeric),
           (105,15.00::numeric)
  ), actual AS (
    SELECT 'point'::text AS kind, order_id, amount
    FROM orders WHERE order_id = 103
    UNION ALL
    SELECT 'range'::text, order_id, amount
    FROM orders WHERE order_id >= 102 AND order_id < 105
  ), expected(kind,order_id,amount) AS (
    VALUES ('point',103,8.00::numeric),
           ('range',102,25.00::numeric),
           ('range',103,8.00::numeric),
           ('range',104,40.00::numeric)
  ), differences AS (
    (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
    UNION ALL
    (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
  )
  SELECT COUNT(*) INTO discrepancy_count FROM differences;
  IF discrepancy_count <> 0 THEN
    RAISE EXCEPTION '093 row assertion failed: % differences', discrepancy_count;
  END IF;

  WITH orders(order_id,amount) AS (
    VALUES (101,12.00::numeric),(102,25.00::numeric),
           (103,8.00::numeric),(104,40.00::numeric),
           (105,15.00::numeric)
  ), actual AS (
    SELECT COUNT(*)::bigint AS total_count, SUM(amount) AS total_amount,
           COUNT(*) FILTER (WHERE order_id >= 102 AND order_id < 105)::bigint AS range_count,
           SUM(amount) FILTER (WHERE order_id >= 102 AND order_id < 105) AS range_amount
    FROM orders
  ), expected(total_count,total_amount,range_count,range_amount) AS (
    VALUES (5::bigint,100.00::numeric,3::bigint,73.00::numeric)
  ), differences AS (
    (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
    UNION ALL
    (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
  )
  SELECT COUNT(*) INTO discrepancy_count FROM differences;
  IF discrepancy_count <> 0 THEN
    RAISE EXCEPTION '093 aggregate assertion failed: % differences', discrepancy_count;
  END IF;
END
$assert$;
ROLLBACK;
