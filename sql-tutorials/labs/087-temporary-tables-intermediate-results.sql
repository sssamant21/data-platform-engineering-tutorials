-- Chapter 087: read-only intermediate-result lab. Synthetic data only.
-- Run: psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/087-temporary-tables-intermediate-results.sql
-- PostgreSQL 18 required; no permanent or temporary objects are created.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '20s';
-- Fail closed on wrong database/version; SELECT raises division-by-zero if unsafe.
SELECT current_database() AS database_name,
       current_setting('server_version') AS server_version,
       1 / CASE WHEN current_database() = 'sql_tutorials'
                 AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
                THEN 1 ELSE 0 END AS environment_guard;
-- Expected result: 101 => 3 / 30.00; 102 => 1 / 20.00.
WITH orders(order_id, customer_id, status, amount) AS (
 VALUES (1,101,'paid',10.00::numeric), (2,101,'paid',15.00::numeric),
        (3,101,'pending',99.00::numeric), (4,102,'paid',20.00::numeric),
        (5,103,'failed',50.00::numeric), (6,101,'paid',5.00::numeric)
), intermediate AS (
 SELECT customer_id, COUNT(*)::integer AS paid_count, SUM(amount) AS paid_total
 FROM orders WHERE status='paid' GROUP BY customer_id
)
SELECT * FROM intermediate ORDER BY customer_id;
-- Exact, multiplicity-sensitive bidirectional comparison and source reconciliation.
WITH orders(order_id, customer_id, status, amount) AS (
 VALUES (1,101,'paid',10.00::numeric), (2,101,'paid',15.00::numeric),
        (3,101,'pending',99.00::numeric), (4,102,'paid',20.00::numeric),
        (5,103,'failed',50.00::numeric), (6,101,'paid',5.00::numeric)
), actual AS (
 SELECT customer_id, COUNT(*)::integer AS paid_count, SUM(amount) AS paid_total
 FROM orders WHERE status='paid' GROUP BY customer_id
), expected(customer_id,paid_count,paid_total) AS (
 VALUES (101,3,30.00::numeric),(102,1,20.00::numeric)
), diff AS (
 (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
 UNION ALL
 (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
), checks AS (
 SELECT (SELECT COUNT(*)=0 FROM diff) AS exact_rows,
        (SELECT COUNT(*)=6 FROM orders) AS six_source_rows,
        (SELECT COUNT(*)=4 FROM orders WHERE status='paid') AS four_paid_rows,
        (SELECT COUNT(*)=2 FROM actual) AS two_customers,
        (SELECT COALESCE(SUM(paid_total),0)=50.00::numeric FROM actual) AS total_50
)
SELECT *, 1 / CASE WHEN exact_rows AND six_source_rows AND four_paid_rows
                         AND two_customers AND total_50 THEN 1 ELSE 0 END AS fail_closed_acceptance
FROM checks;
ROLLBACK;
