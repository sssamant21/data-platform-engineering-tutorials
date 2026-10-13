-- Chapter 080 read-only PostgreSQL 18 security incident baseline.
SELECT current_setting('server_version') AS version,clock_timestamp() AS inspected_at;
SELECT rolname,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls
FROM pg_roles ORDER BY rolname;
SELECT parent.rolname AS granted_role,member.rolname AS member,
 m.admin_option,m.inherit_option,m.set_option
FROM pg_auth_members m JOIN pg_roles parent ON parent.oid=m.roleid
 JOIN pg_roles member ON member.oid=m.member ORDER BY 1,2;
SELECT name,setting FROM pg_settings
WHERE name IN ('ssl','password_encryption','log_connections',
 'log_disconnections','log_statement','log_line_prefix','shared_preload_libraries')
ORDER BY name;
SELECT line_number,type,database,user_name,address,auth_method,error
FROM pg_hba_file_rules ORDER BY line_number;
SELECT schemaname,tablename,policyname,permissive,roles,cmd,qual,with_check
FROM pg_policies ORDER BY schemaname,tablename,policyname;
SELECT extname,extversion FROM pg_extension ORDER BY extname;
SELECT a.usename,a.client_addr,s.ssl,s.version,s.cipher
FROM pg_stat_activity a JOIN pg_stat_ssl s USING(pid)
WHERE a.datname=current_database();
