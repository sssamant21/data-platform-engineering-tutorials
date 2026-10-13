\set ON_ERROR_STOP on
SELECT current_database(), current_user, current_setting('server_version');
CREATE SCHEMA ch038;
CREATE TABLE ch038.events (
 event_id bigint NOT NULL,
 event_time timestamptz NOT NULL,
 tenant_id integer NOT NULL,
 payload text NOT NULL,
 PRIMARY KEY (event_id,event_time)
) PARTITION BY RANGE(event_time);
CREATE TABLE ch038.events_2026_01 PARTITION OF ch038.events
 FOR VALUES FROM ('2026-01-01 00:00:00+00') TO ('2026-02-01 00:00:00+00');
CREATE TABLE ch038.events_2026_02 PARTITION OF ch038.events
 FOR VALUES FROM ('2026-02-01 00:00:00+00') TO ('2026-03-01 00:00:00+00');
CREATE TABLE ch038.events_2026_03 PARTITION OF ch038.events
 FOR VALUES FROM ('2026-03-01 00:00:00+00') TO ('2026-04-01 00:00:00+00');
CREATE INDEX events_tenant_time_idx ON ch038.events(tenant_id,event_time);
INSERT INTO ch038.events(event_id,event_time,tenant_id,payload)
SELECT g, timestamptz '2026-01-01 00:00:00+00'+(g-1)*interval '15 minutes',
 g%100,md5(g::text)
FROM generate_series(1,9000) g;
ANALYZE ch038.events;
SELECT tableoid::regclass AS partition_name,count(*) FROM ch038.events GROUP BY 1 ORDER BY 1;
