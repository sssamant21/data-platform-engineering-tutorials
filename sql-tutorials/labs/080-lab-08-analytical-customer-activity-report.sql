-- Chapter 080: PostgreSQL 18 isolated, synthetic read-only analytical customer activity capstone
-- Run: psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/080-lab-08-analytical-customer-activity-report.sql
-- Never use production credentials or a production endpoint.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
SELECT current_database() AS database_name, current_user AS role_name,
       current_setting('server_version') AS server_version,
       inet_server_addr() AS server_ip, inet_server_port() AS server_port;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials' THEN 1 ELSE 0 END AS database_guard;
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
                THEN 1 ELSE 0 END AS version_guard;

-- Events have unique event IDs and pre-normalized UTC calendar dates.
-- Each customer's daily events are ordered deterministically by date, then event ID.
WITH customers(customer_id, customer_name) AS (
 VALUES (1,'Aster'),(2,'Birch'),(3,'Cedar'),(4,'Dune')
), events(event_id,customer_id,event_day,activity_type,amount) AS (
 VALUES (101,1,DATE '2026-02-02','purchase',20::numeric),
        (102,1,DATE '2026-02-09','purchase',30::numeric),
        (103,1,DATE '2026-02-16','visit',0::numeric),
        (201,2,DATE '2026-02-03','purchase',40::numeric),
        (202,2,DATE '2026-02-10','purchase',10::numeric),
        (301,3,DATE '2026-02-09','visit',0::numeric),
        (302,3,DATE '2026-02-16','purchase',15::numeric)
), sequenced AS (
 SELECT e.*, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY event_day,event_id) AS event_number,
        LAG(event_day) OVER (PARTITION BY customer_id ORDER BY event_day,event_id) AS previous_day,
        SUM(amount) OVER (PARTITION BY customer_id ORDER BY event_day,event_id
             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_spend
 FROM events e
), customer_metrics AS (
 SELECT c.customer_id,c.customer_name,
        COUNT(s.event_id) AS event_count,
        COUNT(s.event_id) FILTER (WHERE s.activity_type='purchase') AS purchases,
        COALESCE(SUM(s.amount),0::numeric) AS lifetime_spend,
        MIN(s.event_day) AS first_activity,
        MAX(s.event_day) AS last_activity
 FROM customers c LEFT JOIN sequenced s USING (customer_id)
 GROUP BY c.customer_id,c.customer_name
), ranked AS (
 SELECT *, ROW_NUMBER() OVER (ORDER BY lifetime_spend DESC,customer_id) AS spend_position,
        DENSE_RANK() OVER (ORDER BY lifetime_spend DESC) AS spend_rank
 FROM customer_metrics
)
SELECT customer_id,customer_name,event_count,purchases,lifetime_spend,
       first_activity,last_activity,spend_position,spend_rank
FROM ranked ORDER BY customer_id;

-- Reconciliation: all seven events, four customers, three active customers,
-- five purchases, total spend 115; exact customer-level results in both directions.
WITH customers(customer_id, customer_name) AS (
 VALUES (1,'Aster'),(2,'Birch'),(3,'Cedar'),(4,'Dune')
), events(event_id,customer_id,event_day,activity_type,amount) AS (
 VALUES (101,1,DATE '2026-02-02','purchase',20::numeric),
        (102,1,DATE '2026-02-09','purchase',30::numeric),
        (103,1,DATE '2026-02-16','visit',0::numeric),
        (201,2,DATE '2026-02-03','purchase',40::numeric),
        (202,2,DATE '2026-02-10','purchase',10::numeric),
        (301,3,DATE '2026-02-09','visit',0::numeric),
        (302,3,DATE '2026-02-16','purchase',15::numeric)
), sequenced AS (
 SELECT e.*,ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY event_day,event_id) AS event_number,
        LAG(event_day) OVER (PARTITION BY customer_id ORDER BY event_day,event_id) AS previous_day,
        SUM(amount) OVER (PARTITION BY customer_id ORDER BY event_day,event_id
             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_spend
 FROM events e
), metrics AS (
 SELECT c.customer_id,c.customer_name,COUNT(s.event_id) AS event_count,
        COUNT(s.event_id) FILTER (WHERE s.activity_type='purchase') AS purchases,
        COALESCE(SUM(s.amount),0::numeric) AS lifetime_spend,
        MIN(s.event_day) AS first_activity,MAX(s.event_day) AS last_activity
 FROM customers c LEFT JOIN sequenced s USING (customer_id)
 GROUP BY c.customer_id,c.customer_name
), actual AS (
 SELECT customer_id,customer_name,event_count,purchases,lifetime_spend,
        first_activity,last_activity,
        ROW_NUMBER() OVER (ORDER BY lifetime_spend DESC,customer_id) AS spend_position,
        DENSE_RANK() OVER (ORDER BY lifetime_spend DESC) AS spend_rank
 FROM metrics
), expected(customer_id,customer_name,event_count,purchases,lifetime_spend,first_activity,last_activity,spend_position,spend_rank) AS (
 VALUES (1,'Aster',3::bigint,2::bigint,50::numeric,DATE '2026-02-02',DATE '2026-02-16',1::bigint,1::bigint),
        (2,'Birch',2::bigint,2::bigint,50::numeric,DATE '2026-02-03',DATE '2026-02-10',2::bigint,1::bigint),
        (3,'Cedar',2::bigint,1::bigint,15::numeric,DATE '2026-02-09',DATE '2026-02-16',3::bigint,2::bigint),
        (4,'Dune',0::bigint,0::bigint,0::numeric,NULL::date,NULL::date,4::bigint,3::bigint)
), diff AS (
 (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
 UNION ALL
 (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
), checks AS (
 SELECT (SELECT COUNT(*)=7 FROM events) AS seven_events,
        (SELECT COUNT(*)=4 FROM customers) AS four_customers,
        (SELECT COUNT(DISTINCT customer_id)=3 FROM events) AS three_active,
        (SELECT COUNT(*)=5 FROM events WHERE activity_type='purchase') AS five_purchases,
        (SELECT SUM(amount)=115 FROM events) AS spend_115,
        (SELECT COUNT(*)=0 FROM diff) AS exact_report,
        (SELECT COUNT(*)=7 FROM sequenced) AS sequence_complete,
        (SELECT COUNT(*)=2 FROM sequenced WHERE customer_id=1 AND previous_day IS NOT NULL
          AND event_day-previous_day=7) AS aster_weekly,
        (SELECT MAX(running_spend)=50 FROM sequenced WHERE customer_id=1) AS aster_running_spend
)
SELECT *, 1 / CASE WHEN seven_events AND four_customers AND three_active
 AND five_purchases AND spend_115 AND exact_report AND sequence_complete
 AND aster_weekly AND aster_running_spend THEN 1 ELSE 0 END AS fail_closed_acceptance
FROM checks;
ROLLBACK;
