\set ON_ERROR_STOP on
-- Do not automatically destroy an existing schema. Clean up explicitly after verifying target.
CREATE SCHEMA ch032;
CREATE TABLE ch032.orders (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 tenant_id integer NOT NULL,
 created_at timestamptz NOT NULL,
 status text NOT NULL,
 amount numeric(12,2) NOT NULL,
 email text NOT NULL
);
INSERT INTO ch032.orders(tenant_id,created_at,status,amount,email)
SELECT (g % 100)+1,
 timestamptz '2026-01-01 00:00:00+00' + g * interval '1 minute',
 CASE WHEN g % 20 = 0 THEN 'open' ELSE 'closed' END,
 (g % 10000)::numeric / 100,
 'User' || (g % 2000) || '@example.test'
FROM generate_series(1,100000) g;
ANALYZE ch032.orders;
SELECT count(*) AS fixture_rows FROM ch032.orders;
