-- 071: Window-function anatomy, synthetic six-batch workload.
-- PostgreSQL 18 only; execute ONLY on an independently verified disposable instance.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
SELECT current_database() AS database_name, current_setting('server_version') AS server_version,
       inet_server_addr() AS server_ip, inet_server_port() AS server_port;
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer BETWEEN 180000 AND 189999 THEN 1 ELSE 0 END AS version_guard;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials' THEN 1 ELSE 0 END AS database_guard;

-- Six rows retained; grand total 230; API 120, FILE 110.
WITH batches(batch_id,service,records) AS (
 VALUES (1,'api',40),(2,'api',60),(3,'file',30),
        (4,'file',70),(5,'api',20),(6,'file',10)
)
SELECT batch_id,service,records,
       SUM(records) OVER () AS grand_total,
       SUM(records) OVER (PARTITION BY service) AS service_total,
       SUM(records) OVER (
         PARTITION BY service ORDER BY batch_id
         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS service_running_total
FROM batches ORDER BY batch_id;

-- GROUP BY reduces the grain to two service rows.
WITH batches(batch_id,service,records) AS (
 VALUES (1,'api',40),(2,'api',60),(3,'file',30),
        (4,'file',70),(5,'api',20),(6,'file',10)
)
SELECT service,COUNT(*) AS batch_count,SUM(records) AS service_total
FROM batches GROUP BY service ORDER BY service;

-- Fail-closed acceptance: exact ordered rows and totals, including grouped reconciliation.
WITH batches(batch_id,service,records) AS (
 VALUES (1,'api',40),(2,'api',60),(3,'file',30),
        (4,'file',70),(5,'api',20),(6,'file',10)
), windowed AS (
 SELECT batch_id,service,records,
        SUM(records) OVER () AS grand_total,
        SUM(records) OVER (PARTITION BY service) AS service_total,
        SUM(records) OVER (
          PARTITION BY service ORDER BY batch_id
          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS running_total,
        COUNT(*) OVER (PARTITION BY service) AS partition_count
 FROM batches
), grouped AS (
 SELECT service,SUM(records) AS service_total FROM batches GROUP BY service
), checks AS (
 SELECT
  (SELECT COUNT(*)=6 FROM windowed) AS row_count_ok,
  (SELECT COUNT(*)=2 FROM grouped) AS group_count_ok,
  (SELECT COALESCE(bool_and(grand_total=230),false) FROM windowed) AS grand_total_ok,
  (SELECT COALESCE(bool_and(service_total=CASE service WHEN 'api' THEN 120 ELSE 110 END),false) FROM windowed) AS partition_total_ok,
  (SELECT COALESCE(bool_and(partition_count=3),false) FROM windowed) AS partition_count_ok,
  (SELECT array_agg(running_total ORDER BY batch_id)=ARRAY[40,100,30,100,120,110] FROM windowed) AS running_totals_ok,
  (SELECT COUNT(*)=0 FROM windowed w JOIN grouped g USING(service)
   WHERE w.service_total IS DISTINCT FROM g.service_total) AS reconciliation_ok
)
SELECT *, 1 / CASE WHEN row_count_ok AND group_count_ok AND grand_total_ok
 AND partition_total_ok AND partition_count_ok AND running_totals_ok
 AND reconciliation_ok THEN 1 ELSE 0 END AS fail_closed_acceptance
FROM checks;
ROLLBACK;
