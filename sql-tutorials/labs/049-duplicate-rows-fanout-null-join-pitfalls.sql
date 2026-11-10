-- Chapter 049: synthetic fan-out / NULL diagnostics. PostgreSQL 18 disposable sql_tutorials ONLY.
-- Expected assertions are predictions, not runtime evidence.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '3s';
SET LOCAL idle_in_transaction_session_timeout = '60s';
DO $guard$
BEGIN
 IF current_database() <> 'sql_tutorials' THEN
  RAISE EXCEPTION 'Lab 049 requires disposable sql_tutorials database';
 END IF;
 IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999 THEN
  RAISE EXCEPTION 'Lab 049 requires PostgreSQL 18';
 END IF;
 IF pg_is_in_recovery() THEN RAISE EXCEPTION 'Lab 049 refuses standby'; END IF;
END $guard$;
CREATE TEMP TABLE lab049_orders (order_id integer PRIMARY KEY, amount numeric(12,2) NOT NULL) ON COMMIT DROP;
CREATE TEMP TABLE lab049_items (item_id integer PRIMARY KEY, order_id integer, item_amount numeric(12,2) NOT NULL) ON COMMIT DROP;
CREATE TEMP TABLE lab049_payments (payment_id integer PRIMARY KEY, order_id integer, payment_amount numeric(12,2) NOT NULL) ON COMMIT DROP;
CREATE TEMP TABLE lab049_staging (row_id integer PRIMARY KEY, external_order_id text) ON COMMIT DROP;
INSERT INTO lab049_orders VALUES (101,40.00),(102,30.00),(103,20.00);
INSERT INTO lab049_items VALUES (1,101,15.00),(2,101,25.00),(3,102,30.00),(4,103,20.00),(5,NULL,7.00);
INSERT INTO lab049_payments VALUES (1,101,10.00),(2,101,30.00),(3,102,30.00),(4,103,20.00);
INSERT INTO lab049_staging VALUES (1,'EXT-A'),(2,'EXT-A'),(3,'EXT-B'),(4,NULL);
-- Observe multiplication; NOT the correct revenue report.
SELECT o.order_id, COUNT(*) AS multiplied_rows
FROM lab049_orders o JOIN lab049_items i USING(order_id)
JOIN lab049_payments p USING(order_id)
GROUP BY o.order_id ORDER BY o.order_id;
-- Correct: aggregate each child to order grain first.
WITH i AS (SELECT order_id,SUM(item_amount) AS item_total FROM lab049_items GROUP BY order_id),
p AS (SELECT order_id,SUM(payment_amount) AS paid_total FROM lab049_payments GROUP BY order_id)
SELECT o.order_id,o.amount,COALESCE(i.item_total,0) AS item_total,
       COALESCE(p.paid_total,0) AS paid_total
FROM lab049_orders o LEFT JOIN i USING(order_id) LEFT JOIN p USING(order_id)
ORDER BY o.order_id;
-- Orphan or NULL-key imported item.
SELECT i.item_id,i.order_id FROM lab049_items i
LEFT JOIN lab049_orders o ON o.order_id=i.order_id
WHERE o.order_id IS NULL ORDER BY i.item_id;
DO $assert$
DECLARE
 n_orders integer; order_total numeric; n_items integer; n_null integer;
 n_payments integer; n_pairs integer; wrong_total numeric;
 n_safe integer; safe_total numeric; item_total numeric; paid_total numeric;
 n_orphans integer; n_dupe_keys integer;
BEGIN
 SELECT count(*),sum(amount) INTO n_orders,order_total FROM lab049_orders;
 SELECT count(*) FILTER (WHERE order_id IS NOT NULL),count(*) FILTER (WHERE order_id IS NULL)
 INTO n_items,n_null FROM lab049_items;
 SELECT count(*) INTO n_payments FROM lab049_payments;
 SELECT count(*),sum(o.amount) INTO n_pairs,wrong_total
 FROM lab049_orders o JOIN lab049_items i USING(order_id)
 JOIN lab049_payments p USING(order_id);
 WITH i AS (SELECT order_id,sum(item_amount) item_total FROM lab049_items GROUP BY order_id),
 p AS (SELECT order_id,sum(payment_amount) paid_total FROM lab049_payments GROUP BY order_id)
 SELECT count(*),sum(o.amount),sum(COALESCE(i.item_total,0)),sum(COALESCE(p.paid_total,0))
 INTO n_safe,safe_total,item_total,paid_total
 FROM lab049_orders o LEFT JOIN i USING(order_id) LEFT JOIN p USING(order_id);
 SELECT count(*) INTO n_orphans FROM lab049_items i
 LEFT JOIN lab049_orders o ON o.order_id=i.order_id WHERE o.order_id IS NULL;
 SELECT count(*) INTO n_dupe_keys FROM
 (SELECT external_order_id FROM lab049_staging WHERE external_order_id IS NOT NULL
 GROUP BY external_order_id HAVING count(*)>1) d;
 IF (n_orders,order_total,n_items,n_null,n_payments,n_pairs,wrong_total,n_safe,
     safe_total,item_total,paid_total,n_orphans,n_dupe_keys)
 IS DISTINCT FROM (3,90.00::numeric,4,1,4,6,210.00::numeric,3,
                   90.00::numeric,90.00::numeric,90.00::numeric,1,1) THEN
  RAISE EXCEPTION 'Lab 049 acceptance mismatch: orders %, total %, items %, null %, payments %, pairs %, wrong %, safe rows %, safe total %, item total %, paid total %, orphans %, duplicates %',
  n_orders,order_total,n_items,n_null,n_payments,n_pairs,wrong_total,n_safe,
  safe_total,item_total,paid_total,n_orphans,n_dupe_keys;
 END IF;
 RAISE NOTICE 'PASS predicted lab049: orders=3 total=90.00 valid_items=4 null_items=1 payments=4 joined_rows=6 wrong_total=210.00 safe_rows=3 safe_total=90.00 orphan_items=1 duplicate_keys=1';
END $assert$;
ROLLBACK;
