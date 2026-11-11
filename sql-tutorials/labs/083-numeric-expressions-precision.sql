-- 083 — Numeric expressions and precision. Synthetic, read-only PostgreSQL 18.
-- Run only in disposable database sql_tutorials; never use production credentials.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
SELECT current_database() AS database_name, current_user AS login_name,
       current_setting('server_version') AS server_version,
       inet_server_addr() AS server_address, inet_server_port() AS server_port;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials' THEN 1 ELSE 0 END AS database_guard;
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
                THEN 1 ELSE 0 END AS version_guard;

-- Observe the synthetic line-level rounding difference.
WITH lines(line_id, amount) AS (
 VALUES (1, 19.995::numeric), (2, 10.005::numeric),
        (3, 0.100::numeric), (4, NULL::numeric)
)
SELECT COUNT(*) AS rows_total, COUNT(amount) AS measured_rows,
       SUM(amount) AS raw_total, ROUND(SUM(amount), 2) AS rounded_total,
       SUM(ROUND(amount, 2)) AS sum_rounded_lines
FROM lines;

-- Exact, bidirectional set comparison and fail-closed assertions.
WITH lines(line_id, amount) AS (
 VALUES (1, 19.995::numeric), (2, 10.005::numeric),
        (3, 0.100::numeric), (4, NULL::numeric)
), actual AS (
 SELECT COUNT(*)::bigint AS rows_total,
        COUNT(amount)::bigint AS measured_rows,
        SUM(amount) AS raw_total,
        ROUND(SUM(amount), 2) AS rounded_total,
        SUM(ROUND(amount, 2)) AS sum_rounded_lines,
        (0.1::numeric + 0.2::numeric = 0.3::numeric) AS exact_match,
        (0.1::double precision + 0.2::double precision =
         0.3::double precision) AS float_match,
        (5 / 2)::integer AS integer_quotient,
        (5::numeric / 2) AS decimal_quotient,
        (5::numeric / NULLIF(0, 0)) AS undefined_ratio,
        ROUND(-1.235::numeric, 2) AS negative_tie,
        CAST(12.345 AS NUMERIC(8,2)) AS scaled_value
 FROM lines
), expected(rows_total, measured_rows, raw_total, rounded_total,
           sum_rounded_lines, exact_match, float_match, integer_quotient,
           decimal_quotient, undefined_ratio, negative_tie, scaled_value) AS (
 VALUES (4::bigint, 3::bigint, 30.100::numeric, 30.10::numeric,
         30.11::numeric, TRUE, FALSE, 2::integer,
         2.5::numeric, NULL::numeric, -1.24::numeric, 12.35::numeric)
), differences AS (
 (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
 UNION ALL
 (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
), checks AS (
 SELECT (SELECT COUNT(*) = 1 FROM actual) AS exactly_one_row,
        (SELECT COUNT(*) = 0 FROM differences) AS exact_expected_results,
        (SELECT COUNT(*) = 1 FROM actual WHERE undefined_ratio IS NULL) AS zero_denominator_is_null
)
SELECT *, 1 / CASE WHEN exactly_one_row AND exact_expected_results
                         AND zero_denominator_is_null
                   THEN 1 ELSE 0 END AS fail_closed_acceptance
FROM checks;
ROLLBACK;
