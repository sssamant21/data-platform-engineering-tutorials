\set ON_ERROR_STOP on
\timing on
SELECT inhrelid::regclass AS partition_name FROM pg_inherits
 WHERE inhparent='ch039.events'::regclass ORDER BY 1;
EXPLAIN (ANALYZE,BUFFERS,SETTINGS)
SELECT count(*) FROM ch039.events
WHERE event_time >= timestamptz '2026-02-01 00:00:00+00'
AND event_time < timestamptz '2026-03-01 00:00:00+00';
EXPLAIN (ANALYZE,BUFFERS,SETTINGS)
SELECT count(*) FROM ch039.events WHERE tenant_id=42;
EXPLAIN (ANALYZE,BUFFERS,SETTINGS)
SELECT event_id FROM ch039.events WHERE tenant_id=42
AND event_time >= timestamptz '2026-02-01 00:00:00+00'
AND event_time < timestamptz '2026-03-01 00:00:00+00'
ORDER BY event_time DESC LIMIT 20;
SET plan_cache_mode=force_custom_plan;
PREPARE monthly(timestamptz,timestamptz) AS
 SELECT count(*) FROM ch039.events WHERE event_time >= $1 AND event_time < $2;
EXPLAIN (ANALYZE,BUFFERS) EXECUTE monthly('2026-02-01 00:00:00+00','2026-03-01 00:00:00+00');
DEALLOCATE monthly;
SET plan_cache_mode=force_generic_plan;
PREPARE monthly(timestamptz,timestamptz) AS
 SELECT count(*) FROM ch039.events WHERE event_time >= $1 AND event_time < $2;
EXPLAIN (ANALYZE,BUFFERS) EXECUTE monthly('2026-02-01 00:00:00+00','2026-03-01 00:00:00+00');
DEALLOCATE monthly;
RESET plan_cache_mode;
ANALYZE ch039.events;
SELECT relid::regclass,n_live_tup,last_analyze,last_autoanalyze
 FROM pg_stat_user_tables WHERE relid='ch039.events'::regclass
 OR relid IN (SELECT inhrelid FROM pg_inherits WHERE inhparent='ch039.events'::regclass);
