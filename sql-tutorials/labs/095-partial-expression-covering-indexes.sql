-- Chapter 095: partial, expression and covering indexes
-- PostgreSQL 18; synthetic VALUES only; NO CREATE INDEX or persistent objects.
-- Run with psql -X -v ON_ERROR_STOP=1 against isolated database sql_tutorials.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
 IF current_database() <> 'sql_tutorials' THEN
  RAISE EXCEPTION 'Expected isolated sql_tutorials database, got %', current_database();
 END IF;
 IF current_setting('server_version_num')::integer / 10000 <> 18 THEN
  RAISE EXCEPTION 'Expected PostgreSQL 18, got %', current_setting('server_version');
 END IF;
END
$guard$;

-- Plain EXPLAIN does NOT execute the SELECT. VALUES has no physical indexes.
EXPLAIN (FORMAT TEXT, COSTS ON)
SELECT order_id, amount
FROM (VALUES
 (101,10,'open',TIMESTAMP '2026-11-01 09:00',20.00::numeric),
 (102,10,'paid',TIMESTAMP '2026-11-01 10:00',30.00::numeric),
 (103,10,'open',TIMESTAMP '2026-11-02 11:00',15.00::numeric),
 (104,20,'open',TIMESTAMP '2026-11-02 12:00',40.00::numeric),
 (105,10,'open',TIMESTAMP '2026-11-03 08:00',25.00::numeric),
 (106,20,'paid',TIMESTAMP '2026-11-03 13:00',10.00::numeric)
) AS o(order_id,tenant_id,status,created_at,amount)
WHERE tenant_id=10 AND status='open'
ORDER BY created_at DESC, order_id DESC;

-- Expected ordered IDs 105, 103, 101.
WITH orders(order_id,tenant_id,status,created_at,amount) AS (
 VALUES
 (101,10,'open',TIMESTAMP '2026-11-01 09:00',20.00::numeric),
 (102,10,'paid',TIMESTAMP '2026-11-01 10:00',30.00::numeric),
 (103,10,'open',TIMESTAMP '2026-11-02 11:00',15.00::numeric),
 (104,20,'open',TIMESTAMP '2026-11-02 12:00',40.00::numeric),
 (105,10,'open',TIMESTAMP '2026-11-03 08:00',25.00::numeric),
 (106,20,'paid',TIMESTAMP '2026-11-03 13:00',10.00::numeric)
)
SELECT order_id, amount FROM orders
WHERE tenant_id=10 AND status='open'
ORDER BY created_at DESC,order_id DESC;

-- Expression index query shape (no physical expression index created).
WITH customers(customer_id,email) AS (
 VALUES (1,'Alice@Example.Test'),(2,'bob@example.test'),(3,'ALICE@example.test')
)
SELECT customer_id FROM customers
WHERE lower(email)=lower('alice@example.test')
ORDER BY customer_id;

-- Assertions: bidirectional EXCEPT ALL detects missing, extra and duplicate rows.
DO $assert$
DECLARE discrepancies bigint;
BEGIN
 WITH orders(order_id,tenant_id,status,created_at,amount) AS (
  VALUES
  (101,10,'open',TIMESTAMP '2026-11-01 09:00',20.00::numeric),
  (102,10,'paid',TIMESTAMP '2026-11-01 10:00',30.00::numeric),
  (103,10,'open',TIMESTAMP '2026-11-02 11:00',15.00::numeric),
  (104,20,'open',TIMESTAMP '2026-11-02 12:00',40.00::numeric),
  (105,10,'open',TIMESTAMP '2026-11-03 08:00',25.00::numeric),
  (106,20,'paid',TIMESTAMP '2026-11-03 13:00',10.00::numeric)
 ), actual AS (
  SELECT order_id,amount FROM orders WHERE tenant_id=10 AND status='open'
 ), expected(order_id,amount) AS (
  VALUES (105,25.00::numeric),(103,15.00::numeric),(101,20.00::numeric)
 ), differences AS (
  (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
  UNION ALL
  (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
 )
 SELECT COUNT(*) INTO discrepancies FROM differences;
 IF discrepancies <> 0 THEN
  RAISE EXCEPTION '095 order multiset mismatch: %', discrepancies;
 END IF;

 WITH orders(order_id,tenant_id,status,created_at,amount) AS (
  VALUES
  (101,10,'open',TIMESTAMP '2026-11-01 09:00',20.00::numeric),
  (102,10,'paid',TIMESTAMP '2026-11-01 10:00',30.00::numeric),
  (103,10,'open',TIMESTAMP '2026-11-02 11:00',15.00::numeric),
  (104,20,'open',TIMESTAMP '2026-11-02 12:00',40.00::numeric),
  (105,10,'open',TIMESTAMP '2026-11-03 08:00',25.00::numeric),
  (106,20,'paid',TIMESTAMP '2026-11-03 13:00',10.00::numeric)
 ), actual AS (
  SELECT COUNT(*)::bigint AS total_count,
   COUNT(*) FILTER (WHERE status='open')::bigint AS open_count,
   SUM(amount) FILTER (WHERE status='open') AS open_amount,
   COUNT(*) FILTER (WHERE tenant_id=10 AND status='open')::bigint AS tenant_open_count,
   SUM(amount) FILTER (WHERE tenant_id=10 AND status='open') AS tenant_open_amount
  FROM orders
 ), expected(total_count,open_count,open_amount,tenant_open_count,tenant_open_amount) AS (
  VALUES (6::bigint,4::bigint,100.00::numeric,3::bigint,60.00::numeric)
 ), differences AS (
  (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
  UNION ALL
  (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
 )
 SELECT COUNT(*) INTO discrepancies FROM differences;
 IF discrepancies <> 0 THEN
  RAISE EXCEPTION '095 aggregate mismatch: %', discrepancies;
 END IF;

 WITH customers(customer_id,email) AS (
  VALUES (1,'Alice@Example.Test'),(2,'bob@example.test'),(3,'ALICE@example.test')
 ), actual AS (
  SELECT customer_id FROM customers WHERE lower(email)=lower('alice@example.test')
 ), expected(customer_id) AS (VALUES (1),(3)),
 differences AS (
  (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
  UNION ALL
  (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
 )
 SELECT COUNT(*) INTO discrepancies FROM differences;
 IF discrepancies <> 0 THEN
  RAISE EXCEPTION '095 email-expression mismatch: %', discrepancies;
 END IF;
 RAISE NOTICE '095 synthetic assertions passed in this execution';
END
$assert$;
ROLLBACK;
