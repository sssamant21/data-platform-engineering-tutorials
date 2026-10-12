\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout='3s';
SET LOCAL lock_timeout='500ms';
SET LOCAL max_parallel_workers_per_gather=0;
EXPLAIN (ANALYZE,BUFFERS,TIMING OFF,FORMAT JSON)
SELECT id FROM c030_incident.requests WHERE a=7 AND b=7;
ROLLBACK;
