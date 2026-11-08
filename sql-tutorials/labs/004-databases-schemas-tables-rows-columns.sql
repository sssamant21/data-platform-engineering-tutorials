-- Chapter 004: PostgreSQL 18, disposable sql_tutorials database only.
-- All statements are read-only; ON_ERROR_STOP=1 makes failures observable.
BEGIN READ ONLY;

-- Fail loudly if the environment is not the intended isolated lab.
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer / 10000 = 18 THEN 1 ELSE 0 END AS pg18_assertion;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials' THEN 1 ELSE 0 END AS lab_database_assertion;
SELECT 1 / CASE WHEN EXISTS (
  SELECT 1 FROM pg_catalog.pg_namespace WHERE nspname = 'public'
) THEN 1 ELSE 0 END AS public_schema_assertion;

-- Session and schema metadata; output varies by role and configuration.
SELECT current_database() AS database_name,
       current_user AS role_name,
       current_schema() AS default_schema;
SHOW search_path;
SELECT current_schemas(true) AS effective_schemas;
SELECT schema_name FROM information_schema.schemata ORDER BY schema_name;

-- Inventory: an empty result is valid for a newly initialized lab.
SELECT n.nspname AS schema_name, c.relname AS table_name
FROM pg_catalog.pg_class AS c
JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r','p')
  AND n.nspname NOT IN ('pg_catalog','information_schema')
  AND n.nspname NOT LIKE 'pg_toast%'
ORDER BY n.nspname, c.relname;

-- Query synthetic rows; no CREATE TABLE or permanent writes.
WITH orders (order_id, customer_name, amount_usd, status) AS (
 VALUES (2001,'Ava',45.50::numeric(10,2),'paid'),
        (2002,'Noah',80.00::numeric(10,2),'pending'),
        (2003,'Mia',24.50::numeric(10,2),'paid'),
        (2004,'Ava',10.00::numeric(10,2),'paid')
)
SELECT order_id, customer_name, amount_usd, status FROM orders ORDER BY order_id;

WITH orders (order_id, customer_name, amount_usd, status) AS (
 VALUES (2001,'Ava',45.50::numeric(10,2),'paid'),
        (2002,'Noah',80.00::numeric(10,2),'pending'),
        (2003,'Mia',24.50::numeric(10,2),'paid'),
        (2004,'Ava',10.00::numeric(10,2),'paid')
), totals AS (
 SELECT COUNT(*) AS row_count,
        COUNT(*) FILTER (WHERE status = 'paid') AS paid_count,
        SUM(amount_usd) FILTER (WHERE status = 'paid') AS paid_total,
        COUNT(DISTINCT customer_name) AS customer_count
 FROM orders
)
SELECT row_count, paid_count, paid_total, customer_count,
       1 / CASE WHEN row_count = 4 AND paid_count = 3
                     AND paid_total = 80.00 AND customer_count = 3
                THEN 1 ELSE 0 END AS assertion
FROM totals;

SELECT 'PASS' AS chapter_004_lab_result;
ROLLBACK;
