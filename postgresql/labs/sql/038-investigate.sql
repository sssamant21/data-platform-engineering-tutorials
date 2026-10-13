\set ON_ERROR_STOP on
\timing on
SELECT inhparent::regclass AS parent,inhrelid::regclass AS child
FROM pg_inherits WHERE inhparent='ch038.events'::regclass ORDER BY 2;
SELECT c.oid::regclass,pg_get_expr(c.relpartbound,c.oid) AS partition_bound
FROM pg_class c WHERE c.oid IN
 (SELECT inhrelid FROM pg_inherits WHERE inhparent='ch038.events'::regclass);
EXPLAIN (ANALYZE,BUFFERS)
SELECT count(*) FROM ch038.events
WHERE event_time >= timestamptz '2026-02-01 00:00:00+00'
AND event_time < timestamptz '2026-03-01 00:00:00+00';
EXPLAIN (ANALYZE,BUFFERS) SELECT count(*) FROM ch038.events;
SELECT count(*) AS before_detach FROM ch038.events;
ALTER TABLE ch038.events DETACH PARTITION ch038.events_2026_02;
SELECT count(*) AS detached_rows FROM ch038.events_2026_02;
ALTER TABLE ch038.events ATTACH PARTITION ch038.events_2026_02
FOR VALUES FROM ('2026-02-01 00:00:00+00') TO ('2026-03-01 00:00:00+00');
ANALYZE ch038.events;
SELECT count(*) AS after_attach FROM ch038.events;
SELECT tableoid::regclass AS partition_name,count(*) FROM ch038.events GROUP BY 1 ORDER BY 1;
