-- PG18: Chapter 011 isolated role/database teardown; standalone SQL, no transaction.
-- Requires disposable Chapter 004 system-id and explicit chapter-specific authorization.
-- DO NOT run this on production; operations cannot be rolled back together.
\set ON_ERROR_STOP on
\if :{?expected_system_id}
\else
  \echo 'REFUSED: supply independently verified -v expected_system_id'
  \quit 3
\endif
\if :{?confirm_cleanup}
\else
  \echo 'REFUSED: supply chapter-specific cleanup confirmation'
  \quit 3
\endif
SELECT CASE WHEN current_database()='ops_lab'
  AND current_user='lab_admin'
  AND inet_server_addr()=inet '127.0.0.1'
  AND inet_server_port()=55432
  AND NOT pg_is_in_recovery()
  AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
  AND current_setting('data_directory') LIKE '/tmp/postgresql-dbre-lab.%/primary'
  AND EXISTS (SELECT 1 FROM pg_control_system() c
              WHERE c.system_identifier::text=:'expected_system_id')
  AND :'confirm_cleanup'='011-DROP-ROLES-DB'
  AND EXISTS (SELECT 1 FROM pg_database d JOIN pg_roles r ON r.oid=d.datdba
              WHERE d.datname='c011_db' AND r.rolname='c011_owner')
  AND (SELECT count(*) FROM pg_roles WHERE rolname IN ('c011_runtime','c011_deploy','c011_writer','c011_reader','c011_owner'))=5
  AND NOT EXISTS (SELECT 1 FROM pg_stat_activity WHERE datname='c011_db')
  THEN 'true' ELSE 'false' END AS cleanup_permitted
\gset
\if :cleanup_permitted
  \echo 'Approved disposable cluster and expected lab role set matched.'
\else
  \echo 'REFUSED: cluster, database, ownership, role set, sessions or token mismatch'
  \quit 3
\endif
DROP DATABASE c011_db;
DROP ROLE c011_runtime;
DROP ROLE c011_deploy;
DROP ROLE c011_writer;
DROP ROLE c011_reader;
DROP ROLE c011_owner;
SELECT rolname FROM pg_roles WHERE rolname IN ('c011_runtime','c011_deploy','c011_writer','c011_reader','c011_owner');
SELECT datname FROM pg_database WHERE datname='c011_db';
