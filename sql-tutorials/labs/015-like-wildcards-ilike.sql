-- Chapter 015: LIKE, wildcards and PostgreSQL-specific ILIKE.
-- Run ONLY on independently verified disposable PostgreSQL 18.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/015-like-wildcards-ilike.sql
-- Synthetic VALUES only. No persistent objects or credentials.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials'
 AND current_setting('server_version_num')::integer >= 180000
 AND current_setting('server_version_num')::integer < 190000
 THEN 1 ELSE 0 END AS environment_assertion;

-- Prefix match; expected 101,104,106. COLLATE "C" fixes ASCII case behavior.
WITH customers(id,code) AS (
 VALUES (101,'ALPHA'::text),(102,'alpha2'),(103,'BETA'),
        (104,'A_100'),(105,'GAMMA'),(106,'AL'))
SELECT id FROM customers WHERE code COLLATE "C" LIKE 'A%' ORDER BY id;

-- Literal underscore, literal percent, PostgreSQL ILIKE, and NULL behavior.
SELECT 'A_100' LIKE 'A!_100' ESCAPE '!' AS literal_underscore,
       '20% discount' LIKE '%!%%' ESCAPE '!' AS literal_percent,
       'alpha2' COLLATE "C" ILIKE 'AL%' AS pg_ilike,
       'alpha2' COLLATE "C" LIKE 'AL%' AS case_sensitive,
       NULL::text NOT LIKE 'A%' AS unknown_result;

-- Exact-result assertions. Fail closed on mismatch (division by zero).
WITH customers(id,code,email,note) AS (
 VALUES
 (101,'ALPHA'::text,'Ada@Example.test'::text,'priority_1'::text),
 (102,'alpha2','ben@example.test','20% discount'),
 (103,'BETA',NULL::text,'priorityX1'),
 (104,'A_100','Cia@Example.test','100% ready'),
 (105,'GAMMA','dan@sample.test',NULL::text),
 (106,'AL','eve@example.test','regular')
), checks AS (
 SELECT
 (SELECT array_agg(id ORDER BY id) FROM customers WHERE code COLLATE "C" LIKE 'A%') = ARRAY[101,104,106] AS prefix,
 (SELECT array_agg(id ORDER BY id) FROM customers WHERE code COLLATE "C" LIKE '%A') = ARRAY[101,103,105] AS suffix,
 (SELECT array_agg(id ORDER BY id) FROM customers WHERE code COLLATE "C" ILIKE 'al%') = ARRAY[101,102,106] AS insensitive,
 (SELECT array_agg(id ORDER BY id) FROM customers WHERE note LIKE '%!%%' ESCAPE '!') = ARRAY[102,104] AS percent_literal,
 (SELECT array_agg(id ORDER BY id) FROM customers WHERE code LIKE '%!_%' ESCAPE '!') = ARRAY[104] AS underscore_literal,
 (SELECT array_agg(id ORDER BY id) FROM customers WHERE note LIKE 'priority_1') = ARRAY[101,103] AS one_char,
 (SELECT array_agg(id ORDER BY id) FROM customers WHERE note LIKE 'priority!_1' ESCAPE '!') = ARRAY[101] AS escaped_one_char,
 (SELECT array_agg(id ORDER BY id) FROM customers WHERE email IS NULL) = ARRAY[103] AS missing_email,
 (SELECT array_agg(id ORDER BY id) FROM customers WHERE code COLLATE "C" NOT LIKE 'A%') = ARRAY[102,103,105] AS excluded,
 (NULL::text LIKE '%') IS NULL AS null_unknown,
 ('alpha2' COLLATE "C" ILIKE 'AL%') IS TRUE AS ilike_true
)
SELECT 1 / CASE WHEN prefix AND suffix AND insensitive AND percent_literal
 AND underscore_literal AND one_char AND escaped_one_char AND missing_email
 AND excluded AND null_unknown AND ilike_true THEN 1 ELSE 0 END AS acceptance_assertion
FROM checks;
ROLLBACK;
