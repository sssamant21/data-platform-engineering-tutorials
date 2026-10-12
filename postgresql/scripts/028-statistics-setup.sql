\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '1s';
SET LOCAL statement_timeout = '10s';
CREATE SCHEMA c028_stats AUTHORIZATION lab_admin;
CREATE TABLE c028_stats.correlated (
    id integer PRIMARY KEY, a integer NOT NULL, b integer NOT NULL
);
INSERT INTO c028_stats.correlated
SELECT i, (i-1)%100, (i-1)%100 FROM generate_series(1,20000) AS s(i);
GRANT USAGE ON SCHEMA c028_stats TO lab_app;
GRANT SELECT ON c028_stats.correlated TO lab_app;
COMMIT;
ANALYZE c028_stats.correlated;
