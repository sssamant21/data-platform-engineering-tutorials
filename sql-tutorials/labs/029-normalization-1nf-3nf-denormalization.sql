-- Chapter 029 — Normalization (1NF–3NF) and intentional denormalization
-- Synthetic data only. Read-only; no persistent objects or writes.
-- Independently verify disposable PostgreSQL 18 primary host/container and credentials.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/029-normalization-1nf-3nf-denormalization.sql
-- Actual PostgreSQL 18 runtime validation PENDING.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
DO $guard$
BEGIN
 IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
    OR current_database() <> 'sql_tutorials' OR pg_is_in_recovery() THEN
   RAISE EXCEPTION 'Requires independently verified isolated PostgreSQL 18 primary sql_tutorials';
 END IF;
END
$guard$;

-- The first query demonstrates one row per order line (3 rows).
WITH customers(customer_id,customer_name) AS (
 VALUES (1,'Ada'),(2,'Ben')
), products(product_id,product_name) AS (
 VALUES ('P10','Keyboard'),('P20','Mouse')
), orders(order_id,customer_id) AS (
 VALUES (100,1),(101,2)
), order_items(order_id,line_no,product_id,quantity,unit_price_at_sale) AS (
 VALUES (100,1,'P10',2,25.00::numeric(10,2)),
        (100,2,'P20',1,10.00::numeric(10,2)),
        (101,1,'P10',1,25.00::numeric(10,2))
)
SELECT o.order_id,c.customer_name,i.line_no,p.product_name,
       i.quantity,i.unit_price_at_sale,
       i.quantity*i.unit_price_at_sale AS line_total
FROM orders o
JOIN customers c ON c.customer_id=o.customer_id
JOIN order_items i ON i.order_id=o.order_id
JOIN products p ON p.product_id=i.product_id
ORDER BY o.order_id,i.line_no;
-- Expected rows: (100,Ada,1,Keyboard,2,25.00,50.00);
-- (100,Ada,2,Mouse,1,10.00,10.00); (101,Ben,1,Keyboard,1,25.00,25.00).

-- Demonstrate source-derived versus intentionally stale cached order total.
WITH order_items(order_id,line_no,quantity,unit_price_at_sale) AS (
 VALUES (100,1,2,25.00::numeric),(100,2,1,10.00::numeric),
        (101,1,1,25.00::numeric)
), cached(order_id,cached_total) AS (
 VALUES (100,55.00::numeric),(101,25.00::numeric)
)
SELECT i.order_id, SUM(i.quantity*i.unit_price_at_sale) AS source_total,
       c.cached_total,
       SUM(i.quantity*i.unit_price_at_sale)-c.cached_total AS drift
FROM order_items i JOIN cached c ON c.order_id=i.order_id
GROUP BY i.order_id,c.cached_total
ORDER BY i.order_id;
-- Expected: (100,60.00,55.00,5.00), (101,25.00,25.00,0.00).

-- Fail-closed exact acceptance assertions. No external tables accessed.
DO $assert$
DECLARE
 n_customers bigint; n_products bigint; n_orders bigint; n_lines bigint;
 total numeric; orphan_orders bigint; orphan_products bigint;
 order100 numeric; order101 numeric; drift_count bigint;
BEGIN
 WITH customers(customer_id,customer_name) AS (
  VALUES (1,'Ada'),(2,'Ben')
 ), products(product_id,product_name) AS (
  VALUES ('P10','Keyboard'),('P20','Mouse')
 ), orders(order_id,customer_id) AS (
  VALUES (100,1),(101,2)
 ), order_items(order_id,line_no,product_id,quantity,unit_price_at_sale) AS (
  VALUES (100,1,'P10',2,25.00::numeric),(100,2,'P20',1,10.00::numeric),
         (101,1,'P10',1,25.00::numeric)
 ), cached(order_id,cached_total) AS (
  VALUES (100,55.00::numeric),(101,25.00::numeric)
 ), totals AS (
  SELECT order_id,SUM(quantity*unit_price_at_sale) AS amount
  FROM order_items GROUP BY order_id
 )
 SELECT (SELECT COUNT(*) FROM customers),
        (SELECT COUNT(*) FROM products),
        (SELECT COUNT(*) FROM orders),
        (SELECT COUNT(*) FROM order_items),
        (SELECT SUM(quantity*unit_price_at_sale) FROM order_items),
        (SELECT COUNT(*) FROM orders o LEFT JOIN customers c ON c.customer_id=o.customer_id WHERE c.customer_id IS NULL),
        (SELECT COUNT(*) FROM order_items i LEFT JOIN products p ON p.product_id=i.product_id WHERE p.product_id IS NULL),
        (SELECT amount FROM totals WHERE order_id=100),
        (SELECT amount FROM totals WHERE order_id=101),
        (SELECT COUNT(*) FROM totals t JOIN cached c USING(order_id) WHERE t.amount IS DISTINCT FROM c.cached_total)
 INTO n_customers,n_products,n_orders,n_lines,total,orphan_orders,orphan_products,order100,order101,drift_count;
 IF n_customers <> 2 OR n_products <> 2 OR n_orders <> 2 OR n_lines <> 3
    OR total IS DISTINCT FROM 85::numeric
    OR orphan_orders <> 0 OR orphan_products <> 0
    OR order100 IS DISTINCT FROM 60::numeric
    OR order101 IS DISTINCT FROM 25::numeric
    OR drift_count <> 1 THEN
   RAISE EXCEPTION 'Ch029 acceptance failed: customers %, products %, orders %, lines %, total %, orphans %/%, totals %/%, drift %',
     n_customers,n_products,n_orders,n_lines,total,orphan_orders,orphan_products,order100,order101,drift_count;
 END IF;
 RAISE NOTICE 'Chapter 029 synthetic acceptance assertions passed';
END
$assert$;
ROLLBACK;
