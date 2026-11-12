-- 104: synthetic masking and audit-metadata model; NOT a live access-control or audit test.
-- Execute only on disposable PostgreSQL 18 database sql_tutorials.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
  IF current_database() <> 'sql_tutorials' THEN
    RAISE EXCEPTION 'Expected disposable sql_tutorials database; got %', current_database();
  END IF;
  IF current_setting('server_version_num')::integer / 10000 <> 18 THEN
    RAISE EXCEPTION 'PostgreSQL 18 required; got %', current_setting('server_version');
  END IF;
END
$guard$;

WITH claims(claim_id,tenant_id,member_email,amount,status) AS (
 VALUES (201,10,'alex@example.test',40.00::numeric(10,2),'PAID'),
        (202,10,'blair@example.test',60.00::numeric(10,2),'OPEN'),
        (203,20,'casey@example.test',25.00::numeric(10,2),'PAID'),
        (204,20,'drew@example.test',75.00::numeric(10,2),'OPEN')
)
SELECT tenant_id,status,count(*) AS claim_count,sum(amount) AS total_amount
FROM claims GROUP BY tenant_id,status ORDER BY tenant_id,status;

WITH contacts(email) AS (
 VALUES ('alex@example.test'),('blair@example.test'),
        ('casey@example.test'),('drew@example.test')
)
SELECT left(split_part(email,'@',1),1) || '***@' ||
       split_part(email,'@',2) AS masked_email
FROM contacts ORDER BY email;

-- Audit metadata is invented, not from pgAudit or real database logs.
WITH events(event_id,event_time,actor,action,object_name,outcome,request_id) AS (
 VALUES (1,'2026-11-01 10:00:00+00'::timestamptz,'reporter','SELECT','claims_report','ALLOWED','req-001'),
        (2,'2026-11-01 10:01:00+00'::timestamptz,'support','SELECT','support_claims','ALLOWED','req-002'),
        (3,'2026-11-01 10:02:00+00'::timestamptz,'unknown','SELECT','claims_raw','DENIED','req-003')
)
SELECT count(*) AS event_count,
       count(*) FILTER (WHERE event_time IS NULL OR nullif(actor,'') IS NULL
           OR nullif(action,'') IS NULL OR nullif(object_name,'') IS NULL
           OR nullif(outcome,'') IS NULL OR nullif(request_id,'') IS NULL) AS incomplete_events
FROM events;

DO $assert$
DECLARE missing_count integer; extra_count integer; mask_missing integer;
        mask_extra integer; claim_total numeric(10,2); claim_count integer;
        audit_count integer; incomplete_count integer;
BEGIN
  WITH claims(claim_id,tenant_id,amount,status) AS (
    VALUES (201,10,40.00::numeric(10,2),'PAID'),
           (202,10,60.00::numeric(10,2),'OPEN'),
           (203,20,25.00::numeric(10,2),'PAID'),
           (204,20,75.00::numeric(10,2),'OPEN')
  ), actual AS (
    SELECT tenant_id,status,count(*)::bigint AS n,sum(amount)::numeric(10,2) AS total
    FROM claims GROUP BY tenant_id,status
  ), expected(tenant_id,status,n,total) AS (
    VALUES (10,'OPEN',1::bigint,60.00::numeric(10,2)),
           (10,'PAID',1::bigint,40.00::numeric(10,2)),
           (20,'OPEN',1::bigint,75.00::numeric(10,2)),
           (20,'PAID',1::bigint,25.00::numeric(10,2))
  ), missing AS (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual),
     extra AS (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
  SELECT (SELECT count(*) FROM missing),(SELECT count(*) FROM extra),
         (SELECT count(*) FROM claims),(SELECT sum(amount) FROM claims)
  INTO missing_count,extra_count,claim_count,claim_total;

  WITH contacts(email) AS (
    VALUES ('alex@example.test'),('blair@example.test'),
           ('casey@example.test'),('drew@example.test')
  ), actual(masked_email) AS (
    SELECT left(split_part(email,'@',1),1) || '***@' ||
           split_part(email,'@',2) FROM contacts
  ), expected(masked_email) AS (
    VALUES ('a***@example.test'),('b***@example.test'),
           ('c***@example.test'),('d***@example.test')
  ), missing AS (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual),
     extra AS (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected)
  SELECT (SELECT count(*) FROM missing),(SELECT count(*) FROM extra)
  INTO mask_missing,mask_extra;

  WITH events(event_id,event_time,actor,action,object_name,outcome,request_id) AS (
    VALUES (1,'2026-11-01 10:00:00+00'::timestamptz,'reporter','SELECT','claims_report','ALLOWED','req-001'),
           (2,'2026-11-01 10:01:00+00'::timestamptz,'support','SELECT','support_claims','ALLOWED','req-002'),
           (3,'2026-11-01 10:02:00+00'::timestamptz,'unknown','SELECT','claims_raw','DENIED','req-003')
  )
  SELECT count(*),count(*) FILTER (WHERE event_time IS NULL OR nullif(actor,'') IS NULL
    OR nullif(action,'') IS NULL OR nullif(object_name,'') IS NULL
    OR nullif(outcome,'') IS NULL OR nullif(request_id,'') IS NULL)
  INTO audit_count,incomplete_count FROM events;

  IF missing_count <> 0 OR extra_count <> 0 OR mask_missing <> 0 OR mask_extra <> 0
     OR claim_count <> 4 OR claim_total <> 200.00
     OR audit_count <> 3 OR incomplete_count <> 0 THEN
    RAISE EXCEPTION '104 assertions failed: report %/%, masks %/%, claims %/%, audit %/%',
      missing_count,extra_count,mask_missing,mask_extra,claim_count,claim_total,
      audit_count,incomplete_count;
  END IF;
  RAISE NOTICE '104 synthetic assertions passed: 4 claims, total 200, 4 masks, 3 complete audit events';
END
$assert$;
ROLLBACK;
