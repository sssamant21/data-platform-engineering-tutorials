-- LAB ONLY: executes one known insert. Rollback does NOT reclaim sequence values.
-- No arbitrary SQL accepted; inspect the isolated fixture and privileges first.
\set ON_ERROR_STOP on
\set QUIET on
BEGIN;
SET LOCAL statement_timeout='3s';
SET LOCAL lock_timeout='500ms';
EXPLAIN (ANALYZE TRUE, BUFFERS TRUE, WAL TRUE, TIMING FALSE, SUMMARY TRUE, FORMAT JSON)
INSERT INTO c027_plans.mutation_probe(payload)
VALUES ('synthetic-plan-probe') RETURNING id;
ROLLBACK;
