-- Chapter 011: WHERE and comparison operators. Synthetic in-query data ONLY.
-- Confirm disposable PostgreSQL 18 endpoint; name/version check is not sufficient proof.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/011-where-comparison-operators.sql
BEGIN READ ONLY;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials'
 AND current_setting('server_version_num')::integer / 10000 = 18
 THEN 1 ELSE 0 END AS environment_assertion;

-- A paid orders
WITH orders(order_id,customer_name,amount,status,order_date) AS (VALUES
(201,'Ava',50.00::numeric(10,2),'paid',DATE '2026-11-01'),
(202,'Ben',100.00::numeric(10,2),'pending',DATE '2026-11-02'),
(203,'Ava',150.00::numeric(10,2),'paid',DATE '2026-11-03'),
(204,'Chen',100.00::numeric(10,2),NULL,DATE '2026-11-04'),
(205,'Ben',0.00::numeric(10,2),'cancelled',DATE '2026-11-05'),
(206,'Chen',200.00::numeric(10,2),'paid',DATE '2026-11-06')
)
SELECT order_id FROM orders WHERE status = 'paid' ORDER BY order_id;

-- B inclusive threshold
WITH orders(order_id,customer_name,amount,status,order_date) AS (VALUES
(201,'Ava',50.00::numeric(10,2),'paid',DATE '2026-11-01'),
(202,'Ben',100.00::numeric(10,2),'pending',DATE '2026-11-02'),
(203,'Ava',150.00::numeric(10,2),'paid',DATE '2026-11-03'),
(204,'Chen',100.00::numeric(10,2),NULL,DATE '2026-11-04'),
(205,'Ben',0.00::numeric(10,2),'cancelled',DATE '2026-11-05'),
(206,'Chen',200.00::numeric(10,2),'paid',DATE '2026-11-06')
)
SELECT order_id FROM orders WHERE amount >= 100 ORDER BY order_id;

-- C strict threshold
WITH orders(order_id,customer_name,amount,status,order_date) AS (VALUES
(201,'Ava',50.00::numeric(10,2),'paid',DATE '2026-11-01'),
(202,'Ben',100.00::numeric(10,2),'pending',DATE '2026-11-02'),
(203,'Ava',150.00::numeric(10,2),'paid',DATE '2026-11-03'),
(204,'Chen',100.00::numeric(10,2),NULL,DATE '2026-11-04'),
(205,'Ben',0.00::numeric(10,2),'cancelled',DATE '2026-11-05'),
(206,'Chen',200.00::numeric(10,2),'paid',DATE '2026-11-06')
)
SELECT order_id FROM orders WHERE amount > 100 ORDER BY order_id;

-- D not paid (NULL excluded)
WITH orders(order_id,customer_name,amount,status,order_date) AS (VALUES
(201,'Ava',50.00::numeric(10,2),'paid',DATE '2026-11-01'),
(202,'Ben',100.00::numeric(10,2),'pending',DATE '2026-11-02'),
(203,'Ava',150.00::numeric(10,2),'paid',DATE '2026-11-03'),
(204,'Chen',100.00::numeric(10,2),NULL,DATE '2026-11-04'),
(205,'Ben',0.00::numeric(10,2),'cancelled',DATE '2026-11-05'),
(206,'Chen',200.00::numeric(10,2),'paid',DATE '2026-11-06')
)
SELECT order_id FROM orders WHERE status <> 'paid' ORDER BY order_id;

-- E missing status
WITH orders(order_id,customer_name,amount,status,order_date) AS (VALUES
(201,'Ava',50.00::numeric(10,2),'paid',DATE '2026-11-01'),
(202,'Ben',100.00::numeric(10,2),'pending',DATE '2026-11-02'),
(203,'Ava',150.00::numeric(10,2),'paid',DATE '2026-11-03'),
(204,'Chen',100.00::numeric(10,2),NULL,DATE '2026-11-04'),
(205,'Ben',0.00::numeric(10,2),'cancelled',DATE '2026-11-05'),
(206,'Chen',200.00::numeric(10,2),'paid',DATE '2026-11-06')
)
SELECT order_id FROM orders WHERE status IS NULL ORDER BY order_id;

-- F before Nov 04
WITH orders(order_id,customer_name,amount,status,order_date) AS (VALUES
(201,'Ava',50.00::numeric(10,2),'paid',DATE '2026-11-01'),
(202,'Ben',100.00::numeric(10,2),'pending',DATE '2026-11-02'),
(203,'Ava',150.00::numeric(10,2),'paid',DATE '2026-11-03'),
(204,'Chen',100.00::numeric(10,2),NULL,DATE '2026-11-04'),
(205,'Ben',0.00::numeric(10,2),'cancelled',DATE '2026-11-05'),
(206,'Chen',200.00::numeric(10,2),'paid',DATE '2026-11-06')
)
SELECT order_id FROM orders WHERE order_date < DATE '2026-11-04' ORDER BY order_id;

-- Fail-closed acceptance: counts and exact expected ID sets.
WITH orders(order_id,customer_name,amount,status,order_date) AS (VALUES
(201,'Ava',50.00::numeric(10,2),'paid',DATE '2026-11-01'),
(202,'Ben',100.00::numeric(10,2),'pending',DATE '2026-11-02'),
(203,'Ava',150.00::numeric(10,2),'paid',DATE '2026-11-03'),
(204,'Chen',100.00::numeric(10,2),NULL,DATE '2026-11-04'),
(205,'Ben',0.00::numeric(10,2),'cancelled',DATE '2026-11-05'),
(206,'Chen',200.00::numeric(10,2),'paid',DATE '2026-11-06')
), checks AS (
 SELECT
 (SELECT array_agg(order_id ORDER BY order_id) FROM orders WHERE status='paid') = ARRAY[201,203,206] AS a,
 (SELECT array_agg(order_id ORDER BY order_id) FROM orders WHERE amount>=100) = ARRAY[202,203,204,206] AS b,
 (SELECT array_agg(order_id ORDER BY order_id) FROM orders WHERE amount>100) = ARRAY[203,206] AS c,
 (SELECT array_agg(order_id ORDER BY order_id) FROM orders WHERE status<>'paid') = ARRAY[202,205] AS d,
 (SELECT array_agg(order_id ORDER BY order_id) FROM orders WHERE status IS NULL) = ARRAY[204] AS e,
 (SELECT array_agg(order_id ORDER BY order_id) FROM orders WHERE order_date<DATE '2026-11-04') = ARRAY[201,202,203] AS f,
 (SELECT COUNT(*) FROM orders)=6 AS total_rows
)
SELECT 1 / CASE WHEN a AND b AND c AND d AND e AND f AND total_rows THEN 1 ELSE 0 END AS acceptance_assertion FROM checks;
ROLLBACK;
