-- Chapter 094: Composite indexes and column order
-- PostgreSQL 18; isolated database sql_tutorials; synthetic read-only VALUES.
-- No persistent objects; psql required for ON_ERROR_STOP.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
  IF current_database() <> 'sql_tutorials' THEN
    RAISE EXCEPTION 'Expected isolated sql_tutorials database; got %', current_database();
  END IF;
  IF current_setting('server_version_num')::integer / 10000 <> 18 THEN
    RAISE EXCEPTION 'Expected PostgreSQL 18; got %', current_setting('server_version');
  END IF;
END
$guard$;

-- Estimated plan for VALUES, NOT a composite-index demonstration.
EXPLAIN (FORMAT TEXT, COSTS ON)
SELECT order_id, amount
FROM (VALUES
 (10,101,'paid',TIMESTAMP '2026-11-01 09:00',20.00::numeric),
 (10,102,'pending',TIMESTAMP '2026-11-01 10:00',15.00::numeric),
 (10,103,'paid',TIMESTAMP '2026-11-02 11:00',30.00::numeric),
 (20,104,'paid',TIMESTAMP '2026-11-02 12:00',40.00::numeric),
 (10,105,'paid',TIMESTAMP '2026-11-03 08:00',50.00::numeric),
 (20,106,'failed',TIMESTAMP '2026-11-01 13:00',10.00::numeric)
) AS o(tenant_id,order_id,status,created_at,amount)
WHERE tenant_id = 10 AND status = 'paid'
  AND created_at >= TIMESTAMP '2026-11-01'
  AND created_at < TIMESTAMP '2026-11-03'
ORDER BY created_at DESC, order_id DESC;

-- Expected order: 103 (30.00), 101 (20.00).
WITH orders(tenant_id,order_id,status,created_at,amount) AS (
 VALUES
 (10,101,'paid',TIMESTAMP '2026-11-01 09:00',20.00::numeric),
 (10,102,'pending',TIMESTAMP '2026-11-01 10:00',15.00::numeric),
 (10,103,'paid',TIMESTAMP '2026-11-02 11:00',30.00::numeric),
 (20,104,'paid',TIMESTAMP '2026-11-02 12:00',40.00::numeric),
 (10,105,'paid',TIMESTAMP '2026-11-03 08:00',50.00::numeric),
 (20,106,'failed',TIMESTAMP '2026-11-01 13:00',10.00::numeric)
)
SELECT order_id, amount FROM orders
WHERE tenant_id = 10 AND status = 'paid'
  AND created_at >= TIMESTAMP '2026-11-01'
  AND created_at < TIMESTAMP '2026-11-03'
ORDER BY created_at DESC, order_id DESC;

-- Fail closed on unexpected rows or aggregates (two-way EXCEPT ALL).
DO $assert$
DECLARE discrepancies integer;
BEGIN
 WITH orders(tenant_id,order_id,status,created_at,amount) AS (
  VALUES
  (10,101,'paid',TIMESTAMP '2026-11-01 09:00',20.00::numeric),
  (10,102,'pending',TIMESTAMP '2026-11-01 10:00',15.00::numeric),
  (10,103,'paid',TIMESTAMP '2026-11-02 11:00',30.00::numeric),
  (20,104,'paid',TIMESTAMP '2026-11-02 12:00',40.00::numeric),
  (10,105,'paid',TIMESTAMP '2026-11-03 08:00',50.00::numeric),
  (20,106,'failed',TIMESTAMP '2026-11-01 13:00',10.00::numeric)
 ), actual AS (
  SELECT order_id,amount FROM orders
  WHERE tenant_id = 10 AND status = 'paid'
    AND created_at >= TIMESTAMP '2026-11-01'
    AND created_at < TIMESTAMP '2026-11-03'
 ), expected(order_id,amount) AS (
  VALUES (103,30.00::numeric),(101,20.00::numeric)
 ), differences AS (
  (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
  UNION ALL
  (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
 )
 SELECT COUNT(*) INTO discrepancies FROM differences;
 IF discrepancies <> 0 THEN
  RAISE EXCEPTION '094 row assertion failed: % differences',discrepancies;
 END IF;

 WITH orders(tenant_id,order_id,status,created_at,amount) AS (
  VALUES
  (10,101,'paid',TIMESTAMP '2026-11-01 09:00',20.00::numeric),
  (10,102,'pending',TIMESTAMP '2026-11-01 10:00',15.00::numeric),
  (10,103,'paid',TIMESTAMP '2026-11-02 11:00',30.00::numeric),
  (20,104,'paid',TIMESTAMP '2026-11-02 12:00',40.00::numeric),
  (10,105,'paid',TIMESTAMP '2026-11-03 08:00',50.00::numeric),
  (20,106,'failed',TIMESTAMP '2026-11-01 13:00',10.00::numeric)
 ), actual AS (
  SELECT COUNT(*)::bigint AS all_count,
   COUNT(*) FILTER (WHERE tenant_id=10 AND status='paid')::bigint AS tenant_paid_count,
   SUM(amount) FILTER (WHERE tenant_id=10 AND status='paid') AS tenant_paid_total,
   COUNT(*) FILTER (WHERE tenant_id=10 AND status='paid'
    AND created_at>=TIMESTAMP '2026-11-01'
    AND created_at<TIMESTAMP '2026-11-03')::bigint AS range_count,
   SUM(amount) FILTER (WHERE tenant_id=10 AND status='paid'
    AND created_at>=TIMESTAMP '2026-11-01'
    AND created_at<TIMESTAMP '2026-11-03') AS range_total,
   COUNT(*) FILTER (WHERE tenant_id=20 AND status='paid')::bigint AS other_paid_count,
   SUM(amount) FILTER (WHERE tenant_id=20 AND status='paid') AS other_paid_total
  FROM orders
 ), expected(all_count,tenant_paid_count,tenant_paid_total,range_count,range_total,other_paid_count,other_paid_total) AS (
  VALUES (6::bigint,3::bigint,100.00::numeric,2::bigint,50.00::numeric,1::bigint,40.00::numeric)
 ), differences AS (
  (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
  UNION ALL
  (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
 )
 SELECT COUNT(*) INTO discrepancies FROM differences;
 IF discrepancies <> 0 THEN
  RAISE EXCEPTION '094 aggregate assertion failed: % differences',discrepancies;
 END IF;
 RAISE NOTICE '094 synthetic assertions passed (static expectation; runtime execution required to confirm)';
END
$assert$;
ROLLBACK;
