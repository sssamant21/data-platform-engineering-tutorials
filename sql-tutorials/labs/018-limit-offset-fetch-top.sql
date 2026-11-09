-- Chapter 018: LIMIT, OFFSET, FETCH, and TOP across dialects.
-- PostgreSQL 18 only; TOP examples are explained in the chapter, not executed here.
-- Execute ONLY on an independently verified disposable sql_tutorials database.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/018-limit-offset-fetch-top.sql
-- Synthetic inline data, no persistent objects or writes.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials'
 AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
 THEN 1 ELSE 0 END AS environment_assertion;

-- Expected IDs 201, 202: oldest two with deterministic tie-break.
WITH events(event_id, created_at) AS (
 VALUES (201,TIMESTAMP '2026-01-01 09:00'),
 (202,TIMESTAMP '2026-01-01 09:05'),
 (203,TIMESTAMP '2026-01-01 09:05'),
 (204,TIMESTAMP '2026-01-02 10:00'),
 (205,TIMESTAMP '2026-01-03 11:00'),
 (206,TIMESTAMP '2026-01-03 12:00')
)
SELECT event_id FROM events ORDER BY created_at, event_id FETCH FIRST 2 ROWS ONLY;

-- Expected IDs 203, 204: second page, PostgreSQL LIMIT/OFFSET.
WITH events(event_id) AS (VALUES (201),(202),(203),(204),(205),(206))
SELECT event_id FROM events ORDER BY event_id LIMIT 2 OFFSET 2;

-- Expected IDs 203, 204: standard OFFSET/FETCH variant.
WITH events(event_id) AS (VALUES (201),(202),(203),(204),(205),(206))
SELECT event_id FROM events ORDER BY event_id OFFSET 2 ROWS FETCH NEXT 2 ROWS ONLY;

-- Expected IDs 205, 206: keyset after ID 204.
WITH events(event_id) AS (VALUES (201),(202),(203),(204),(205),(206))
SELECT event_id FROM events WHERE event_id > 204 ORDER BY event_id FETCH FIRST 2 ROWS ONLY;

-- Exact fail-closed acceptance: arrays encode order, ties check only set/count.
WITH events(event_id, severity, created_at) AS (
 VALUES (201,2,TIMESTAMP '2026-01-01 09:00'),
 (202,1,TIMESTAMP '2026-01-01 09:05'),
 (203,1,TIMESTAMP '2026-01-01 09:05'),
 (204,3,TIMESTAMP '2026-01-02 10:00'),
 (205,2,TIMESTAMP '2026-01-03 11:00'),
 (206,1,TIMESTAMP '2026-01-03 12:00')
), checks AS (
 SELECT
 (SELECT array_agg(event_id ORDER BY created_at,event_id)
  FROM (SELECT event_id,created_at FROM events ORDER BY created_at,event_id FETCH FIRST 2 ROWS ONLY) p)
  = ARRAY[201,202] AS first_page,
 (SELECT array_agg(event_id ORDER BY event_id)
  FROM (SELECT event_id FROM events ORDER BY event_id LIMIT 2 OFFSET 2) p)
  = ARRAY[203,204] AS offset_page,
 (SELECT array_agg(event_id ORDER BY event_id)
  FROM (SELECT event_id FROM events ORDER BY event_id OFFSET 2 ROWS FETCH NEXT 2 ROWS ONLY) p)
  = ARRAY[203,204] AS fetch_page,
 (SELECT array_agg(event_id ORDER BY event_id)
  FROM (SELECT event_id FROM events WHERE event_id > 204 ORDER BY event_id LIMIT 2) p)
  = ARRAY[205,206] AS keyset_page,
 (SELECT COUNT(*) FROM (SELECT event_id FROM events ORDER BY severity FETCH FIRST 2 ROWS WITH TIES) p)
  = 3 AS with_ties_count,
 (SELECT array_agg(event_id ORDER BY event_id) FROM
  (SELECT event_id FROM events ORDER BY severity FETCH FIRST 2 ROWS WITH TIES) p)
  = ARRAY[202,203,206] AS with_ties_set,
 (SELECT COUNT(*) FROM (SELECT event_id FROM events ORDER BY event_id LIMIT 0) p)
  = 0 AS zero_limit,
 (SELECT COUNT(*) FROM (SELECT event_id FROM events ORDER BY event_id LIMIT 2 OFFSET 100) p)
  = 0 AS past_end,
 (SELECT COUNT(*) FROM events) = 6 AS six_rows
)
SELECT 1 / CASE WHEN first_page AND offset_page AND fetch_page AND keyset_page
 AND with_ties_count AND with_ties_set AND zero_limit AND past_end AND six_rows
 THEN 1 ELSE 0 END AS acceptance_assertion FROM checks;
ROLLBACK;
