\set ON_ERROR_STOP on
\echo 'WARNING: drops ch033 schema and all its lab objects'
DROP SCHEMA IF EXISTS ch033 CASCADE;
SELECT count(*) AS remaining_ch033_schema FROM pg_namespace WHERE nspname='ch033';
