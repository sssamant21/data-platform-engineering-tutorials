-- Chapter 083 read-only PostgreSQL configuration drift inspection.
SELECT current_setting('server_version') AS version,clock_timestamp() AS inspected_at;
SELECT name,setting,unit,source,sourcefile,sourceline,context,pending_restart
FROM pg_settings WHERE name IN
 ('shared_buffers','max_connections','work_mem','statement_timeout',
  'log_min_duration_statement','shared_preload_libraries','wal_level',
  'max_wal_senders','ssl','password_encryption')
ORDER BY name;
SELECT sourcefile,sourceline,name,setting,applied,error
FROM pg_file_settings ORDER BY sourcefile,sourceline;
SELECT d.datname,r.rolname,s.setconfig
FROM pg_db_role_setting s
LEFT JOIN pg_database d ON d.oid=s.setdatabase
LEFT JOIN pg_roles r ON r.oid=s.setrole
ORDER BY d.datname NULLS FIRST,r.rolname NULLS FIRST;
