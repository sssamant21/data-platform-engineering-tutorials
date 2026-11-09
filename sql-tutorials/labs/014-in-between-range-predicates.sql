-- Chapter 014 — IN, BETWEEN, and range predicates
-- Run ONLY on independently verified disposable PostgreSQL 18 sandbox.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/014-in-between-range-predicates.sql
-- No persistent tables, writes, or credentials. Expected assertions = 1.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
-- Fail closed on unexpected server version or database name.
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials'
 AND current_setting('server_version_num')::integer >= 180000
 AND current_setting('server_version_num')::integer < 190000
 THEN 1 ELSE 0 END AS environment_assertion;

-- A: membership; expected IDs 501,502,503,506.
WITH events(event_id,category) AS (
 VALUES (501,'payment'::text),(502,'refund'::text),(503,'payment'::text),
        (504,'adjustment'::text),(505,NULL::text),(506,'payment'::text))
SELECT event_id FROM events WHERE category IN ('payment','refund') ORDER BY event_id;

-- B: expected NULL, TRUE.
SELECT 7 NOT IN (1,NULL) AS unsafe_exclusion,
       7 NOT IN (1,2) AS known_exclusion;

-- C: inclusive numeric interval; expected IDs 502,503,504.
WITH amounts(event_id,amount) AS (
 VALUES (501,25::numeric),(502,50::numeric),(503,75::numeric),
        (504,100::numeric),(505,125::numeric),(506,NULL::numeric))
SELECT event_id FROM amounts WHERE amount BETWEEN 50 AND 100 ORDER BY event_id;

-- D: exclusive interval; expected ID 503.
WITH amounts(event_id,amount) AS (
 VALUES (501,25::numeric),(502,50::numeric),(503,75::numeric),
        (504,100::numeric),(505,125::numeric),(506,NULL::numeric))
SELECT event_id FROM amounts WHERE amount > 50 AND amount < 100 ORDER BY event_id;

-- E: half-open Nov 1; expected IDs 501,502,503.
WITH events(event_id,event_ts) AS (
 VALUES (501,timestamp '2026-11-01 00:00:00'),
        (502,timestamp '2026-11-01 12:30:00'),
        (503,timestamp '2026-11-01 23:59:59'),
        (504,timestamp '2026-11-02 00:00:00'),
        (505,timestamp '2026-11-02 08:00:00'),
        (506,timestamp '2026-11-03 00:00:00'))
SELECT event_id FROM events
WHERE event_ts >= timestamp '2026-11-01 00:00:00'
  AND event_ts < timestamp '2026-11-02 00:00:00'
ORDER BY event_id;

-- F: exact-result checks. Any failure aborts with division by zero.
WITH events(event_id,category,amount,event_ts) AS (
 VALUES
 (501,'payment'::text,25::numeric,timestamp '2026-11-01 00:00:00'),
 (502,'refund'::text,50::numeric,timestamp '2026-11-01 12:30:00'),
 (503,'payment'::text,75::numeric,timestamp '2026-11-01 23:59:59'),
 (504,'adjustment'::text,100::numeric,timestamp '2026-11-02 00:00:00'),
 (505,NULL::text,125::numeric,timestamp '2026-11-02 08:00:00'),
 (506,'payment'::text,NULL::numeric,timestamp '2026-11-03 00:00:00')
), checks AS (
 SELECT
 (SELECT array_agg(event_id ORDER BY event_id) FROM events WHERE category IN ('payment','refund')) = ARRAY[501,502,503,506] AS membership,
 (SELECT array_agg(event_id ORDER BY event_id) FROM events WHERE category NOT IN ('payment','refund') OR category IS NULL) = ARRAY[504,505] AS exceptions,
 (SELECT array_agg(event_id ORDER BY event_id) FROM events WHERE amount BETWEEN 50 AND 100) = ARRAY[502,503,504] AS inclusive_range,
 (SELECT array_agg(event_id ORDER BY event_id) FROM events WHERE amount > 50 AND amount < 100) = ARRAY[503] AS exclusive_range,
 (SELECT COUNT(*) FROM events WHERE amount BETWEEN 100 AND 50) = 0 AS reversed_bounds,
 (SELECT array_agg(event_id ORDER BY event_id) FROM events WHERE amount NOT BETWEEN 50 AND 100) = ARRAY[501,505] AS outside_range,
 (SELECT array_agg(event_id ORDER BY event_id) FROM events WHERE amount >= 75 AND amount < 125) = ARRAY[503,504] AS half_open_amount,
 (SELECT array_agg(event_id ORDER BY event_id) FROM events WHERE event_ts >= timestamp '2026-11-01 00:00:00' AND event_ts < timestamp '2026-11-02 00:00:00') = ARRAY[501,502,503] AS nov1,
 (SELECT array_agg(event_id ORDER BY event_id) FROM events WHERE event_ts >= timestamp '2026-11-02 00:00:00' AND event_ts < timestamp '2026-11-03 00:00:00') = ARRAY[504,505] AS nov2,
 (7 NOT IN (1,NULL)) IS NULL AS unknown_exclusion,
 ('refund'::text NOT IN ('payment',NULL)) IS NULL AS text_unknown,
 (7 NOT IN (1,2)) IS TRUE AS known_exclusion,
 (SELECT COUNT(*) FROM events WHERE amount IS NULL) = 1 AS missing_amount
)
SELECT 1 / CASE WHEN membership AND exceptions AND inclusive_range
 AND exclusive_range AND reversed_bounds AND outside_range AND half_open_amount
 AND nov1 AND nov2 AND unknown_exclusion AND text_unknown
 AND known_exclusion AND missing_amount THEN 1 ELSE 0 END AS acceptance_assertion
FROM checks;
ROLLBACK;
