-- Chapter 048: EXISTS / NOT EXISTS; PostgreSQL 18; disposable database ONLY.
-- Predicted assertions; not evidence of runtime execution.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '3s';
SET LOCAL idle_in_transaction_session_timeout = '60s';
DO $guard$
BEGIN
 IF current_database() <> 'sql_tutorials' THEN
   RAISE EXCEPTION 'Refusing lab outside disposable sql_tutorials database';
 END IF;
 IF current_setting('server_version_num')::integer < 180000
    OR current_setting('server_version_num')::integer >= 190000 THEN
   RAISE EXCEPTION 'PostgreSQL 18 required';
 END IF;
 IF pg_is_in_recovery() THEN
   RAISE EXCEPTION 'Refusing lab on standby';
 END IF;
END $guard$;
CREATE TEMP TABLE lab048_customers (
 customer_id integer PRIMARY KEY,
 customer_name text NOT NULL
) ON COMMIT DROP;
CREATE TEMP TABLE lab048_orders (
 order_id integer PRIMARY KEY,
 customer_id integer,
 status text NOT NULL
) ON COMMIT DROP;
INSERT INTO lab048_customers VALUES
 (1,'Ana'),(2,'Ben'),(3,'Cleo'),(4,'Dev');
INSERT INTO lab048_orders VALUES
 (101,1,'paid'),(102,1,'pending'),(103,2,'paid'),(104,NULL,'pending'),(105,4,'pending');
-- Positive semi-join: Ana, Ben, Dev (3 rows)
SELECT c.customer_id,c.customer_name
FROM lab048_customers c
WHERE EXISTS (SELECT 1 FROM lab048_orders o WHERE o.customer_id=c.customer_id)
ORDER BY c.customer_id;
-- Anti-join: Cleo (1 row)
SELECT c.customer_id,c.customer_name
FROM lab048_customers c
WHERE NOT EXISTS (SELECT 1 FROM lab048_orders o WHERE o.customer_id=c.customer_id)
ORDER BY c.customer_id;
-- Intentionally unsafe NOT IN with NULL yields zero rows.
SELECT c.customer_id FROM lab048_customers c
WHERE c.customer_id NOT IN (SELECT o.customer_id FROM lab048_orders o);
-- Reconcile source rows and matches, with fail-closed assertions.
DO $assert$
DECLARE
 n_customers integer;
 n_orders integer;
 n_has integer;
 n_missing integer;
 n_matched_orders integer;
 n_null_keys integer;
 n_not_in integer;
 n_paid integer;
BEGIN
 SELECT count(*) INTO n_customers FROM lab048_customers;
 SELECT count(*) INTO n_orders FROM lab048_orders;
 SELECT count(*) INTO n_has FROM lab048_customers c
 WHERE EXISTS (SELECT 1 FROM lab048_orders o WHERE o.customer_id=c.customer_id);
 SELECT count(*) INTO n_missing FROM lab048_customers c
 WHERE NOT EXISTS (SELECT 1 FROM lab048_orders o WHERE o.customer_id=c.customer_id);
 SELECT count(*) INTO n_matched_orders FROM lab048_orders o
 JOIN lab048_customers c ON c.customer_id=o.customer_id;
 SELECT count(*) INTO n_null_keys FROM lab048_orders WHERE customer_id IS NULL;
 SELECT count(*) INTO n_not_in FROM lab048_customers c
 WHERE c.customer_id NOT IN (SELECT o.customer_id FROM lab048_orders o);
 SELECT count(*) INTO n_paid FROM lab048_customers c
 WHERE EXISTS (SELECT 1 FROM lab048_orders o
               WHERE o.customer_id=c.customer_id AND o.status='paid');
 IF (n_customers,n_orders,n_has,n_missing,n_matched_orders,n_null_keys,n_not_in,n_paid)
    IS DISTINCT FROM (4,5,3,1,4,1,0,2) THEN
  RAISE EXCEPTION 'Lab 048 mismatch: customers %, orders %, exists %, anti %, matched %, null %, not_in %, paid %',
   n_customers,n_orders,n_has,n_missing,n_matched_orders,n_null_keys,n_not_in,n_paid;
 END IF;
 RAISE NOTICE 'PASS lab048: customers=4 orders=5 exists=3 anti=1 matched_orders=4 null_keys=1 not_in=0 paid_customers=2';
END $assert$;
ROLLBACK;
