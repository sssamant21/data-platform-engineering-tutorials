\set ON_ERROR_STOP on
CREATE SCHEMA ch040;
CREATE TABLE ch040.events (event_id bigint NOT NULL,event_time timestamptz NOT NULL,tenant_id integer NOT NULL,payload text NOT NULL,PRIMARY KEY(event_id,event_time)) PARTITION BY RANGE(event_time);
CREATE TABLE ch040.events_2026_01 PARTITION OF ch040.events FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE ch040.events_2026_02 PARTITION OF ch040.events FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE ch040.events_2026_03 PARTITION OF ch040.events FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE INDEX events_tenant_time_idx ON ch040.events(tenant_id,event_time DESC);
INSERT INTO ch040.events(event_id,event_time,tenant_id,payload) SELECT g,timestamptz '2026-01-01 00:00:00+00'+(g-1)*interval '10 minutes',g%100,md5(g::text) FROM generate_series(1,12000) g;
ANALYZE ch040.events;
SELECT tableoid::regclass,count(*) FROM ch040.events GROUP BY 1 ORDER BY 1;
