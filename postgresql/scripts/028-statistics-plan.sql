\set ON_ERROR_STOP on
\if :{?shape}
\else
  \echo 'Pass -v shape=compatible|incompatible|groups'
  \quit 2
\endif
SELECT :'shape' = 'compatible' AS compatible,
       :'shape' = 'incompatible' AS incompatible,
       :'shape' = 'groups' AS groups,
       :'shape' IN ('compatible','incompatible','groups') AS valid \gset
\if :valid
\else
  \echo 'Invalid shape'
  \quit 2
\endif
BEGIN READ ONLY;
SET LOCAL statement_timeout = '3s';
SET LOCAL lock_timeout = '500ms';
SET LOCAL max_parallel_workers_per_gather = 0;
\if :compatible
EXPLAIN (ANALYZE, BUFFERS, TIMING OFF, FORMAT JSON)
SELECT id FROM c028_stats.correlated WHERE a=7 AND b=7;
\elif :incompatible
EXPLAIN (ANALYZE, BUFFERS, TIMING OFF, FORMAT JSON)
SELECT id FROM c028_stats.correlated WHERE a=7 AND b=8;
\else
EXPLAIN (ANALYZE, BUFFERS, TIMING OFF, FORMAT JSON)
SELECT a,b,count(*) FROM c028_stats.correlated GROUP BY a,b;
\endif
ROLLBACK;
