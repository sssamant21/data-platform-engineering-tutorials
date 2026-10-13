-- Chapter 079: read-only PostgreSQL 18 security posture inspection.
SELECT current_setting('server_version') AS version,clock_timestamp() AS inspected_at;
SELECT name,setting,source,pending_restart
FROM pg_settings
WHERE name IN ('ssl','ssl_min_protocol_version','ssl_max_protocol_version',
 'ssl_ciphers','password_encryption','log_connections','log_disconnections',
 'log_statement','log_line_prefix','shared_preload_libraries','listen_addresses')
ORDER BY name;
SELECT rolname,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls
FROM pg_roles ORDER BY rolname;
SELECT extname,extversion FROM pg_extension ORDER BY extname;
SELECT a.usename,a.client_addr,s.ssl,s.version,s.cipher
FROM pg_stat_activity a JOIN pg_stat_ssl s USING(pid)
WHERE a.datname=current_database();
SELECT nspname,nspowner::regrole AS owner,nspacl
FROM pg_namespace WHERE nspname='public';
