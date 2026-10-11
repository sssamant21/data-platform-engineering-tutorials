-- PostgreSQL 18. lab_admin in the disposable lab.
-- No corrections: privileged metadata inspection only.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '5s';
SET LOCAL lock_timeout = '1s';

SELECT clock_timestamp() AS captured_at, current_database(), current_user,
       inet_server_addr(), inet_server_port(), pg_postmaster_start_time(),
       pg_is_in_recovery(), version();

SELECT name,setting,unit,source,sourcefile,sourceline,context,pending_restart
FROM pg_settings
WHERE pending_restart
ORDER BY name;

SELECT sourcefile,sourceline,seqno,name,setting,applied,error
FROM pg_file_settings
WHERE error IS NOT NULL OR name IN
 ('shared_buffers','work_mem','log_min_duration_statement',
  'fsync','full_page_writes','synchronous_commit','wal_level')
ORDER BY seqno;

SELECT COALESCE(d.datname,'<all databases>') AS database_scope,
       COALESCE(r.rolname,'<all roles>') AS role_scope, x.setting
FROM pg_db_role_setting AS s
LEFT JOIN pg_database AS d ON d.oid=s.setdatabase
LEFT JOIN pg_roles AS r ON r.oid=s.setrole
CROSS JOIN LATERAL unnest(s.setconfig) AS x(setting)
ORDER BY database_scope,role_scope,x.setting;

SELECT rule_number,file_name,line_number,error
FROM pg_hba_file_rules
WHERE error IS NOT NULL
ORDER BY rule_number;

COMMIT;
