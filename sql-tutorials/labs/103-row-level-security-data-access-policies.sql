-- Chapter 103: synthetic tenant-isolation policy model, NOT real PostgreSQL RLS testing.
-- PostgreSQL 18, disposable sql_tutorials database, no production credentials.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
  IF current_database() <> 'sql_tutorials' THEN
    RAISE EXCEPTION 'Expected disposable sql_tutorials database, got %', current_database();
  END IF;
  IF current_setting('server_version_num')::integer / 10000 <> 18 THEN
    RAISE EXCEPTION 'PostgreSQL 18 required, got %', current_setting('server_version');
  END IF;
END
$guard$;

-- Inline data only. The tenant predicate models a policy; no real policy is created.
WITH orders(order_id, tenant_id, amount) AS (
  VALUES (101,10,20.00::numeric(10,2)),
         (102,10,30.00::numeric(10,2)),
         (103,20,25.00::numeric(10,2)),
         (104,10,40.00::numeric(10,2)),
         (105,20,35.00::numeric(10,2))
), contexts(context_name, tenant_id) AS (
  VALUES ('tenant_10',10),('tenant_20',20),('missing',NULL::integer)
)
SELECT c.context_name, count(o.order_id) AS visible_rows,
       coalesce(sum(o.amount),0)::numeric(10,2) AS visible_amount
FROM contexts c LEFT JOIN orders o ON o.tenant_id = c.tenant_id
GROUP BY c.context_name ORDER BY c.context_name;

-- Bidirectional EXCEPT ALL assertion detects missing, extra, and duplicate rows.
DO $assert$
DECLARE missing_count integer; extra_count integer;
        total_orders integer;
        missing_rows integer; extra_rows integer;
BEGIN
  WITH orders(order_id,tenant_id,amount) AS (
    VALUES (101,10,20.00::numeric(10,2)),
           (102,10,30.00::numeric(10,2)),
           (103,20,25.00::numeric(10,2)),
           (104,10,40.00::numeric(10,2)),
           (105,20,35.00::numeric(10,2))
  ), contexts(context_name,tenant_id) AS (
    VALUES ('tenant_10',10),('tenant_20',20),('missing',NULL::integer)
  ), actual AS (
    SELECT c.context_name, count(o.order_id)::bigint AS visible_rows,
           coalesce(sum(o.amount),0)::numeric(10,2) AS visible_amount
    FROM contexts c LEFT JOIN orders o ON o.tenant_id = c.tenant_id
    GROUP BY c.context_name
  ), actual_rows AS (
    SELECT c.context_name,o.order_id,o.tenant_id,o.amount
    FROM contexts c JOIN orders o ON o.tenant_id = c.tenant_id
  ), expected_rows(context_name,order_id,tenant_id,amount) AS (
    VALUES ('tenant_10',101,10,20.00::numeric(10,2)),
           ('tenant_10',102,10,30.00::numeric(10,2)),
           ('tenant_10',104,10,40.00::numeric(10,2)),
           ('tenant_20',103,20,25.00::numeric(10,2)),
           ('tenant_20',105,20,35.00::numeric(10,2))
  ), missing_detail AS (
    SELECT * FROM expected_rows EXCEPT ALL SELECT * FROM actual_rows
  ), extra_detail AS (
    SELECT * FROM actual_rows EXCEPT ALL SELECT * FROM expected_rows
  ), expected(context_name,visible_rows,visible_amount) AS (
    VALUES ('tenant_10',3::bigint,90.00::numeric(10,2)),
           ('tenant_20',2::bigint,60.00::numeric(10,2)),
           ('missing',0::bigint,0.00::numeric(10,2))
  ), missing AS (
    SELECT * FROM expected EXCEPT ALL SELECT * FROM actual
  ), extra AS (
    SELECT * FROM actual EXCEPT ALL SELECT * FROM expected
  )
  SELECT (SELECT count(*) FROM missing),(SELECT count(*) FROM extra),
         (SELECT count(*) FROM orders),
         (SELECT count(*) FROM missing_detail),(SELECT count(*) FROM extra_detail)
  INTO missing_count,extra_count,total_orders,missing_rows,extra_rows;

  IF missing_count <> 0 OR extra_count <> 0 OR total_orders <> 5 THEN
    RAISE EXCEPTION '103 model mismatch: missing %, extra %, total %',
      missing_count,extra_count,total_orders;
  END IF;
  IF missing_rows <> 0 OR extra_rows <> 0 THEN
    RAISE EXCEPTION '103 exact tenant rows mismatch: missing %, extra %', missing_rows,extra_rows;
  END IF;
  RAISE NOTICE '103 synthetic assertions passed: 5 orders, tenant 10 = 3/90, tenant 20 = 2/60, absent = 0, no aggregate or exact row differences';
END
$assert$;
ROLLBACK;
