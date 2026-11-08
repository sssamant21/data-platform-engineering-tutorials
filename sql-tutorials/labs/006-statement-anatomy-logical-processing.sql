-- Chapter 006 — Anatomy of a SQL statement and logical query processing
-- PostgreSQL 18 isolated sql_tutorials lab only. Read-only; no persistent changes.
-- Run from sql-tutorials/: psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f labs/006-statement-anatomy-logical-processing.sql
BEGIN READ ONLY;

-- Fail fast if not on the expected lab server and database.
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer / 10000 = 18
  AND current_database() = 'sql_tutorials' THEN 1 ELSE 0 END AS environment_assertion;

-- A. Six fictional source rows.
WITH orders(order_id, customer_id, amount_usd, status) AS (
 VALUES (5001,101,40.00::numeric(10,2),'paid'),
        (5002,101,25.00::numeric(10,2),'paid'),
        (5003,102,70.00::numeric(10,2),'pending'),
        (5004,102,90.00::numeric(10,2),'paid'),
        (5005,103,15.00::numeric(10,2),'paid'),
        (5006,103,10.00::numeric(10,2),'paid')
)
SELECT order_id, customer_id, amount_usd, status
FROM orders ORDER BY order_id;

-- B. WHERE removes pending rows before grouping.
WITH orders(order_id, customer_id, amount_usd, status) AS (
 VALUES (5001,101,40.00::numeric(10,2),'paid'),
        (5002,101,25.00::numeric(10,2),'paid'),
        (5003,102,70.00::numeric(10,2),'pending'),
        (5004,102,90.00::numeric(10,2),'paid'),
        (5005,103,15.00::numeric(10,2),'paid'),
        (5006,103,10.00::numeric(10,2),'paid')
)
SELECT customer_id, COUNT(*) AS paid_orders, SUM(amount_usd) AS paid_total
FROM orders WHERE status = 'paid'
GROUP BY customer_id ORDER BY customer_id;

-- C. HAVING filters groups; ORDER BY and LIMIT choose the top group.
WITH orders(order_id, customer_id, amount_usd, status) AS (
 VALUES (5001,101,40.00::numeric(10,2),'paid'),
        (5002,101,25.00::numeric(10,2),'paid'),
        (5003,102,70.00::numeric(10,2),'pending'),
        (5004,102,90.00::numeric(10,2),'paid'),
        (5005,103,15.00::numeric(10,2),'paid'),
        (5006,103,10.00::numeric(10,2),'paid')
)
SELECT customer_id, COUNT(*) AS paid_orders, SUM(amount_usd) AS paid_total
FROM orders WHERE status = 'paid'
GROUP BY customer_id HAVING SUM(amount_usd) >= 50
ORDER BY paid_total DESC, customer_id ASC LIMIT 1;

-- D. Assert counts, grouping grain, totals, HAVING count, and top customer.
WITH orders(order_id, customer_id, amount_usd, status) AS (
 VALUES (5001,101,40.00::numeric(10,2),'paid'),
        (5002,101,25.00::numeric(10,2),'paid'),
        (5003,102,70.00::numeric(10,2),'pending'),
        (5004,102,90.00::numeric(10,2),'paid'),
        (5005,103,15.00::numeric(10,2),'paid'),
        (5006,103,10.00::numeric(10,2),'paid')
), paid AS (
 SELECT * FROM orders WHERE status = 'paid'
), grouped AS (
 SELECT customer_id, COUNT(*) AS paid_orders, SUM(amount_usd) AS paid_total
 FROM paid GROUP BY customer_id
), ranked AS (
 SELECT customer_id, paid_total FROM grouped
 WHERE paid_total >= 50
 ORDER BY paid_total DESC, customer_id ASC LIMIT 1
), metrics AS (
 SELECT (SELECT COUNT(*) FROM orders) AS input_rows,
        (SELECT COUNT(*) FROM paid) AS paid_rows,
        (SELECT COUNT(*) FROM grouped) AS customer_groups,
        (SELECT SUM(amount_usd) FROM paid) AS revenue_usd,
        (SELECT COUNT(*) FROM grouped WHERE paid_total >= 50) AS qualifying_groups,
        (SELECT customer_id FROM ranked) AS top_customer,
        (SELECT paid_total FROM ranked) AS top_total,
        (SELECT paid_total FROM grouped WHERE customer_id=101) AS customer_101_total,
        (SELECT paid_total FROM grouped WHERE customer_id=103) AS customer_103_total
)
SELECT *, CASE WHEN input_rows=6 AND paid_rows=5 AND customer_groups=3
                  AND revenue_usd=180.00 AND qualifying_groups=2
                  AND top_customer=102 AND top_total=90.00
                  AND customer_101_total=65.00 AND customer_103_total=25.00
               THEN 'PASS' ELSE 'FAIL' END AS result,
       1 / CASE WHEN input_rows=6 AND paid_rows=5 AND customer_groups=3
                  AND revenue_usd=180.00 AND qualifying_groups=2
                  AND top_customer=102 AND top_total=90.00
                  AND customer_101_total=65.00 AND customer_103_total=25.00
                THEN 1 ELSE 0 END AS assertion
FROM metrics;

ROLLBACK;
