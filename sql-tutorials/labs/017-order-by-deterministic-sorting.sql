-- Chapter 017 — ORDER BY and deterministic sorting.
-- Run ONLY against an independently verified disposable PostgreSQL 18 database.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/017-order-by-deterministic-sorting.sql
-- All data are synthetic inline VALUES. No persistent objects, DDL or DML.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials'
 AND current_setting('server_version_num')::integer >= 180000
 AND current_setting('server_version_num')::integer < 190000
 THEN 1 ELSE 0 END AS environment_assertion;

-- Priority ascending, timestamp ascending, unique event ID ascending.
-- Expected IDs: 102, 103, 105, 101, 106, 104.
WITH events(event_id,priority,created_at) AS (
 VALUES (101,2,TIMESTAMP '2026-01-03 09:00'),
 (102,1,TIMESTAMP '2026-01-03 09:05'),
 (103,1,TIMESTAMP '2026-01-03 09:05'),
 (104,3,TIMESTAMP '2026-01-02 20:00'),
 (105,1,TIMESTAMP '2026-01-03 09:05'),
 (106,2,TIMESTAMP '2026-01-04 07:00')
)
SELECT event_id,priority,created_at FROM events
ORDER BY priority ASC,created_at ASC,event_id ASC;

-- Explicit unresolved-first rule; expected IDs: 101,103,106,104,102,105.
WITH events(event_id,resolved_at) AS (
 VALUES (101,NULL::timestamp),
 (102,TIMESTAMP '2026-01-03 10:00'),
 (103,NULL::timestamp),
 (104,TIMESTAMP '2026-01-03 08:00'),
 (105,TIMESTAMP '2026-01-03 11:00'),
 (106,NULL::timestamp)
)
SELECT event_id,resolved_at FROM events
ORDER BY CASE WHEN resolved_at IS NULL THEN 0 ELSE 1 END,
 resolved_at ASC,event_id ASC;

-- Fail-closed checks: exact arrays, NULL placement, row count, PostgreSQL C collation.
WITH events(event_id,service,priority,created_at,resolved_at) AS (
 VALUES
 (101,'api'::text,2,TIMESTAMP '2026-01-03 09:00',NULL::timestamp),
 (102,'ingest',1,TIMESTAMP '2026-01-03 09:05',TIMESTAMP '2026-01-03 10:00'),
 (103,'api',1,TIMESTAMP '2026-01-03 09:05',NULL::timestamp),
 (104,'billing',3,TIMESTAMP '2026-01-02 20:00',TIMESTAMP '2026-01-03 08:00'),
 (105,'ingest',1,TIMESTAMP '2026-01-03 09:05',TIMESTAMP '2026-01-03 11:00'),
 (106,'api',2,TIMESTAMP '2026-01-04 07:00',NULL::timestamp)
), checks AS (
 SELECT
 (SELECT array_agg(event_id ORDER BY priority ASC,created_at ASC,event_id ASC)
  FROM events) = ARRAY[102,103,105,101,106,104] AS priority_order,
 (SELECT array_agg(event_id ORDER BY created_at DESC,event_id DESC)
  FROM events) = ARRAY[106,105,103,102,101,104] AS newest_order,
 (SELECT array_agg(event_id ORDER BY
     CASE WHEN resolved_at IS NULL THEN 0 ELSE 1 END,resolved_at ASC,event_id ASC)
  FROM events) = ARRAY[101,103,106,104,102,105] AS null_first_order,
 (SELECT array_agg(event_id ORDER BY resolved_at ASC NULLS FIRST,event_id ASC)
  FROM events) = ARRAY[101,103,106,104,102,105] AS pg_null_first,
 (SELECT array_agg(event_id ORDER BY service COLLATE "C" ASC,event_id ASC)
  FROM events) = ARRAY[101,103,106,104,102,105] AS c_collation_order,
 (SELECT array_agg(event_id ORDER BY priority DESC,event_id ASC)
  FROM events) = ARRAY[104,101,106,102,103,105] AS priority_desc,
 (SELECT COUNT(*) FROM events) = 6 AS six_rows,
 (SELECT COUNT(DISTINCT event_id) FROM events) = 6 AS unique_ids
)
SELECT 1 / CASE WHEN priority_order AND newest_order AND null_first_order
 AND pg_null_first AND c_collation_order AND priority_desc AND six_rows AND unique_ids
 THEN 1 ELSE 0 END AS acceptance_assertion FROM checks;
ROLLBACK;
