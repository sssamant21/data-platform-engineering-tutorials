\set ON_ERROR_STOP on
DO $$
BEGIN
 IF current_database() <> 'ch060_lab' THEN
   RAISE EXCEPTION 'Refusing to run outside dedicated ch060_lab database';
 END IF;
END $$;
CREATE SCHEMA IF NOT EXISTS ch060;
CREATE TABLE IF NOT EXISTS ch060.requests (
 request_id text PRIMARY KEY,
 payload text NOT NULL,
 committed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO ch060.requests(request_id,payload)
VALUES ('baseline-001','sample')
ON CONFLICT (request_id) DO NOTHING;
INSERT INTO ch060.requests(request_id,payload)
VALUES ('baseline-001','sample')
ON CONFLICT (request_id) DO NOTHING;
SELECT request_id,count(*) AS rows_per_request
FROM ch060.requests GROUP BY request_id ORDER BY request_id;
