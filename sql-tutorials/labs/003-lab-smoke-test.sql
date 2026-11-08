-- Chapter 003 — PostgreSQL 18 smoke test (read-only)
-- Execute with: psql -X -v ON_ERROR_STOP=1 -f -
-- Expected: one final row showing PASS; any failed assertion causes a SQL error.
-- Only use the isolated sql_tutorials lab database.

SELECT current_database() AS database_name,
       current_user AS connected_role,
       current_setting('server_version') AS server_version;

-- Assert PostgreSQL 18 and expected isolated database/role.
SELECT 1 / CASE
  WHEN current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
   AND current_database() = 'sql_tutorials'
   AND current_user = 'sql_lab'
  THEN 1 ELSE 0 END AS environment_assertion;

-- Synthetic rows exist only within this statement.
WITH orders(order_id, amount_usd, status) AS (
  VALUES (1001, 120.00::numeric(10,2), 'paid'),
         (1002, 75.00::numeric(10,2), 'pending'),
         (1003, 40.00::numeric(10,2), 'paid'),
         (1004, 60.00::numeric(10,2), 'paid')
), summary AS (
  SELECT COUNT(*) FILTER (WHERE status = 'paid') AS paid_count,
         SUM(amount_usd) FILTER (WHERE status = 'paid') AS paid_revenue
  FROM orders
)
SELECT paid_count, paid_revenue,
       CASE WHEN paid_count = 3 AND paid_revenue = 220.00
            THEN 'PASS' ELSE 'FAIL' END AS result,
       1 / CASE WHEN paid_count = 3 AND paid_revenue = 220.00
                THEN 1 ELSE 0 END AS assertion
FROM summary;
