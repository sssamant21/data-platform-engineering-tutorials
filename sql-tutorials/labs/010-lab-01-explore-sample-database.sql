-- Chapter 010 / Lab 01: synthetic retail; PostgreSQL 18, disposable sql_tutorials only.
-- Run with psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/010-lab-01-explore-sample-database.sql
-- Confirm the endpoint is isolated before executing; database name alone is insufficient.
BEGIN READ ONLY;
-- Guard: expect 1. Deliberate error if wrong database or major version.
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials'
  AND current_setting('server_version_num')::integer / 10000 = 18
  THEN 1 ELSE 0 END AS environment_assertion;
-- A. Projection: 3 customers, in ID order.
WITH customers(customer_id, customer_name, email) AS (
 VALUES (1, 'Ava', 'ava@example.invalid'), (2, 'Ben', NULL),
        (3, 'Chen', 'chen@example.invalid')
)
SELECT customer_id, customer_name, email FROM customers ORDER BY customer_id;
-- B. NULL: expected customer 2.
WITH customers(customer_id, customer_name, email) AS (
 VALUES (1, 'Ava', 'ava@example.invalid'), (2, 'Ben', NULL),
        (3, 'Chen', 'chen@example.invalid')
)
SELECT customer_id FROM customers WHERE email IS NULL ORDER BY customer_id;
-- C. Five extended line values: 25.00, 6.00, 30.00, 12.50, 4.00.
WITH order_lines(line_id, order_id, product_name, quantity, unit_price) AS (
 VALUES (1,101,'Notebook',2,12.50::numeric(10,2)),
        (2,101,'Pen',3,2.00::numeric(10,2)),
        (3,102,'Bag',1,30.00::numeric(10,2)),
        (4,103,'Notebook',1,12.50::numeric(10,2)),
        (5,104,'Pen',2,2.00::numeric(10,2))
)
SELECT line_id, order_id, quantity * unit_price AS line_total
FROM order_lines ORDER BY line_id;
-- D. Four order totals: 31.00, 30.00, 12.50, 4.00.
WITH orders(order_id, customer_id, order_date, status) AS (
 VALUES (101,1,DATE '2026-11-01','paid'),
        (102,1,DATE '2026-11-02','paid'),
        (103,2,DATE '2026-11-03','pending'),
        (104,2,DATE '2026-11-04','paid')
), order_lines(line_id, order_id, product_name, quantity, unit_price) AS (
 VALUES (1,101,'Notebook',2,12.50::numeric(10,2)),
        (2,101,'Pen',3,2.00::numeric(10,2)),
        (3,102,'Bag',1,30.00::numeric(10,2)),
        (4,103,'Notebook',1,12.50::numeric(10,2)),
        (5,104,'Pen',2,2.00::numeric(10,2))
)
SELECT o.order_id, SUM(l.quantity * l.unit_price) AS order_total
FROM orders o JOIN order_lines l ON o.order_id = l.order_id
GROUP BY o.order_id ORDER BY o.order_id;
-- E. Stretch: Ava and Ben, but not Chen.
WITH customers(customer_id, customer_name) AS (
 VALUES (1,'Ava'),(2,'Ben'),(3,'Chen')
), orders(order_id, customer_id) AS (
 VALUES (101,1),(102,1),(103,2),(104,2)
)
SELECT DISTINCT c.customer_id, c.customer_name
FROM customers c JOIN orders o ON c.customer_id=o.customer_id
ORDER BY c.customer_id;
-- F. Fail-closed acceptance. Expected acceptance_assertion=1.
WITH customers(customer_id, customer_name, email) AS (
 VALUES (1,'Ava','ava@example.invalid'),(2,'Ben',NULL),
        (3,'Chen','chen@example.invalid')
), orders(order_id, customer_id) AS (
 VALUES (101,1),(102,1),(103,2),(104,2)
), order_lines(line_id, order_id, quantity, unit_price) AS (
 VALUES (1,101,2,12.50::numeric(10,2)),
        (2,101,3,2.00::numeric(10,2)),
        (3,102,1,30.00::numeric(10,2)),
        (4,103,1,12.50::numeric(10,2)),
        (5,104,2,2.00::numeric(10,2))
), totals AS (
 SELECT order_id, SUM(quantity * unit_price) AS amount
 FROM order_lines GROUP BY order_id
), checks AS (
 SELECT (SELECT COUNT(*) FROM customers) AS customers_count,
        (SELECT COUNT(*) FROM customers WHERE email IS NULL) AS missing_emails,
        (SELECT COUNT(*) FROM orders) AS orders_count,
        (SELECT COUNT(*) FROM order_lines) AS lines_count,
        (SELECT COUNT(*) FROM totals) AS grouped_orders,
        (SELECT SUM(amount) FROM totals) AS grand_total,
        (SELECT COUNT(*) FROM customers c WHERE NOT EXISTS
          (SELECT 1 FROM orders o WHERE o.customer_id=c.customer_id)) AS customers_without_orders,
        (SELECT COUNT(*) FROM totals WHERE
          (order_id=101 AND amount=31.00) OR
          (order_id=102 AND amount=30.00) OR
          (order_id=103 AND amount=12.50) OR
          (order_id=104 AND amount=4.00)) AS matching_order_totals
)
SELECT 1 / CASE WHEN customers_count=3 AND missing_emails=1
 AND orders_count=4 AND lines_count=5 AND grouped_orders=4
 AND grand_total=77.50 AND customers_without_orders=1
 AND matching_order_totals=4 THEN 1 ELSE 0 END AS acceptance_assertion
FROM checks;
ROLLBACK;
