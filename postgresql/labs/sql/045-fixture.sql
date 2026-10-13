\set ON_ERROR_STOP on
CREATE SCHEMA ch045;
CREATE TABLE ch045.orders (
 order_id integer PRIMARY KEY,
 status text NOT NULL,
 amount numeric(12,2) NOT NULL,
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO ch045.orders(order_id,status,amount)
SELECT g,'valid',(g%1000)::numeric/100 FROM generate_series(1,1000) g;
CREATE TABLE ch045.recovery_markers (
 marker_name text PRIMARY KEY,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
SELECT count(*) AS baseline_rows FROM ch045.orders;
