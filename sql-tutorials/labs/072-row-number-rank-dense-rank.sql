-- Chapter 072: ROW_NUMBER, RANK, DENSE_RANK. Synthetic data only.
-- PostgreSQL 18; independently verify a disposable endpoint and least-privilege role.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
SELECT current_database() AS database_name, current_setting('server_version') AS server_version,
       inet_server_addr() AS server_ip, inet_server_port() AS server_port;
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer BETWEEN 180000 AND 189999 THEN 1 ELSE 0 END AS version_guard;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials' THEN 1 ELSE 0 END AS database_guard;

-- Show complete ranks with deterministic row numbering and explicit NULL placement.
WITH batches(batch_id,service,records) AS (
 VALUES (1,'api',90),(2,'api',70),(3,'api',90),(4,'api',40),
        (5,'file',60),(6,'file',60),(7,'file',30),(8,'file',NULL)
)
SELECT batch_id,service,records,
 ROW_NUMBER() OVER (PARTITION BY service ORDER BY CASE WHEN records IS NULL THEN 1 ELSE 0 END,records DESC,batch_id) AS row_num,
 RANK() OVER (PARTITION BY service ORDER BY CASE WHEN records IS NULL THEN 1 ELSE 0 END,records DESC) AS competition_rank,
 DENSE_RANK() OVER (PARTITION BY service ORDER BY CASE WHEN records IS NULL THEN 1 ELSE 0 END,records DESC) AS dense_rank
FROM batches ORDER BY service,row_num;

-- One deterministic winner per service.
WITH batches(batch_id,service,records) AS (
 VALUES (1,'api',90),(2,'api',70),(3,'api',90),(4,'api',40),
        (5,'file',60),(6,'file',60),(7,'file',30),(8,'file',NULL)
), numbered AS (
 SELECT batch_id,service,records,
 ROW_NUMBER() OVER (PARTITION BY service ORDER BY CASE WHEN records IS NULL THEN 1 ELSE 0 END,records DESC,batch_id) AS rn
 FROM batches
)
SELECT service,batch_id,records FROM numbered WHERE rn=1 ORDER BY service;

-- All tied leaders.
WITH batches(batch_id,service,records) AS (
 VALUES (1,'api',90),(2,'api',70),(3,'api',90),(4,'api',40),
        (5,'file',60),(6,'file',60),(7,'file',30),(8,'file',NULL)
), ranked AS (
 SELECT batch_id,service,records,
 RANK() OVER (PARTITION BY service ORDER BY CASE WHEN records IS NULL THEN 1 ELSE 0 END,records DESC) AS rnk
 FROM batches
)
SELECT service,batch_id,records FROM ranked WHERE rnk=1 ORDER BY service,batch_id;

-- Fail closed if any expected row, rank, winner, NULL, or partition count differs.
WITH batches(batch_id,service,records) AS (
 VALUES (1,'api',90),(2,'api',70),(3,'api',90),(4,'api',40),
        (5,'file',60),(6,'file',60),(7,'file',30),(8,'file',NULL)
), ranked AS (
 SELECT batch_id,service,records,
 ROW_NUMBER() OVER (PARTITION BY service ORDER BY CASE WHEN records IS NULL THEN 1 ELSE 0 END,records DESC,batch_id) AS rn,
 RANK() OVER (PARTITION BY service ORDER BY CASE WHEN records IS NULL THEN 1 ELSE 0 END,records DESC) AS rnk,
 DENSE_RANK() OVER (PARTITION BY service ORDER BY CASE WHEN records IS NULL THEN 1 ELSE 0 END,records DESC) AS drnk
 FROM batches
), expected(service,batch_id,records,rn,rnk,drnk) AS (
 VALUES ('api',1,90,1::bigint,1::bigint,1::bigint),
 ('api',3,90,2::bigint,1::bigint,1::bigint),
 ('api',2,70,3::bigint,3::bigint,2::bigint),
 ('api',4,40,4::bigint,4::bigint,3::bigint),
 ('file',5,60,1::bigint,1::bigint,1::bigint),
 ('file',6,60,2::bigint,1::bigint,1::bigint),
 ('file',7,30,3::bigint,3::bigint,2::bigint),
 ('file',8,NULL::integer,4::bigint,4::bigint,3::bigint)
), mismatches AS (
 (SELECT * FROM ranked EXCEPT ALL SELECT * FROM expected)
 UNION ALL
 (SELECT * FROM expected EXCEPT ALL SELECT * FROM ranked)
), checks AS (
 SELECT
 (SELECT COUNT(*)=8 FROM ranked) AS row_count_ok,
 (SELECT COUNT(*)=2 FROM (SELECT service FROM ranked GROUP BY service HAVING COUNT(*)=4) s) AS partition_count_ok,
 (SELECT COUNT(*)=1 FROM ranked WHERE records IS NULL AND batch_id=8 AND rn=4) AS null_last_ok,
 (SELECT array_agg(batch_id ORDER BY service)=ARRAY[1,5] FROM ranked WHERE rn=1) AS winners_ok,
 (SELECT array_agg(batch_id ORDER BY batch_id)=ARRAY[1,3,5,6] FROM ranked WHERE rnk=1) AS tied_leaders_ok,
 (SELECT COUNT(*)=0 FROM mismatches) AS exact_rows_ok
)
SELECT *, 1 / CASE WHEN row_count_ok AND partition_count_ok AND null_last_ok
 AND winners_ok AND tied_leaders_ok AND exact_rows_ok THEN 1 ELSE 0 END AS fail_closed_acceptance
FROM checks;
ROLLBACK;
