-- Chapter 046: Multi-table joins and join condition design.
-- Synthetic fixtures; disposable PostgreSQL 18+ database sql_tutorials ONLY.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/046-multi-table-joins-condition-design.sql
BEGIN;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
DO $guard$
BEGIN
 IF current_setting('server_version_num')::integer < 180000
    OR current_database() <> 'sql_tutorials'
    OR pg_is_in_recovery() THEN
   RAISE EXCEPTION 'Requires isolated writable sql_tutorials database on PostgreSQL 18+';
 END IF;
END
$guard$;
CREATE TEMP TABLE lab046_customers (customer_id integer PRIMARY KEY, customer_name text NOT NULL) ON COMMIT DROP;
CREATE TEMP TABLE lab046_orders (order_id integer PRIMARY KEY, customer_id integer NOT NULL) ON COMMIT DROP;
CREATE TEMP TABLE lab046_items (item_id integer PRIMARY KEY, order_id integer NOT NULL REFERENCES lab046_orders(order_id), item_amount numeric(12,2) NOT NULL) ON COMMIT DROP;
CREATE TEMP TABLE lab046_payments (payment_id integer PRIMARY KEY, order_id integer NOT NULL REFERENCES lab046_orders(order_id), payment_amount numeric(12,2) NOT NULL) ON COMMIT DROP;
INSERT INTO lab046_customers VALUES (1,'Ana'),(2,'Ben'),(3,'Cleo');
INSERT INTO lab046_orders VALUES (101,1),(102,1),(103,2),(104,99);
INSERT INTO lab046_items VALUES (1,101,30),(2,101,20),(3,102,15),(4,103,25),(5,104,10);
INSERT INTO lab046_payments VALUES (1,101,40),(2,101,10),(3,102,15),(4,103,25);
-- Item-grain result, 5 rows; unmatched customer on order 104 is retained.
SELECT o.order_id, c.customer_name, i.item_id, i.item_amount
FROM lab046_orders o LEFT JOIN lab046_customers c ON c.customer_id=o.customer_id
JOIN lab046_items i ON i.order_id=o.order_id
ORDER BY o.order_id,i.item_id;
-- Correct order-grain result: 4 rows.
WITH item_totals AS (
 SELECT order_id,SUM(item_amount) AS item_total FROM lab046_items GROUP BY order_id
), payment_totals AS (
 SELECT order_id,SUM(payment_amount) AS paid_total FROM lab046_payments GROUP BY order_id
)
SELECT o.order_id,c.customer_name,COALESCE(i.item_total,0) AS item_total,
       COALESCE(p.paid_total,0) AS paid_total,
       COALESCE(i.item_total,0)-COALESCE(p.paid_total,0) AS balance
FROM lab046_orders o LEFT JOIN lab046_customers c ON c.customer_id=o.customer_id
LEFT JOIN item_totals i ON i.order_id=o.order_id
LEFT JOIN payment_totals p ON p.order_id=o.order_id
ORDER BY o.order_id;
DO $verify$
DECLARE v_orders bigint; v_items bigint; v_item_join bigint; v_report bigint;
        v_item_total numeric; v_paid_total numeric; v_orphans bigint;
        v_bad_balances bigint;
BEGIN
 SELECT COUNT(*) INTO v_orders FROM lab046_orders;
 SELECT COUNT(*) INTO v_items FROM lab046_items;
 SELECT COUNT(*) INTO v_item_join FROM lab046_orders o
 JOIN lab046_items i ON i.order_id=o.order_id;
 WITH item_totals AS (
  SELECT order_id,SUM(item_amount) AS item_total FROM lab046_items GROUP BY order_id
 ), payment_totals AS (
  SELECT order_id,SUM(payment_amount) AS paid_total FROM lab046_payments GROUP BY order_id
 ), report AS (
  SELECT o.order_id,COALESCE(i.item_total,0) AS item_total,COALESCE(p.paid_total,0) AS paid_total
  FROM lab046_orders o LEFT JOIN item_totals i ON i.order_id=o.order_id
  LEFT JOIN payment_totals p ON p.order_id=o.order_id
 )
 SELECT COUNT(*),SUM(item_total),SUM(paid_total),
        COUNT(*) FILTER (WHERE (order_id=104 AND item_total-paid_total<>10)
                               OR (order_id<>104 AND item_total<>paid_total))
 INTO v_report,v_item_total,v_paid_total,v_bad_balances FROM report;
 SELECT COUNT(*) INTO v_orphans FROM lab046_orders o
 LEFT JOIN lab046_customers c ON c.customer_id=o.customer_id
 WHERE c.customer_id IS NULL;
 IF (v_orders,v_items,v_item_join,v_report,v_item_total,v_paid_total,v_orphans,v_bad_balances)
 IS DISTINCT FROM (4::bigint,5::bigint,5::bigint,4::bigint,100::numeric,90::numeric,1::bigint,0::bigint)
 THEN RAISE EXCEPTION 'Chapter 046 reconciliation assertion failed'; END IF;
 RAISE NOTICE 'PASS: orders=4, item_rows=5, joined_item_rows=5, report_rows=4, item_total=100.00, paid_total=90.00, orphan_orders=1';
END
$verify$;
ROLLBACK;
-- Expected: ROLLBACK, no persistent objects.
