\set ON_ERROR_STOP on
\if :{?mode}
\else
  \echo 'Pass -v mode=sleep|cpu|spill_low|spill_high'
  \quit 2
\endif
SELECT :'mode'='sleep' AS sleep,
       :'mode'='cpu' AS cpu,
       :'mode'='spill_low' AS spill_low,
       :'mode' IN ('sleep','cpu','spill_low','spill_high') AS valid \gset
\if :valid
\else
  \echo 'Invalid mode'
  \quit 2
\endif
BEGIN READ ONLY;
SET LOCAL statement_timeout='8s';
SET LOCAL lock_timeout='500ms';
SET LOCAL max_parallel_workers_per_gather=0;
SET LOCAL temp_file_limit='32MB';
\if :sleep
SELECT pg_sleep(4);
\elif :cpu
SET LOCAL work_mem='1MB';
-- ProjectSet in a subquery avoids the FROM FunctionScan's large tuplestore.
SELECT sum(length(md5(i::text)))
FROM (SELECT generate_series(1,2000000) AS i) AS s;
\else
\if :spill_low
SET LOCAL work_mem='64kB';
\else
SET LOCAL work_mem='32MB';
\endif
EXPLAIN (ANALYZE, BUFFERS, TIMING OFF, FORMAT JSON)
SELECT i, repeat(md5(i::text),8) AS payload
FROM generate_series(1,30000) AS s(i)
ORDER BY payload,i;
\endif
ROLLBACK;
