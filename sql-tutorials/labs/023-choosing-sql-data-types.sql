-- Chapter 023: choosing SQL data types (PostgreSQL 18).
-- Run only after independently confirming isolated lab host and credentials.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/023-choosing-sql-data-types.sql
-- Synthetic, read-only, no persistent objects. Runtime acceptance pending.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
DO $guard$
BEGIN
  IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
     OR current_database() <> 'sql_tutorials'
     OR pg_is_in_recovery() THEN
    RAISE EXCEPTION 'Requires independently verified disposable PostgreSQL 18 primary sql_tutorials';
  END IF;
END
$guard$;

-- Six synthetic order events, exact amounts and nullable Boolean states.
WITH events(order_id, postal_code, amount_usd, paid, event_at) AS (
  VALUES
  (9001::bigint, '00123'::varchar(12), 19.95::numeric(12,2), TRUE, TIMESTAMPTZ '2026-11-01 14:30:00+00'),
  (9002, '00456', 10.50, FALSE, TIMESTAMPTZ '2026-11-01 15:00:00+00'),
  (9003, '00789', 25.00, NULL::boolean, TIMESTAMPTZ '2026-11-01 15:30:00+00'),
  (9004, '00123', 12.00, TRUE, TIMESTAMPTZ '2026-11-02 08:00:00+00'),
  (9005, '00456', 20.00, FALSE, TIMESTAMPTZ '2026-11-02 09:00:00+00'),
  (9006, '00789', 4.00, NULL::boolean, TIMESTAMPTZ '2026-11-02 10:00:00+00')
)
SELECT count(*) AS event_count,
       sum(amount_usd) AS total_usd,
       count(paid) AS known_payment_states,
       count(*) FILTER (WHERE paid IS NULL) AS unknown_payment_states,
       min(postal_code) AS first_postal_code
FROM events;
-- Expected: 6 | 91.45 | 4 | 2 | 00123

SELECT 0.1::numeric + 0.2::numeric = 0.3::numeric AS exact_decimal,
       ('00123'::varchar(12) = '00123') AS leading_zero_preserved,
       (TIMESTAMPTZ '2026-11-01 14:30:00+00' AT TIME ZONE 'UTC')
          = TIMESTAMP '2026-11-01 14:30:00' AS utc_instant_matches;
-- Expected: true | true | true

-- Timezone conversion changes wall-clock representation, not event instant.
SELECT TIMESTAMPTZ '2026-11-01 14:30:00+00' AT TIME ZONE 'UTC' AS utc_wall_time,
       TIMESTAMPTZ '2026-11-01 14:30:00+00' AT TIME ZONE 'America/New_York' AS ny_wall_time;
-- Expected: 2026-11-01 14:30:00 | 2026-11-01 09:30:00 (EST)

DO $assert$
DECLARE n bigint; total numeric; known bigint; missing bigint;
BEGIN
  WITH events(amount_usd,paid) AS (
    VALUES (19.95::numeric(12,2),TRUE),(10.50,FALSE),
           (25.00,NULL::boolean),(12.00,TRUE),
           (20.00,FALSE),(4.00,NULL::boolean)
  )
  SELECT count(*),sum(amount_usd),count(paid),
         count(*) FILTER (WHERE paid IS NULL)
  INTO n,total,known,missing FROM events;
  IF n <> 6 OR total IS DISTINCT FROM 91.45::numeric
     OR known <> 4 OR missing <> 2
     OR (0.1::numeric + 0.2::numeric = 0.3::numeric) IS NOT TRUE
     OR (TIMESTAMPTZ '2026-11-01 14:30:00+00' AT TIME ZONE 'America/New_York')
          IS DISTINCT FROM TIMESTAMP '2026-11-01 09:30:00'
  THEN
    RAISE EXCEPTION 'Chapter 023 data-type assertions failed';
  END IF;
  RAISE NOTICE 'Chapter 023 synthetic assertions passed';
END
$assert$;
ROLLBACK;
-- No schema/table creation; all work read-only and transaction ended.
