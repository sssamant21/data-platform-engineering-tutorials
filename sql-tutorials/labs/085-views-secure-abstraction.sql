-- Chapter 085 — Views and secure abstraction
-- Isolated PostgreSQL 18 database sql_tutorials ONLY; synthetic inline records.
-- Read-only simulation of a reporting-view contract; NO CREATE VIEW, DDL or persistent writes.
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

SELECT 1 / CASE WHEN current_database() = 'sql_tutorials'
                  AND current_setting('server_version_num')::integer / 10000 = 18
                THEN 1 ELSE 0 END AS environment_guard;

WITH customers(customer_id, customer_name) AS (
 VALUES (1,'Ada'::text),(2,'Ben'::text),(3,'Cy'::text),(4,'Dee'::text)
), orders(order_id, customer_id, status, amount) AS (
 VALUES (101,1,'paid'::text,20.00::numeric(12,2)),
        (102,1,'paid',30.00::numeric(12,2)),
        (103,1,'pending',99.00::numeric(12,2)),
        (104,2,'paid',15.00::numeric(12,2)),
        (105,4,'paid',7.50::numeric(12,2)),
        (106,4,'cancelled',5.00::numeric(12,2))
), paid_by_customer AS (
 SELECT customer_id, COUNT(*)::bigint AS paid_order_count, SUM(amount) AS paid_amount
 FROM orders WHERE status = 'paid' GROUP BY customer_id
), reporting_order_totals AS (
 SELECT c.customer_id, c.customer_name,
        COALESCE(p.paid_order_count,0::bigint) AS paid_order_count,
        COALESCE(p.paid_amount,0::numeric)::numeric(12,2) AS paid_amount
 FROM customers c LEFT JOIN paid_by_customer p USING (customer_id)
)
SELECT * FROM reporting_order_totals ORDER BY customer_id;

-- Exact row-set and reconciliation assertions, including zero-activity customer.
WITH customers(customer_id, customer_name) AS (
 VALUES (1,'Ada'::text),(2,'Ben'::text),(3,'Cy'::text),(4,'Dee'::text)
), orders(order_id, customer_id, status, amount) AS (
 VALUES (101,1,'paid'::text,20.00::numeric(12,2)),
        (102,1,'paid',30.00::numeric(12,2)),
        (103,1,'pending',99.00::numeric(12,2)),
        (104,2,'paid',15.00::numeric(12,2)),
        (105,4,'paid',7.50::numeric(12,2)),
        (106,4,'cancelled',5.00::numeric(12,2))
), paid_by_customer AS (
 SELECT customer_id, COUNT(*)::bigint AS paid_order_count, SUM(amount) AS paid_amount
 FROM orders WHERE status = 'paid' GROUP BY customer_id
), actual AS (
 SELECT c.customer_id, c.customer_name,
        COALESCE(p.paid_order_count,0::bigint) AS paid_order_count,
        COALESCE(p.paid_amount,0::numeric)::numeric(12,2) AS paid_amount
 FROM customers c LEFT JOIN paid_by_customer p USING (customer_id)
), expected(customer_id, customer_name, paid_order_count, paid_amount) AS (
 VALUES (1,'Ada'::text,2::bigint,50.00::numeric(12,2)),
        (2,'Ben'::text,1::bigint,15.00::numeric(12,2)),
        (3,'Cy'::text,0::bigint,0.00::numeric(12,2)),
        (4,'Dee'::text,1::bigint,7.50::numeric(12,2))
), differences AS (
 (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
 UNION ALL
 (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
), checks AS (
 SELECT (SELECT COUNT(*) = 0 FROM differences) AS exact_rows_match,
        (SELECT COUNT(*) = 4 FROM actual) AS four_customers,
        (SELECT SUM(paid_order_count) = 4 FROM actual) AS four_paid_orders,
        (SELECT SUM(paid_amount) = 72.50::numeric FROM actual) AS total_72_50,
        (SELECT COUNT(*) = 4 FROM orders WHERE status = 'paid') AS source_reconciles
)
SELECT *, 1 / CASE WHEN exact_rows_match AND four_customers AND four_paid_orders
                        AND total_72_50 AND source_reconciles
                   THEN 1 ELSE 0 END AS fail_closed_acceptance
FROM checks;
ROLLBACK;
