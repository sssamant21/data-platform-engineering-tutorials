-- SQL Tutorials — Chapter 001 (PostgreSQL 18 reference)
-- All statements are read-only. No persistent tables or writes.

-- 1. First query (expected: SQL is working | 5)
SELECT 'SQL is working' AS message, 2 + 3 AS answer;

-- 2. All sample orders (expected: four rows, order IDs 1001-1004)
WITH orders (order_id, customer_name, total_usd, status) AS (
    VALUES
        (1001, 'Ava',  120.00::numeric(10,2), 'paid'),
        (1002, 'Noah',  75.00::numeric(10,2), 'pending'),
        (1003, 'Ava',   40.00::numeric(10,2), 'paid'),
        (1004, 'Mia',   60.00::numeric(10,2), 'paid')
)
SELECT order_id, customer_name, total_usd
FROM orders
ORDER BY order_id;

-- 3. Paid orders (expected IDs: 1001, 1003, 1004)
WITH orders (order_id, customer_name, total_usd, status) AS (
    VALUES
        (1001, 'Ava',  120.00::numeric(10,2), 'paid'),
        (1002, 'Noah',  75.00::numeric(10,2), 'pending'),
        (1003, 'Ava',   40.00::numeric(10,2), 'paid'),
        (1004, 'Mia',   60.00::numeric(10,2), 'paid')
)
SELECT order_id, customer_name, total_usd
FROM orders
WHERE status = 'paid'
ORDER BY order_id;

-- 4. Paid order count and revenue (expected: 3 | 220.00)
WITH orders (order_id, customer_name, total_usd, status) AS (
    VALUES
        (1001, 'Ava',  120.00::numeric(10,2), 'paid'),
        (1002, 'Noah',  75.00::numeric(10,2), 'pending'),
        (1003, 'Ava',   40.00::numeric(10,2), 'paid'),
        (1004, 'Mia',   60.00::numeric(10,2), 'paid')
)
SELECT COUNT(*) AS paid_order_count,
       SUM(total_usd) AS paid_revenue_usd
FROM orders
WHERE status = 'paid';
