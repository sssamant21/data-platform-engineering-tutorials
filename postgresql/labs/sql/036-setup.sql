\set ON_ERROR_STOP on
\echo 'DISPOSABLE DATABASE ONLY: replace ch036'
SELECT current_database(), current_user, current_setting('server_version');
DROP SCHEMA IF EXISTS ch036 CASCADE;
CREATE SCHEMA ch036;
CREATE TABLE ch036.events (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, tenant_id integer NOT NULL, status text NOT NULL, payload text NOT NULL);
INSERT INTO ch036.events(tenant_id,status,payload)
SELECT g % 1000, CASE WHEN g % 4=0 THEN 'open' ELSE 'closed' END, repeat(md5(g::text),2)
FROM generate_series(1,100000) g;
CREATE INDEX events_tenant_idx ON ch036.events(tenant_id);
ANALYZE ch036.events;
SELECT count(*) AS fixture_rows FROM ch036.events;
