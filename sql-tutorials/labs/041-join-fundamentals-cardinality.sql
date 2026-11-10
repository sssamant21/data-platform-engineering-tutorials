-- Chapter 041: join fundamentals and relationship cardinality
-- PostgreSQL 18 only; synthetic data; isolated sql_tutorials database.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/041-join-fundamentals-cardinality.sql
-- Never use production credentials or production databases.
BEGIN;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
DO $guard$
BEGIN
 IF current_setting('server_version_num')::int < 180000
    OR current_database() <> 'sql_tutorials'
    OR pg_is_in_recovery() THEN
   RAISE EXCEPTION 'Requires writable isolated sql_tutorials on PostgreSQL 18+';
 END IF;
END
$guard$;
CREATE TEMP TABLE lab041_customers (
 customer_id integer PRIMARY KEY, customer_name text NOT NULL
) ON COMMIT DROP;
CREATE TEMP TABLE lab041_orders (
 order_id integer PRIMARY KEY,
 customer_id integer NOT NULL REFERENCES lab041_customers(customer_id),
 amount numeric(10,2) NOT NULL CHECK (amount >= 0)
) ON COMMIT DROP;
CREATE TEMP TABLE lab041_order_items (
 item_id integer PRIMARY KEY,
 order_id integer NOT NULL REFERENCES lab041_orders(order_id),
 sku text NOT NULL
) ON COMMIT DROP;
INSERT INTO lab041_customers VALUES (1,'Ada'),(2,'Ben'),(3,'Cy');
INSERT INTO lab041_orders VALUES (101,1,20.00),(102,1,30.00),(103,2,15.00);
INSERT INTO lab041_order_items VALUES
 (1,101,'PEN'),(2,101,'BOOK'),(3,102,'PAD'),(4,103,'CASE');

-- Inner join: exactly one customer per order.
SELECT o.order_id, c.customer_name, o.amount
FROM lab041_orders o INNER JOIN lab041_customers c
 ON c.customer_id = o.customer_id ORDER BY o.order_id;
-- Expected: (101,Ada,20.00), (102,Ada,30.00), (103,Ben,15.00)

-- Left join: preserve Cy with NULL order.
SELECT c.customer_name, o.order_id
FROM lab041_customers c LEFT JOIN lab041_orders o
 ON o.customer_id = c.customer_id
ORDER BY c.customer_id, o.order_id;
-- Expected 4 rows: Ada/101, Ada/102, Ben/103, Cy/NULL.

-- One-to-many fan-out: order 101 repeats twice.
SELECT o.order_id, i.sku, o.amount
FROM lab041_orders o JOIN lab041_order_items i
 ON i.order_id = o.order_id ORDER BY o.order_id, i.item_id;
-- Expected 4 rows. Do NOT sum o.amount over this join.

SELECT c.customer_id, c.customer_name, COUNT(o.order_id) AS order_count
FROM lab041_customers c LEFT JOIN lab041_orders o
 ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name ORDER BY c.customer_id;
-- Expected counts: Ada 2, Ben 1, Cy 0.

DO $verify$
DECLARE
 n_customers bigint; n_orders bigint; n_inner bigint; n_left bigint;
 n_items bigint; n_distinct bigint; total numeric(10,2);
BEGIN
 SELECT count(*) INTO n_customers FROM lab041_customers;
 SELECT count(*) INTO n_orders FROM lab041_orders;
 SELECT count(*) INTO n_inner FROM lab041_orders o
  JOIN lab041_customers c ON c.customer_id=o.customer_id;
 SELECT count(*) INTO n_left FROM lab041_customers c
  LEFT JOIN lab041_orders o ON o.customer_id=c.customer_id;
 SELECT count(*) INTO n_items FROM lab041_orders o
  JOIN lab041_order_items i ON i.order_id=o.order_id;
 SELECT count(DISTINCT o.customer_id),sum(o.amount)
  INTO n_distinct,total FROM lab041_orders o;
 IF (n_customers,n_orders,n_inner,n_left,n_items,n_distinct,total)
    IS DISTINCT FROM (3::bigint,3::bigint,3::bigint,4::bigint,4::bigint,2::bigint,65.00::numeric) THEN
  RAISE EXCEPTION 'Join/cardinality reconciliation failed';
 END IF;
 IF (SELECT count(*) FROM lab041_customers c LEFT JOIN lab041_orders o
     ON o.customer_id=c.customer_id
     WHERE c.customer_id=3 AND o.order_id IS NULL) <> 1 THEN
  RAISE EXCEPTION 'Unmatched customer expectation failed';
 END IF;
 RAISE NOTICE 'PASS: 3 customers, 3 orders, 3 inner rows, 4 left rows, 4 item rows, revenue 65.00';
END
$verify$;
ROLLBACK;
-- Expected final psql command tag: ROLLBACK. No persistent tables.
