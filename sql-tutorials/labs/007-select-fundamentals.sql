-- Chapter 007: SELECT fundamentals — PostgreSQL 18 isolated lab
-- Run with: psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f labs/007-select-fundamentals.sql
-- Read-only transaction, fictional data only, no persistent objects.
BEGIN READ ONLY;

-- Abort on unexpected server version or database (division-by-zero on failure).
SELECT 1 / CASE
  WHEN current_setting('server_version_num')::integer / 10000 = 18
   AND current_database() = 'sql_tutorials'
  THEN 1 ELSE 0 END AS environment_assertion;

-- A: literal expressions (one row: hello, SQL | 42).
SELECT 'hello, SQL' AS message, 7 * 6 AS answer;

-- B: all columns (six rows, four columns).
WITH orders(order_id, customer_name, amount_usd, status) AS (
  VALUES (7001,'Ava',120.00::numeric(10,2),'paid'),
         (7002,'Noah',75.00::numeric(10,2),'pending'),
         (7003,'Mia',40.00::numeric(10,2),'paid'),
         (7004,'Ava',60.00::numeric(10,2),'paid'),
         (7005,'Leo',15.00::numeric(10,2),'cancelled'),
         (7006,'Mia',90.00::numeric(10,2),'pending')
)
SELECT * FROM orders ORDER BY order_id;

-- C: explicit projection (six rows, two columns).
WITH orders(order_id, customer_name, amount_usd, status) AS (
  VALUES (7001,'Ava',120.00::numeric(10,2),'paid'),
         (7002,'Noah',75.00::numeric(10,2),'pending'),
         (7003,'Mia',40.00::numeric(10,2),'paid'),
         (7004,'Ava',60.00::numeric(10,2),'paid'),
         (7005,'Leo',15.00::numeric(10,2),'cancelled'),
         (7006,'Mia',90.00::numeric(10,2),'pending')
)
SELECT order_id, customer_name FROM orders ORDER BY order_id;

-- D: paid orders only (three rows, IDs 7001, 7003, 7004).
WITH orders(order_id, customer_name, amount_usd, status) AS (
  VALUES (7001,'Ava',120.00::numeric(10,2),'paid'),
         (7002,'Noah',75.00::numeric(10,2),'pending'),
         (7003,'Mia',40.00::numeric(10,2),'paid'),
         (7004,'Ava',60.00::numeric(10,2),'paid'),
         (7005,'Leo',15.00::numeric(10,2),'cancelled'),
         (7006,'Mia',90.00::numeric(10,2),'pending')
)
SELECT order_id, customer_name, amount_usd
FROM orders WHERE status = 'paid' ORDER BY order_id;

-- E: paid order summary (one row: 3 | 220.00).
WITH orders(order_id, customer_name, amount_usd, status) AS (
  VALUES (7001,'Ava',120.00::numeric(10,2),'paid'),
         (7002,'Noah',75.00::numeric(10,2),'pending'),
         (7003,'Mia',40.00::numeric(10,2),'paid'),
         (7004,'Ava',60.00::numeric(10,2),'paid'),
         (7005,'Leo',15.00::numeric(10,2),'cancelled'),
         (7006,'Mia',90.00::numeric(10,2),'pending')
)
SELECT COUNT(*) AS paid_order_count, SUM(amount_usd) AS paid_revenue_usd
FROM orders WHERE status = 'paid';

-- F: machine-checkable acceptance; an error stops psql with ON_ERROR_STOP=1.
WITH orders(order_id, customer_name, amount_usd, status) AS (
  VALUES (7001,'Ava',120.00::numeric(10,2),'paid'),
         (7002,'Noah',75.00::numeric(10,2),'pending'),
         (7003,'Mia',40.00::numeric(10,2),'paid'),
         (7004,'Ava',60.00::numeric(10,2),'paid'),
         (7005,'Leo',15.00::numeric(10,2),'cancelled'),
         (7006,'Mia',90.00::numeric(10,2),'pending')
), metrics AS (
  SELECT COUNT(*) AS total_rows,
         COUNT(*) FILTER (WHERE status='paid') AS paid_rows,
         COUNT(*) FILTER (WHERE status='pending') AS pending_rows,
         SUM(amount_usd) FILTER (WHERE status='paid') AS paid_sum,
         ARRAY_AGG(order_id ORDER BY order_id) FILTER (WHERE status='paid') AS paid_ids
  FROM orders
)
SELECT CASE WHEN total_rows = 6 AND paid_rows = 3 AND pending_rows = 2
                 AND paid_sum = 220.00::numeric(10,2)
                 AND paid_ids = ARRAY[7001,7003,7004]
            THEN 'pass' ELSE (1 / (total_rows - total_rows))::text END AS acceptance
FROM metrics;

ROLLBACK;
