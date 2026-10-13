\set ON_ERROR_STOP on
SELECT current_database() AS database_name,current_setting('server_version') AS version;
SELECT rolname,rolcanlogin,rolsuper,rolbypassrls
FROM pg_roles WHERE rolname LIKE 'ch051_%' ORDER BY rolname;
SELECT r.rolname AS member,g.rolname AS granted_role,m.inherit_option,m.set_option,m.admin_option
FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member
JOIN pg_roles g ON g.oid=m.roleid WHERE r.rolname LIKE 'ch051_%';
SELECT
 has_table_privilege('ch051_reader','ch051.events','SELECT') AS reader_select_pass,
 NOT has_table_privilege('ch051_reader','ch051.events','INSERT') AS reader_no_insert_pass,
 has_table_privilege('ch051_writer','ch051.events','INSERT') AS writer_insert_pass,
 NOT has_schema_privilege('ch051_writer','ch051','CREATE') AS writer_no_create_pass,
 NOT (SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname='ch051_writer') AS writer_no_bypass_pass;
SELECT defaclrole::regrole AS creator,defaclnamespace::regnamespace AS schema,
 defaclobjtype,defaclacl FROM pg_default_acl WHERE defaclrole='ch051_owner'::regrole;
