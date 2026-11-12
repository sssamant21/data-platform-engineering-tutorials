-- Chapter 099: keyset pagination, benchmarking and regression tests.
-- PostgreSQL 18 only; synthetic read-only lab, no persistent objects.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/099-keyset-pagination-benchmark-regression.sql
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout='15s';
SET LOCAL lock_timeout='2s';
SET LOCAL idle_in_transaction_session_timeout='30s';

DO $guard$
BEGIN
 IF current_database() <> 'sql_tutorials' THEN
  RAISE EXCEPTION 'Isolated sql_tutorials database required; found %',current_database();
 END IF;
 IF current_setting('server_version_num')::integer / 10000 <> 18 THEN
  RAISE EXCEPTION 'PostgreSQL 18 required; found %',current_setting('server_version');
 END IF;
END
$guard$;

-- Estimated plan only. No index or physical table exists in this fixture.
EXPLAIN (COSTS ON)
WITH events(event_id,event_time) AS (
 VALUES (109,timestamp '2026-11-01 12:05'),
        (108,timestamp '2026-11-01 12:04'),
        (107,timestamp '2026-11-01 12:04'),
        (106,timestamp '2026-11-01 12:03'),
        (105,timestamp '2026-11-01 12:02'),
        (104,timestamp '2026-11-01 12:02'),
        (103,timestamp '2026-11-01 12:01'),
        (102,timestamp '2026-11-01 12:00'),
        (101,timestamp '2026-11-01 11:59')
)
SELECT event_id FROM events
WHERE (event_time,event_id) < (timestamp '2026-11-01 12:04',107)
ORDER BY event_time DESC,event_id DESC LIMIT 3;

-- Display all three pages in order; fixed synthetic data only.
WITH events(event_id,event_time) AS (
 VALUES (109,timestamp '2026-11-01 12:05'),
        (108,timestamp '2026-11-01 12:04'),
        (107,timestamp '2026-11-01 12:04'),
        (106,timestamp '2026-11-01 12:03'),
        (105,timestamp '2026-11-01 12:02'),
        (104,timestamp '2026-11-01 12:02'),
        (103,timestamp '2026-11-01 12:01'),
        (102,timestamp '2026-11-01 12:00'),
        (101,timestamp '2026-11-01 11:59')
), page1 AS (
 SELECT * FROM events ORDER BY event_time DESC,event_id DESC LIMIT 3
), page2 AS (
 SELECT * FROM events
 WHERE (event_time,event_id) < (SELECT event_time,event_id FROM page1 ORDER BY event_time,event_id LIMIT 1)
 ORDER BY event_time DESC,event_id DESC LIMIT 3
), page3 AS (
 SELECT * FROM events
 WHERE (event_time,event_id) < (SELECT event_time,event_id FROM page2 ORDER BY event_time,event_id LIMIT 1)
 ORDER BY event_time DESC,event_id DESC LIMIT 3
)
SELECT page,event_id,event_time FROM (
 SELECT 1 AS page,* FROM page1 UNION ALL
 SELECT 2 AS page,* FROM page2 UNION ALL
 SELECT 3 AS page,* FROM page3
) pages ORDER BY page,event_time DESC,event_id DESC;

DO $assert$
DECLARE mismatch_count bigint; total_rows bigint; pages_count bigint;
BEGIN
 WITH events(event_id,event_time) AS (
  VALUES (109,timestamp '2026-11-01 12:05'),
         (108,timestamp '2026-11-01 12:04'),
         (107,timestamp '2026-11-01 12:04'),
         (106,timestamp '2026-11-01 12:03'),
         (105,timestamp '2026-11-01 12:02'),
         (104,timestamp '2026-11-01 12:02'),
         (103,timestamp '2026-11-01 12:01'),
         (102,timestamp '2026-11-01 12:00'),
         (101,timestamp '2026-11-01 11:59')
 ), page1 AS (
  SELECT * FROM events ORDER BY event_time DESC,event_id DESC LIMIT 3
 ), page2 AS (
  SELECT * FROM events
  WHERE (event_time,event_id) < (SELECT event_time,event_id FROM page1 ORDER BY event_time,event_id LIMIT 1)
  ORDER BY event_time DESC,event_id DESC LIMIT 3
 ), page3 AS (
  SELECT * FROM events
  WHERE (event_time,event_id) < (SELECT event_time,event_id FROM page2 ORDER BY event_time,event_id LIMIT 1)
  ORDER BY event_time DESC,event_id DESC LIMIT 3
 ), actual AS (
  SELECT 1 AS page,event_id FROM page1 UNION ALL
  SELECT 2 AS page,event_id FROM page2 UNION ALL
  SELECT 3 AS page,event_id FROM page3
 ), expected(page,event_id) AS (
  VALUES (1,109),(1,108),(1,107),
         (2,106),(2,105),(2,104),
         (3,103),(3,102),(3,101)
 ), offset_pages AS (
  SELECT 1 AS page,event_id FROM
    (SELECT event_id FROM events ORDER BY event_time DESC,event_id DESC LIMIT 3 OFFSET 0) q
  UNION ALL
  SELECT 2 AS page,event_id FROM
    (SELECT event_id FROM events ORDER BY event_time DESC,event_id DESC LIMIT 3 OFFSET 3) q
  UNION ALL
  SELECT 3 AS page,event_id FROM
    (SELECT event_id FROM events ORDER BY event_time DESC,event_id DESC LIMIT 3 OFFSET 6) q
 ), diffs AS (
  (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
  UNION ALL (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
  UNION ALL (SELECT * FROM actual EXCEPT ALL SELECT * FROM offset_pages)
  UNION ALL (SELECT * FROM offset_pages EXCEPT ALL SELECT * FROM actual)
 )
 SELECT (SELECT count(*) FROM diffs),
        (SELECT count(*) FROM actual),
        (SELECT count(DISTINCT page) FROM actual)
 INTO mismatch_count,total_rows,pages_count;
 IF mismatch_count <> 0 OR total_rows <> 9 OR pages_count <> 3 THEN
  RAISE EXCEPTION '099 regression failure: mismatches %, rows %, pages %',
   mismatch_count,total_rows,pages_count;
 END IF;
 RAISE NOTICE '099 assertions passed: 9 rows, 3 pages, no mismatch';
END
$assert$;
ROLLBACK;
