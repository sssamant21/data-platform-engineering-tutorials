-- PG18 fixed fixture query only. psql -X -qAt -v mode=estimated|executed
\set ON_ERROR_STOP on
\set QUIET on
\if :{?mode}
\else
  \echo 'Specify estimated or executed mode'
  SELECT 1/0;
\endif
SELECT :'mode'='estimated' AS estimated_mode, :'mode'='executed' AS executed_mode \gset
BEGIN READ ONLY;
SET LOCAL statement_timeout='3s';
SET LOCAL lock_timeout='500ms';
\if :estimated_mode
EXPLAIN (ANALYZE FALSE, COSTS TRUE, SETTINGS TRUE, SUMMARY TRUE, FORMAT JSON)
SELECT i.id,
       (SELECT count(*) FROM c027_plans.items j
        WHERE j.id BETWEEN i.id AND i.id+2) AS nearby
FROM c027_plans.items i WHERE i.id<=3;
\elif :executed_mode
EXPLAIN (ANALYZE TRUE, BUFFERS TRUE, TIMING FALSE, SETTINGS TRUE, SUMMARY TRUE, FORMAT JSON)
SELECT i.id,
       (SELECT count(*) FROM c027_plans.items j
        WHERE j.id BETWEEN i.id AND i.id+2) AS nearby
FROM c027_plans.items i WHERE i.id<=3;
\else
  \echo 'Invalid mode; no plan executed'
  SELECT 1/0;
\endif
ROLLBACK;
