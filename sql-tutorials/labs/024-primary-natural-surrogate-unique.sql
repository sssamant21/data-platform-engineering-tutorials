-- Chapter 024: Primary keys, natural keys, surrogate keys and UNIQUE.
-- Isolated PostgreSQL 18 primary only; never use production credentials.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/024-primary-natural-surrogate-unique.sql
-- Temporary objects, synthetic data, rollback-only. Runtime validation pending.
BEGIN;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';
DO $guard$
BEGIN
  IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999
     OR current_database() <> 'sql_tutorials'
     OR pg_is_in_recovery() THEN
    RAISE EXCEPTION 'Requires independently verified isolated PostgreSQL 18 primary sql_tutorials';
  END IF;
END
$guard$;

CREATE TEMP TABLE ch024_orders (
  order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_code TEXT NOT NULL,
  external_ref TEXT NOT NULL,
  amount_usd NUMERIC(12,2) NOT NULL,
  CONSTRAINT ch024_tenant_ref_uniq UNIQUE (tenant_code, external_ref)
) ON COMMIT DROP;

CREATE TEMP TABLE ch024_contacts (
  contact_id INTEGER PRIMARY KEY,
  email TEXT UNIQUE
) ON COMMIT DROP;

INSERT INTO ch024_orders (tenant_code, external_ref, amount_usd)
VALUES ('T1','A-100',19.95),('T2','A-100',10.50),('T1','A-101',25.00);
INSERT INTO ch024_contacts (contact_id,email)
VALUES (1,NULL),(2,NULL),(3,'synthetic@example.test');

SELECT count(*) AS order_count,
       count(DISTINCT tenant_code) AS tenant_count,
       count(DISTINCT (tenant_code,external_ref)) AS business_key_count,
       sum(amount_usd) AS amount_total
FROM ch024_orders;
-- Expected: 3 | 2 | 3 | 55.45

SELECT count(*) FILTER (WHERE email IS NULL) AS null_emails
FROM ch024_contacts;
-- Expected: 2 (ordinary PostgreSQL UNIQUE treats NULLs as distinct)

-- Catch only the expected unique_violation; all other errors fail the lab.
DO $duplicate$
DECLARE rejected boolean := false;
BEGIN
  BEGIN
    INSERT INTO ch024_orders (tenant_code,external_ref,amount_usd)
    VALUES ('T1','A-100',99.00);
  EXCEPTION WHEN unique_violation THEN
    rejected := true;
  END;
  IF NOT rejected THEN
    RAISE EXCEPTION 'Expected business-key duplicate rejection did not occur';
  END IF;
  RAISE NOTICE 'Expected duplicate business key rejected (SQLSTATE 23505)';
END
$duplicate$;

DO $assert$
DECLARE n bigint; tenants bigint; keys bigint; total numeric; nulls bigint;
BEGIN
  SELECT count(*), count(DISTINCT tenant_code),
         count(DISTINCT (tenant_code,external_ref)), sum(amount_usd)
  INTO n,tenants,keys,total FROM ch024_orders;
  SELECT count(*) FILTER (WHERE email IS NULL) INTO nulls FROM ch024_contacts;
  IF n <> 3 OR tenants <> 2 OR keys <> 3
     OR total IS DISTINCT FROM 55.45::numeric
     OR nulls <> 2
     OR EXISTS (SELECT 1 FROM ch024_orders WHERE order_id IS NULL)
  THEN
    RAISE EXCEPTION 'Chapter 024 assertions failed';
  END IF;
  RAISE NOTICE 'Chapter 024 synthetic assertions passed';
END
$assert$;
ROLLBACK;
-- Both temporary tables are discarded. No persistent schema changes.
