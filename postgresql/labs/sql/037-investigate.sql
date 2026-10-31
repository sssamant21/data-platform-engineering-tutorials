\set ON_ERROR_STOP on
-- One-time synthetic churn only; identity and original fixture contents are required.
\if :{?expected_system_id}
\else
 \echo 'REFUSED: expected_system_id required'
 SELECT 1/0 AS refusal_nonzero;
\endif
\if :{?confirm_churn}
\else
 \echo 'REFUSED: confirm_churn=037-CHURN required'
 SELECT 1/0 AS refusal_nonzero;
\endif
SELECT CASE WHEN current_database()='ops_lab' AND current_user='lab_admin'
 AND inet_server_addr()=inet '127.0.0.1' AND inet_server_port()=55432
 AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
 AND current_setting('data_directory') ~ '^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+/primary$'
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
 \echo 'Verified 037 pre-churn fixture'
\else
 \echo 'REFUSED: wrong cluster or changed fixture'
 SELECT 1/0 AS refusal_nonzero;
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
