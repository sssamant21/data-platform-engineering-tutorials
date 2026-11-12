-- Chapter 107: synthetic data-quality and reconciliation model.
-- PostgreSQL 18 only; disposable database sql_tutorials; read-only.
-- A passing assertion means the EXPECTED quality-gate failure was detected.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
 IF current_database() <> 'sql_tutorials' THEN
  RAISE EXCEPTION 'Disposable database sql_tutorials required; got %', current_database();
 END IF;
 IF current_setting('server_version_num')::integer / 10000 <> 18 THEN
  RAISE EXCEPTION 'PostgreSQL 18 required; got %', current_setting('server_version');
 END IF;
END
$guard$;

-- Candidate feed: six rows, duplicate 103, two invalid, one orphan.
WITH customers(customer_id) AS (VALUES (1),(2),(3)),
candidate_orders(order_id,customer_id,amount,status) AS (
 VALUES (101,1,40.00::numeric,'paid'::text),
        (102,2,30.00,'paid'),
        (103,3,20.00,'pending'),
        (103,3,20.00,'pending'),
        (104,NULL::integer,-10.00,'paid'),
        (105,99,10.00,'paid')
),
duplicates AS (
 SELECT order_id FROM candidate_orders GROUP BY order_id HAVING count(*) > 1
)
SELECT
 (SELECT count(*) FROM candidate_orders) AS candidate_rows,
 (SELECT count(*) FROM duplicates) AS duplicate_key_groups,
 (SELECT count(*) FROM candidate_orders
   WHERE order_id IS NULL OR customer_id IS NULL OR amount IS NULL
      OR amount < 0 OR status IS NULL OR status NOT IN ('paid','pending')) AS invalid_rows,
 (SELECT count(*) FROM candidate_orders o
   WHERE customer_id IS NOT NULL AND NOT EXISTS
      (SELECT 1 FROM customers c WHERE c.customer_id=o.customer_id)) AS orphan_rows;

-- Snapshot totals are equal but row-level values are not.
WITH source_orders(order_id,amount) AS (
 VALUES (101,40.00::numeric),(102,30.00),(103,20.00),(104,10.00)
), target_orders(order_id,amount) AS (
 VALUES (101,40.00::numeric),(102,30.00),(103,25.00),(104,5.00)
)
SELECT 'source' AS side,count(*) AS rows,sum(amount) AS total FROM source_orders
UNION ALL
SELECT 'target',count(*),sum(amount) FROM target_orders
ORDER BY side;

-- Fail closed if the modeled metrics differ from their exact expected values.
DO $assert$
DECLARE missing_count integer; extra_count integer;
BEGIN
 WITH customers(customer_id) AS (VALUES (1),(2),(3)),
 candidate_orders(order_id,customer_id,amount,status) AS (
  VALUES (101,1,40.00::numeric,'paid'::text),
         (102,2,30.00,'paid'),
         (103,3,20.00,'pending'),
         (103,3,20.00,'pending'),
         (104,NULL::integer,-10.00,'paid'),
         (105,99,10.00,'paid')
 ),
 source_orders(order_id,amount) AS (
  VALUES (101,40.00::numeric),(102,30.00),(103,20.00),(104,10.00)
 ), target_orders(order_id,amount) AS (
  VALUES (101,40.00::numeric),(102,30.00),(103,25.00),(104,5.00)
 ),
 duplicates AS (
  SELECT order_id FROM candidate_orders GROUP BY order_id HAVING count(*) > 1
 ),
 source_only AS (SELECT * FROM source_orders EXCEPT ALL SELECT * FROM target_orders),
 target_only AS (SELECT * FROM target_orders EXCEPT ALL SELECT * FROM source_orders),
 actual(metric,n) AS (
  SELECT 'candidate_rows',count(*)::bigint FROM candidate_orders
  UNION ALL SELECT 'duplicate_groups',count(*)::bigint FROM duplicates
  UNION ALL SELECT 'invalid_rows',count(*)::bigint FROM candidate_orders
    WHERE order_id IS NULL OR customer_id IS NULL OR amount IS NULL
       OR amount < 0 OR status IS NULL OR status NOT IN ('paid','pending')
  UNION ALL SELECT 'orphan_rows',count(*)::bigint FROM candidate_orders o
    WHERE customer_id IS NOT NULL AND NOT EXISTS
      (SELECT 1 FROM customers c WHERE c.customer_id=o.customer_id)
  UNION ALL SELECT 'source_rows',count(*)::bigint FROM source_orders
  UNION ALL SELECT 'target_rows',count(*)::bigint FROM target_orders
  UNION ALL SELECT 'source_cents',sum(amount*100)::bigint FROM source_orders
  UNION ALL SELECT 'target_cents',sum(amount*100)::bigint FROM target_orders
  UNION ALL SELECT 'source_only',count(*)::bigint FROM source_only
  UNION ALL SELECT 'target_only',count(*)::bigint FROM target_only
  UNION ALL SELECT 'promotion_approved',0::bigint
 ),
 expected(metric,n) AS (
  VALUES ('candidate_rows',6::bigint),('duplicate_groups',1::bigint),
   ('invalid_rows',2::bigint),('orphan_rows',1::bigint),
   ('source_rows',4::bigint),('target_rows',4::bigint),
   ('source_cents',10000::bigint),('target_cents',10000::bigint),
   ('source_only',2::bigint),('target_only',2::bigint),
   ('promotion_approved',0::bigint)
 ),
 missing_rows AS (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual),
 extra_rows AS (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
 SELECT (SELECT count(*) FROM missing_rows),(SELECT count(*) FROM extra_rows)
 INTO missing_count,extra_count;
 IF missing_count <> 0 OR extra_count <> 0 THEN
  RAISE EXCEPTION '107 assertion mismatch: missing %, extra %',missing_count,extra_count;
 END IF;
 RAISE NOTICE '107 expected quality-gate FAILURE detected: 6 candidate, 1 duplicate group, 2 invalid, 1 orphan; equal 4-row/100.00 snapshots but 2+2 row differences; promotion blocked';
END
$assert$;
ROLLBACK;
