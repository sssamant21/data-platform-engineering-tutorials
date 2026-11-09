-- Chapter 030 / Lab 03: normalized operational schema
-- PostgreSQL 18 ONLY; isolated disposable database sql_tutorials ONLY.
-- Verify host/container/credentials OUTSIDE this script. Never use production.
-- Run: psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/030-lab-03-normalized-operational-schema.sql
BEGIN;
SET LOCAL lock_timeout = '2s';
SET LOCAL statement_timeout = '30s';
SET LOCAL idle_in_transaction_session_timeout = '60s';
DO $guard$
BEGIN
 IF current_setting('server_version_num')::integer < 180000
    OR current_setting('server_version_num')::integer >= 190000
    OR current_database() <> 'sql_tutorials'
    OR pg_is_in_recovery()
 THEN
   RAISE EXCEPTION 'Wrong PostgreSQL version/database or standby: aborting';
 END IF;
END
$guard$;

CREATE TEMP TABLE customers (
 customer_id INTEGER PRIMARY KEY,
 customer_code VARCHAR(20) NOT NULL UNIQUE,
 customer_name VARCHAR(100) NOT NULL
) ON COMMIT DROP;
CREATE TEMP TABLE products (
 product_id INTEGER PRIMARY KEY,
 sku VARCHAR(20) NOT NULL UNIQUE,
 product_name VARCHAR(100) NOT NULL,
 list_price NUMERIC(12,2) NOT NULL CHECK (list_price >= 0)
) ON COMMIT DROP;
CREATE TEMP TABLE orders (
 order_id INTEGER PRIMARY KEY,
 order_code VARCHAR(20) NOT NULL UNIQUE,
 customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
 ordered_on DATE NOT NULL
) ON COMMIT DROP;
CREATE TEMP TABLE order_items (
 order_id INTEGER NOT NULL REFERENCES orders(order_id),
 line_no INTEGER NOT NULL CHECK (line_no > 0),
 product_id INTEGER NOT NULL REFERENCES products(product_id),
 quantity INTEGER NOT NULL CHECK (quantity > 0),
 unit_price_at_order NUMERIC(12,2) NOT NULL CHECK (unit_price_at_order >= 0),
 PRIMARY KEY (order_id, line_no)
) ON COMMIT DROP;

INSERT INTO customers VALUES (1,'C-001','Synthetic Alice'),(2,'C-002','Synthetic Bob');
INSERT INTO products VALUES (10,'SKU-A','Sample Pen',14.00),(20,'SKU-B','Sample Notebook',32.00);
INSERT INTO orders VALUES (100,'ORD-001',1,DATE '2026-01-02'),(200,'ORD-002',1,DATE '2026-01-03');
INSERT INTO order_items VALUES
 (100,1,10,2,12.50),
 (100,2,20,1,30.00),
 (200,1,10,3,10.00);

-- Expected ORD-001=55.00; ORD-002=30.00.
SELECT o.order_code, SUM(i.quantity * i.unit_price_at_order) AS order_total
FROM orders o JOIN order_items i ON i.order_id=o.order_id
GROUP BY o.order_id,o.order_code ORDER BY o.order_code;

-- Fail closed on counts, foreign-key integrity, totals, and historical price.
DO $assert$
DECLARE
  actual_total NUMERIC;
  first_total NUMERIC;
  second_total NUMERIC;
BEGIN
 IF (SELECT count(*) FROM customers) <> 2
    OR (SELECT count(*) FROM products) <> 2
    OR (SELECT count(*) FROM orders) <> 2
    OR (SELECT count(*) FROM order_items) <> 3
 THEN RAISE EXCEPTION 'Unexpected entity counts'; END IF;
 SELECT SUM(quantity * unit_price_at_order) INTO actual_total FROM order_items;
 SELECT SUM(quantity * unit_price_at_order) INTO first_total FROM order_items WHERE order_id=100;
 SELECT SUM(quantity * unit_price_at_order) INTO second_total FROM order_items WHERE order_id=200;
 IF actual_total IS DISTINCT FROM 85.00::NUMERIC
    OR first_total IS DISTINCT FROM 55.00::NUMERIC
    OR second_total IS DISTINCT FROM 30.00::NUMERIC
 THEN RAISE EXCEPTION 'Reconciliation mismatch: %, %, %',actual_total,first_total,second_total; END IF;
 IF EXISTS (SELECT 1 FROM order_items i LEFT JOIN orders o ON o.order_id=i.order_id WHERE o.order_id IS NULL)
 THEN RAISE EXCEPTION 'Orphan order item'; END IF;
 IF (SELECT unit_price_at_order FROM order_items WHERE order_id=200 AND line_no=1)
    IS DISTINCT FROM 10.00::NUMERIC
 THEN RAISE EXCEPTION 'Historical price changed'; END IF;
END
$assert$;
SELECT 'PASS' AS lab_acceptance, 2 AS expected_orders, 3 AS expected_lines, 85.00::NUMERIC(12,2) AS expected_revenue;
ROLLBACK;
