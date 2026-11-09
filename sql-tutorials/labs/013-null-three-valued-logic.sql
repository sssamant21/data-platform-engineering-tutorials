-- Chapter 013: NULL handling and SQL three-valued logic
-- Synthetic inline VALUES; no persistent objects. Verify disposable endpoint independently.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/013-null-three-valued-logic.sql
BEGIN READ ONLY;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials'
  AND current_setting('server_version_num')::integer / 10000 = 18
  THEN 1 ELSE 0 END AS environment_assertion;

-- A: NULL status: 402, 406
WITH orders(order_id,status,amount) AS (
 VALUES (401,'paid'::text,25.00::numeric),
 (402,NULL::text,0.00::numeric),
 (403,'pending'::text,NULL::numeric),
 (404,''::text,10.00::numeric),
 (405,'paid'::text,NULL::numeric),
 (406,NULL::text,80.00::numeric))
SELECT order_id FROM orders WHERE status IS NULL ORDER BY order_id;

-- B: NULL, TRUE, TRUE
SELECT NULL::text = 'paid' AS ordinary_equality,
 NULL::text IS NOT DISTINCT FROM NULL::text AS null_safe_equality,
 NULL::text IS DISTINCT FROM 'paid' AS null_safe_difference;

-- C: 402, 403, 404, 406
WITH orders(order_id,status) AS (
 VALUES (401,'paid'::text),(402,NULL::text),(403,'pending'::text),
 (404,''::text),(405,'paid'::text),(406,NULL::text))
SELECT order_id FROM orders WHERE status IS DISTINCT FROM 'paid' ORDER BY order_id;

-- D: 6, 4, 2, 115
WITH amounts(amount) AS (
 VALUES (25.00::numeric),(0.00::numeric),(NULL::numeric),
 (10.00::numeric),(NULL::numeric),(80.00::numeric))
SELECT COUNT(*) AS all_rows, COUNT(amount) AS known_amounts,
 COUNT(*)-COUNT(amount) AS missing_amounts, SUM(amount) AS known_sum
FROM amounts;

-- E: NULL, TRUE
SELECT 3 NOT IN (1, NULL) AS unsafe_result,
       3 NOT IN (1, 2) AS safe_result;

-- F: prioritized quality labels
WITH orders(order_id,status,amount) AS (
 VALUES (401,'paid'::text,25.00::numeric),
 (402,NULL::text,0.00::numeric),
 (403,'pending'::text,NULL::numeric),
 (404,''::text,10.00::numeric),
 (405,'paid'::text,NULL::numeric),
 (406,NULL::text,80.00::numeric))
SELECT order_id,
 CASE WHEN status IS NULL THEN 'missing_status'
 WHEN status = '' THEN 'blank_status'
 WHEN amount IS NULL THEN 'missing_amount'
 ELSE 'ok' END AS quality_flag
FROM orders ORDER BY order_id;

-- Exact-result acceptance: fail closed on any mismatch.
WITH orders(order_id,status,amount) AS (
 VALUES (401,'paid'::text,25.00::numeric),
 (402,NULL::text,0.00::numeric),
 (403,'pending'::text,NULL::numeric),
 (404,''::text,10.00::numeric),
 (405,'paid'::text,NULL::numeric),
 (406,NULL::text,80.00::numeric)
), checks AS (
 SELECT
 (SELECT array_agg(order_id ORDER BY order_id) FROM orders WHERE status IS NULL)
   = ARRAY[402,406] AS missing_status,
 (SELECT array_agg(order_id ORDER BY order_id) FROM orders WHERE status IS NOT NULL)
   = ARRAY[401,403,404,405] AS present_status,
 (SELECT array_agg(order_id ORDER BY order_id) FROM orders WHERE NOT(status = 'paid'))
   = ARRAY[403,404] AS ordinary_not,
 (SELECT array_agg(order_id ORDER BY order_id) FROM orders WHERE status IS DISTINCT FROM 'paid')
   = ARRAY[402,403,404,406] AS null_safe_not,
 (SELECT COUNT(*) FROM orders) = 6 AS total_count,
 (SELECT COUNT(amount) FROM orders) = 4 AS known_count,
 (SELECT SUM(amount) FROM orders) = 115.00::numeric AS amount_sum,
 (NULL::text = 'paid') IS NULL AS unknown_comparison,
 (NULL::text IS NOT DISTINCT FROM NULL::text) AS null_safe_equal,
 (NULL::text IS DISTINCT FROM 'paid') AS null_safe_different,
 (3 NOT IN (1,NULL)) IS NULL AS not_in_unknown,
 (3 NOT IN (1,2)) IS TRUE AS not_in_true,
 (SELECT array_agg(order_id ORDER BY order_id) FROM orders
  WHERE status IS NULL OR amount IS NULL OR status = '')
    = ARRAY[402,403,404,405,406] AS exceptions
)
SELECT 1 / CASE WHEN missing_status AND present_status AND ordinary_not
 AND null_safe_not AND total_count AND known_count AND amount_sum
 AND unknown_comparison AND null_safe_equal AND null_safe_different
 AND not_in_unknown AND not_in_true AND exceptions THEN 1 ELSE 0 END
 AS acceptance_assertion FROM checks;
ROLLBACK;
