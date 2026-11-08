-- Chapter 009: Data types, NULL and explicit type conversion
-- Only isolated PostgreSQL 18 sql_tutorials database; synthetic rows; no persistent writes.
-- Run: psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/009-data-types-null-explicit-conversion.sql
BEGIN READ ONLY;

-- Stop on wrong database/version (division-by-zero assertion).
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials'
  AND current_setting('server_version_num')::integer / 10000 = 18
  THEN 1 ELSE 0 END AS environment_assertion;

-- A: NULL is different from an empty string. Expected 101 false, 102 true, 103 false.
WITH customers(customer_id, email) AS (
 VALUES (101, 'ava@example.invalid'::text), (102, NULL::text), (103, ''::text)
)
SELECT customer_id, email IS NULL AS missing_email
FROM customers ORDER BY customer_id;

-- B: exact decimals, fractional vs integer division. Expected 39.90 | 0 | 0.33.
SELECT CAST('19.95' AS NUMERIC(10,2)) * 2 AS line_total_usd,
       1 / 3 AS integer_ratio,
       ROUND(CAST(1 AS NUMERIC) / 3, 2) AS numeric_ratio;

-- C: missing equality is UNKNOWN. Expected NULL | true | 2026-11-08.
SELECT NULL::integer = NULL::integer AS equality_test,
       NULL::integer IS NULL AS missing_test,
       CAST('2026-11-08' AS DATE) AS order_date;

-- D: constrained example parser; regex is PostgreSQL-specific.
-- Expected 12.50, NULL, 7.25 in row order.
WITH raw_data(seq, raw_amount) AS (
 VALUES (1, '12.50'::text), (2, 'not-a-number'::text), (3, '7.25'::text)
)
SELECT seq, CASE
 WHEN raw_amount ~ '^[0-9]+(\.[0-9]{1,2})?$'
 THEN CAST(raw_amount AS NUMERIC(10,2))
 ELSE NULL::NUMERIC(10,2) END AS parsed_amount
FROM raw_data ORDER BY seq;

-- E: distinguish missing vs empty. Expected missing_count=1, empty_count=1.
WITH customers(customer_id, email) AS (
 VALUES (101, 'ava@example.invalid'::text), (102, NULL::text), (103, ''::text)
)
SELECT COUNT(*) FILTER (WHERE email IS NULL) AS missing_count,
       COUNT(*) FILTER (WHERE email = '') AS empty_count
FROM customers;

-- F: fail closed on incorrect results; expected acceptance_assertion=1.
WITH customers(customer_id, email) AS (
 VALUES (101, 'ava@example.invalid'::text), (102, NULL::text), (103, ''::text)
), raw_data(seq, raw_amount) AS (
 VALUES (1, '12.50'::text), (2, 'not-a-number'::text), (3, '7.25'::text)
), parsed AS (
 SELECT seq, CASE WHEN raw_amount ~ '^[0-9]+(\.[0-9]{1,2})?$'
   THEN CAST(raw_amount AS NUMERIC(10,2))
   ELSE NULL::NUMERIC(10,2) END AS amount
 FROM raw_data
), checks AS (
 SELECT (SELECT COUNT(*) FROM customers WHERE email IS NULL) AS missing_count,
        (SELECT COUNT(*) FROM customers WHERE email = '') AS empty_count,
        (SELECT COUNT(*) FROM parsed WHERE amount IS NOT NULL) AS valid_count,
        (SELECT SUM(amount) FROM parsed) AS parsed_sum
)
SELECT 1 / CASE WHEN missing_count = 1 AND empty_count = 1
  AND valid_count = 2 AND parsed_sum = 19.75
  AND CAST('19.95' AS NUMERIC(10,2)) * 2 = 39.90
  AND 1 / 3 = 0 AND ROUND(CAST(1 AS NUMERIC) / 3, 2) = 0.33
  AND (NULL::integer IS NULL)
  THEN 1 ELSE 0 END AS acceptance_assertion
FROM checks;

ROLLBACK;
