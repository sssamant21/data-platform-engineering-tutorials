-- Chapter 101: least privilege and SQL access-control principles.
-- PostgreSQL 18; disposable database sql_tutorials; synthetic permissions only.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
 IF current_database() <> 'sql_tutorials' THEN
  RAISE EXCEPTION 'Expected disposable sql_tutorials database, found %', current_database();
 END IF;
 IF current_setting('server_version_num')::integer / 10000 <> 18 THEN
  RAISE EXCEPTION 'PostgreSQL 18 required; found %', current_setting('server_version');
 END IF;
END
$guard$;

-- Read-only, session-specific introspection: values vary with lab login.
SELECT current_database() AS database_name,
       current_user AS effective_role,
       session_user AS login_role,
       has_database_privilege(current_user, current_database(), 'CONNECT') AS can_connect,
       has_schema_privilege(current_user, 'pg_catalog', 'USAGE') AS can_use_catalog;

-- Synthetic policy; this does not inspect or modify real role grants.
WITH policy(role_name, object_name, action, permitted) AS (
 VALUES
 ('reporting_reader','reporting.daily_sales','SELECT',true),
 ('reporting_reader','reporting.daily_sales','INSERT',false),
 ('reporting_reader','reporting.daily_sales','UPDATE',false),
 ('reporting_reader','reporting.daily_sales','DELETE',false),
 ('ingest_writer','staging.orders','INSERT',true),
 ('ingest_writer','staging.orders','UPDATE',true),
 ('ingest_writer','staging.orders','DELETE',false),
 ('migration_deployer','staging','CREATE',true),
 ('migration_deployer','reporting','CREATE',false)
)
SELECT role_name, count(*) FILTER (WHERE permitted) AS allowed,
       count(*) FILTER (WHERE NOT permitted) AS denied
FROM policy GROUP BY role_name ORDER BY role_name;

DO $assert$
DECLARE allowed_count integer; forbidden_count integer; missing_count integer; policy_rows integer;
BEGIN
 WITH policy(role_name,object_name,action,permitted) AS (
 VALUES
 ('reporting_reader','reporting.daily_sales','SELECT',true),
 ('reporting_reader','reporting.daily_sales','INSERT',false),
 ('reporting_reader','reporting.daily_sales','UPDATE',false),
 ('reporting_reader','reporting.daily_sales','DELETE',false),
 ('ingest_writer','staging.orders','INSERT',true),
 ('ingest_writer','staging.orders','UPDATE',true),
 ('ingest_writer','staging.orders','DELETE',false),
 ('migration_deployer','staging','CREATE',true),
 ('migration_deployer','reporting','CREATE',false)
 ), expected(role_name,object_name,action) AS (
 VALUES
 ('reporting_reader','reporting.daily_sales','SELECT'),
 ('ingest_writer','staging.orders','INSERT'),
 ('ingest_writer','staging.orders','UPDATE'),
 ('migration_deployer','staging','CREATE')
 ), actual AS (
 SELECT role_name,object_name,action FROM policy WHERE permitted
 ), forbidden AS (
 SELECT role_name,object_name,action FROM actual
 EXCEPT ALL SELECT role_name,object_name,action FROM expected
 ), missing AS (
 SELECT role_name,object_name,action FROM expected
 EXCEPT ALL SELECT role_name,object_name,action FROM actual
 )
 SELECT (SELECT count(*) FROM actual),
        (SELECT count(*) FROM forbidden),
        (SELECT count(*) FROM missing),
        (SELECT count(*) FROM policy)
 INTO allowed_count,forbidden_count,missing_count,policy_rows;
 IF allowed_count<>4 OR forbidden_count<>0 OR missing_count<>0 OR policy_rows<>9 THEN
  RAISE EXCEPTION '101 policy assertion failed: allowed %, forbidden %, missing %, rows %',
    allowed_count,forbidden_count,missing_count,policy_rows;
 END IF;
 RAISE NOTICE '101 assertions passed: 9 synthetic policy rows, 4 allowed, 0 forbidden, 0 missing';
END
$assert$;

ROLLBACK;
