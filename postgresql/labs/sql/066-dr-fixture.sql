\set ON_ERROR_STOP on
DO $$
BEGIN
 IF current_database() <> 'ch066_lab' THEN
  RAISE EXCEPTION 'Refusing DR fixture outside ch066_lab';
 END IF;
END $$;
CREATE SCHEMA IF NOT EXISTS ch066;
CREATE TABLE IF NOT EXISTS ch066.reference_data (
 id integer PRIMARY KEY,
 payload text NOT NULL
);
CREATE TABLE IF NOT EXISTS ch066.events (
 event_key text PRIMARY KEY,
 description text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO ch066.reference_data(id,payload) VALUES (1,'recover-me')
ON CONFLICT (id) DO NOTHING;
SELECT * FROM ch066.reference_data ORDER BY id;
