-- Chapter 019: CASE, COALESCE, NULLIF. PostgreSQL 18 only.
-- Run ONLY against an independently verified disposable sql_tutorials database.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/019-case-coalesce-nullif.sql
-- Synthetic inline data only; no writes or persistent objects.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials'
 AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
 THEN 1 ELSE 0 END AS environment_assertion;

-- Expected priorities: critical, warning, unclassified, informational, critical, warning.
WITH events(event_id,severity) AS (
 VALUES (301,1),(302,2),(303,NULL::integer),(304,3),(305,1),(306,2)
)
SELECT event_id,
 CASE WHEN severity IS NULL THEN 'unclassified'
      WHEN severity=1 THEN 'critical'
      WHEN severity=2 THEN 'warning'
      ELSE 'informational' END AS priority
FROM events ORDER BY event_id;

-- Expected owners: platform, unassigned, data, unassigned, sre, app.
WITH events(event_id,owner_team) AS (
 VALUES (301,'platform'),(302,NULL),(303,'data'),(304,NULL),(305,'sre'),(306,'app')
)
SELECT event_id, COALESCE(owner_team,'unassigned') AS display_owner
FROM events ORDER BY event_id;

-- Expected rates: 5.00, NULL, 4.00, 0.00, NULL, NULL.
WITH events(event_id,requests,errors) AS (
 VALUES (301,100,5),(302,0,0),(303,50,2),(304,20,0),
        (305,NULL::integer,1),(306,40,NULL::integer)
)
SELECT event_id, ROUND(100.0*errors/NULLIF(requests,0),2) AS error_pct
FROM events ORDER BY event_id;

-- Fail-closed exact assertions, including NULL position and classification.
WITH events(event_id,severity,owner_team,requests,errors) AS (
 VALUES (301,1,'platform',100,5),
        (302,2,NULL::text,0,0),
        (303,NULL::integer,'data',50,2),
        (304,3,NULL::text,20,0),
        (305,1,'sre',NULL::integer,1),
        (306,2,'app',40,NULL::integer)
), classified AS (
 SELECT event_id,owner_team,requests,errors,
 CASE WHEN severity IS NULL THEN 'unclassified'
      WHEN severity=1 THEN 'critical'
      WHEN severity=2 THEN 'warning'
      ELSE 'informational' END AS priority,
 COALESCE(owner_team,'unassigned') AS display_owner,
 ROUND(100.0*errors/NULLIF(requests,0),2) AS error_pct
 FROM events
), checks AS (
 SELECT
  (SELECT array_agg(priority ORDER BY event_id) FROM classified)
   = ARRAY['critical','warning','unclassified','informational','critical','warning'] AS priority_ok,
  (SELECT array_agg(display_owner ORDER BY event_id) FROM classified)
   = ARRAY['platform','unassigned','data','unassigned','sre','app'] AS owner_ok,
  (SELECT array_agg(error_pct ORDER BY event_id) FROM classified)
   IS NOT DISTINCT FROM ARRAY[5.00,NULL,4.00,0.00,NULL,NULL]::numeric[] AS rates_ok,
  (SELECT COUNT(*) FROM classified WHERE owner_team IS NULL)=2 AS missing_owner_ok,
  (SELECT COUNT(*) FROM classified WHERE requests=0)=1 AS zero_requests_ok,
  (SELECT COUNT(*) FROM classified)=6 AS row_count_ok
)
SELECT 1 / CASE WHEN priority_ok AND owner_ok AND rates_ok
 AND missing_owner_ok AND zero_requests_ok AND row_count_ok
 THEN 1 ELSE 0 END AS acceptance_assertion FROM checks;
ROLLBACK;
