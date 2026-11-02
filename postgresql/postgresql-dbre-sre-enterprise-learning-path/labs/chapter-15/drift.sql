\set ON_ERROR_STOP on
-- Synthetic training policy only; read-only, no ALTER SYSTEM/SET/restart.
-- Deliberately expect 200 max_connections to illustrate REVIEW on stock images.
WITH policy(name, expected) AS (
  VALUES
    ('max_connections'::text, '200'::text),
    ('wal_level', 'replica'),
    ('password_encryption', 'scram-sha-256')
)
SELECT p.name,
       s.setting AS observed,
       p.expected,
       s.source,
       CASE WHEN s.setting = p.expected THEN 'MATCH' ELSE 'REVIEW' END AS finding
FROM policy AS p
LEFT JOIN pg_settings AS s ON s.name = p.name
ORDER BY p.name;
