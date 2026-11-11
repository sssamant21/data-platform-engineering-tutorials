-- Chapter 062: IN, ANY, ALL, multi-row subqueries. Synthetic read-only PostgreSQL 18.
-- Independently verify a disposable endpoint; guards below do NOT prove isolation.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
SELECT current_database() AS database_name,
       current_setting('server_version') AS server_version,
       inet_server_addr() AS server_ip, inet_server_port() AS server_port;
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer
                    BETWEEN 180000 AND 189999 THEN 1 ELSE 0 END AS version_guard;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials'
                    THEN 1 ELSE 0 END AS database_guard;

-- Membership: expected batch IDs 1, 2, 5, 6.
WITH batches(batch_id,region) AS (
 VALUES (1,'East'),(2,'East'),(3,'West'),(4,'West'),(5,'North'),(6,'North')
)
SELECT batch_id FROM batches
WHERE region IN (SELECT region FROM (VALUES ('East'),('North')) AS selected(region))
ORDER BY batch_id;

-- Greater than at least one threshold: expected 1, 2, 3.
WITH batches(batch_id,processed) AS (
 VALUES (1,120),(2,80),(3,50),(4,30),(5,10),(6,NULL::integer)
)
SELECT batch_id FROM batches
WHERE processed > ANY (SELECT threshold FROM (VALUES (40),(90)) AS t(threshold))
ORDER BY batch_id;

-- Greater than every threshold: expected 1.
WITH batches(batch_id,processed) AS (
 VALUES (1,120),(2,80),(3,50),(4,30),(5,10),(6,NULL::integer)
)
SELECT batch_id FROM batches
WHERE processed > ALL (SELECT threshold FROM (VALUES (40),(90)) AS t(threshold))
ORDER BY batch_id;

-- NULL-bearing NOT IN: expected zero rows.
SELECT b.batch_id FROM (VALUES (1),(2),(3)) AS b(batch_id)
WHERE b.batch_id NOT IN (
 SELECT x.id FROM (VALUES (2),(NULL::integer)) AS x(id)
)
ORDER BY b.batch_id;

-- Explicitly exclude NULL from lookup: expected IDs 1, 3.
SELECT b.batch_id FROM (VALUES (1),(2),(3)) AS b(batch_id)
WHERE b.batch_id NOT IN (
 SELECT x.id FROM (VALUES (2),(NULL::integer)) AS x(id) WHERE x.id IS NOT NULL
)
ORDER BY b.batch_id;

-- Empty set semantics: expected f, t, f (even for NULL left side, ALL empty = true).
SELECT
  50 > ANY (SELECT v.n FROM (VALUES (40)) AS v(n) WHERE FALSE) AS any_empty,
  50 > ALL (SELECT v.n FROM (VALUES (40)) AS v(n) WHERE FALSE) AS all_empty,
  50 IN (SELECT v.n FROM (VALUES (40)) AS v(n) WHERE FALSE) AS in_empty,
  NULL::integer > ALL (SELECT v.n FROM (VALUES (40)) AS v(n) WHERE FALSE) AS null_all_empty;

-- Acceptance assertions: all must be TRUE; fail closed if not.
WITH batches(batch_id,region,processed) AS (
 VALUES (1,'East',120),(2,'East',80),(3,'West',50),
        (4,'West',30),(5,'North',10),(6,'North',NULL::integer)
), thresholds(threshold) AS (VALUES (40),(90)),
 membership AS (
 SELECT batch_id FROM batches
 WHERE region IN (SELECT region FROM (VALUES ('East'),('North')) AS r(region))
), any_matches AS (
 SELECT batch_id FROM batches WHERE processed > ANY (SELECT threshold FROM thresholds)
), all_matches AS (
 SELECT batch_id FROM batches WHERE processed > ALL (SELECT threshold FROM thresholds)
), null_not_in AS (
 SELECT b.batch_id FROM (VALUES (1),(2),(3)) AS b(batch_id)
 WHERE b.batch_id NOT IN (SELECT id FROM (VALUES (2),(NULL::integer)) AS x(id))
), filtered_not_in AS (
 SELECT b.batch_id FROM (VALUES (1),(2),(3)) AS b(batch_id)
 WHERE b.batch_id NOT IN (
   SELECT id FROM (VALUES (2),(NULL::integer)) AS x(id) WHERE id IS NOT NULL
 )
), checks AS (
 SELECT
 (SELECT COUNT(*)=6 AND COUNT(processed)=5 AND SUM(processed)=290 FROM batches) AS fixture_ok,
 (SELECT array_agg(batch_id ORDER BY batch_id)=ARRAY[1,2,5,6] FROM membership) AS in_ok,
 (SELECT array_agg(batch_id ORDER BY batch_id)=ARRAY[1,2,3] FROM any_matches) AS any_ok,
 (SELECT array_agg(batch_id ORDER BY batch_id)=ARRAY[1] FROM all_matches) AS all_ok,
 (SELECT COUNT(*)=0 FROM null_not_in) AS null_not_in_ok,
 (SELECT array_agg(batch_id ORDER BY batch_id)=ARRAY[1,3] FROM filtered_not_in) AS filtered_not_in_ok,
 (50 > ANY (SELECT threshold FROM thresholds WHERE FALSE)) IS FALSE AS empty_any_ok,
 (50 > ALL (SELECT threshold FROM thresholds WHERE FALSE)) IS TRUE AS empty_all_ok,
 (NULL::integer > ALL (SELECT threshold FROM thresholds WHERE FALSE)) IS TRUE AS null_empty_all_ok
)
SELECT * FROM checks;
WITH batches(batch_id,region,processed) AS (
 VALUES (1,'East',120),(2,'East',80),(3,'West',50),
        (4,'West',30),(5,'North',10),(6,'North',NULL::integer)
), thresholds(threshold) AS (VALUES (40),(90)),
 checks AS (
 SELECT
 (SELECT COUNT(*)=6 AND COUNT(processed)=5 AND SUM(processed)=290 FROM batches) AS a,
 (SELECT array_agg(batch_id ORDER BY batch_id)=ARRAY[1,2,5,6]
  FROM batches WHERE region IN (SELECT region FROM (VALUES ('East'),('North')) AS r(region))) AS b,
 (SELECT array_agg(batch_id ORDER BY batch_id)=ARRAY[1,2,3]
  FROM batches WHERE processed > ANY (SELECT threshold FROM thresholds)) AS c,
 (SELECT array_agg(batch_id ORDER BY batch_id)=ARRAY[1]
  FROM batches WHERE processed > ALL (SELECT threshold FROM thresholds)) AS d,
 (SELECT COUNT(*)=0 FROM (SELECT b.batch_id FROM (VALUES (1),(2),(3)) AS b(batch_id)
  WHERE b.batch_id NOT IN (SELECT id FROM (VALUES (2),(NULL::integer)) AS x(id))) AS z) AS e,
 (50 > ALL (SELECT threshold FROM thresholds WHERE FALSE)) IS TRUE AS f
)
SELECT 1 / CASE WHEN COALESCE(a AND b AND c AND d AND e AND f,FALSE)
                    THEN 1 ELSE 0 END AS acceptance_guard FROM checks;
ROLLBACK;
-- Static expectations are NOT runtime evidence.
