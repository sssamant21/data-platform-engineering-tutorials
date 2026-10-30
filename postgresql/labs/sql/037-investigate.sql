\set ON_ERROR_STOP on
-- Fail closed before the intentional UPDATE/DELETE churn. One run per fixture.
\if :{?expected_system_id}
\else
 \echo 'REFUSED: supply observed disposable lab cluster ID'
 \quit 3
\endif
\if :{?confirm_churn}
\else
 \echo 'REFUSED: -v confirm_churn=037-CHURN required'
 \quit 3
\endif
SELECT CASE WHEN current_database()='ops_lab' AND current_user='lab_admin'
 AND inet_server_addr()=inet '127.0.0.1' AND inet_server_port()=55432
 AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
 AND current_setting('data_directory') ~ '^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+/primary\timing on
SELECT pg_relation_size('ch037.orders'::regclass) AS heap_bytes,
 pg_indexes_size('ch037.orders'::regclass) AS index_bytes;
SELECT relname,n_live_tup,n_dead_tup,last_vacuum,last_autovacuum
 FROM pg_stat_user_tables WHERE relid='ch037.orders'::regclass;
EXPLAIN (ANALYZE, BUFFERS)
 SELECT id FROM ch037.orders WHERE customer_id=42 ORDER BY created_at DESC LIMIT 10;
UPDATE ch037.orders SET status='updated' WHERE id BETWEEN 1 AND 20000;
DELETE FROM ch037.orders WHERE id BETWEEN 20001 AND 30000;
SELECT pg_stat_clear_snapshot();
SELECT n_live_tup,n_dead_tup FROM pg_stat_user_tables WHERE relid='ch037.orders'::regclass;
ANALYZE ch037.orders;
VACUUM (ANALYZE) ch037.orders;
SELECT pg_stat_clear_snapshot();
SELECT n_live_tup,n_dead_tup,last_vacuum FROM pg_stat_user_tables WHERE relid='ch037.orders'::regclass;
SELECT pg_relation_size('ch037.orders'::regclass) AS heap_bytes,
 pg_indexes_size('ch037.orders'::regclass) AS index_bytes;
SELECT datname,age(datfrozenxid) AS xid_age FROM pg_database WHERE datname=current_database();

 AND NOT pg_is_in_recovery()
 AND EXISTS (SELECT 1 FROM pg_control_system() c
             WHERE c.system_identifier::text=:'expected_system_id')
 AND :'confirm_churn'='037-CHURN'
 AND (SELECT count(*) FROM ch037.orders)=100000
 AND (SELECT count(*) FROM ch037.orders WHERE status='updated')=0
 AND (SELECT count(*) FROM ch037.orders WHERE id BETWEEN 1 AND 20000)=20000
 AND (SELECT count(*) FROM ch037.orders WHERE id BETWEEN 20001 AND 30000)=10000
 AND (SELECT n.nspowner FROM pg_namespace n WHERE n.nspname='ch037')
       = (SELECT oid FROM pg_roles WHERE rolname='lab_admin')
 THEN 'true' ELSE 'false' END AS churn_permitted
\gset
\if :churn_permitted
 \echo 'Chapter 037 expected fixture verified before synthetic churn'
\else
 \echo 'REFUSED: unexpected target or fixture state; no writes applied'
 \quit 3
\endif
\timing on
SELECT pg_relation_size('ch037.orders'::regclass) AS heap_bytes,
 pg_indexes_size('ch037.orders'::regclass) AS index_bytes;
SELECT relname,n_live_tup,n_dead_tup,last_vacuum,last_autovacuum
 FROM pg_stat_user_tables WHERE relid='ch037.orders'::regclass;
EXPLAIN (ANALYZE, BUFFERS)
 SELECT id FROM ch037.orders WHERE customer_id=42 ORDER BY created_at DESC LIMIT 10;
UPDATE ch037.orders SET status='updated' WHERE id BETWEEN 1 AND 20000;
DELETE FROM ch037.orders WHERE id BETWEEN 20001 AND 30000;
SELECT pg_stat_clear_snapshot();
SELECT n_live_tup,n_dead_tup FROM pg_stat_user_tables WHERE relid='ch037.orders'::regclass;
ANALYZE ch037.orders;
VACUUM (ANALYZE) ch037.orders;
SELECT pg_stat_clear_snapshot();
SELECT n_live_tup,n_dead_tup,last_vacuum FROM pg_stat_user_tables WHERE relid='ch037.orders'::regclass;
SELECT pg_relation_size('ch037.orders'::regclass) AS heap_bytes,
 pg_indexes_size('ch037.orders'::regclass) AS index_bytes;
SELECT datname,age(datfrozenxid) AS xid_age FROM pg_database WHERE datname=current_database();
