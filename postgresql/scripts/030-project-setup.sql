\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout='10s';
SET LOCAL lock_timeout='1s';
CREATE SCHEMA c030_incident AUTHORIZATION lab_admin;
CREATE TABLE c030_incident.requests(id integer PRIMARY KEY,a integer NOT NULL,b integer NOT NULL);
INSERT INTO c030_incident.requests
SELECT i,(i-1)%100,(i-1)%100 FROM generate_series(1,20000) AS s(i);
GRANT USAGE ON SCHEMA c030_incident TO lab_app;
GRANT SELECT ON c030_incident.requests TO lab_app;
COMMIT;
ANALYZE c030_incident.requests;
