-- Chapter 077: read-only connection security inspection.
SELECT current_setting('server_version') AS version,
 current_setting('ssl') AS ssl_enabled,
 current_setting('password_encryption') AS password_encryption,
 current_setting('hba_file') AS hba_file,
 clock_timestamp() AS inspected_at;
SELECT line_number,type,database,user_name,address,auth_method,error
FROM pg_hba_file_rules ORDER BY line_number;
SELECT a.pid,a.usename,a.datname,a.client_addr,s.ssl,s.version,s.cipher
FROM pg_stat_activity a JOIN pg_stat_ssl s USING(pid)
WHERE a.datname=current_database()
ORDER BY a.pid;
SELECT rolname,rolcanlogin,rolvaliduntil
FROM pg_roles WHERE rolname LIKE 'ch077_%' ORDER BY rolname;
