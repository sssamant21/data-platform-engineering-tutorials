-- Chapter 020, Lab 02: filter and rank operational records.
-- PostgreSQL 18; disposable sql_tutorials database only. Synthetic inline data.
-- Run: psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/020-lab-02-filter-and-rank-operational-records.sql
-- No persistent objects, DDL, or writes. Verify isolation independently.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SELECT 1 / CASE WHEN current_database()='sql_tutorials'
 AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
 THEN 1 ELSE 0 END AS environment_assertion;

-- Ranked six rows. Expected IDs: 401,407,403,405,408,402.
WITH events(event_id,service,severity,latency_ms,owner_team,event_date) AS (
 VALUES
 (401,'api',1,900,'sre',DATE '2026-11-01'),
 (402,'billing',2,300,NULL::text,DATE '2026-11-01'),
 (403,'ingest',1,NULL::integer,'data',DATE '2026-11-02'),
 (404,'api',3,120,'app',DATE '2026-11-02'),
 (405,'search',2,750,'sre',DATE '2026-11-03'),
 (406,'billing',NULL::integer,600,NULL::text,DATE '2026-11-03'),
 (407,'api',1,900,'platform',DATE '2026-11-04'),
 (408,'search',2,750,'data',DATE '2026-11-04')
)
SELECT event_id,service,
 CASE WHEN severity=1 THEN 'P1' WHEN severity=2 THEN 'P2' ELSE 'other' END AS priority,
 COALESCE(owner_team,'unassigned') AS display_owner, latency_ms
FROM events
WHERE severity IN (1,2)
 AND event_date >= DATE '2026-11-01' AND event_date < DATE '2026-11-05'
ORDER BY severity, latency_ms DESC NULLS LAST, event_id;

-- Reconcile exact sorted IDs, pages, counts, NULL behavior and service groups.
WITH events(event_id,service,severity,latency_ms,owner_team,event_date) AS (
 VALUES
 (401,'api',1,900,'sre',DATE '2026-11-01'),
 (402,'billing',2,300,NULL::text,DATE '2026-11-01'),
 (403,'ingest',1,NULL::integer,'data',DATE '2026-11-02'),
 (404,'api',3,120,'app',DATE '2026-11-02'),
 (405,'search',2,750,'sre',DATE '2026-11-03'),
 (406,'billing',NULL::integer,600,NULL::text,DATE '2026-11-03'),
 (407,'api',1,900,'platform',DATE '2026-11-04'),
 (408,'search',2,750,'data',DATE '2026-11-04')
), selected AS (
 SELECT * FROM events WHERE severity IN (1,2)
 AND event_date >= DATE '2026-11-01' AND event_date < DATE '2026-11-05'
), ranked AS (
 SELECT event_id,service,severity,latency_ms,
 ROW_NUMBER() OVER (ORDER BY severity,latency_ms DESC NULLS LAST,event_id) AS rn
 FROM selected
), checks AS (
 SELECT
 (SELECT array_agg(event_id ORDER BY rn) FROM ranked)
   = ARRAY[401,407,403,405,408,402] AS ranking_ok,
 (SELECT array_agg(event_id ORDER BY rn) FROM ranked WHERE rn BETWEEN 1 AND 3)
   = ARRAY[401,407,403] AS page1_ok,
 (SELECT array_agg(event_id ORDER BY rn) FROM ranked WHERE rn BETWEEN 4 AND 6)
   = ARRAY[405,408,402] AS page2_ok,
 (SELECT COUNT(*) FROM selected)=6 AS count_ok,
 (SELECT COUNT(DISTINCT service) FROM selected)=4 AS services_ok,
 (SELECT COUNT(*) FROM selected WHERE latency_ms IS NULL)=1 AS missing_latency_ok,
 (SELECT COUNT(*) FROM events WHERE owner_team IS NULL)=2 AS missing_owner_ok,
 (SELECT array_agg(service || ':' || n::text ORDER BY service)
  FROM (SELECT service,COUNT(*) AS n FROM selected GROUP BY service) AS grouped)
   = ARRAY['api:2','billing:1','ingest:1','search:2'] AS grouped_ok
)
SELECT 1 / CASE WHEN ranking_ok AND page1_ok AND page2_ok
 AND count_ok AND services_ok AND missing_latency_ok AND missing_owner_ok AND grouped_ok
 THEN 1 ELSE 0 END AS acceptance_assertion FROM checks;
ROLLBACK;
