-- Chapter 090 — synthetic, read-only reusable customer reporting contract.
-- Isolated PostgreSQL 18 database sql_tutorials only; no persistent objects.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/090-lab-09-reusable-reporting-objects.sql
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '20s';
SELECT current_database() AS database_name,
       current_setting('server_version') AS server_version,
       1 / CASE WHEN current_database() = 'sql_tutorials'
                  AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
                THEN 1 ELSE 0 END AS environment_guard;
-- Report contract: one row per customer, including customers without paid orders.
WITH customers(customer_id, customer_name, attributes) AS (
 VALUES (1,'Aster','{"region":"east"}'::jsonb),
        (2,'Birch','{"region":"west"}'::jsonb),
        (3,'Cedar','{}'::jsonb),
        (4,'Dune','{"region":"east"}'::jsonb)
), orders(order_id, customer_id, status, amount) AS (
 VALUES (101,1,'paid',30.00::numeric(10,2)),
        (102,1,'paid',20.00), (103,1,'pending',90.00),
        (104,2,'paid',25.00), (105,2,'refunded',40.00),
        (106,3,'paid',10.00)
), paid AS (
 SELECT customer_id, COUNT(*) AS paid_order_count, SUM(amount) AS paid_total
 FROM orders WHERE status='paid' GROUP BY customer_id
), report AS (
 SELECT c.customer_id,c.customer_name,
        COALESCE(c.attributes->>'region','unassigned') AS region,
        COALESCE(p.paid_order_count,0) AS paid_order_count,
        COALESCE(p.paid_total,0::numeric) AS paid_total,
        CASE WHEN COALESCE(p.paid_total,0)>=40 THEN 'high' ELSE 'standard' END AS tier
 FROM customers c LEFT JOIN paid p USING (customer_id)
)
SELECT * FROM report ORDER BY customer_id;
-- Model an outdated snapshot captured before the final paid order arrived.
WITH orders(order_id,customer_id,status,amount) AS (
 VALUES (101,1,'paid',30.00::numeric(10,2)),
        (102,1,'paid',20.00),(103,1,'pending',90.00),
        (104,2,'paid',25.00),(105,2,'refunded',40.00),
        (106,3,'paid',10.00)
)
SELECT SUM(amount) FILTER (WHERE status='paid') AS live_paid_total,
       SUM(amount) FILTER (WHERE status='paid' AND order_id<106) AS snapshot_paid_total,
       SUM(amount) FILTER (WHERE status='paid' AND order_id>=106) AS snapshot_lag_amount
FROM orders;
-- Fail-closed, exact multiset contract and independent aggregate reconciliation.
WITH customers(customer_id, customer_name, attributes) AS (
 VALUES (1,'Aster','{"region":"east"}'::jsonb),
        (2,'Birch','{"region":"west"}'::jsonb),
        (3,'Cedar','{}'::jsonb),
        (4,'Dune','{"region":"east"}'::jsonb)
), orders(order_id,customer_id,status,amount) AS (
 VALUES (101,1,'paid',30.00::numeric(10,2)),
        (102,1,'paid',20.00),(103,1,'pending',90.00),
        (104,2,'paid',25.00),(105,2,'refunded',40.00),
        (106,3,'paid',10.00)
), paid AS (
 SELECT customer_id,COUNT(*) AS paid_order_count,SUM(amount) AS paid_total
 FROM orders WHERE status='paid' GROUP BY customer_id
), actual AS (
 SELECT c.customer_id,c.customer_name,
        COALESCE(c.attributes->>'region','unassigned') AS region,
        COALESCE(p.paid_order_count,0) AS paid_order_count,
        COALESCE(p.paid_total,0::numeric) AS paid_total,
        CASE WHEN COALESCE(p.paid_total,0)>=40 THEN 'high' ELSE 'standard' END AS tier
 FROM customers c LEFT JOIN paid p USING (customer_id)
), expected(customer_id,customer_name,region,paid_order_count,paid_total,tier) AS (
 VALUES (1,'Aster','east',2::bigint,50.00::numeric,'high'),
        (2,'Birch','west',1::bigint,25.00::numeric,'standard'),
        (3,'Cedar','unassigned',1::bigint,10.00::numeric,'standard'),
        (4,'Dune','east',0::bigint,0.00::numeric,'standard')
), difference AS (
 (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
 UNION ALL
 (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
), checks AS (
 SELECT (SELECT count(*)=4 FROM customers) AS four_customers,
        (SELECT count(*)=6 FROM orders) AS six_orders,
        (SELECT count(*)=4 FROM actual) AS four_report_rows,
        (SELECT count(*)=0 FROM difference) AS exact_report_rows,
        (SELECT sum(paid_order_count)=4 FROM actual) AS four_paid_orders,
        (SELECT sum(paid_total)=85.00 FROM actual) AS report_total_85,
        (SELECT sum(amount)=85.00 FROM orders WHERE status='paid') AS source_total_85,
        (SELECT sum(amount)=75.00 FROM orders WHERE status='paid' AND order_id<106) AS snapshot_total_75,
        (SELECT count(*)=1 FROM actual WHERE customer_id=4 AND paid_total=0) AS zero_activity_preserved
)
SELECT *, 1 / CASE WHEN four_customers AND six_orders AND four_report_rows
                        AND exact_report_rows AND four_paid_orders AND report_total_85
                        AND source_total_85 AND snapshot_total_75 AND zero_activity_preserved
                   THEN 1 ELSE 0 END AS fail_closed_acceptance
FROM checks;
ROLLBACK;
