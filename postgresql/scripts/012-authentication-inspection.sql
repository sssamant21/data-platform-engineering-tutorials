-- PostgreSQL 18; lab_admin or a role granted access to the HBA inspection view.
-- Current file contents are not proof of the last successfully loaded HBA.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';

SELECT clock_timestamp() AS observed_at,current_database(),session_user,current_user,
       inet_server_addr(),inet_server_port(),inet_client_addr(),pg_is_in_recovery();

SELECT name,setting,context,pending_restart
FROM pg_settings
WHERE name IN ('hba_file','ident_file','listen_addresses','port','ssl','password_encryption')
ORDER BY name;

SELECT rule_number,file_name,line_number,type,database,user_name,address,netmask,
       auth_method,options,error
FROM pg_hba_file_rules
ORDER BY rule_number NULLS LAST,file_name,line_number;

SELECT rolname,rolcanlogin,rolvaliduntil,rolconnlimit
FROM pg_roles
WHERE rolname IN ('lab_admin','lab_app','lab_repl','lab_observer')
ORDER BY rolname;

SELECT ssl,version,cipher,bits
FROM pg_stat_ssl
WHERE pid=pg_backend_pid();

COMMIT;
