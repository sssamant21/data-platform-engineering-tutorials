\set ON_ERROR_STOP on
\echo 'LAB ONLY: will refuse to overwrite existing ch034; run reviewed cleanup separately'
SELECT current_database() AS database_name, current_user AS operator;
-- Do not automatically destroy an existing schema. Clean up explicitly after verifying target.
CREATE SCHEMA ch034;
CREATE TABLE ch034.events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 customer_id integer NOT NULL,
 occurred_at timestamptz NOT NULL,
 status text NOT NULL,
 payload text NOT NULL
) WITH (fillfactor = 80);
INSERT INTO ch034.events (customer_id, occurred_at, status, payload)
SELECT (g % 2000) + 1,
       timestamptz '2026-01-01 00:00:00+00' + g * interval '1 minute',
       CASE WHEN g % 5 = 0 THEN 'open' ELSE 'closed' END,
       repeat(md5(g::text), 3)
FROM generate_series(1, 100000) AS g;
CREATE INDEX events_customer_idx ON ch034.events (customer_id);
CREATE INDEX events_customer_time_idx ON ch034.events (customer_id, occurred_at DESC);
CREATE INDEX events_status_idx ON ch034.events (status);
ANALYZE ch034.events;
SELECT count(*) AS initial_rows FROM ch034.events;
