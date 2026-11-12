-- Chapter 100: Lab 10, baseline, tune and remeasure a slow query.
-- PostgreSQL 18 only. Synthetic inline CTEs; no persistent objects.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/100-lab-10-baseline-tune-remeasure.sql
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
 IF current_database() <> 'sql_tutorials' THEN
  RAISE EXCEPTION 'Isolated sql_tutorials database required; found %', current_database();
 END IF;
 IF current_setting('server_version_num')::integer / 10000 <> 18 THEN
  RAISE EXCEPTION 'PostgreSQL 18 required; found %', current_setting('server_version');
 END IF;
END
$guard$;

-- Baseline estimated plan. No physical index exists in this fixture.
EXPLAIN (COSTS ON)
WITH orders(order_id,tenant_id,status,created_at,amount) AS (
 VALUES
 (101,10,'PAID',timestamp '2026-11-01 00:00:00',10.00::numeric),
 (102,10,'PAID',timestamp '2026-11-01 09:00:00',20.00::numeric),
 (103,10,'PAID',timestamp '2026-11-01 23:59:59.999',30.00::numeric),
 (104,10,'PAID',timestamp '2026-11-01 12:30:00',40.00::numeric),
 (105,10,'PENDING',timestamp '2026-11-01 10:00:00',50.00::numeric),
 (106,10,'PAID',timestamp '2026-10-31 23:59:59.999',60.00::numeric),
 (107,10,'PAID',timestamp '2026-11-02 00:00:00',70.00::numeric),
 (108,20,'PAID',timestamp '2026-11-01 08:00:00',80.00::numeric),
 (109,20,'PENDING',timestamp '2026-11-01 11:00:00',90.00::numeric),
 (110,10,'FAILED',timestamp '2026-11-01 16:00:00',100.00::numeric),
 (111,20,'PAID',timestamp '2026-11-02 14:00:00',110.00::numeric),
 (112,10,'PAID',timestamp '2026-11-03 14:00:00',120.00::numeric)
)
SELECT count(*) AS paid_orders,coalesce(sum(amount),0)::numeric(12,2) AS paid_revenue
FROM orders WHERE tenant_id=10 AND status='PAID'
 AND created_at::date=DATE '2026-11-01';

-- Candidate estimated plan; no measured speedup is implied.
EXPLAIN (COSTS ON)
WITH orders(order_id,tenant_id,status,created_at,amount) AS (
 VALUES
 (101,10,'PAID',timestamp '2026-11-01 00:00:00',10.00::numeric),
 (102,10,'PAID',timestamp '2026-11-01 09:00:00',20.00::numeric),
 (103,10,'PAID',timestamp '2026-11-01 23:59:59.999',30.00::numeric),
 (104,10,'PAID',timestamp '2026-11-01 12:30:00',40.00::numeric),
 (105,10,'PENDING',timestamp '2026-11-01 10:00:00',50.00::numeric),
 (106,10,'PAID',timestamp '2026-10-31 23:59:59.999',60.00::numeric),
 (107,10,'PAID',timestamp '2026-11-02 00:00:00',70.00::numeric),
 (108,20,'PAID',timestamp '2026-11-01 08:00:00',80.00::numeric),
 (109,20,'PENDING',timestamp '2026-11-01 11:00:00',90.00::numeric),
 (110,10,'FAILED',timestamp '2026-11-01 16:00:00',100.00::numeric),
 (111,20,'PAID',timestamp '2026-11-02 14:00:00',110.00::numeric),
 (112,10,'PAID',timestamp '2026-11-03 14:00:00',120.00::numeric)
)
SELECT count(*) AS paid_orders,coalesce(sum(amount),0)::numeric(12,2) AS paid_revenue
FROM orders WHERE tenant_id=10 AND status='PAID'
 AND created_at>=timestamp '2026-11-01 00:00:00'
 AND created_at<timestamp '2026-11-02 00:00:00';

-- Show report and validate row-level multiset equivalence plus expected totals.
DO $assert$
DECLARE differences bigint; all_orders bigint; paid_orders bigint; paid_revenue numeric;
BEGIN
 WITH orders(order_id,tenant_id,status,created_at,amount) AS (
  VALUES
  (101,10,'PAID',timestamp '2026-11-01 00:00:00',10.00::numeric),
  (102,10,'PAID',timestamp '2026-11-01 09:00:00',20.00::numeric),
  (103,10,'PAID',timestamp '2026-11-01 23:59:59.999',30.00::numeric),
  (104,10,'PAID',timestamp '2026-11-01 12:30:00',40.00::numeric),
  (105,10,'PENDING',timestamp '2026-11-01 10:00:00',50.00::numeric),
  (106,10,'PAID',timestamp '2026-10-31 23:59:59.999',60.00::numeric),
  (107,10,'PAID',timestamp '2026-11-02 00:00:00',70.00::numeric),
  (108,20,'PAID',timestamp '2026-11-01 08:00:00',80.00::numeric),
  (109,20,'PENDING',timestamp '2026-11-01 11:00:00',90.00::numeric),
  (110,10,'FAILED',timestamp '2026-11-01 16:00:00',100.00::numeric),
  (111,20,'PAID',timestamp '2026-11-02 14:00:00',110.00::numeric),
  (112,10,'PAID',timestamp '2026-11-03 14:00:00',120.00::numeric)
 ), baseline AS (
  SELECT order_id,amount FROM orders WHERE tenant_id=10 AND status='PAID'
   AND created_at::date=DATE '2026-11-01'
 ), candidate AS (
  SELECT order_id,amount FROM orders WHERE tenant_id=10 AND status='PAID'
   AND created_at>=timestamp '2026-11-01 00:00:00'
   AND created_at<timestamp '2026-11-02 00:00:00'
 ), differences AS (
  (SELECT * FROM baseline EXCEPT ALL SELECT * FROM candidate)
  UNION ALL
  (SELECT * FROM candidate EXCEPT ALL SELECT * FROM baseline)
 ), expected(order_id,amount) AS (
  VALUES (101,10.00::numeric),(102,20.00::numeric),
         (103,30.00::numeric),(104,40.00::numeric)
 ), expectation_diffs AS (
  (SELECT * FROM candidate EXCEPT ALL SELECT * FROM expected)
  UNION ALL
  (SELECT * FROM expected EXCEPT ALL SELECT * FROM candidate)
 )
 SELECT (SELECT count(*) FROM differences)+(SELECT count(*) FROM expectation_diffs),
        (SELECT count(*) FROM orders),
        (SELECT count(*) FROM candidate),
        (SELECT coalesce(sum(amount),0) FROM candidate)
 INTO differences,all_orders,paid_orders,paid_revenue;
 IF differences<>0 OR all_orders<>12 OR paid_orders<>4 OR paid_revenue<>100.00 THEN
  RAISE EXCEPTION '100 failed: diffs %, all %, paid %, revenue %',
   differences,all_orders,paid_orders,paid_revenue;
 END IF;
 RAISE NOTICE '100 assertions passed: 12 orders, 4 paid, 100.00 revenue, zero differences';
END
$assert$;

-- The fixture is inline and read-only; rollback documents the safety boundary.
ROLLBACK;
