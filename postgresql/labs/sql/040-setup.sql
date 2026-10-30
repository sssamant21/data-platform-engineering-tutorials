\set ON_ERROR_STOP on
-- Only the independently verified Chapter 004 disposable PG18 primary.
\if :{?expected_system_id}
\else
 \echo 'REFUSED: expected_system_id required'
 \quit 3
\endif
\if :{?confirm_stage}
\else
 \echo 'REFUSED: confirm_stage required'
 \quit 3
\endif
SELECT CASE WHEN current_database()='ops_lab' AND current_user='lab_admin'
 AND inet_server_addr()=inet '127.0.0.1' AND inet_server_port()=55432
 AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
 AND current_setting('data_directory') ~ '^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+/primary$'
 AND NOT pg_is_in_recovery()
 AND EXISTS (SELECT 1 FROM pg_control_system() c
             WHERE c.system_identifier::text=:'expected_system_id')
 AND :'confirm_stage'='040-CREATE'
 AND to_regnamespace('ch040') IS NULL
 THEN 'true' ELSE 'false' END AS stage_permitted
\gset
\if :stage_permitted
 \echo 'Verified Chapter 040 target and fixture stage'
\else
 \echo 'REFUSED: wrong cluster, token or fixture state'
 \quit 3
\endif
BEGIN;
SET LOCAL lock_timeout='1s';
SET LOCAL statement_timeout='25s';
CREATE SCHEMA ch040;
CREATE TABLE ch040.events (event_id bigint NOT NULL,event_time timestamptz NOT NULL,tenant_id integer NOT NULL,payload text NOT NULL,PRIMARY KEY(event_id,event_time)) PARTITION BY RANGE(event_time);
CREATE TABLE ch040.events_2026_01 PARTITION OF ch040.events FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE ch040.events_2026_02 PARTITION OF ch040.events FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE ch040.events_2026_03 PARTITION OF ch040.events FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE INDEX events_tenant_time_idx ON ch040.events(tenant_id,event_time DESC);
INSERT INTO ch040.events(event_id,event_time,tenant_id,payload) SELECT g,timestamptz '2026-01-01 00:00:00+00'+(g-1)*interval '10 minutes',g%100,md5(g::text) FROM generate_series(1,12000) g;
COMMIT;
ANALYZE ch040.events;
SELECT tableoid::regclass,count(*) FROM ch040.events GROUP BY 1 ORDER BY 1;
