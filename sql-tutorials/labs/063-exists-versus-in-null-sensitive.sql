-- 063 EXISTS versus IN: synthetic read-only PostgreSQL 18 lab.
-- Independently verify an isolated disposable endpoint before running.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
SELECT current_database() AS database_name, current_setting('server_version') AS server_version,
       inet_server_addr() AS server_ip, inet_server_port() AS server_port;
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
                THEN 1 ELSE 0 END AS version_guard;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials' THEN 1 ELSE 0 END AS database_guard;

-- EXISTS: expected IDs 1,3,6; duplicate alerts do not multiply batches.
WITH batches(batch_id) AS (VALUES (1),(2),(3),(4),(5),(6)),
alerts(alert_id,batch_id) AS (
 VALUES (101,1),(102,1),(103,3),(104,NULL::integer),(105,6)
)
SELECT b.batch_id FROM batches b
WHERE EXISTS (SELECT 1 FROM alerts a WHERE a.batch_id=b.batch_id)
ORDER BY b.batch_id;

-- IN: same filtered IDs; NULL lookup makes nonmatch UNKNOWN.
WITH batches(batch_id) AS (VALUES (1),(2),(3),(4),(5),(6)),
alerts(batch_id) AS (VALUES (1),(1),(3),(NULL::integer),(6))
SELECT b.batch_id FROM batches b WHERE b.batch_id IN (SELECT batch_id FROM alerts)
ORDER BY b.batch_id;

-- NOT EXISTS: expected 2,4,5.
WITH batches(batch_id) AS (VALUES (1),(2),(3),(4),(5),(6)),
alerts(batch_id) AS (VALUES (1),(1),(3),(NULL::integer),(6))
SELECT b.batch_id FROM batches b
WHERE NOT EXISTS (SELECT 1 FROM alerts a WHERE a.batch_id=b.batch_id)
ORDER BY b.batch_id;

-- NULL-bearing NOT IN: expected zero rows.
WITH batches(batch_id) AS (VALUES (1),(2),(3),(4),(5),(6)),
alerts(batch_id) AS (VALUES (1),(1),(3),(NULL::integer),(6))
SELECT b.batch_id FROM batches b WHERE b.batch_id NOT IN (SELECT batch_id FROM alerts)
ORDER BY b.batch_id;

-- A nonmatch differs in raw Boolean truth value: FALSE versus NULL.
WITH alerts(batch_id) AS (VALUES (1),(1),(3),(NULL::integer),(6))
SELECT EXISTS (SELECT 1 FROM alerts a WHERE a.batch_id=2) AS exists_nonmatch,
       2 IN (SELECT batch_id FROM alerts) AS in_nonmatch,
       EXISTS (SELECT NULL) AS exists_null_row,
       NULL::integer IS NOT DISTINCT FROM NULL::integer AS null_safe_equality;

-- Acceptance: all checks must be TRUE. No persistent objects or writes.
WITH batches(batch_id,source,processed) AS (
 VALUES (1,'api',100),(2,'file',50),(3,'api',70),
        (4,'file',20),(5,'api',NULL::integer),(6,'file',40)
), alerts(alert_id,batch_id,kind) AS (
 VALUES (101,1,'error'),(102,1,'warning'),(103,3,'error'),
        (104,NULL::integer,'orphan'),(105,6,'warning')
), flagged AS (
 SELECT b.batch_id FROM batches b
 WHERE EXISTS (SELECT 1 FROM alerts a WHERE a.batch_id=b.batch_id)
), unflagged AS (
 SELECT b.batch_id FROM batches b
 WHERE NOT EXISTS (SELECT 1 FROM alerts a WHERE a.batch_id=b.batch_id)
), via_in AS (
 SELECT b.batch_id FROM batches b WHERE b.batch_id IN (SELECT batch_id FROM alerts)
), via_not_in AS (
 SELECT b.batch_id FROM batches b WHERE b.batch_id NOT IN (SELECT batch_id FROM alerts)
), checks AS (
 SELECT
 (SELECT COUNT(*)=6 AND COUNT(processed)=5 AND SUM(processed)=280 FROM batches) AS fixture_ok,
 (SELECT COUNT(*)=5 AND COUNT(DISTINCT batch_id)=3
         AND COUNT(*) FILTER (WHERE batch_id IS NULL)=1 FROM alerts) AS alerts_ok,
 (SELECT array_agg(batch_id ORDER BY batch_id)=ARRAY[1,3,6] FROM flagged) AS exists_ok,
 (SELECT array_agg(batch_id ORDER BY batch_id)=ARRAY[1,3,6] FROM via_in) AS in_ok,
 (SELECT array_agg(batch_id ORDER BY batch_id)=ARRAY[2,4,5] FROM unflagged) AS not_exists_ok,
 (SELECT COUNT(*)=0 FROM via_not_in) AS not_in_null_ok,
 (SELECT COUNT(*)=6 FROM flagged)=FALSE AS not_every_batch_flagged,
 (2 IN (SELECT batch_id FROM alerts)) IS UNKNOWN AS in_unknown_ok,
 (EXISTS (SELECT 1 FROM alerts a WHERE a.batch_id=2)) IS FALSE AS exists_false_ok,
 (EXISTS (SELECT NULL)) IS TRUE AS exists_null_row_ok
)
SELECT * FROM checks;

-- Fail closed if any assertion is false or unknown.
WITH batches(batch_id,processed) AS (
 VALUES (1,100),(2,50),(3,70),(4,20),(5,NULL::integer),(6,40)
), alerts(batch_id) AS (VALUES (1),(1),(3),(NULL::integer),(6)),
checks AS (
 SELECT
 (SELECT COUNT(*)=6 AND SUM(processed)=280 FROM batches) AS a,
 (SELECT array_agg(batch_id ORDER BY batch_id)=ARRAY[1,3,6] FROM batches b
   WHERE EXISTS (SELECT 1 FROM alerts x WHERE x.batch_id=b.batch_id)) AS b,
 (SELECT array_agg(batch_id ORDER BY batch_id)=ARRAY[2,4,5] FROM batches b
   WHERE NOT EXISTS (SELECT 1 FROM alerts x WHERE x.batch_id=b.batch_id)) AS c,
 (SELECT COUNT(*)=0 FROM batches b WHERE b.batch_id NOT IN
   (SELECT batch_id FROM alerts)) AS d,
 (SELECT COUNT(*)=1 FROM alerts WHERE batch_id IS NULL) AS e
)
SELECT 1 / CASE WHEN COALESCE(a AND b AND c AND d AND e,FALSE) THEN 1 ELSE 0 END
       AS acceptance_guard FROM checks;
ROLLBACK;
-- Static expectations only: no PostgreSQL 18 execution claimed.
