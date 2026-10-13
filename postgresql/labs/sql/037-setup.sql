\set ON_ERROR_STOP on
SELECT current_database(), current_user, current_setting('server_version');
CREATE SCHEMA IF NOT EXISTS ch037;
CREATE TABLE IF NOT EXISTS ch037.orders (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 customer_id integer NOT NULL,
 status text NOT NULL,
 created_at timestamptz NOT NULL,
 payload text NOT NULL
);
INSERT INTO ch037.orders(customer_id,status,created_at,payload)
SELECT g%2000, CASE WHEN g%5=0 THEN 'open' ELSE 'closed' END,
 timestamptz '2026-01-01 00:00:00+00'+g*interval '1 minute',
 repeat(md5(g::text),3)
FROM generate_series(1,100000) g;
CREATE INDEX IF NOT EXISTS orders_customer_time_idx ON ch037.orders(customer_id,created_at DESC);
ANALYZE ch037.orders;
SELECT count(*) AS fixture_rows FROM ch037.orders;
