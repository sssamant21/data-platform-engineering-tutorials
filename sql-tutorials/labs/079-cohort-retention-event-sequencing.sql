-- Chapter 079: synthetic, read-only PostgreSQL 18 cohort retention and event sequencing.
-- Run only on a disposable local sql_tutorials database; never production.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/079-cohort-retention-event-sequencing.sql
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

SELECT current_database() AS database_name, current_user AS role_name,
       current_setting('server_version') AS server_version,
       inet_server_addr() AS server_ip, inet_server_port() AS server_port;
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
                THEN 1 ELSE 0 END AS version_guard;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials'
                THEN 1 ELSE 0 END AS database_guard;

-- Synthetic events are pre-normalized to a single reporting timezone.
-- Distinct users (not event counts) determine cohort activity.
WITH events(user_id,event_id,event_day) AS (
 VALUES (1,101,DATE '2026-01-05'),(1,102,DATE '2026-01-12'),
        (1,103,DATE '2026-01-19'),(2,201,DATE '2026-01-06'),
        (2,202,DATE '2026-01-13'),(3,301,DATE '2026-01-07'),
        (4,401,DATE '2026-01-12'),(4,402,DATE '2026-01-20'),
        (5,501,DATE '2026-01-13'),(6,601,DATE '2026-01-19')
), annotated AS (
 SELECT *, MIN(event_day) OVER (PARTITION BY user_id) AS first_day,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY event_day,event_id) AS event_number,
        LAG(event_day) OVER (PARTITION BY user_id ORDER BY event_day,event_id) AS previous_day
 FROM events
), weekly_users AS (
 SELECT DISTINCT user_id, date_trunc('week',first_day)::date AS cohort_week,
        date_trunc('week',event_day)::date AS activity_week
 FROM annotated
), sizes AS (
 SELECT cohort_week,COUNT(*) AS cohort_size FROM weekly_users
 WHERE cohort_week=activity_week GROUP BY cohort_week
), retention AS (
 SELECT cohort_week, ((activity_week-cohort_week)/7) AS week_number,
        COUNT(*) AS active_users
 FROM weekly_users GROUP BY cohort_week,activity_week
)
SELECT r.cohort_week,r.week_number,s.cohort_size,r.active_users,
       ROUND(100.0*r.active_users/NULLIF(s.cohort_size,0),2) AS retention_pct
FROM retention r JOIN sizes s USING (cohort_week)
ORDER BY r.cohort_week,r.week_number;

-- Exact multiset acceptance plus sequencing, all using synthetic inline rows.
WITH events(user_id,event_id,event_day) AS (
 VALUES (1,101,DATE '2026-01-05'),(1,102,DATE '2026-01-12'),
        (1,103,DATE '2026-01-19'),(2,201,DATE '2026-01-06'),
        (2,202,DATE '2026-01-13'),(3,301,DATE '2026-01-07'),
        (4,401,DATE '2026-01-12'),(4,402,DATE '2026-01-20'),
        (5,501,DATE '2026-01-13'),(6,601,DATE '2026-01-19')
), annotated AS (
 SELECT *,MIN(event_day) OVER (PARTITION BY user_id) AS first_day,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY event_day,event_id) AS event_number,
        LAG(event_day) OVER (PARTITION BY user_id ORDER BY event_day,event_id) AS previous_day
 FROM events
), weekly_users AS (
 SELECT DISTINCT user_id,date_trunc('week',first_day)::date AS cohort_week,
        date_trunc('week',event_day)::date AS activity_week FROM annotated
), sizes AS (
 SELECT cohort_week,COUNT(*) AS cohort_size FROM weekly_users
 WHERE cohort_week=activity_week GROUP BY cohort_week
), retention AS (
 SELECT cohort_week,((activity_week-cohort_week)/7) AS week_number,
        COUNT(*) AS active_users
 FROM weekly_users GROUP BY cohort_week,activity_week
), actual AS (
 SELECT r.cohort_week,r.week_number,s.cohort_size,r.active_users,
        ROUND(100.0*r.active_users/NULLIF(s.cohort_size,0),2) AS retention_pct
 FROM retention r JOIN sizes s USING (cohort_week)
), expected(cohort_week,week_number,cohort_size,active_users,retention_pct) AS (
 VALUES (DATE '2026-01-05',0,3::bigint,3::bigint,100.00::numeric),
        (DATE '2026-01-05',1,3::bigint,2::bigint,66.67::numeric),
        (DATE '2026-01-05',2,3::bigint,1::bigint,33.33::numeric),
        (DATE '2026-01-12',0,2::bigint,2::bigint,100.00::numeric),
        (DATE '2026-01-12',1,2::bigint,1::bigint,50.00::numeric),
        (DATE '2026-01-19',0,1::bigint,1::bigint,100.00::numeric)
), differences AS (
 (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
 UNION ALL
 (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
), checks AS (
 SELECT (SELECT COUNT(*)=10 FROM events) AS event_count_ok,
        (SELECT COUNT(DISTINCT user_id)=6 FROM events) AS user_count_ok,
        (SELECT COUNT(*)=6 FROM actual) AS retention_rows_ok,
        (SELECT COUNT(*)=0 FROM differences) AS retention_exact_ok,
        (SELECT COUNT(*)=3 FROM annotated WHERE user_id=1) AS sequence_count_ok,
        (SELECT COUNT(*)=1 FROM annotated WHERE user_id=1 AND event_number=1
                AND previous_day IS NULL) AS first_event_ok,
        (SELECT COUNT(*)=2 FROM annotated WHERE user_id=1 AND event_number IN (2,3)
                AND event_day-previous_day=7) AS interval_ok
)
SELECT *, 1 / CASE WHEN event_count_ok AND user_count_ok AND retention_rows_ok
                        AND retention_exact_ok AND sequence_count_ok
                        AND first_event_ok AND interval_ok
                   THEN 1 ELSE 0 END AS fail_closed_acceptance
FROM checks;
ROLLBACK;
