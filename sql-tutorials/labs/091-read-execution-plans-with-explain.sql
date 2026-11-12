-- Chapter 091: EXPLAIN estimated plans and synthetic read-only acceptance.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/091-read-execution-plans-with-explain.sql
-- Never run against production. EXPLAIN (ANALYZE) is deliberately not used.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '20s';
SELECT current_database() AS database_name,
       current_setting('server_version') AS server_version,
       1 / CASE WHEN current_database() = 'sql_tutorials'
                 AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
                THEN 1 ELSE 0 END AS environment_guard;

-- Estimated plan only: target query is NOT executed by EXPLAIN.
EXPLAIN (FORMAT TEXT, COSTS ON)
SELECT customer_id, SUM(amount) AS paid_total
FROM (VALUES (1, 'paid', 20.00::numeric(10,2)),
             (1, 'paid', 15.00::numeric(10,2)),
             (2, 'pending', 90.00::numeric(10,2)),
             (2, 'paid', 10.00::numeric(10,2)))
 AS orders(customer_id,status,amount)
WHERE status = 'paid'
GROUP BY customer_id
ORDER BY customer_id;

-- Bounded actual SELECT for comparison, still read-only.
WITH orders(customer_id,status,amount) AS (
 VALUES (1,'paid',20.00::numeric(10,2)),
        (1,'paid',15.00::numeric(10,2)),
        (2,'pending',90.00::numeric(10,2)),
        (2,'paid',10.00::numeric(10,2))
)
SELECT customer_id, count(*) AS paid_orders, sum(amount) AS paid_total
FROM orders WHERE status='paid'
GROUP BY customer_id ORDER BY customer_id;

-- A second estimated plan: preserve a customer with no paid orders.
EXPLAIN (FORMAT TEXT, COSTS ON)
WITH customers(customer_id,customer_name) AS (
 VALUES (1,'Aster'),(2,'Birch'),(3,'Cedar')
), orders(customer_id,status,amount) AS (
 VALUES (1,'paid',20.00::numeric(10,2)),(1,'paid',15.00::numeric(10,2)),
        (2,'pending',90.00::numeric(10,2)),(2,'paid',10.00::numeric(10,2))
), paid AS (
 SELECT customer_id, count(*) AS paid_orders, sum(amount) AS paid_total
 FROM orders WHERE status='paid' GROUP BY customer_id
)
SELECT c.customer_id,c.customer_name,
       coalesce(p.paid_orders,0) AS paid_orders,
       coalesce(p.paid_total,0::numeric) AS paid_total
FROM customers c LEFT JOIN paid p USING(customer_id)
ORDER BY c.customer_id;

-- Fail-closed exact multiset assertion, plus independent source checks.
WITH customers(customer_id,customer_name) AS (
 VALUES (1,'Aster'),(2,'Birch'),(3,'Cedar')
), orders(customer_id,status,amount) AS (
 VALUES (1,'paid',20.00::numeric(10,2)),(1,'paid',15.00::numeric(10,2)),
        (2,'pending',90.00::numeric(10,2)),(2,'paid',10.00::numeric(10,2))
), paid AS (
 SELECT customer_id,count(*) AS paid_orders,sum(amount) AS paid_total
 FROM orders WHERE status='paid' GROUP BY customer_id
), actual AS (
 SELECT c.customer_id,c.customer_name,
        coalesce(p.paid_orders,0) AS paid_orders,
        coalesce(p.paid_total,0::numeric) AS paid_total
 FROM customers c LEFT JOIN paid p USING(customer_id)
), expected(customer_id,customer_name,paid_orders,paid_total) AS (
 VALUES (1,'Aster',2::bigint,35.00::numeric),
        (2,'Birch',1::bigint,10.00::numeric),
        (3,'Cedar',0::bigint,0.00::numeric)
), diff AS (
 (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
 UNION ALL
 (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
), checks AS (
 SELECT (SELECT count(*)=4 FROM orders) AS four_orders,
        (SELECT count(*)=3 FROM orders WHERE status='paid') AS three_paid,
        (SELECT sum(amount)=45.00 FROM orders WHERE status='paid') AS total_45,
        (SELECT count(*)=3 FROM actual) AS three_customers,
        (SELECT count(*)=0 FROM diff) AS exact_results
)
SELECT *, 1 / CASE WHEN four_orders AND three_paid AND total_45
                         AND three_customers AND exact_results
                   THEN 1 ELSE 0 END AS fail_closed_acceptance
FROM checks;
ROLLBACK;
