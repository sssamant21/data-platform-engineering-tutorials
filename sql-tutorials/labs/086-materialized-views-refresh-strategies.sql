-- Chapter 086 — Materialized views and refresh strategies
-- Synthetic read-only simulation; NO CREATE/REFRESH MATERIALIZED VIEW.
-- Run with psql -X -v ON_ERROR_STOP=1 in isolated PostgreSQL 18 database sql_tutorials.
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials'
                  AND current_setting('server_version_num')::integer / 10000 = 18
                THEN 1 ELSE 0 END AS environment_guard;

WITH orders(order_id, order_day, service, status, amount, arrived_at) AS (
 VALUES
 (1,DATE '2026-11-01','api'::text,'paid'::text,20.00::numeric(12,2),TIMESTAMP '2026-11-01 10:00'),
 (2,DATE '2026-11-01','api','paid',30.00::numeric(12,2),TIMESTAMP '2026-11-01 11:00'),
 (3,DATE '2026-11-01','api','paid',10.00::numeric(12,2),TIMESTAMP '2026-11-02 08:00'),
 (4,DATE '2026-11-01','file','paid',15.00::numeric(12,2),TIMESTAMP '2026-11-01 12:00'),
 (5,DATE '2026-11-02','api','pending',99.00::numeric(12,2),TIMESTAMP '2026-11-02 09:00')
), snapshot AS (
 SELECT service, COUNT(*)::bigint AS paid_orders, SUM(amount)::numeric(12,2) AS revenue
 FROM orders WHERE status='paid' AND arrived_at <= TIMESTAMP '2026-11-01 23:59:59'
 GROUP BY service
), live AS (
 SELECT service, COUNT(*)::bigint AS paid_orders, SUM(amount)::numeric(12,2) AS revenue
 FROM orders WHERE status='paid' GROUP BY service
)
SELECT COALESCE(s.service,l.service) AS service,
       s.paid_orders AS snapshot_orders, s.revenue AS snapshot_revenue,
       l.paid_orders AS live_orders, l.revenue AS live_revenue,
       (l.revenue-s.revenue)::numeric(12,2) AS revenue_gap
FROM snapshot s FULL JOIN live l USING (service)
ORDER BY service;

-- Fail-closed exact row-set and source reconciliation assertions.
WITH orders(order_id, order_day, service, status, amount, arrived_at) AS (
 VALUES
 (1,DATE '2026-11-01','api'::text,'paid'::text,20.00::numeric(12,2),TIMESTAMP '2026-11-01 10:00'),
 (2,DATE '2026-11-01','api','paid',30.00::numeric(12,2),TIMESTAMP '2026-11-01 11:00'),
 (3,DATE '2026-11-01','api','paid',10.00::numeric(12,2),TIMESTAMP '2026-11-02 08:00'),
 (4,DATE '2026-11-01','file','paid',15.00::numeric(12,2),TIMESTAMP '2026-11-01 12:00'),
 (5,DATE '2026-11-02','api','pending',99.00::numeric(12,2),TIMESTAMP '2026-11-02 09:00')
), snapshot AS (
 SELECT service, COUNT(*)::bigint AS paid_orders, SUM(amount)::numeric(12,2) AS revenue
 FROM orders WHERE status='paid' AND arrived_at <= TIMESTAMP '2026-11-01 23:59:59'
 GROUP BY service
), live AS (
 SELECT service, COUNT(*)::bigint AS paid_orders, SUM(amount)::numeric(12,2) AS revenue
 FROM orders WHERE status='paid' GROUP BY service
), actual AS (
 SELECT COALESCE(s.service,l.service) AS service,
        s.paid_orders AS snapshot_orders, s.revenue AS snapshot_revenue,
        l.paid_orders AS live_orders, l.revenue AS live_revenue,
        (l.revenue-s.revenue)::numeric(12,2) AS revenue_gap
 FROM snapshot s FULL JOIN live l USING (service)
), expected(service,snapshot_orders,snapshot_revenue,live_orders,live_revenue,revenue_gap) AS (
 VALUES ('api'::text,2::bigint,50.00::numeric(12,2),3::bigint,60.00::numeric(12,2),10.00::numeric(12,2)),
        ('file'::text,1::bigint,15.00::numeric(12,2),1::bigint,15.00::numeric(12,2),0.00::numeric(12,2))
), differences AS (
 (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
 UNION ALL
 (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
), checks AS (
 SELECT (SELECT COUNT(*)=0 FROM differences) AS exact_rows_match,
        (SELECT COUNT(*)=2 FROM actual) AS two_services,
        (SELECT SUM(live_revenue)=75.00::numeric FROM actual) AS live_total_75,
        (SELECT COUNT(*)=1 FROM orders WHERE status='paid'
          AND arrived_at > TIMESTAMP '2026-11-01 23:59:59') AS one_late_paid_order
)
SELECT *, 1 / CASE WHEN exact_rows_match AND two_services AND live_total_75
                         AND one_late_paid_order THEN 1 ELSE 0 END AS fail_closed_acceptance
FROM checks;
ROLLBACK;
