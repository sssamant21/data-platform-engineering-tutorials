-- Chapter 081: synthetic PostgreSQL 18 string/regex lab; read-only.
-- Run ONLY on isolated sql_tutorials: psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/081-string-functions-and-regular-expressions.sql
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
SELECT current_database() AS database_name, current_user AS role_name,
       current_setting('server_version') AS server_version,
       inet_server_addr() AS server_ip, inet_server_port() AS server_port;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials' THEN 1 ELSE 0 END AS database_guard;
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
                THEN 1 ELSE 0 END AS version_guard;

-- Preserve raw input, normalize without writes, classify quality.
WITH incoming(record_id,raw_email,raw_code) AS (
 VALUES (1,'  Alice@Example.COM  ',' EVT-0042 '),
        (2,'bob@example.org','EVT-0100'),
        (3,NULL::text,'evt-0042'),
        (4,'  invalid-email  ','BAD42'),
        (5,'carol@example.net',NULL::text)
), normalized AS (
 SELECT record_id,raw_email,raw_code,
        LOWER(TRIM(raw_email)) AS normalized_email,
        TRIM(raw_code) AS normalized_code,
        CHAR_LENGTH(TRIM(raw_email)) AS trimmed_chars
 FROM incoming
), classified AS (
 SELECT record_id,normalized_email,normalized_code,trimmed_chars,
        CASE WHEN normalized_code IS NULL THEN 'missing'
             WHEN normalized_code ~ '^EVT-[0-9]{4}$' THEN 'valid'
             ELSE 'invalid' END AS code_status,
        COALESCE(normalized_code ~* '^EVT-[0-9]{4}$',FALSE) AS case_insensitive_match,
        REGEXP_REPLACE(normalized_code,'[0-9]','X','g') AS masked_code
 FROM normalized
)
SELECT * FROM classified ORDER BY record_id;

-- Exact expected multiset, count reconciliation and fail-closed acceptance.
WITH incoming(record_id,raw_email,raw_code) AS (
 VALUES (1,'  Alice@Example.COM  ',' EVT-0042 '),
        (2,'bob@example.org','EVT-0100'),
        (3,NULL::text,'evt-0042'),
        (4,'  invalid-email  ','BAD42'),
        (5,'carol@example.net',NULL::text)
), normalized AS (
 SELECT record_id,LOWER(TRIM(raw_email)) AS normalized_email,
        TRIM(raw_code) AS normalized_code,
        CHAR_LENGTH(TRIM(raw_email)) AS trimmed_chars
 FROM incoming
), actual AS (
 SELECT record_id,normalized_email,normalized_code,trimmed_chars,
        CASE WHEN normalized_code IS NULL THEN 'missing'
             WHEN normalized_code ~ '^EVT-[0-9]{4}$' THEN 'valid'
             ELSE 'invalid' END AS code_status,
        COALESCE(normalized_code ~* '^EVT-[0-9]{4}$',FALSE) AS case_insensitive_match,
        REGEXP_REPLACE(normalized_code,'[0-9]','X','g') AS masked_code
 FROM normalized
), expected(record_id,normalized_email,normalized_code,trimmed_chars,code_status,case_insensitive_match,masked_code) AS (
 VALUES (1,'alice@example.com','EVT-0042',17,'valid',TRUE,'EVT-XXXX'),
        (2,'bob@example.org','EVT-0100',15,'valid',TRUE,'EVT-XXXX'),
        (3,NULL::text,'evt-0042',NULL::integer,'invalid',TRUE,'evt-XXXX'),
        (4,'invalid-email','BAD42',13,'invalid',FALSE,'BADXX'),
        (5,'carol@example.net',NULL::text,17,'missing',FALSE,NULL::text)
), differences AS (
 (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
 UNION ALL
 (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
), checks AS (
 SELECT (SELECT COUNT(*)=5 FROM incoming) AS five_source_rows,
        (SELECT COUNT(*)=5 FROM actual) AS five_output_rows,
        (SELECT COUNT(*)=2 FROM actual WHERE code_status='valid') AS two_valid,
        (SELECT COUNT(*)=2 FROM actual WHERE code_status='invalid') AS two_invalid,
        (SELECT COUNT(*)=1 FROM actual WHERE code_status='missing') AS one_missing,
        (SELECT COUNT(*)=0 FROM differences) AS exact_expected_rows
)
SELECT *, 1 / CASE WHEN five_source_rows AND five_output_rows AND two_valid
 AND two_invalid AND one_missing AND exact_expected_rows THEN 1 ELSE 0 END AS fail_closed_acceptance
FROM checks;
ROLLBACK;
