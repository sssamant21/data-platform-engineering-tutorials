\set ON_ERROR_STOP on
\echo '1. Baseline'
EXPLAIN (ANALYZE, BUFFERS) SELECT id, amount FROM ch032.orders WHERE tenant_id=7 AND created_at >= '2026-02-01' ORDER BY created_at DESC LIMIT 20;
\echo '2. Composite'
CREATE INDEX orders_tenant_created_idx ON ch032.orders (tenant_id, created_at DESC);
ANALYZE ch032.orders;
EXPLAIN (ANALYZE, BUFFERS) SELECT id, amount FROM ch032.orders WHERE tenant_id=7 AND created_at >= '2026-02-01' ORDER BY created_at DESC LIMIT 20;
\echo '3. Partial'
CREATE INDEX orders_open_tenant_created_idx ON ch032.orders (tenant_id, created_at DESC) WHERE status='open';
ANALYZE ch032.orders;
EXPLAIN (ANALYZE, BUFFERS) SELECT id FROM ch032.orders WHERE tenant_id=1 AND status='open' ORDER BY created_at DESC LIMIT 20;
SET plan_cache_mode = force_generic_plan;
PREPARE ch032_status(integer,text) AS SELECT id FROM ch032.orders WHERE tenant_id=$1 AND status=$2 ORDER BY created_at DESC LIMIT 20;
EXPLAIN EXECUTE ch032_status(1,'open');
DEALLOCATE ch032_status;
RESET plan_cache_mode;
\echo '4. Expression'
EXPLAIN (ANALYZE, BUFFERS) SELECT count(*) FROM ch032.orders WHERE lower(email)='user1@example.test';
CREATE INDEX orders_lower_email_idx ON ch032.orders ((lower(email)));
ANALYZE ch032.orders;
EXPLAIN (ANALYZE, BUFFERS) SELECT count(*) FROM ch032.orders WHERE lower(email)='user1@example.test';
\echo '5. Covering'
EXPLAIN (ANALYZE, BUFFERS) SELECT tenant_id, created_at, amount FROM ch032.orders WHERE tenant_id=7 ORDER BY created_at DESC LIMIT 20;
CREATE INDEX orders_tenant_created_cover_idx ON ch032.orders (tenant_id, created_at DESC) INCLUDE (amount);
ANALYZE ch032.orders;
EXPLAIN (ANALYZE, BUFFERS) SELECT tenant_id, created_at, amount FROM ch032.orders WHERE tenant_id=7 ORDER BY created_at DESC LIMIT 20;
VACUUM (ANALYZE) ch032.orders;
EXPLAIN (ANALYZE, BUFFERS) SELECT tenant_id, created_at, amount FROM ch032.orders WHERE tenant_id=7 ORDER BY created_at DESC LIMIT 20;
\echo '6. Size and definition'
SELECT indexname, indexdef, pg_size_pretty(pg_relation_size((quote_ident(schemaname)||'.'||quote_ident(indexname))::regclass)) AS size
FROM pg_indexes WHERE schemaname='ch032' ORDER BY indexname;
