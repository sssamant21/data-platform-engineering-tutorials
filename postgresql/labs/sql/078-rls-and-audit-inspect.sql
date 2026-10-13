-- Chapter 078 read-only RLS and audit inspection.
SELECT schemaname,tablename,policyname,permissive,roles,cmd,qual,with_check
FROM pg_policies WHERE schemaname='app' ORDER BY tablename,policyname;
SELECT c.relname,c.relowner::regrole AS owner,c.relrowsecurity,c.relforcerowsecurity
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='app' AND c.relkind IN ('r','p');
SELECT rolname,rolcanlogin,rolsuper,rolbypassrls
FROM pg_roles WHERE rolname LIKE 'ch078_%' ORDER BY rolname;
SELECT name,setting FROM pg_settings
WHERE name IN ('log_connections','log_disconnections','log_statement','log_line_prefix')
ORDER BY name;
SELECT extname,extversion FROM pg_extension WHERE extname='pgaudit';
