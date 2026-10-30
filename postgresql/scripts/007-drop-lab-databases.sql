-- Chapter 007: destructive cleanup restricted to the exact disposable PG18 lab.
-- This is NOT atomic: if the second DROP fails, examine the partial outcome.
-- Never use this script with a production/shared cluster.
\set ON_ERROR_STOP on
\if :{?expected_system_id}
\else
  \echo 'REFUSED: -v expected_system_id=OBSERVED_LAB_SYSTEM_ID required'
  \quit 3
\endif
\if :{?confirm_cleanup}
\else
  \echo 'REFUSED: -v confirm_cleanup=007-DROP-DATABASES required'
  \quit 3
\endif

SELECT CASE WHEN current_database() = 'postgres'
  AND current_user = 'lab_admin'
  AND inet_server_port() = 55432
  AND inet_server_addr() = inet '127.0.0.1'
  AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
  AND current_setting('data_directory') ~ '^/tmp/postgresql-dbre-lab\.[[:alnum:]]+/primary$'
  AND NOT pg_is_in_recovery()
  AND EXISTS (SELECT 1 FROM pg_control_system() c
              WHERE c.system_identifier::text = :'expected_system_id')
  AND :'confirm_cleanup' = '007-DROP-DATABASES'
  AND (SELECT count(*) FROM pg_database
       WHERE datname IN ('chapter007_libc','chapter007_builtin')) = 2
  AND (SELECT count(*) FROM pg_database
       WHERE (datname='chapter007_libc' AND datlocprovider='c')
          OR (datname='chapter007_builtin' AND datlocprovider='b')) = 2
  AND NOT EXISTS (
      SELECT 1 FROM pg_database d
      WHERE d.datname IN ('chapter007_libc','chapter007_builtin')
        AND pg_get_userbyid(d.datdba) <> 'lab_admin')
  AND NOT EXISTS (
      SELECT 1 FROM pg_stat_activity a
      WHERE a.datname IN ('chapter007_libc','chapter007_builtin'))
  THEN 'true' ELSE 'false' END AS cleanup_permitted
\gset
\if :cleanup_permitted
  \echo 'Target and both lab databases verified; dropping exact chapter007 names.'
\else
  \echo 'REFUSED: cluster identity, role, provider, ownership, sessions or confirmation did not match'
  \quit 3
\endif

-- Two separate standalone commands; CREATE/DROP DATABASE cannot run in a transaction.
DROP DATABASE chapter007_libc;
DROP DATABASE chapter007_builtin;
SELECT count(*) AS remaining_chapter007_dbs
FROM pg_database WHERE datname IN ('chapter007_libc','chapter007_builtin');
