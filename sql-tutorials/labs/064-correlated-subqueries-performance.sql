-- Chapter 064: synthetic, read-only PostgreSQL 18 correlated subquery lab.
-- Verify independently that host/port/container/database are disposable.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
SELECT current_database() AS database_name, current_setting('server_version') AS server_version,
       inet_server_addr() AS server_ip, inet_server_port() AS server_port;
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
                THEN 1 ELSE 0 END AS version_guard;
SELECT 1 / CASE WHEN current_database()='sql_tutorials' THEN 1 ELSE 0 END AS database_guard;

-- Expected above-average batch IDs: 1,5.
WITH batches(batch_id,source,processed) AS (
 VALUES (1,'api',100),(2,'api',40),(3,'api',60),
        (4,'file',30),(5,'file',70),(6,'queue',20)
)
SELECT b.batch_id, b.source, b.processed
FROM batches b
WHERE b.processed > (SELECT AVG(x.processed) FROM batches x WHERE x.source=b.source)
ORDER BY b.batch_id;

-- Expected per-batch alert counts: (1,2),(2,0),(3,0),(4,1),(5,0),(6,1).
WITH batches(batch_id) AS (VALUES (1),(2),(3),(4),(5),(6)),
alerts(alert_id,batch_id) AS (VALUES (101,1),(102,1),(103,4),(104,6))
SELECT b.batch_id,
       (SELECT COUNT(*) FROM alerts a WHERE a.batch_id=b.batch_id) AS alert_count
FROM batches b ORDER BY b.batch_id;

-- EXPLAIN only, not EXPLAIN ANALYZE; no performance conclusion from six rows.
EXPLAIN
WITH batches(batch_id,source,processed) AS (
 VALUES (1,'api',100),(2,'api',40),(3,'api',60),
        (4,'file',30),(5,'file',70),(6,'queue',20)
)
SELECT b.batch_id FROM batches b
WHERE b.processed > (SELECT AVG(x.processed) FROM batches x WHERE x.source=b.source);

-- Assertions: all columns must be TRUE.
WITH batches(batch_id,source,processed) AS (
 VALUES (1,'api',100),(2,'api',40),(3,'api',60),
        (4,'file',30),(5,'file',70),(6,'queue',20)
), alerts(alert_id,batch_id) AS (
 VALUES (101,1),(102,1),(103,4),(104,6)
), correlated AS (
 SELECT b.batch_id FROM batches b
 WHERE b.processed > (SELECT AVG(x.processed) FROM batches x WHERE x.source=b.source)
), grouped AS (
 SELECT b.batch_id FROM batches b
 JOIN (SELECT source,AVG(processed) AS avg_processed FROM batches GROUP BY source) s
   ON s.source=b.source
 WHERE b.processed>s.avg_processed
), flagged AS (
 SELECT b.batch_id FROM batches b
 WHERE EXISTS (SELECT 1 FROM alerts a WHERE a.batch_id=b.batch_id)
), unflagged AS (
 SELECT b.batch_id FROM batches b
 WHERE NOT EXISTS (SELECT 1 FROM alerts a WHERE a.batch_id=b.batch_id)
), alert_counts AS (
 SELECT b.batch_id,(SELECT COUNT(*) FROM alerts a WHERE a.batch_id=b.batch_id) AS n
 FROM batches b
), checks AS (
 SELECT
 (SELECT COUNT(*)=6 AND SUM(processed)=320 FROM batches) AS fixture_ok,
 (SELECT COUNT(*)=4 FROM alerts) AS alerts_ok,
 (SELECT array_agg(batch_id ORDER BY batch_id)=ARRAY[1,5] FROM correlated) AS correlated_ok,
 (SELECT array_agg(batch_id ORDER BY batch_id)=ARRAY[1,5] FROM grouped) AS grouped_ok,
 (SELECT array_agg(batch_id ORDER BY batch_id)=ARRAY[1,4,6] FROM flagged) AS exists_ok,
 (SELECT array_agg(batch_id ORDER BY batch_id)=ARRAY[2,3,5] FROM unflagged) AS not_exists_ok,
 (SELECT array_agg(n ORDER BY batch_id)=ARRAY[2::bigint,0,0,1,0,1] FROM alert_counts) AS counts_ok,
 (SELECT COUNT(*)=3 FROM (SELECT source FROM batches GROUP BY source) s) AS sources_ok
)
SELECT * FROM checks;

-- Fail closed: repeat essential checks as an executable acceptance guard.
WITH batches(batch_id,source,processed) AS (
 VALUES (1,'api',100),(2,'api',40),(3,'api',60),
        (4,'file',30),(5,'file',70),(6,'queue',20)
), alerts(batch_id) AS (VALUES (1),(1),(4),(6)),
above AS (
 SELECT b.batch_id FROM batches b
 WHERE b.processed > (SELECT AVG(x.processed) FROM batches x WHERE x.source=b.source)
), flagged AS (
 SELECT b.batch_id FROM batches b
 WHERE EXISTS (SELECT 1 FROM alerts a WHERE a.batch_id=b.batch_id)
)
SELECT 1 / CASE WHEN
 (SELECT COUNT(*)=6 AND SUM(processed)=320 FROM batches)
 AND (SELECT array_agg(batch_id ORDER BY batch_id)=ARRAY[1,5] FROM above)
 AND (SELECT array_agg(batch_id ORDER BY batch_id)=ARRAY[1,4,6] FROM flagged)
 AND (SELECT COUNT(*)=4 FROM alerts)
 THEN 1 ELSE 0 END AS acceptance_guard;
ROLLBACK;
-- Static expectations only. Runtime validation requires retained execution evidence.
