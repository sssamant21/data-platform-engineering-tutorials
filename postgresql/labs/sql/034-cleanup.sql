\set ON_ERROR_STOP on
\echo 'DISPOSABLE DATABASE ONLY: removing ch034 lab schema'
DROP SCHEMA IF EXISTS ch034 CASCADE;
SELECT count(*) AS remaining_ch034_schemas FROM pg_namespace WHERE nspname='ch034';
