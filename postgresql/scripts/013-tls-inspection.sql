-- PG18: read-only settings and this authenticated session's TLS evidence.
-- pg_stat_ssl does not expose the server leaf fingerprint.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout='5s';
SET LOCAL lock_timeout='1s';
SELECT clock_timestamp() AS observed_at,current_database(),session_user,current_user,
       inet_server_addr(),inet_server_port(),pg_is_in_recovery();
SELECT name,setting,source,context,pending_restart
FROM pg_settings
WHERE name IN ('ssl','ssl_cert_file','ssl_key_file','ssl_ca_file',
               'ssl_min_protocol_version','ssl_max_protocol_version',
               'ssl_passphrase_command_supports_reload')
ORDER BY name;
SELECT ssl,version,cipher,bits,client_dn,issuer_dn
FROM pg_stat_ssl WHERE pid=pg_backend_pid();
COMMIT;
