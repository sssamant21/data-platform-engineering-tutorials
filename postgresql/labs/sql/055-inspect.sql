\set ON_ERROR_STOP on
SELECT current_setting('server_version') AS version,
 current_setting('ssl') AS ssl,
 current_setting('password_encryption') AS password_encryption,
 current_setting('hba_file') AS hba_file,
 current_setting('log_destination') AS log_destination,
 current_setting('shared_preload_libraries') AS shared_preload_libraries;
SELECT rolname,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls
FROM pg_roles ORDER BY rolname;
SELECT r.rolname AS member,g.rolname AS granted_role,
 m.admin_option,m.inherit_option,m.set_option
FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member
JOIN pg_roles g ON g.oid=m.roleid ORDER BY 1,2;
SELECT line_number,type,database,user_name,address,auth_method,error
FROM pg_hba_file_rules ORDER BY line_number;
SELECT ssl,version,cipher,bits FROM pg_stat_ssl WHERE pid=pg_backend_pid();
SELECT schemaname,tablename,policyname,permissive,roles,cmd,qual,with_check
FROM pg_policies WHERE schemaname NOT LIKE 'pg_%' ORDER BY schemaname,tablename,policyname;
SELECT extname,extversion FROM pg_extension WHERE extname='pgaudit';
