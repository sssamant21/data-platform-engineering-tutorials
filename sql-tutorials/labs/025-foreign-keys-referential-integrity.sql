-- Chapter 025: Foreign keys and referential integrity
-- ONLY on independently verified disposable PostgreSQL 18 primary sql_tutorials.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/025-foreign-keys-referential-integrity.sql
-- Synthetic records, temporary tables, rollback-only; runtime validation pending.
BEGIN;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
DO $guard$
BEGIN
 IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
    OR current_database() <> 'sql_tutorials' OR pg_is_in_recovery() THEN
   RAISE EXCEPTION 'Requires isolated PostgreSQL 18 primary database sql_tutorials';
 END IF;
END
$guard$;

CREATE TEMP TABLE ch025_customers (
 customer_id integer PRIMARY KEY,
 customer_name text NOT NULL
) ON COMMIT DROP;
CREATE TEMP TABLE ch025_orders (
 order_id integer PRIMARY KEY,
 customer_id integer NOT NULL,
 amount_usd numeric(12,2) NOT NULL,
 CONSTRAINT ch025_orders_customer_fk FOREIGN KEY (customer_id)
   REFERENCES ch025_customers(customer_id) ON DELETE NO ACTION
) ON COMMIT DROP;

INSERT INTO ch025_customers VALUES
 (1,'Fictional Ada'),(2,'Fictional Ben'),(3,'Fictional Cy');
INSERT INTO ch025_orders VALUES
 (101,1,10.00),(102,1,15.00),(103,2,20.00),(104,3,30.00);

SELECT c.customer_id,c.customer_name,COUNT(o.order_id) AS order_count
FROM ch025_customers c LEFT JOIN ch025_orders o USING(customer_id)
GROUP BY c.customer_id,c.customer_name ORDER BY c.customer_id;
-- Expected 1/Fictional Ada/2, 2/Fictional Ben/1, 3/Fictional Cy/1.

SELECT COUNT(*) AS orphan_count FROM ch025_orders o
LEFT JOIN ch025_customers c USING(customer_id)
WHERE c.customer_id IS NULL;
-- Expected: 0

DO $expected_fk_failures$
DECLARE rejected_child boolean := false; rejected_parent boolean := false;
BEGIN
 BEGIN
   INSERT INTO ch025_orders VALUES (105,999,5.00);
 EXCEPTION WHEN foreign_key_violation THEN rejected_child := true;
 END;
 IF NOT rejected_child THEN
   RAISE EXCEPTION 'Expected orphan INSERT to fail with 23503';
 END IF;
 RAISE NOTICE 'Expected invalid child rejected (SQLSTATE 23503)';
 BEGIN
   DELETE FROM ch025_customers WHERE customer_id = 1;
 EXCEPTION WHEN foreign_key_violation THEN rejected_parent := true;
 END;
 IF NOT rejected_parent THEN
   RAISE EXCEPTION 'Expected referenced parent DELETE to fail with 23503';
 END IF;
 RAISE NOTICE 'Expected referenced parent delete rejected (SQLSTATE 23503)';
END
$expected_fk_failures$;

DO $assert$
DECLARE customers_count bigint; orders_count bigint; orphan_count bigint;
        amount_total numeric; ada_orders bigint;
BEGIN
 SELECT COUNT(*) INTO customers_count FROM ch025_customers;
 SELECT COUNT(*),SUM(amount_usd),COUNT(*) FILTER (WHERE customer_id=1)
 INTO orders_count,amount_total,ada_orders FROM ch025_orders;
 SELECT COUNT(*) INTO orphan_count FROM ch025_orders o
 LEFT JOIN ch025_customers c USING(customer_id) WHERE c.customer_id IS NULL;
 IF customers_count <> 3 OR orders_count <> 4 OR orphan_count <> 0
    OR amount_total IS DISTINCT FROM 75.00::numeric OR ada_orders <> 2 THEN
   RAISE EXCEPTION 'Chapter 025 assertions failed';
 END IF;
 RAISE NOTICE 'Chapter 025 synthetic assertions passed';
END
$assert$;
ROLLBACK;
-- Temporary tables removed; no persistent DDL or data changes.
