-- Chapter 012: AND, OR, NOT, and Boolean precedence.
-- Synthetic VALUES only. Independently verify disposable endpoint before running.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/012-and-or-not-boolean-precedence.sql
BEGIN READ ONLY;
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials'
 AND current_setting('server_version_num')::integer / 10000 = 18
 THEN 1 ELSE 0 END AS environment_assertion;

-- A: expected 303, 306
WITH orders(order_id, customer_name, amount, status, priority) AS (
 VALUES
 (301,'Ava',50.00::numeric(10,2),'paid',TRUE),
 (302,'Ben',100.00::numeric(10,2),'pending',FALSE),
 (303,'Ava',150.00::numeric(10,2),'paid',FALSE),
 (304,'Chen',100.00::numeric(10,2),NULL,TRUE),
 (305,'Ben',0.00::numeric(10,2),'cancelled',FALSE),
 (306,'Chen',200.00::numeric(10,2),'paid',TRUE),
 (307,'Dee',125.00::numeric(10,2),'pending',TRUE)
)
SELECT order_id FROM orders WHERE status = 'paid' AND amount >= 100 ORDER BY order_id;

-- B: expected 301, 302, 304, 306, 307
WITH orders(order_id, customer_name, amount, status, priority) AS (
 VALUES
 (301,'Ava',50.00::numeric(10,2),'paid',TRUE),
 (302,'Ben',100.00::numeric(10,2),'pending',FALSE),
 (303,'Ava',150.00::numeric(10,2),'paid',FALSE),
 (304,'Chen',100.00::numeric(10,2),NULL,TRUE),
 (305,'Ben',0.00::numeric(10,2),'cancelled',FALSE),
 (306,'Chen',200.00::numeric(10,2),'paid',TRUE),
 (307,'Dee',125.00::numeric(10,2),'pending',TRUE)
)
SELECT order_id FROM orders WHERE status = 'pending' OR priority = TRUE ORDER BY order_id;

-- C1: expected 301, 302, 303, 306, 307
WITH orders(order_id, customer_name, amount, status, priority) AS (
 VALUES
 (301,'Ava',50.00::numeric(10,2),'paid',TRUE),
 (302,'Ben',100.00::numeric(10,2),'pending',FALSE),
 (303,'Ava',150.00::numeric(10,2),'paid',FALSE),
 (304,'Chen',100.00::numeric(10,2),NULL,TRUE),
 (305,'Ben',0.00::numeric(10,2),'cancelled',FALSE),
 (306,'Chen',200.00::numeric(10,2),'paid',TRUE),
 (307,'Dee',125.00::numeric(10,2),'pending',TRUE)
)
SELECT order_id FROM orders WHERE status = 'paid' OR status = 'pending' AND amount >= 100 ORDER BY order_id;

-- C2: expected 302, 303, 306, 307
WITH orders(order_id, customer_name, amount, status, priority) AS (
 VALUES
 (301,'Ava',50.00::numeric(10,2),'paid',TRUE),
 (302,'Ben',100.00::numeric(10,2),'pending',FALSE),
 (303,'Ava',150.00::numeric(10,2),'paid',FALSE),
 (304,'Chen',100.00::numeric(10,2),NULL,TRUE),
 (305,'Ben',0.00::numeric(10,2),'cancelled',FALSE),
 (306,'Chen',200.00::numeric(10,2),'paid',TRUE),
 (307,'Dee',125.00::numeric(10,2),'pending',TRUE)
)
SELECT order_id FROM orders WHERE (status = 'paid' OR status = 'pending') AND amount >= 100 ORDER BY order_id;

-- D: expected 302, 305, 307
WITH orders(order_id, customer_name, amount, status, priority) AS (
 VALUES
 (301,'Ava',50.00::numeric(10,2),'paid',TRUE),
 (302,'Ben',100.00::numeric(10,2),'pending',FALSE),
 (303,'Ava',150.00::numeric(10,2),'paid',FALSE),
 (304,'Chen',100.00::numeric(10,2),NULL,TRUE),
 (305,'Ben',0.00::numeric(10,2),'cancelled',FALSE),
 (306,'Chen',200.00::numeric(10,2),'paid',TRUE),
 (307,'Dee',125.00::numeric(10,2),'pending',TRUE)
)
SELECT order_id FROM orders WHERE NOT (status = 'paid') ORDER BY order_id;

-- E: expected 303, 306, 307
WITH orders(order_id, customer_name, amount, status, priority) AS (
 VALUES
 (301,'Ava',50.00::numeric(10,2),'paid',TRUE),
 (302,'Ben',100.00::numeric(10,2),'pending',FALSE),
 (303,'Ava',150.00::numeric(10,2),'paid',FALSE),
 (304,'Chen',100.00::numeric(10,2),NULL,TRUE),
 (305,'Ben',0.00::numeric(10,2),'cancelled',FALSE),
 (306,'Chen',200.00::numeric(10,2),'paid',TRUE),
 (307,'Dee',125.00::numeric(10,2),'pending',TRUE)
)
SELECT order_id FROM orders WHERE (status = 'paid' AND amount >= 100) OR (status = 'pending' AND priority = TRUE) ORDER BY order_id;

-- Fail-closed assertion of exact ID sets and total input count.
WITH orders(order_id, customer_name, amount, status, priority) AS (
 VALUES
 (301,'Ava',50.00::numeric(10,2),'paid',TRUE),
 (302,'Ben',100.00::numeric(10,2),'pending',FALSE),
 (303,'Ava',150.00::numeric(10,2),'paid',FALSE),
 (304,'Chen',100.00::numeric(10,2),NULL,TRUE),
 (305,'Ben',0.00::numeric(10,2),'cancelled',FALSE),
 (306,'Chen',200.00::numeric(10,2),'paid',TRUE),
 (307,'Dee',125.00::numeric(10,2),'pending',TRUE)
), checks AS (
 SELECT (SELECT COUNT(*) FROM orders) = 7 AS total_rows,
 (SELECT array_agg(order_id ORDER BY order_id) FROM orders WHERE status = 'paid' AND amount >= 100) = ARRAY[303,306] AS check_a,
 (SELECT array_agg(order_id ORDER BY order_id) FROM orders WHERE status = 'pending' OR priority = TRUE) = ARRAY[301,302,304,306,307] AS check_b,
 (SELECT array_agg(order_id ORDER BY order_id) FROM orders WHERE status = 'paid' OR status = 'pending' AND amount >= 100) = ARRAY[301,302,303,306,307] AS check_c1,
 (SELECT array_agg(order_id ORDER BY order_id) FROM orders WHERE (status = 'paid' OR status = 'pending') AND amount >= 100) = ARRAY[302,303,306,307] AS check_c2,
 (SELECT array_agg(order_id ORDER BY order_id) FROM orders WHERE NOT (status = 'paid')) = ARRAY[302,305,307] AS check_d,
 (SELECT array_agg(order_id ORDER BY order_id) FROM orders WHERE (status = 'paid' AND amount >= 100) OR (status = 'pending' AND priority = TRUE)) = ARRAY[303,306,307] AS check_e
)
SELECT 1 / CASE WHEN total_rows AND check_a AND check_b AND check_c1 AND check_c2 AND check_d AND check_e THEN 1 ELSE 0 END AS acceptance_assertion FROM checks;
ROLLBACK;
