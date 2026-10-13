\set ON_ERROR_STOP on
SELECT current_setting('server_version') AS version,
 current_setting('hba_file') AS hba_file,
 current_setting('ssl') AS ssl,
 current_setting('ssl_min_protocol_version') AS ssl_min_protocol_version,
 current_setting('password_encryption') AS password_encryption;
SELECT line_number,type,database,user_name,address,auth_method,error
FROM pg_hba_file_rules ORDER BY line_number;
SELECT ssl,version,cipher,bits,client_dn
FROM pg_stat_ssl WHERE pid=pg_backend_pid();
SELECT rolname,rolcanlogin,rolvaliduntil FROM pg_roles
WHERE rolcanlogin ORDER BY rolname;
