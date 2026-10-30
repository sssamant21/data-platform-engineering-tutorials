\set ON_ERROR_STOP on
SELECT current_database() AS database_name,current_setting('server_version') AS version;
SELECT rolname,rolcanlogin,rolsuper,rolbypassrls
FROM pg_roles WHERE rolname LIKE 'ch051_%' ORDER BY rolname;
SELECT r.rolname AS member,g.rolname AS granted_role,m.inherit_option,m.set_option,m.admin_option
FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member
JOIN pg_roles g ON g.oid=m.roleid WHERE r.rolname LIKE 'ch051_%';
SELECT
 has_table_privilege('ch051_reader','ch051.events','SELECT') AS reader_select_pass,
 has_table_privilege('ch051_reader','ch051.after_default_grants','SELECT') AS future_reader_select_pass,
 has_table_privilege('ch051_writer','ch051.after_default_grants','INSERT') AS future_writer_insert_pass,
 NOT has_table_privilege('ch051_reader','ch051.events','INSERT') AS reader_no_insert_pass,
 has_table_privilege('ch051_writer','ch051.events','INSERT') AS writer_insert_pass,
 NOT has_schema_privilege('ch051_writer','ch051','CREATE') AS writer_no_create_pass,
 NOT (SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname='ch051_writer') AS writer_no_bypass_pass;
SELECT defaclrole::regrole AS creator,defaclnamespace::regnamespace AS schema,
 defaclobjtype,defaclacl FROM pg_default_acl WHERE defaclrole='ch051_owner'::regrole;

-- Metadata columns are not a PASS gate by themselves. Fail the psql process on drift.
DO $accept$
BEGIN
 IF current_database()<>'ch051_lab' THEN RAISE EXCEPTION 'Wrong Chapter 051 database'; END IF;
 IF NOT (
  has_table_privilege('ch051_reader','ch051.events','SELECT')
  AND has_table_privilege('ch051_reader','ch051.after_default_grants','SELECT')
  AND has_table_privilege('ch051_writer','ch051.after_default_grants','INSERT')
  AND NOT has_table_privilege('ch051_reader','ch051.events','INSERT')
  AND has_table_privilege('ch051_writer','ch051.events','INSERT')
  AND NOT has_schema_privilege('ch051_writer','ch051','CREATE')
  AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname='ch051_writer'
              AND NOT rolsuper AND NOT rolbypassrls AND NOT rolcreaterole AND NOT rolcreatedb)
  AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname='ch051_reader'
              AND NOT rolsuper AND NOT rolbypassrls AND NOT rolcreaterole AND NOT rolcreatedb)
  AND (SELECT count(*) FROM pg_roles WHERE rolname IN
    ('ch051_owner','ch051_reader_group','ch051_writer_group','ch051_reader','ch051_writer'))=5
  AND (SELECT count(*) FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member
       JOIN pg_roles g ON g.oid=m.roleid
       WHERE (r.rolname='ch051_reader' AND g.rolname='ch051_reader_group'
              OR r.rolname='ch051_writer' AND g.rolname='ch051_writer_group')
         AND m.inherit_option AND NOT m.set_option AND NOT m.admin_option)=2
 ) THEN
   RAISE EXCEPTION 'FAIL: Chapter 051 role grants or least-privilege contract violated';
 END IF;
 RAISE NOTICE 'PASS: Chapter 051 metadata acceptance contract';
END $accept$;
