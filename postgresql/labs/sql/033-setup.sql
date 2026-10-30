\set ON_ERROR_STOP on
\echo 'LAB ONLY: will refuse to overwrite existing ch033; run reviewed cleanup separately'
SELECT current_database() AS database_name, current_user AS operator, version();
-- Do not automatically destroy an existing schema. Clean up explicitly after verifying target.
CREATE SCHEMA ch033;
CREATE TABLE ch033.orders (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  customer_id integer NOT NULL,
  status text NOT NULL,
  created_at timestamptz NOT NULL,
  amount numeric(12,2) NOT NULL
);
INSERT INTO ch033.orders (customer_id, status, created_at, amount)
SELECT (g % 1000) + 1,
       CASE WHEN g % 5 = 0 THEN 'open' ELSE 'closed' END,
       timestamptz '2026-01-01 00:00:00+00' + (g * interval '1 minute'),
       ((g % 20000) / 100.0)::numeric(12,2)
FROM generate_series(1, 100000) AS g;
ANALYZE ch033.orders;
SELECT count(*) AS fixture_rows, count(DISTINCT status) AS distinct_statuses FROM ch033.orders;
