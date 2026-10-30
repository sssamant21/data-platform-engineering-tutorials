\set ON_ERROR_STOP on
-- DROP only the fully verified Chapter 037 disposable table and schema.
-- No CASCADE, no generic delete, no implicit adoption of an occupied namespace.
\if :{?expected_system_id}
\else
 \echo 'REFUSED: expected_system_id required'
 \quit 3
\endif
\if :{?confirm_cleanup}
\else
 \echo 'REFUSED: confirm_cleanup=037-DROP required'
 \quit 3
\endif
SELECT CASE WHEN current_database()='ops_lab' AND current_user='lab_admin'
 AND inet_server_addr()=inet '127.0.0.1' AND inet_server_port()=55432
 AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
 AND current_setting('data_directory') ~ '^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+/primary$'
 AND NOT pg_is_in_recovery()
 AND EXISTS (SELECT 1 FROM pg_control_system() c
             WHERE c.system_identifier::text=:'expected_system_id')
 AND :'confirm_cleanup'='037-DROP'
 AND (SELECT n.nspowner FROM pg_namespace n WHERE n.nspname='ch037')
     = (SELECT oid FROM pg_roles WHERE rolname='lab_admin')
 AND (SELECT count(*) FROM ch037.orders)=90000
 AND NOT EXISTS (
   SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE n.nspname='ch037' AND c.relkind IN ('r','p','v','m','f')
     AND c.relname<>'orders')
 THEN 'true' ELSE 'false' END AS cleanup_permitted
\gset
\if :cleanup_permitted
 \echo 'Verified Chapter 037 fixture; removing exact lab table and namespace'
\else
 \echo 'REFUSED: unexpected target, contents, ownership, or fixture count'
 \quit 3
\endif
BEGIN;
SET LOCAL statement_timeout='10s';
SET LOCAL lock_timeout='1s';
DROP TABLE ch037.orders;
DROP SCHEMA ch037;
COMMIT;
SELECT to_regnamespace('ch037') IS NULL AS lab_schema_removed;
