-- Chapter 021: Entity relationships and conceptual data modeling
-- Target: isolated PostgreSQL 18, database sql_tutorials; synthetic read-only lab.
-- Not runtime validated until executed with retained evidence.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
DO $guard$
BEGIN
  IF current_setting('server_version_num')::integer < 180000
     OR current_setting('server_version_num')::integer >= 190000
     OR current_database() <> 'sql_tutorials' THEN
    RAISE EXCEPTION 'Requires isolated PostgreSQL 18 database sql_tutorials';
  END IF;
END
$guard$;

-- Each query uses the same tiny synthetic model; no persistent tables are created.
-- C03 has no orders. O100 has two lines. O101 has one line.
WITH customers(code) AS (VALUES ('C01'),('C02'),('C03')),
orders(order_no,customer_code) AS (VALUES ('O100','C01'),('O101','C02'))
SELECT c.code AS customer_without_order
FROM customers c LEFT JOIN orders o ON o.customer_code=c.code
WHERE o.order_no IS NULL
ORDER BY c.code;
-- Expected: C03.

WITH orders(order_no,customer_code) AS (VALUES ('O100','C01'),('O101','C02')),
lines(order_no,line_no,sku,quantity,unit_price) AS (
  VALUES ('O100',1,'SKU-A',2,12.50::numeric),
         ('O100',2,'SKU-B',1,7.00::numeric),
         ('O101',1,'SKU-B',2,7.50::numeric))
SELECT o.order_no, COUNT(*) AS joined_rows,
       COUNT(DISTINCT o.order_no) AS distinct_orders,
       SUM(l.quantity*l.unit_price) AS amount
FROM orders o JOIN lines l ON l.order_no=o.order_no
GROUP BY o.order_no ORDER BY o.order_no;
-- Expected: O100 | 2 | 1 | 32.00; O101 | 1 | 1 | 15.00.

WITH customers(code) AS (VALUES ('C01'),('C02'),('C03')),
orders(order_no,customer_code) AS (VALUES ('O100','C01'),('O101','C02'))
SELECT o.order_no AS orphan_order
FROM orders o LEFT JOIN customers c ON c.code=o.customer_code
WHERE c.code IS NULL;
-- Expected: zero rows.

-- Fail-closed checks. Any deviation raises an exception and psql ON_ERROR_STOP halts.
DO $assert$
DECLARE
  customer_without_order text;
  orphan_count integer;
  joined_count integer;
  distinct_count integer;
  total_o100 numeric;
  total_o101 numeric;
BEGIN
  WITH customers(code) AS (VALUES ('C01'),('C02'),('C03')),
  orders(order_no,customer_code) AS (VALUES ('O100','C01'),('O101','C02'))
  SELECT MIN(c.code) FILTER (WHERE o.order_no IS NULL),
         COUNT(*) FILTER (WHERE o.order_no IS NULL)
  INTO customer_without_order, orphan_count
  FROM customers c LEFT JOIN orders o ON o.customer_code=c.code;
  IF customer_without_order IS DISTINCT FROM 'C03' OR orphan_count <> 1 THEN
    RAISE EXCEPTION 'Optional customer participation assertion failed';
  END IF;

  WITH orders(order_no,customer_code) AS (VALUES ('O100','C01'),('O101','C02')),
  lines(order_no,line_no,sku,quantity,unit_price) AS (
    VALUES ('O100',1,'SKU-A',2,12.50::numeric),
           ('O100',2,'SKU-B',1,7.00::numeric),
           ('O101',1,'SKU-B',2,7.50::numeric))
  SELECT COUNT(*), COUNT(DISTINCT o.order_no),
         SUM(l.quantity*l.unit_price) FILTER (WHERE o.order_no='O100'),
         SUM(l.quantity*l.unit_price) FILTER (WHERE o.order_no='O101')
  INTO joined_count, distinct_count, total_o100, total_o101
  FROM orders o JOIN lines l ON l.order_no=o.order_no;
  IF joined_count <> 3 OR distinct_count <> 2
     OR total_o100 IS DISTINCT FROM 32.00::numeric
     OR total_o101 IS DISTINCT FROM 15.00::numeric THEN
    RAISE EXCEPTION 'Join grain / amount assertion failed';
  END IF;

  WITH customers(code) AS (VALUES ('C01'),('C02'),('C03')),
  orders(order_no,customer_code) AS (VALUES ('O100','C01'),('O101','C02'))
  SELECT COUNT(*) INTO orphan_count
  FROM orders o LEFT JOIN customers c ON c.code=o.customer_code
  WHERE c.code IS NULL;
  IF orphan_count <> 0 THEN RAISE EXCEPTION 'Orphan order assertion failed'; END IF;
  RAISE NOTICE 'Chapter 021 synthetic assertions passed (not independent runtime certification)';
END
$assert$;
ROLLBACK;
