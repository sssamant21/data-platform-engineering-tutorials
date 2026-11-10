-- 043 LEFT OUTER JOIN: synthetic retail staging only
-- Run on isolated disposable PostgreSQL 18 database sql_tutorials.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/043-left-outer-join-unmatched-rows.sql
-- Never run with production credentials.
BEGIN;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
DO $guard$
BEGIN
 IF current_setting('server_version_num')::integer < 180000
    OR current_database() <> 'sql_tutorials'
    OR pg_is_in_recovery() THEN
   RAISE EXCEPTION 'Requires isolated writable sql_tutorials database on PostgreSQL 18+';
 END IF;
END
$guard$;
CREATE TEMP TABLE lab043_customers (
 customer_id integer PRIMARY KEY, customer_name text NOT NULL
) ON COMMIT DROP;
-- No FK on staging: deliberately model one unmatched synthetic customer ID.
CREATE TEMP TABLE lab043_orders (
 order_id integer PRIMARY KEY,
 customer_id integer NOT NULL,
 amount numeric(10,2) NOT NULL CHECK (amount >= 0)
) ON COMMIT DROP;
INSERT INTO lab043_customers VALUES (1,'Ada'),(2,'Ben'),(3,'Cy');
INSERT INTO lab043_orders VALUES (101,1,20.00),(102,1,30.00),(103,2,15.00),(104,99,9.00);

-- 4 rows; order 104 has NULL customer_name.
SELECT o.order_id, c.customer_name, o.amount
FROM lab043_orders o LEFT JOIN lab043_customers c
 ON c.customer_id=o.customer_id
ORDER BY o.order_id;

-- Missing right-side key: one row 104,99,9.00.
SELECT o.order_id,o.customer_id,o.amount
FROM lab043_orders o LEFT JOIN lab043_customers c
 ON c.customer_id=o.customer_id
WHERE c.customer_id IS NULL ORDER BY o.order_id;

-- ON predicate preserves four orders; only orders 101/102 show Ada.
SELECT o.order_id,c.customer_name
FROM lab043_orders o LEFT JOIN lab043_customers c
 ON c.customer_id=o.customer_id AND c.customer_name='Ada'
ORDER BY o.order_id;

-- WHERE predicate returns only orders 101/102.
SELECT o.order_id,c.customer_name
FROM lab043_orders o LEFT JOIN lab043_customers c
 ON c.customer_id=o.customer_id
WHERE c.customer_name='Ada' ORDER BY o.order_id;

-- Swap preserved side: four rows; Cy appears once with NULL order.
SELECT c.customer_id,c.customer_name,o.order_id
FROM lab043_customers c LEFT JOIN lab043_orders o
 ON o.customer_id=c.customer_id
ORDER BY c.customer_id,o.order_id;

DO $verify$
DECLARE
 source_count bigint; left_count bigint; matched_count bigint; missing_count bigint;
 source_amount numeric; left_amount numeric; matched_amount numeric; missing_amount numeric;
 on_count bigint; on_ada_count bigint; where_count bigint;
 customer_left_count bigint; no_order_customers bigint;
BEGIN
 SELECT count(*),sum(amount) INTO source_count,source_amount FROM lab043_orders;
 SELECT count(*),sum(o.amount) INTO left_count,left_amount
 FROM lab043_orders o LEFT JOIN lab043_customers c ON c.customer_id=o.customer_id;
 SELECT count(*),sum(o.amount) INTO matched_count,matched_amount
 FROM lab043_orders o JOIN lab043_customers c ON c.customer_id=o.customer_id;
 SELECT count(*),sum(o.amount) INTO missing_count,missing_amount
 FROM lab043_orders o LEFT JOIN lab043_customers c ON c.customer_id=o.customer_id
 WHERE c.customer_id IS NULL;
 SELECT count(*),count(c.customer_id) INTO on_count,on_ada_count
 FROM lab043_orders o LEFT JOIN lab043_customers c
 ON c.customer_id=o.customer_id AND c.customer_name='Ada';
 SELECT count(*) INTO where_count
 FROM lab043_orders o LEFT JOIN lab043_customers c ON c.customer_id=o.customer_id
 WHERE c.customer_name='Ada';
 SELECT count(*),count(*) FILTER (WHERE o.order_id IS NULL)
 INTO customer_left_count,no_order_customers
 FROM lab043_customers c LEFT JOIN lab043_orders o ON o.customer_id=c.customer_id;
 IF (source_count,left_count,matched_count,missing_count,source_amount,left_amount,matched_amount,missing_amount,on_count,on_ada_count,where_count,customer_left_count,no_order_customers)
 IS DISTINCT FROM
 (4::bigint,4::bigint,3::bigint,1::bigint,74.00::numeric,74.00::numeric,65.00::numeric,9.00::numeric,4::bigint,2::bigint,2::bigint,4::bigint,1::bigint)
 THEN RAISE EXCEPTION 'Chapter 043 expected-result assertion failed'; END IF;
 IF source_count <> matched_count + missing_count
    OR source_amount <> matched_amount + missing_amount THEN
   RAISE EXCEPTION 'Chapter 043 reconciliation failed';
 END IF;
 RAISE NOTICE 'PASS: source 4/74.00; left 4/74.00; matched 3/65.00; missing 1/9.00; ON 4; WHERE 2; customer-left 4';
END
$verify$;
ROLLBACK;
-- Expected final tag: ROLLBACK; no persistent objects.
