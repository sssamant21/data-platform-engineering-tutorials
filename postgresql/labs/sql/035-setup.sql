\set ON_ERROR_STOP on
\echo 'DISPOSABLE DATABASE ONLY: replacing ch035 schema'
SELECT current_database() AS database_name, current_user AS operator;
DROP SCHEMA IF EXISTS ch035 CASCADE;
CREATE SCHEMA ch035;
CREATE TABLE ch035.events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 customer_id integer NOT NULL,
 status text NOT NULL,
 payload text NOT NULL
) WITH (fillfactor=80);
INSERT INTO ch035.events (customer_id,status,payload)
SELECT g % 1000, CASE WHEN g % 3=0 THEN 'open' ELSE 'closed' END, repeat(md5(g::text),3)
FROM generate_series(1,100000) AS g;
CREATE INDEX events_customer_idx ON ch035.events(customer_id);
CREATE INDEX events_status_idx ON ch035.events(status);
ANALYZE ch035.events;
SELECT count(*) AS fixture_rows FROM ch035.events;
