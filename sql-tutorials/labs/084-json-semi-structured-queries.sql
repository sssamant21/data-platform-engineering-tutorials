-- Chapter 084: JSON and semi-structured SQL queries
-- Isolated PostgreSQL 18 database sql_tutorials ONLY. Synthetic data; no persistent writes.
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

-- Fail closed if run in the wrong database or PostgreSQL major version.
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials'
                  AND current_setting('server_version_num')::integer / 10000 = 18
                THEN 1 ELSE 0 END AS environment_guard;

WITH events(event_id, payload) AS (
  VALUES (1, '{"source":"api","priority":null,"tags":["etl","urgent"]}'::jsonb),
         (2, '{"source":"file","tags":[]}'::jsonb),
         (3, '{"source":"api","priority":"high","tags":[]}'::jsonb),
         (4, NULL::jsonb)
)
SELECT event_id, payload->>'source' AS source_name,
       payload ? 'priority' AS has_priority_key,
       jsonb_typeof(payload->'priority') AS priority_json_type
FROM events ORDER BY event_id;

WITH events(event_id, payload) AS (
  VALUES (1, '{"source":"api","priority":null,"tags":["etl","urgent"]}'::jsonb),
         (2, '{"source":"file","tags":[]}'::jsonb),
         (3, '{"source":"api","priority":"high","tags":[]}'::jsonb),
         (4, NULL::jsonb)
), expanded AS (
 SELECT e.event_id, t.value AS tag
 FROM events AS e
 CROSS JOIN LATERAL jsonb_array_elements_text(
   CASE WHEN jsonb_typeof(e.payload->'tags') = 'array'
        THEN e.payload->'tags' ELSE '[]'::jsonb END
 ) AS t(value)
)
SELECT * FROM expanded ORDER BY event_id, tag;

-- Bidirectional exact set assertions. SQL NULL and JSON null intentionally differ.
WITH events(event_id, payload) AS (
  VALUES (1, '{"source":"api","priority":null,"tags":["etl","urgent"]}'::jsonb),
         (2, '{"source":"file","tags":[]}'::jsonb),
         (3, '{"source":"api","priority":"high","tags":[]}'::jsonb),
         (4, NULL::jsonb)
), expanded AS (
 SELECT e.event_id, t.value AS tag
 FROM events AS e
 CROSS JOIN LATERAL jsonb_array_elements_text(
   CASE WHEN jsonb_typeof(e.payload->'tags') = 'array'
        THEN e.payload->'tags' ELSE '[]'::jsonb END
 ) AS t(value)
), actual AS (
 SELECT COUNT(*)::bigint AS event_count,
        COUNT(payload)::bigint AS json_payload_count,
        COUNT(*) FILTER (WHERE payload->>'source' = 'api')::bigint AS api_count,
        COUNT(*) FILTER (WHERE payload->>'source' = 'file')::bigint AS file_count,
        (SELECT COUNT(*) FROM expanded)::bigint AS tag_count,
        COUNT(*) FILTER (WHERE jsonb_typeof(payload->'priority') = 'null')::bigint AS explicit_json_null_priority,
        COUNT(*) FILTER (WHERE payload IS NOT NULL AND NOT (payload ? 'priority'))::bigint AS absent_priority_key,
        COUNT(*) FILTER (WHERE payload IS NULL)::bigint AS sql_null_payload
 FROM events
), expected AS (
 SELECT 4::bigint AS event_count, 3::bigint AS json_payload_count,
        2::bigint AS api_count, 1::bigint AS file_count,
        2::bigint AS tag_count, 1::bigint AS explicit_json_null_priority,
        1::bigint AS absent_priority_key, 1::bigint AS sql_null_payload
), tag_expected(event_id, tag) AS (
 VALUES (1, 'etl'::text), (1, 'urgent'::text)
), differences AS (
 (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
 UNION ALL
 (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
), tag_differences AS (
 (SELECT * FROM expanded EXCEPT ALL SELECT * FROM tag_expected)
 UNION ALL
 (SELECT * FROM tag_expected EXCEPT ALL SELECT * FROM expanded)
), checks AS (
 SELECT (SELECT COUNT(*) = 0 FROM differences) AS metrics_match,
        (SELECT COUNT(*) = 0 FROM tag_differences) AS tags_match,
        (SELECT COUNT(*) = 1 FROM actual) AS one_summary_row
)
SELECT *, 1 / CASE WHEN metrics_match AND tags_match AND one_summary_row
                   THEN 1 ELSE 0 END AS fail_closed_acceptance
FROM checks;
ROLLBACK;
