-- Chapter 076 read-only role and privilege inspection.
SELECT rolname,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls
FROM pg_roles WHERE rolname LIKE 'ch076_%' ORDER BY rolname;
SELECT parent.rolname AS granted_role,member.rolname AS member,
 m.admin_option,m.inherit_option,m.set_option
FROM pg_auth_members m
JOIN pg_roles parent ON parent.oid=m.roleid
JOIN pg_roles member ON member.oid=m.member
WHERE parent.rolname LIKE 'ch076_%' OR member.rolname LIKE 'ch076_%'
ORDER BY 1,2;
SELECT nspname,nspowner::regrole AS owner,nspacl
FROM pg_namespace WHERE nspname='app';
SELECT defaclrole::regrole AS creator,defaclnamespace::regnamespace AS schema,
 defaclobjtype,defaclacl FROM pg_default_acl
WHERE defaclrole IN (SELECT oid FROM pg_roles WHERE rolname LIKE 'ch076_%');
SELECT has_schema_privilege('ch076_app_login','app','USAGE') AS app_schema_usage,
 has_schema_privilege('ch076_app_login','app','CREATE') AS app_schema_create,
 has_table_privilege('ch076_app_login','app.orders','SELECT') AS app_select,
 has_table_privilege('ch076_analyst_login','app.orders','INSERT') AS analyst_insert;
