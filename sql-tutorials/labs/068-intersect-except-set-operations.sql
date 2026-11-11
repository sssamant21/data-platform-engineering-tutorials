-- Chapter 068: INTERSECT / EXCEPT; synthetic, read-only PostgreSQL 18 lab.
-- Verify a disposable endpoint independently; guards are not proof of isolation.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
SELECT current_database() AS database_name,
       current_setting('server_version') AS server_version,
       inet_server_addr() AS server_ip, inet_server_port() AS server_port;
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer BETWEEN 180000 AND 189999 THEN 1 ELSE 0 END AS version_guard;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials' THEN 1 ELSE 0 END AS database_guard;

-- Expected intersection: 102, 103, NULL (3 distinct rows).
WITH source_feed(event_id) AS (
 VALUES (101),(102),(102),(103),(104),(NULL::integer)
), warehouse_feed(event_id) AS (
 VALUES (102),(103),(105),(NULL::integer)
)
SELECT event_id FROM source_feed
INTERSECT
SELECT event_id FROM warehouse_feed
ORDER BY event_id NULLS LAST;

-- Expected source-only distinct: 101,104.
WITH source_feed(event_id) AS (
 VALUES (101),(102),(102),(103),(104),(NULL::integer)
), warehouse_feed(event_id) AS (
 VALUES (102),(103),(105),(NULL::integer)
)
SELECT event_id FROM source_feed
EXCEPT
SELECT event_id FROM warehouse_feed
ORDER BY event_id NULLS LAST;

-- Expected source EXCEPT ALL warehouse: 101,102,104.
WITH source_feed(event_id) AS (
 VALUES (101),(102),(102),(103),(104),(NULL::integer)
), warehouse_feed(event_id) AS (
 VALUES (102),(103),(105),(NULL::integer)
)
SELECT event_id FROM source_feed
EXCEPT ALL
SELECT event_id FROM warehouse_feed
ORDER BY event_id NULLS LAST;

-- Check exact ID sets using IS NOT DISTINCT FROM semantics via EXCEPT and counts.
WITH source_feed(event_id) AS (
 VALUES (101),(102),(102),(103),(104),(NULL::integer)
), warehouse_feed(event_id) AS (
 VALUES (102),(103),(105),(NULL::integer)
), shared AS (
 SELECT event_id FROM source_feed INTERSECT SELECT event_id FROM warehouse_feed
), source_only AS (
 SELECT event_id FROM source_feed EXCEPT SELECT event_id FROM warehouse_feed
), warehouse_only AS (
 SELECT event_id FROM warehouse_feed EXCEPT SELECT event_id FROM source_feed
), shared_all AS (
 SELECT event_id FROM source_feed INTERSECT ALL SELECT event_id FROM warehouse_feed
), source_only_all AS (
 SELECT event_id FROM source_feed EXCEPT ALL SELECT event_id FROM warehouse_feed
), source_known AS (
 SELECT event_id FROM source_feed WHERE event_id IS NOT NULL
), warehouse_known AS (
 SELECT event_id FROM warehouse_feed WHERE event_id IS NOT NULL
), checks AS (
 SELECT
 (SELECT COUNT(*)=6 AND COUNT(event_id)=5 AND COUNT(DISTINCT event_id)=4 FROM source_feed) AS source_counts_ok,
 (SELECT COUNT(*)=4 AND COUNT(event_id)=3 AND COUNT(DISTINCT event_id)=3 FROM warehouse_feed) AS warehouse_counts_ok,
 (SELECT COUNT(*)=3 AND COUNT(event_id)=2 AND MIN(event_id)=102 AND MAX(event_id)=103 FROM shared) AS shared_ok,
 (SELECT COUNT(*)=2 AND MIN(event_id)=101 AND MAX(event_id)=104 FROM source_only) AS source_only_ok,
 (SELECT COUNT(*)=1 AND MIN(event_id)=105 FROM warehouse_only) AS warehouse_only_ok,
 (SELECT COUNT(*)=3 AND COUNT(event_id)=2 FROM shared_all) AS intersect_all_ok,
 (SELECT COUNT(*)=3 AND SUM(event_id)=307 FROM source_only_all) AS except_all_ok,
 (SELECT COUNT(*)=2 FROM (SELECT event_id FROM source_known INTERSECT SELECT event_id FROM warehouse_known) q) AS known_shared_ok,
 (SELECT COUNT(*)=1 FROM source_feed WHERE event_id IS NULL) AS null_source_ok
)
SELECT * FROM checks;

-- Fail closed if any expected result differs.
WITH source_feed(event_id) AS (
 VALUES (101),(102),(102),(103),(104),(NULL::integer)
), warehouse_feed(event_id) AS (
 VALUES (102),(103),(105),(NULL::integer)
), shared AS (
 SELECT event_id FROM source_feed INTERSECT SELECT event_id FROM warehouse_feed
), source_only AS (
 SELECT event_id FROM source_feed EXCEPT SELECT event_id FROM warehouse_feed
), warehouse_only AS (
 SELECT event_id FROM warehouse_feed EXCEPT SELECT event_id FROM source_feed
), shared_all AS (
 SELECT event_id FROM source_feed INTERSECT ALL SELECT event_id FROM warehouse_feed
), source_only_all AS (
 SELECT event_id FROM source_feed EXCEPT ALL SELECT event_id FROM warehouse_feed
)
SELECT 1 / CASE WHEN
 (SELECT COUNT(*)=6 AND COUNT(event_id)=5 AND COUNT(DISTINCT event_id)=4 FROM source_feed)
 AND (SELECT COUNT(*)=4 AND COUNT(event_id)=3 AND COUNT(DISTINCT event_id)=3 FROM warehouse_feed)
 AND (SELECT COUNT(*)=3 AND COUNT(event_id)=2 AND MIN(event_id)=102 AND MAX(event_id)=103 FROM shared)
 AND (SELECT COUNT(*)=2 AND MIN(event_id)=101 AND MAX(event_id)=104 FROM source_only)
 AND (SELECT COUNT(*)=1 AND MIN(event_id)=105 FROM warehouse_only)
 AND (SELECT COUNT(*)=3 AND COUNT(event_id)=2 FROM shared_all)
 AND (SELECT COUNT(*)=3 AND SUM(event_id)=307 FROM source_only_all)
 THEN 1 ELSE 0 END AS acceptance_guard;
ROLLBACK;
