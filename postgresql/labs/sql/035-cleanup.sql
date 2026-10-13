\set ON_ERROR_STOP on
\echo 'DISPOSABLE DATABASE ONLY: dropping ch035'
DROP SCHEMA IF EXISTS ch035 CASCADE;
SELECT count(*) AS remaining_ch035_schemas FROM pg_namespace WHERE nspname='ch035';
