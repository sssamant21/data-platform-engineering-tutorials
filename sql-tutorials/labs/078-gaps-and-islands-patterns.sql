-- Chapter 078: gaps and islands; synthetic read-only PostgreSQL 18 lab.
-- Run only in disposable sql_tutorials database, never production.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/078-gaps-and-islands-patterns.sql
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
SELECT current_database() AS database_name, current_user AS role_name,
       current_setting('server_version') AS server_version,
       inet_server_addr() AS server_ip, inet_server_port() AS server_port;
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer BETWEEN 180000 AND 189999 THEN 1 ELSE 0 END AS version_guard;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials' THEN 1 ELSE 0 END AS database_guard;

-- Islands, deduplicated at (service, batch_no) grain.
WITH events(service,batch_no) AS (
 VALUES ('api',1),('api',2),('api',3),('api',5),('api',6),('api',9),
        ('file',10),('file',11),('file',13),('file',14),('api',5)
), unique_batches AS (
 SELECT DISTINCT service,batch_no FROM events
), numbered AS (
 SELECT service,batch_no,
        ROW_NUMBER() OVER (PARTITION BY service ORDER BY batch_no) AS rn
 FROM unique_batches
), islands AS (
 SELECT service,MIN(batch_no) AS start_batch,MAX(batch_no) AS end_batch,
        COUNT(*) AS batch_count
 FROM (SELECT service,batch_no,batch_no-rn AS island_key FROM numbered) x
 GROUP BY service,island_key
)
SELECT * FROM islands ORDER BY service,start_batch;

-- Internal gaps: no expansion to individual missing positions.
WITH events(service,batch_no) AS (
 VALUES ('api',1),('api',2),('api',3),('api',5),('api',6),('api',9),
        ('file',10),('file',11),('file',13),('file',14),('api',5)
), unique_batches AS (
 SELECT DISTINCT service,batch_no FROM events
), neighbors AS (
 SELECT service,batch_no,
        LAG(batch_no) OVER (PARTITION BY service ORDER BY batch_no) AS prev_batch
 FROM unique_batches
)
SELECT service,prev_batch+1 AS missing_from,batch_no-1 AS missing_through,
       batch_no-prev_batch-1 AS missing_count
FROM neighbors
WHERE prev_batch IS NOT NULL AND batch_no>prev_batch+1
ORDER BY service,missing_from;

-- Exact multiset acceptance: both directions, fail closed.
WITH events(service,batch_no) AS (
 VALUES ('api',1),('api',2),('api',3),('api',5),('api',6),('api',9),
        ('file',10),('file',11),('file',13),('file',14),('api',5)
), unique_batches AS (
 SELECT DISTINCT service,batch_no FROM events
), numbered AS (
 SELECT service,batch_no,
        ROW_NUMBER() OVER (PARTITION BY service ORDER BY batch_no) AS rn,
        LAG(batch_no) OVER (PARTITION BY service ORDER BY batch_no) AS prev_batch
 FROM unique_batches
), actual_islands AS (
 SELECT service,MIN(batch_no) AS start_batch,MAX(batch_no) AS end_batch,
        COUNT(*) AS batch_count
 FROM (SELECT service,batch_no,batch_no-rn AS island_key FROM numbered) n
 GROUP BY service,island_key
), expected_islands(service,start_batch,end_batch,batch_count) AS (
 VALUES ('api',1,3,3::bigint),('api',5,6,2::bigint),('api',9,9,1::bigint),
        ('file',10,11,2::bigint),('file',13,14,2::bigint)
), actual_gaps AS (
 SELECT service,prev_batch+1 AS missing_from,batch_no-1 AS missing_through,
        batch_no-prev_batch-1 AS missing_count
 FROM numbered WHERE prev_batch IS NOT NULL AND batch_no>prev_batch+1
), expected_gaps(service,missing_from,missing_through,missing_count) AS (
 VALUES ('api',4,4,1),('api',7,8,2),('file',12,12,1)
), island_diff AS (
 (SELECT * FROM actual_islands EXCEPT ALL SELECT * FROM expected_islands)
 UNION ALL
 (SELECT * FROM expected_islands EXCEPT ALL SELECT * FROM actual_islands)
), gap_diff AS (
 (SELECT * FROM actual_gaps EXCEPT ALL SELECT * FROM expected_gaps)
 UNION ALL
 (SELECT * FROM expected_gaps EXCEPT ALL SELECT * FROM actual_gaps)
), checks AS (
 SELECT (SELECT COUNT(*)=5 FROM actual_islands) AS islands_ok,
        (SELECT COUNT(*)=3 FROM actual_gaps) AS gap_ranges_ok,
        (SELECT SUM(missing_count)=4 FROM actual_gaps) AS missing_positions_ok,
        (SELECT COUNT(*)=0 FROM island_diff) AS island_multiset_ok,
        (SELECT COUNT(*)=0 FROM gap_diff) AS gap_multiset_ok,
        (SELECT COUNT(*)=10 FROM unique_batches) AS distinct_grain_ok
)
SELECT *,1 / CASE WHEN islands_ok AND gap_ranges_ok AND missing_positions_ok
                        AND island_multiset_ok AND gap_multiset_ok AND distinct_grain_ok
                   THEN 1 ELSE 0 END AS fail_closed_acceptance
FROM checks;
ROLLBACK;
