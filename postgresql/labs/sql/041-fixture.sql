\set ON_ERROR_STOP on
CREATE TABLE ch041_orders (
 order_id bigint PRIMARY KEY,
 customer_id integer NOT NULL,
 amount numeric(12,2) NOT NULL,
 created_at timestamptz NOT NULL
);
INSERT INTO ch041_orders(order_id,customer_id,amount,created_at)
SELECT g,g%1000,(g%5000)::numeric/100,
 timestamptz '2026-01-01 00:00:00+00'+g*interval '1 minute'
FROM generate_series(1,10000) g;
CREATE INDEX ch041_orders_customer_idx ON ch041_orders(customer_id);
ANALYZE ch041_orders;
SELECT count(*) AS source_rows FROM ch041_orders;
