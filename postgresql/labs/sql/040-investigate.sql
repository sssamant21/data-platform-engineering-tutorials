\set ON_ERROR_STOP on
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
