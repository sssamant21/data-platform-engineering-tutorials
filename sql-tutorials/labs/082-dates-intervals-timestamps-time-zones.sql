-- 082: PostgreSQL 18 synthetic temporal lab. Run ONLY on disposable sql_tutorials.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
SET LOCAL TimeZone = 'UTC';
SELECT current_database(), current_user, current_setting('server_version'),
       current_setting('TimeZone'), inet_server_addr(), inet_server_port();
SELECT 1 / CASE WHEN current_database() = 'sql_tutorials' THEN 1 ELSE 0 END AS database_guard;
SELECT 1 / CASE WHEN current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
                THEN 1 ELSE 0 END AS version_guard;

WITH events(id, occurred_at) AS (
 VALUES (1, TIMESTAMPTZ '2026-03-08 06:30:00+00'),
        (2, TIMESTAMPTZ '2026-03-08 07:30:00+00'),
        (3, TIMESTAMPTZ '2026-03-09 00:00:00+00')
)
SELECT id, occurred_at,
       occurred_at AT TIME ZONE 'America/New_York' AS ny_wall_time,
       (occurred_at AT TIME ZONE 'America/New_York')::date AS ny_day
FROM events ORDER BY id;

WITH events(id, occurred_at) AS (
 VALUES (1, TIMESTAMPTZ '2026-03-08 06:30:00+00'),
        (2, TIMESTAMPTZ '2026-03-08 07:30:00+00'),
        (3, TIMESTAMPTZ '2026-03-09 00:00:00+00')
), actual AS (
 SELECT id, occurred_at AT TIME ZONE 'America/New_York' AS wall_time,
        (occurred_at >= TIMESTAMPTZ '2026-03-08 00:00:00+00'
         AND occurred_at < TIMESTAMPTZ '2026-03-09 00:00:00+00') AS in_utc_day
 FROM events
), expected(id,wall_time,in_utc_day) AS (
 VALUES (1, TIMESTAMP '2026-03-08 01:30:00', TRUE),
        (2, TIMESTAMP '2026-03-08 03:30:00', TRUE),
        (3, TIMESTAMP '2026-03-08 20:00:00', FALSE)
), differences AS (
 (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
 UNION ALL
 (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
), checks AS (
 SELECT (SELECT COUNT(*)=3 FROM actual) AS three_events,
        (SELECT COUNT(*)=2 FROM actual WHERE in_utc_day) AS two_in_day,
        (SELECT COUNT(*)=0 FROM differences) AS exact_expected,
        ((TIMESTAMPTZ '2026-03-08 07:30:00+00'
         - TIMESTAMPTZ '2026-03-08 06:30:00+00') = INTERVAL '1 hour') AS elapsed_one_hour
)
SELECT *, 1 / CASE WHEN three_events AND two_in_day AND exact_expected AND elapsed_one_hour
                   THEN 1 ELSE 0 END AS fail_closed_acceptance FROM checks;
ROLLBACK;
