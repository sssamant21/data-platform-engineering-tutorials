-- Chapter 008: aliases, expressions, literals, calculated columns
-- PostgreSQL 18 only; fictional in-query rows; read-only transaction.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/008-aliases-expressions-calculated-columns.sql
BEGIN READ ONLY;

-- Environment guard: fail fast in wrong database/version.
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials'
  AND current_setting('server_version_num')::integer / 10000 = 18
  THEN 1 ELSE 0 END AS environment_assertion;

-- A: output and relation aliases; expected 7001 | 120.00
WITH orders(order_id, amount_usd) AS (VALUES (7001, 120.00::numeric(10,2)))
SELECT o.order_id AS id, o.amount_usd AS amount FROM orders AS o;

-- B: computed line totals; expected 7001 | 39.90, 7002 | 30.00
WITH items(order_id, quantity, unit_price_usd) AS (
 VALUES (7001, 2, 19.95::numeric(10,2)),
        (7002, 3, 10.00::numeric(10,2))
)
SELECT order_id, quantity * unit_price_usd AS line_total_usd
FROM items ORDER BY order_id;

-- C: 10 percent discount; expected 35.91 and 27.00
WITH items(order_id, quantity, unit_price_usd) AS (
 VALUES (7001, 2, 19.95::numeric(10,2)),
        (7002, 3, 10.00::numeric(10,2))
)
SELECT order_id, ROUND(quantity * unit_price_usd * 0.90, 2) AS discounted_usd
FROM items ORDER BY order_id;

-- D: filter using a CTE; expected only 7001 | 39.90
WITH items(order_id, quantity, unit_price_usd) AS (
 VALUES (7001, 2, 19.95::numeric(10,2)),
        (7002, 3, 10.00::numeric(10,2))
), totals AS (
 SELECT order_id, quantity * unit_price_usd AS line_total_usd FROM items
)
SELECT order_id, line_total_usd FROM totals
WHERE line_total_usd >= 35.00 ORDER BY order_id;

-- E: string and numeric expressions; expected Ava Patel | 0.33 | 180.00
SELECT 'Ava' || ' ' || 'Patel' AS display_name,
       ROUND(1::numeric / 3, 2) AS ratio,
       (100.00::numeric(10,2) - 10.00::numeric(10,2)) * 2 AS discounted_total_usd;

-- F: acceptance assertion; expected acceptance_assertion=1, else division by zero
WITH items(order_id, quantity, unit_price_usd) AS (
 VALUES (7001, 2, 19.95::numeric(10,2)),
        (7002, 3, 10.00::numeric(10,2))
), totals AS (
 SELECT order_id,
        quantity * unit_price_usd AS total_usd,
        ROUND(quantity * unit_price_usd * 0.90, 2) AS discounted_usd
 FROM items
), metrics AS (
 SELECT COUNT(*) AS row_count,
        SUM(total_usd) AS gross_usd,
        SUM(discounted_usd) AS net_usd,
        COUNT(*) FILTER (WHERE total_usd >= 35.00) AS high_value_count
 FROM totals
)
SELECT 1 / CASE WHEN row_count = 2 AND gross_usd = 69.90
 AND net_usd = 62.91 AND high_value_count = 1
 AND ROUND(1::numeric / 3, 2) = 0.33
 AND ('Ava' || ' ' || 'Patel') = 'Ava Patel'
 THEN 1 ELSE 0 END AS acceptance_assertion
FROM metrics;

ROLLBACK;
