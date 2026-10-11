-- PG18 read-only metadata. Run against c011_db, preferably as lab_observer.
-- This inventory is bounded to Chapter 011 names, not an all-database security audit.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';

SELECT clock_timestamp() AS observed_at,current_database(),session_user,current_user,
       inet_server_addr(),inet_server_port(),pg_is_in_recovery();

SELECT rolname,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,
       rolbypassrls,rolinherit,rolconnlimit,rolvaliduntil
FROM pg_roles
WHERE rolname IN ('c011_owner','c011_reader','c011_writer','c011_runtime','c011_deploy')
ORDER BY rolname;

SELECT parent.rolname AS granted_role,member.rolname AS member,
       grantor.rolname AS grantor,m.admin_option,m.inherit_option,m.set_option
FROM pg_auth_members m
JOIN pg_roles parent ON parent.oid=m.roleid
JOIN pg_roles member ON member.oid=m.member
JOIN pg_roles grantor ON grantor.oid=m.grantor
WHERE parent.rolname IN ('c011_owner','c011_reader','c011_writer','c011_runtime','c011_deploy')
   OR member.rolname IN ('c011_owner','c011_reader','c011_writer','c011_runtime','c011_deploy')
ORDER BY granted_role,member,grantor;

SELECT r.rolname,has_database_privilege(r.oid,current_database(),'CONNECT') AS can_connect,
       has_database_privilege(r.oid,current_database(),'CREATE') AS can_create_schema
FROM pg_roles r WHERE r.rolname IN ('c011_runtime','c011_deploy')
ORDER BY r.rolname;

SELECT n.nspname,pg_get_userbyid(n.nspowner) AS owner,n.nspacl
FROM pg_namespace n WHERE n.nspname IN ('c011_data','public')
ORDER BY n.nspname;

SELECT n.nspname,c.relname,c.relkind,pg_get_userbyid(c.relowner) AS owner,c.relacl
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='c011_data'
ORDER BY c.relname;

SELECT pg_get_userbyid(d.defaclrole) AS creator,
       COALESCE(n.nspname,'<global>') AS schema_scope,d.defaclobjtype,d.defaclacl
FROM pg_default_acl d LEFT JOIN pg_namespace n ON n.oid=d.defaclnamespace
WHERE d.defaclrole IN (SELECT oid FROM pg_roles
                      WHERE rolname IN ('c011_owner','c011_deploy'))
ORDER BY creator,schema_scope,d.defaclobjtype;

SELECT r.rolname,n.nspname,c.relname,
       has_schema_privilege(r.oid,n.oid,'USAGE') AS schema_usage,
       has_schema_privilege(r.oid,n.oid,'CREATE') AS schema_create,
       has_table_privilege(r.oid,c.oid,'SELECT') AS can_select,
       has_table_privilege(r.oid,c.oid,'INSERT') AS can_insert,
       has_table_privilege(r.oid,c.oid,'UPDATE') AS can_update,
       has_table_privilege(r.oid,c.oid,'DELETE') AS can_delete,
       has_table_privilege(r.oid,c.oid,'TRUNCATE') AS can_truncate
FROM pg_roles r CROSS JOIN pg_class c
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE r.rolname='c011_runtime' AND n.nspname='c011_data' AND c.relkind='r'
ORDER BY c.relname;

SELECT r.rolname AS member,o.rolname AS target,
       pg_has_role(r.oid,o.oid,'MEMBER') AS membership_exists,
       pg_has_role(r.oid,o.oid,'USAGE') AS privileges_available,
       pg_has_role(r.oid,o.oid,'SET') AS may_assume_role
FROM pg_roles r CROSS JOIN pg_roles o
WHERE r.rolname IN ('c011_runtime','c011_deploy')
  AND o.rolname IN ('c011_reader','c011_writer','c011_owner')
ORDER BY member,target;

COMMIT;
