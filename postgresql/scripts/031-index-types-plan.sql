\set ON_ERROR_STOP on
\if :{?shape}
\else
 \echo 'Pass -v shape=eq|range|tags|span|points|ordered|scattered'
 \quit 2
\endif
\if :{?diagnostic}
\else
 \set diagnostic off
\endif
SELECT :'shape'='eq' AS eq, :'shape'='range' AS range_query,
       :'shape'='tags' AS tags, :'shape'='span' AS span_query,
       :'shape'='points' AS points, :'shape'='ordered' AS ordered_query,
       :'shape' IN ('eq','range','tags','span','points','ordered','scattered') AS valid,
       :'diagnostic'='on' AS discourage_seqscan,
       :'diagnostic' IN ('on','off') AS valid_diagnostic \gset
\if :valid
\else
 \echo 'Invalid shape'
 \quit 2
\endif
\if :valid_diagnostic
\else
 \echo 'Invalid diagnostic mode'
 \quit 2
\endif
BEGIN READ ONLY;
SET LOCAL statement_timeout='3s';
SET LOCAL lock_timeout='500ms';
SET LOCAL max_parallel_workers_per_gather=0;
SET LOCAL work_mem='4MB';
\if :discourage_seqscan
 SET LOCAL enable_seqscan=off;
\endif
\if :eq
EXPLAIN (ANALYZE,BUFFERS,TIMING OFF,FORMAT JSON)
SELECT id FROM c031_indexes.events WHERE event_key=42;
\elif :range_query
EXPLAIN (ANALYZE,BUFFERS,TIMING OFF,FORMAT JSON)
SELECT id FROM c031_indexes.events WHERE event_key>=42 AND event_key<92;
\elif :tags
EXPLAIN (ANALYZE,BUFFERS,TIMING OFF,FORMAT JSON)
SELECT id FROM c031_indexes.events WHERE tags @> ARRAY['rare']::text[];
\elif :span_query
EXPLAIN (ANALYZE,BUFFERS,TIMING OFF,FORMAT JSON)
SELECT id FROM c031_indexes.events WHERE span @> 4242;
\elif :points
EXPLAIN (ANALYZE,BUFFERS,TIMING OFF,FORMAT JSON)
SELECT id FROM c031_indexes.events WHERE location <@ box(point(10,10),point(12,12));
\elif :ordered_query
EXPLAIN (ANALYZE,BUFFERS,TIMING OFF,FORMAT JSON)
SELECT id FROM c031_indexes.events
WHERE ordered_at>=timestamp '2026-01-01 01:00:00'
AND ordered_at<timestamp '2026-01-01 01:01:40';
\else
EXPLAIN (ANALYZE,BUFFERS,TIMING OFF,FORMAT JSON)
SELECT id FROM c031_indexes.events
WHERE scattered_at>=timestamp '2026-01-01 01:00:00'
AND scattered_at<timestamp '2026-01-01 01:01:40';
\endif
ROLLBACK;
