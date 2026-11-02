\set ON_ERROR_STOP on
-- CH15 ONLY: run via psql against the disposable pg-fleet-ch15 container.
-- The CREATE DATABASE statements require autocommit (psql -f, no BEGIN).
SELECT 'CREATE ROLE fleet_lab_app_owner NOLOGIN'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fleet_lab_app_owner')
\gexec
SELECT 'CREATE ROLE fleet_lab_reporting_owner NOLOGIN'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fleet_lab_reporting_owner')
\gexec

SELECT 'CREATE DATABASE fleet_lab_app OWNER fleet_lab_app_owner'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'fleet_lab_app')
\gexec
SELECT 'CREATE DATABASE fleet_lab_reporting OWNER fleet_lab_reporting_owner'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'fleet_lab_reporting')
\gexec

\connect fleet_lab_app
CREATE SCHEMA IF NOT EXISTS fleet_demo AUTHORIZATION fleet_lab_app_owner;
CREATE TABLE IF NOT EXISTS fleet_demo.sample_events (
  event_id integer PRIMARY KEY,
  event_type text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO fleet_demo.sample_events(event_id, event_type)
VALUES (1, 'training-created'), (2, 'training-reviewed')
ON CONFLICT (event_id) DO NOTHING;
SELECT count(*) AS app_rows FROM fleet_demo.sample_events;

\connect fleet_lab_reporting
CREATE SCHEMA IF NOT EXISTS fleet_demo AUTHORIZATION fleet_lab_reporting_owner;
CREATE TABLE IF NOT EXISTS fleet_demo.sample_reports (
  report_id integer PRIMARY KEY,
  report_name text NOT NULL
);
INSERT INTO fleet_demo.sample_reports(report_id, report_name)
VALUES (1, 'synthetic-fleet-summary'), (2, 'synthetic-drift-review')
ON CONFLICT (report_id) DO NOTHING;
SELECT count(*) AS report_rows FROM fleet_demo.sample_reports;
