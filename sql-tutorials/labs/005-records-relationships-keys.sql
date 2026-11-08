-- Chapter 005: records, relationships and keys.
-- PostgreSQL 18 isolated sql_tutorials lab only; no persistent writes.
-- Execute with psql -X -v ON_ERROR_STOP=1 -f <file>.
BEGIN READ ONLY;

SELECT 1 / CASE WHEN current_setting('server_version_num')::integer / 10000 = 18
                THEN 1 ELSE 0 END AS postgres_18_assertion;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials'
                THEN 1 ELSE 0 END AS lab_database_assertion;

-- One-to-many customer/order relationships and left-join fan-out.
WITH customers(customer_id, customer_name) AS (
 VALUES (101,'Ava'),(102,'Noah'),(103,'Mia')
), orders(order_id, customer_id, amount_usd) AS (
 VALUES (5001,101,30.00::numeric(10,2)),
        (5002,101,45.00::numeric(10,2)),
        (5003,102,20.00::numeric(10,2))
)
SELECT c.customer_id, c.customer_name, o.order_id, o.amount_usd
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.customer_id
ORDER BY c.customer_id, o.order_id;

-- Assertions: customer count, order count, join fan-out, unmatched customer,
-- total amount, and zero duplicate order identifiers.
WITH customers(customer_id, customer_name) AS (
 VALUES (101,'Ava'),(102,'Noah'),(103,'Mia')
), orders(order_id, customer_id, amount_usd) AS (
 VALUES (5001,101,30.00::numeric(10,2)),
        (5002,101,45.00::numeric(10,2)),
        (5003,102,20.00::numeric(10,2))
), metrics AS (
 SELECT
  (SELECT COUNT(*) FROM customers) AS customers,
  (SELECT COUNT(*) FROM orders) AS orders,
  (SELECT COUNT(*) FROM customers c LEFT JOIN orders o ON c.customer_id=o.customer_id) AS join_rows,
  (SELECT COUNT(*) FROM customers c WHERE NOT EXISTS
     (SELECT 1 FROM orders o WHERE o.customer_id=c.customer_id)) AS customers_without_orders,
  (SELECT SUM(amount_usd) FROM orders) AS total_usd,
  (SELECT COUNT(*) FROM (SELECT order_id FROM orders GROUP BY order_id HAVING COUNT(*) > 1) d) AS duplicate_order_ids
)
SELECT *,
       1 / CASE WHEN customers=3 AND orders=3 AND join_rows=4
                     AND customers_without_orders=1 AND total_usd=95.00
                     AND duplicate_order_ids=0 THEN 1 ELSE 0 END AS assertion
FROM metrics;

-- Staged orphan detection: 5004 references a nonexistent customer 999.
WITH customers(customer_id) AS (VALUES (101),(102),(103)),
staged_orders(order_id, customer_id) AS (
 VALUES (5001,101),(5002,101),(5003,102),(5004,999)
), orphans AS (
 SELECT s.order_id, s.customer_id
 FROM staged_orders s LEFT JOIN customers c ON c.customer_id=s.customer_id
 WHERE c.customer_id IS NULL
)
SELECT order_id, customer_id FROM orphans ORDER BY order_id;

WITH customers(customer_id) AS (VALUES (101),(102),(103)),
staged_orders(order_id, customer_id) AS (
 VALUES (5001,101),(5002,101),(5003,102),(5004,999)
), orphans AS (
 SELECT s.order_id, s.customer_id
 FROM staged_orders s LEFT JOIN customers c ON c.customer_id=s.customer_id
 WHERE c.customer_id IS NULL
)
SELECT COUNT(*) AS orphan_count,
       1 / CASE WHEN COUNT(*)=1 AND MIN(order_id)=5004 AND MIN(customer_id)=999
                THEN 1 ELSE 0 END AS assertion
FROM orphans;

-- Composite key check for order/product line pairs.
WITH order_items(order_id, product_id, quantity) AS (
 VALUES (5001,201,2),(5001,202,1),(5002,201,1)
), duplicate_pairs AS (
 SELECT order_id, product_id FROM order_items
 GROUP BY order_id, product_id HAVING COUNT(*) > 1
)
SELECT COUNT(*) AS duplicate_pair_count,
       1 / CASE WHEN COUNT(*)=0 THEN 1 ELSE 0 END AS assertion
FROM duplicate_pairs;

SELECT 'PASS' AS chapter_005_lab_result;
ROLLBACK;
