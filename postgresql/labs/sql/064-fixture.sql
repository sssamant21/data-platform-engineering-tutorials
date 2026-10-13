\set ON_ERROR_STOP on
DO $$
BEGIN
 IF current_database() <> 'ch064_lab' THEN
  RAISE EXCEPTION 'Refusing to create PITR fixture outside ch064_lab';
 END IF;
END $$;
CREATE SCHEMA IF NOT EXISTS ch064;
CREATE TABLE IF NOT EXISTS ch064.events (
 event_key text PRIMARY KEY,
 phase text NOT NULL,
 inserted_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
SELECT event_key,phase,inserted_at FROM ch064.events ORDER BY inserted_at;
