-- Chapter 022 — PostgreSQL 18 isolated transactional DDL lab.
-- Synthetic data only. Requires independently verified disposable cluster/database.
-- Invocation: psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/022-create-schema-and-tables-isolated.sql
-- Not runtime validated until executed on PostgreSQL 18 with retained evidence.
-- Never run on production; no CREATE DATABASE or DROP DATABASE commands.
BEGIN;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
  IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
     OR current_database() <> 'sql_tutorials'
     OR pg_is_in_recovery() THEN
    RAISE EXCEPTION 'Requires independently verified disposable PostgreSQL 18 primary database sql_tutorials';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'sql_ch022_demo') THEN
    RAISE EXCEPTION 'Training schema sql_ch022_demo already exists: refusing to modify';
  END IF;
END
$guard$;

CREATE SCHEMA sql_ch022_demo;
CREATE TABLE sql_ch022_demo.customers (
  customer_id integer PRIMARY KEY,
  customer_code varchar(16) NOT NULL UNIQUE,
  display_name varchar(80) NOT NULL
);
CREATE TABLE sql_ch022_demo.orders (
  order_id integer PRIMARY KEY,
  customer_id integer NOT NULL REFERENCES sql_ch022_demo.customers(customer_id),
  order_status varchar(12) NOT NULL,
  total_amount numeric(12,2) NOT NULL CHECK (total_amount >= 0)
);

INSERT INTO sql_ch022_demo.customers(customer_id, customer_code, display_name)
VALUES (1,'C001','Example Customer A'),(2,'C002','Example Customer B');
INSERT INTO sql_ch022_demo.orders(order_id,customer_id,order_status,total_amount)
VALUES (1001,1,'PAID',32.00),(1002,1,'PENDING',15.50);

SELECT (SELECT count(*) FROM sql_ch022_demo.customers) AS customer_count,
       (SELECT count(*) FROM sql_ch022_demo.orders) AS order_count,
       (SELECT sum(total_amount) FROM sql_ch022_demo.orders) AS total_amount;
-- Expected: 2 | 2 | 47.50

SELECT count(*) AS order_foreign_keys
FROM pg_constraint
WHERE conrelid = 'sql_ch022_demo.orders'::regclass AND contype = 'f';
-- Expected: 1

DO $assert$
DECLARE
  n_customers bigint;
  n_orders bigint;
  amount numeric;
  n_fk bigint;
BEGIN
  SELECT count(*) INTO n_customers FROM sql_ch022_demo.customers;
  SELECT count(*), sum(total_amount) INTO n_orders, amount FROM sql_ch022_demo.orders;
  SELECT count(*) INTO n_fk FROM pg_constraint
    WHERE conrelid = 'sql_ch022_demo.orders'::regclass AND contype = 'f';
  IF n_customers <> 2 OR n_orders <> 2 OR amount IS DISTINCT FROM 47.50::numeric
     OR n_fk <> 1 THEN
    RAISE EXCEPTION 'Chapter 022 synthetic assertions failed';
  END IF;
  RAISE NOTICE 'Chapter 022 in-transaction assertions passed';
END
$assert$;

ROLLBACK;

-- Fail closed if the rollback did not remove the training schema.
DO $post$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'sql_ch022_demo') THEN
    RAISE EXCEPTION 'Chapter 022 cleanup assertion failed: schema still exists';
  END IF;
  RAISE NOTICE 'Chapter 022 rollback verified: training schema absent';
END
$post$;
SELECT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname='sql_ch022_demo')
  AS schema_exists_after_rollback;
-- Expected: false
