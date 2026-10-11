-- PG18 read-only security evidence. lab_admin for HBA file inspection.
-- Does not expose passwords, verifiers or session query text.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
SELECT clock_timestamp() AS observed_at,current_database(),session_user,current_user,
       inet_server_addr(),inet_server_port(),pg_is_in_recovery();
SELECT name,setting,source,context,pending_restart
FROM pg_settings
WHERE name IN ('listen_addresses','port','ssl','hba_file','log_destination',
 'logging_collector','log_connections','log_disconnections','log_line_prefix',
 'log_statement','log_min_error_statement','log_error_verbosity',
 'log_parameter_max_length','log_parameter_max_length_on_error',
 'shared_preload_libraries')
ORDER BY name;
SELECT rule_number,file_name,line_number,type,database,user_name,address,
       auth_method,error
FROM pg_hba_file_rules
ORDER BY rule_number NULLS LAST,file_name,line_number;
SELECT rolname,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls
FROM pg_roles WHERE rolname IN ('lab_admin','lab_app','lab_observer','lab_repl')
ORDER BY rolname;
SELECT ssl,version,cipher,bits FROM pg_stat_ssl WHERE pid=pg_backend_pid();
SELECT name,default_version,installed_version
FROM pg_available_extensions WHERE name='pgaudit';
SELECT extname,extversion FROM pg_extension WHERE extname='pgaudit';
SELECT name,setting,source,context FROM pg_settings
WHERE name LIKE 'pgaudit.%' ORDER BY name;
COMMIT;
