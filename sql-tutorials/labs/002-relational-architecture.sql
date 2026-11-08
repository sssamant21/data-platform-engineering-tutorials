-- Chapter 002: Relational Databases and DBMS Architecture
-- PostgreSQL 18 reference; read-only; synthetic data; no permanent objects.
-- Expected outcomes described alongside each query.

-- A: Session identity (one row, environment-dependent values).
SELECT current_database() AS database_name,
       current_user AS role_name,
       current_setting('server_version') AS server_version;

-- B: INNER JOIN: Ava 101 40.00; Ava 102 25.00; Noah 103 15.00.
WITH customers(customer_id, customer_name) AS (
    VALUES (1, 'Ava'), (2, 'Noah'), (3, 'Mia')
),
orders(order_id, customer_id, amount_usd) AS (
    VALUES (101, 1, 40.00::numeric(10,2)),
           (102, 1, 25.00::numeric(10,2)),
           (103, 2, 15.00::numeric(10,2))
)
SELECT c.customer_name, o.order_id, o.amount_usd
FROM customers AS c
JOIN orders AS o ON c.customer_id = o.customer_id
ORDER BY o.order_id;

-- C: LEFT JOIN: Ava 2; Noah 1; Mia 0.
-- COUNT(o.order_id), not COUNT(*), excludes the unmatched placeholder row.
WITH customers(customer_id, customer_name) AS (
    VALUES (1, 'Ava'), (2, 'Noah'), (3, 'Mia')
),
orders(order_id, customer_id, amount_usd) AS (
    VALUES (101, 1, 40.00::numeric(10,2)),
           (102, 1, 25.00::numeric(10,2)),
           (103, 2, 15.00::numeric(10,2))
)
SELECT c.customer_name, COUNT(o.order_id) AS order_count
FROM customers AS c
LEFT JOIN orders AS o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY c.customer_id;

-- D: Backend and transaction metadata (one row, environment-dependent).
SELECT current_schema() AS default_schema,
       pg_backend_pid() AS backend_pid,
       current_setting('transaction_isolation') AS isolation_level;

-- E: Only the current backend, not all sessions (one row when permitted).
SELECT pid, datname, usename, state
FROM pg_stat_activity
WHERE pid = pg_backend_pid();
