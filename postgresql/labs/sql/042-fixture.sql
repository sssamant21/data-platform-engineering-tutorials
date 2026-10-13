\set ON_ERROR_STOP on
CREATE TABLE ch042_orders (
 order_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 customer_id integer NOT NULL,
 amount numeric(12,2) NOT NULL,
 status text NOT NULL,
 created_at timestamptz NOT NULL
);
INSERT INTO ch042_orders(customer_id,amount,status,created_at)
SELECT g%500,(g%10000)::numeric/100,
 CASE WHEN g%3=0 THEN 'open' ELSE 'closed' END,
 timestamptz '2026-01-01 00:00:00+00'+g*interval '1 minute'
FROM generate_series(1,10000) g;
CREATE INDEX ch042_orders_customer_idx ON ch042_orders(customer_id);
ANALYZE ch042_orders;
SELECT count(*) AS source_rows FROM ch042_orders;
