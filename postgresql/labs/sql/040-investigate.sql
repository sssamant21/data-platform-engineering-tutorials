\set ON_ERROR_STOP on
-- Chapter 040 capstone changes only the independently identified Chapter 004 PG18 lab.
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
 AND current_setting('data_directory') ~ '^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+/primary\timing on
SELECT inhrelid::regclass AS child FROM pg_inherits WHERE inhparent='ch040.events'::regclass ORDER BY 1;
CREATE TABLE ch040.events_2026_04 PARTITION OF ch040.events
 FOR VALUES FROM ('2026-04-01 00:00:00+00') TO ('2026-05-01 00:00:00+00');
INSERT INTO ch040.events(event_id,event_time,tenant_id,payload)
VALUES (12001,'2026-04-02 00:00:00+00',1,'future');
INSERT INTO ch040.events(event_id,event_time,tenant_id,payload)
VALUES (12002,'2026-01-15 00:00:00+00',1,'late-arrival');
EXPLAIN (ANALYZE,BUFFERS)
SELECT count(*) FROM ch040.events WHERE event_time >= '2026-02-01 00:00:00+00'
AND event_time < '2026-03-01 00:00:00+00';
SELECT count(*) AS parent_before FROM ch040.events;
SELECT count(*) AS january_before FROM ch040.events_2026_01;
ALTER TABLE ch040.events DETACH PARTITION ch040.events_2026_01;
SELECT count(*) AS january_detached FROM ch040.events_2026_01;
ALTER TABLE ch040.events ATTACH PARTITION ch040.events_2026_01
 FOR VALUES FROM ('2026-01-01 00:00:00+00') TO ('2026-02-01 00:00:00+00');
ANALYZE ch040.events;
SELECT count(*) AS parent_after FROM ch040.events;
SELECT tableoid::regclass AS partition_name,count(*) FROM ch040.events GROUP BY 1 ORDER BY 1;

 AND NOT pg_is_in_recovery()
 AND EXISTS (SELECT 1 FROM pg_control_system() c
             WHERE c.system_identifier::text=:'expected_system_id')
 AND :'confirm_stage'='040-LIFECYCLE'
 AND to_regclass('ch040.events') IS NOT NULL AND to_regclass('ch040.events_2026_04') IS NULL AND (SELECT count(*) FROM ch040.events)=12000 AND EXISTS (SELECT 1 FROM pg_inherits WHERE inhparent='ch040.events'::regclass AND inhrelid='ch040.events_2026_01'::regclass)
 THEN 'true' ELSE 'false' END AS stage_permitted
\gset
\if :stage_permitted
 \echo 'Chapter 040 disposable cluster and stage state verified'
\else
 \echo 'REFUSED: target identity, stage token or partition state mismatch'
 \quit 3
\endif
\timing on
SELECT inhrelid::regclass AS child FROM pg_inherits WHERE inhparent='ch040.events'::regclass ORDER BY 1;
CREATE TABLE ch040.events_2026_04 PARTITION OF ch040.events
 FOR VALUES FROM ('2026-04-01 00:00:00+00') TO ('2026-05-01 00:00:00+00');
INSERT INTO ch040.events(event_id,event_time,tenant_id,payload)
VALUES (12001,'2026-04-02 00:00:00+00',1,'future');
INSERT INTO ch040.events(event_id,event_time,tenant_id,payload)
VALUES (12002,'2026-01-15 00:00:00+00',1,'late-arrival');
EXPLAIN (ANALYZE,BUFFERS)
SELECT count(*) FROM ch040.events WHERE event_time >= '2026-02-01 00:00:00+00'
AND event_time < '2026-03-01 00:00:00+00';
SELECT count(*) AS parent_before FROM ch040.events;
SELECT count(*) AS january_before FROM ch040.events_2026_01;
ALTER TABLE ch040.events DETACH PARTITION ch040.events_2026_01;
SELECT count(*) AS january_detached FROM ch040.events_2026_01;
ALTER TABLE ch040.events ATTACH PARTITION ch040.events_2026_01
 FOR VALUES FROM ('2026-01-01 00:00:00+00') TO ('2026-02-01 00:00:00+00');
ANALYZE ch040.events;
SELECT count(*) AS parent_after FROM ch040.events;
SELECT tableoid::regclass AS partition_name,count(*) FROM ch040.events GROUP BY 1 ORDER BY 1;
