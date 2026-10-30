\set ON_ERROR_STOP on
-- Chapter 037 only on the independently verified Chapter 004 PG18 disposable primary.
-- An exact cluster ID and setup token are required; refuse an occupied schema.
\if :{?expected_system_id}
\else
  \echo 'REFUSED: pass -v expected_system_id=OBSERVED_DISPOSABLE_LAB_ID'
  \quit 3
\endif
\if :{?confirm_setup}
\else
  \echo 'REFUSED: pass -v confirm_setup=037-CREATE'
  \quit 3
\endif
SELECT CASE WHEN current_database()='ops_lab'
 AND current_user='lab_admin'
 AND inet_server_addr()=inet '127.0.0.1' AND inet_server_port()=55432
 AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
 AND current_setting('data_directory') ~ '^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+/primary$'
 AND NOT pg_is_in_recovery()
 AND EXISTS (SELECT 1 FROM pg_control_system() c
             WHERE c.system_identifier::text=:'expected_system_id')
 AND :'confirm_setup'='037-CREATE'
 AND to_regnamespace('ch037') IS NULL
 AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname='lab_app')
 THEN 'true' ELSE 'false' END AS setup_permitted
\gset
\if :setup_permitted
 \echo 'Chapter 037 disposable setup target verified'
\else
 \echo 'REFUSED: wrong target/cluster/role or existing lab schema'
 \quit 3
\endif
BEGIN;
SET LOCAL statement_timeout='30s';
SET LOCAL lock_timeout='1s';
CREATE SCHEMA ch037 AUTHORIZATION lab_admin;
CREATE TABLE ch037.orders (
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
CREATE INDEX orders_customer_time_idx ON ch037.orders(customer_id,created_at DESC);
COMMIT;
ANALYZE ch037.orders;
SELECT count(*) AS fixture_rows FROM ch037.orders;
