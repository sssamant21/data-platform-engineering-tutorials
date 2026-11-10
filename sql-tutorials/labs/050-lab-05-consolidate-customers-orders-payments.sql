-- Chapter 050: synthetic customers/orders/payments consolidation.
-- PostgreSQL 18, disposable database sql_tutorials ONLY. Predicted assertions, NOT runtime evidence.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '3s';
SET LOCAL idle_in_transaction_session_timeout = '60s';
DO $guard$
BEGIN
  IF current_database() <> 'sql_tutorials' THEN
    RAISE EXCEPTION 'Lab 050 requires disposable database sql_tutorials';
  END IF;
  IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999 THEN
    RAISE EXCEPTION 'Lab 050 requires PostgreSQL 18';
  END IF;
  IF pg_is_in_recovery() THEN RAISE EXCEPTION 'Lab 050 refuses standby'; END IF;
END $guard$;

CREATE TEMP TABLE lab050_customers (
 customer_id integer PRIMARY KEY, customer_name text NOT NULL
) ON COMMIT DROP;
CREATE TEMP TABLE lab050_orders (
 order_id integer PRIMARY KEY, customer_id integer, order_amount numeric(12,2) NOT NULL CHECK (order_amount >= 0)
) ON COMMIT DROP;
CREATE TEMP TABLE lab050_payments (
 payment_id integer PRIMARY KEY, order_id integer, payment_amount numeric(12,2) NOT NULL CHECK (payment_amount >= 0)
) ON COMMIT DROP;

INSERT INTO lab050_customers VALUES (1,'Avery'),(2,'Blair'),(3,'Casey');
INSERT INTO lab050_orders VALUES (101,1,40.00),(102,1,30.00),(103,2,20.00),(104,3,10.00),(105,99,15.00);
INSERT INTO lab050_payments VALUES (1,101,10.00),(2,101,30.00),(3,102,30.00),(4,103,15.00),(5,105,15.00);

CREATE TEMP VIEW lab050_report AS
WITH payment_summary AS (
 SELECT order_id,COUNT(*) AS payment_count,SUM(payment_amount) AS paid_amount
 FROM lab050_payments GROUP BY order_id
)
SELECT o.order_id,o.customer_id,c.customer_name,o.order_amount,
       COALESCE(p.payment_count,0) AS payment_count,
       COALESCE(p.paid_amount,0::numeric) AS paid_amount,
       o.order_amount-COALESCE(p.paid_amount,0::numeric) AS balance_due,
       CASE WHEN c.customer_id IS NULL THEN 'MISSING_CUSTOMER'
            ELSE 'MATCHED_CUSTOMER' END AS customer_status
FROM lab050_orders o
LEFT JOIN lab050_customers c ON c.customer_id=o.customer_id
LEFT JOIN payment_summary p ON p.order_id=o.order_id;

-- Review order-grain report and data-quality exceptions.
SELECT * FROM lab050_report ORDER BY order_id;
SELECT o.order_id,o.customer_id FROM lab050_orders o
WHERE NOT EXISTS (SELECT 1 FROM lab050_customers c WHERE c.customer_id=o.customer_id)
ORDER BY o.order_id;
SELECT p.payment_id FROM lab050_payments p
WHERE NOT EXISTS (SELECT 1 FROM lab050_orders o WHERE o.order_id=p.order_id)
ORDER BY p.payment_id;

DO $assert$
DECLARE
 n_customers integer; n_orders integer; n_payments integer;
 source_order_total numeric; source_paid_total numeric;
 raw_rows integer; raw_wrong_total numeric;
 report_rows integer; report_distinct integer;
 report_order_total numeric; report_paid_total numeric; report_due_total numeric;
 n_no_payment integer; n_partial integer; n_missing_customer integer;
 n_orphan_payments integer; n_matched_customer integer; n_with_payment integer;
BEGIN
 SELECT count(*) INTO n_customers FROM lab050_customers;
 SELECT count(*),sum(order_amount) INTO n_orders,source_order_total FROM lab050_orders;
 SELECT count(*),sum(payment_amount) INTO n_payments,source_paid_total FROM lab050_payments;
 SELECT count(*),sum(o.order_amount) INTO raw_rows,raw_wrong_total
 FROM lab050_orders o LEFT JOIN lab050_payments p ON p.order_id=o.order_id;
 SELECT count(*),count(DISTINCT order_id),sum(order_amount),sum(paid_amount),sum(balance_due),
        count(*) FILTER (WHERE payment_count=0),
        count(*) FILTER (WHERE paid_amount>0 AND balance_due>0),
        count(*) FILTER (WHERE customer_status='MISSING_CUSTOMER'),
        count(*) FILTER (WHERE customer_status='MATCHED_CUSTOMER'),
        count(*) FILTER (WHERE payment_count>0)
 INTO report_rows,report_distinct,report_order_total,report_paid_total,report_due_total,
      n_no_payment,n_partial,n_missing_customer,n_matched_customer,n_with_payment
 FROM lab050_report;
 SELECT count(*) INTO n_orphan_payments FROM lab050_payments p
 WHERE NOT EXISTS (SELECT 1 FROM lab050_orders o WHERE o.order_id=p.order_id);
 IF (n_customers,n_orders,n_payments,source_order_total,source_paid_total,
     raw_rows,raw_wrong_total,report_rows,report_distinct,report_order_total,
     report_paid_total,report_due_total,n_no_payment,n_partial,n_missing_customer,
     n_orphan_payments,n_matched_customer,n_with_payment)
 IS DISTINCT FROM
    (3,5,5,115.00::numeric,100.00::numeric,
     6,155.00::numeric,5,5,115.00::numeric,
     100.00::numeric,15.00::numeric,1,1,1,0,4,4)
 THEN
   RAISE EXCEPTION 'Lab 050 reconciliation failed; inspect source/report row counts, amounts, and key coverage';
 END IF;
 RAISE NOTICE 'PASS expected lab050: customers=3 orders=5 payments=5 report=5 order_total=115.00 paid=100.00 due=15.00 missing_customer=1 no_payment=1';
END $assert$;
ROLLBACK;
