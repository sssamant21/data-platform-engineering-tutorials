-- PG18 read-only lifecycle evidence, scoped to five Chapter 014 roles.
-- Never selects password verifiers or session query text.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
SELECT clock_timestamp() AS observed_at,current_database(),current_user,
       inet_server_addr(),inet_server_port(),pg_is_in_recovery();
SELECT rolname,rolcanlogin,rolvaliduntil,rolconnlimit,
       rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls
FROM pg_roles
WHERE rolname IN ('c014_owner','c014_reader','c014_single','c014_blue','c014_green')
ORDER BY rolname;
SELECT parent.rolname AS granted_role,member.rolname AS member,
       grantor.rolname AS grantor,m.inherit_option,m.set_option,m.admin_option
FROM pg_auth_members m
JOIN pg_roles parent ON parent.oid=m.roleid
JOIN pg_roles member ON member.oid=m.member
JOIN pg_roles grantor ON grantor.oid=m.grantor
WHERE member.rolname IN ('c014_single','c014_blue','c014_green')
ORDER BY member,granted_role,grantor;
SELECT pid,datname,usename,application_name,client_addr,backend_start,
       state,xact_start,backend_type
FROM pg_stat_activity
WHERE usename IN ('c014_single','c014_blue','c014_green')
ORDER BY usename,backend_start;
SELECT r.rolname,COALESCE(d.datname,'<shared object>') AS database_scope,
       s.classid::regclass AS catalog,s.objid,s.objsubid,s.deptype
FROM pg_shdepend s JOIN pg_roles r ON r.oid=s.refobjid
LEFT JOIN pg_database d ON d.oid=s.dbid
WHERE s.refclassid='pg_authid'::regclass
  AND r.rolname IN ('c014_owner','c014_reader','c014_single','c014_blue','c014_green')
ORDER BY r.rolname,database_scope,catalog,s.objid;
SELECT r.rolname,c.relname,
       has_table_privilege(r.oid,c.oid,'SELECT') AS can_select,
       has_table_privilege(r.oid,c.oid,'INSERT') AS can_insert
FROM pg_roles r CROSS JOIN pg_class c
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE r.rolname IN ('c014_single','c014_blue','c014_green')
  AND n.nspname='c014_data' AND c.relname='probe'
ORDER BY r.rolname;
COMMIT;
