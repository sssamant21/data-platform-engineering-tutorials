-- PostgreSQL 18 locale/encoding/checksum metadata. No catalog writes.
\set ON_ERROR_STOP on
\pset pager off
BEGIN READ ONLY;
SET LOCAL statement_timeout = '5s';
SET LOCAL lock_timeout = '1s';
SELECT current_database(), current_user,
       current_setting('server_version') AS server_version,
       current_setting('data_checksums') AS data_checksums,
       current_setting('server_encoding') AS server_encoding,
       current_setting('client_encoding') AS client_encoding;
SELECT datname, pg_catalog.pg_encoding_to_char(encoding) AS encoding,
       datlocprovider, datcollate, datctype, datlocale,
       datcollversion AS recorded_collation_version,
       pg_catalog.pg_database_collation_actual_version(oid) AS actual_collation_version
FROM pg_catalog.pg_database
WHERE datname IN (current_database(),'template0','template1',
                  'chapter007_libc','chapter007_builtin')
ORDER BY datname;
COMMIT;
