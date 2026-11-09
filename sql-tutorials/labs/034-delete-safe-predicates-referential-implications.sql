-- Chapter 034: DELETE with safe predicates and referential implications
-- Only on an independently verified disposable PostgreSQL 18 sql_tutorials database.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/034-delete-safe-predicates-referential-implications.sql
BEGIN;
SET LOCAL lock_timeout = '2s';
SET LOCAL statement_timeout = '30s';
SET LOCAL idle_in_transaction_session_timeout = '60s';

DO $guard$
BEGIN
  IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
     OR current_database() <> 'sql_tutorials'
     OR pg_is_in_recovery()
  THEN RAISE EXCEPTION 'Unsafe version/database/standby; abort'; END IF;
END
$guard$;

CREATE TEMP TABLE customers (
  customer_id TEXT PRIMARY KEY,
  customer_name TEXT NOT NULL
) ON COMMIT DROP;
CREATE TEMP TABLE orders (
  order_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL REFERENCES customers(customer_id) ON DELETE RESTRICT,
  order_status TEXT NOT NULL CHECK (order_status IN ('active','cancelled'))
) ON COMMIT DROP;
CREATE TEMP TABLE deleted_orders (
  order_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL
) ON COMMIT DROP;

INSERT INTO customers VALUES ('C-01','Synthetic One'),('C-02','Synthetic Two');
INSERT INTO orders VALUES
 ('O-101','C-01','active'),
 ('O-102','C-01','cancelled'),
 ('O-103','C-02','active');

-- Preview exactly the one eligible row.
SELECT order_id,customer_id,order_status FROM orders
 WHERE order_id='O-102' AND order_status='cancelled'
 ORDER BY order_id;
DO $pre$
DECLARE ids TEXT[];
BEGIN
 SELECT array_agg(order_id ORDER BY order_id) INTO ids FROM orders
 WHERE order_id='O-102' AND order_status='cancelled';
 IF ids IS DISTINCT FROM ARRAY['O-102']::TEXT[]
 THEN RAISE EXCEPTION 'Unsafe DELETE candidate set: %',ids; END IF;
END
$pre$;

-- PostgreSQL-specific RETURNING: capture the actual affected key.
WITH removed AS (
 DELETE FROM orders
 WHERE order_id='O-102' AND order_status='cancelled'
 RETURNING order_id,customer_id
)
INSERT INTO deleted_orders SELECT order_id,customer_id FROM removed;
SELECT order_id,customer_id FROM deleted_orders ORDER BY order_id;

-- Expected FK failure, caught in a nested PL/pgSQL exception block.
DO $fk_test$
BEGIN
 BEGIN
   DELETE FROM customers WHERE customer_id='C-01';
   RAISE EXCEPTION 'Expected FK rejection did not occur';
 EXCEPTION
   WHEN foreign_key_violation THEN
     RAISE NOTICE 'Expected SQLSTATE 23503: referenced parent deletion rejected';
 END;
END
$fk_test$;

SELECT order_id,customer_id,order_status FROM orders ORDER BY order_id;
DO $assert$
DECLARE deleted_ids TEXT[]; remaining_ids TEXT[];
        customer_count INTEGER; order_count INTEGER; orphan_count INTEGER;
BEGIN
 SELECT array_agg(order_id ORDER BY order_id) INTO deleted_ids FROM deleted_orders;
 SELECT array_agg(order_id ORDER BY order_id) INTO remaining_ids FROM orders;
 SELECT count(*) INTO customer_count FROM customers;
 SELECT count(*) INTO order_count FROM orders;
 SELECT count(*) INTO orphan_count FROM orders o
 LEFT JOIN customers c ON c.customer_id=o.customer_id
 WHERE c.customer_id IS NULL;
 IF deleted_ids IS DISTINCT FROM ARRAY['O-102']::TEXT[]
 OR remaining_ids IS DISTINCT FROM ARRAY['O-101','O-103']::TEXT[]
 OR customer_count <> 2 OR order_count <> 2 OR orphan_count <> 0
 THEN RAISE EXCEPTION 'Chapter 034 acceptance failed: deleted %, remaining %, customers %, orders %, orphans %',
 deleted_ids,remaining_ids,customer_count,order_count,orphan_count; END IF;
END
$assert$;
SELECT 'PASS' AS lab_acceptance, 2 AS expected_customers,
       2 AS expected_orders, 0 AS expected_orphans;
ROLLBACK;
