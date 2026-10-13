\set ON_ERROR_STOP on
\echo 'DISPOSABLE DATABASE ONLY: remove ch036 schema'
DROP SCHEMA IF EXISTS ch036 CASCADE;
SELECT count(*) AS remaining_ch036_schemas FROM pg_namespace WHERE nspname='ch036';
