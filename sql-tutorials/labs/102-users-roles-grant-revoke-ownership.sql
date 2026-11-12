-- Chapter 102: users, roles, GRANT, REVOKE, and ownership
-- PostgreSQL 18; disposable sql_tutorials database; synthetic policy model.
-- No real role creation, privilege changes, object ownership changes, or persistent writes.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '2s';
SET LOCAL idle_in_transaction_session_timeout = '30s';

DO $guard$
BEGIN
 IF current_database() <> 'sql_tutorials' THEN
  RAISE EXCEPTION 'Expected disposable sql_tutorials database, got %', current_database();
 END IF;
 IF current_setting('server_version_num')::integer / 10000 <> 18 THEN
  RAISE EXCEPTION 'PostgreSQL 18 required, got %', current_setting('server_version');
 END IF;
END
$guard$;

-- Live session metadata only; does not certify privileges of a real application.
SELECT current_database() AS database_name, current_user AS effective_role,
       session_user AS login_role,
       has_database_privilege(current_user, current_database(), 'CONNECT') AS can_connect;

-- Synthetic model of roles and grants. Never confuse with live ACL evidence.
WITH principals(role_name, can_login) AS (
 VALUES ('retail_reader',false), ('retail_app',true), ('ingest_writer',true)
), membership(member_role,group_role) AS (
 VALUES ('retail_app','retail_reader')
), grants(role_name,object_name,privilege_name) AS (
 VALUES ('retail_reader','reporting.daily_sales','SELECT'),
        ('ingest_writer','staging.orders','INSERT')
), candidates(role_name,object_name,privilege_name,approved) AS (
 VALUES ('retail_reader','reporting.daily_sales','UPDATE',false)
)
SELECT (SELECT count(*) FROM principals) AS principals,
       (SELECT count(*) FROM membership) AS memberships,
       (SELECT count(*) FROM grants) AS approved_grants,
       (SELECT count(*) FROM candidates WHERE NOT approved) AS rejected_candidates;

-- An explicit two-way multiset assertion for the approved policy.
DO $assert$
DECLARE principals_count integer; membership_count integer; approved_count integer;
        rejected_count integer; extra_count integer; missing_count integer;
BEGIN
 WITH principals(role_name,can_login) AS (
  VALUES ('retail_reader',false),('retail_app',true),('ingest_writer',true)
 ), membership(member_role,group_role) AS (
  VALUES ('retail_app','retail_reader')
 ), actual(role_name,object_name,privilege_name) AS (
  VALUES ('retail_reader','reporting.daily_sales','SELECT'),
         ('ingest_writer','staging.orders','INSERT')
 ), expected(role_name,object_name,privilege_name) AS (
  VALUES ('retail_reader','reporting.daily_sales','SELECT'),
         ('ingest_writer','staging.orders','INSERT')
 ), candidates(role_name,object_name,privilege_name,approved) AS (
  VALUES ('retail_reader','reporting.daily_sales','UPDATE',false)
 ), extra AS (
  SELECT * FROM actual EXCEPT ALL SELECT * FROM expected
 ), missing AS (
  SELECT * FROM expected EXCEPT ALL SELECT * FROM actual
 )
 SELECT (SELECT count(*) FROM principals), (SELECT count(*) FROM membership),
        (SELECT count(*) FROM actual),
        (SELECT count(*) FROM candidates WHERE NOT approved),
        (SELECT count(*) FROM extra), (SELECT count(*) FROM missing)
 INTO principals_count,membership_count,approved_count,rejected_count,extra_count,missing_count;
 IF principals_count <> 3 OR membership_count <> 1 OR approved_count <> 2
    OR rejected_count <> 1 OR extra_count <> 0 OR missing_count <> 0 THEN
  RAISE EXCEPTION '102 policy model mismatch: principals %, membership %, grants %, rejected %, extra %, missing %',
   principals_count,membership_count,approved_count,rejected_count,extra_count,missing_count;
 END IF;
 RAISE NOTICE '102 assertions passed: 3 principals, 1 membership, 2 grants, 1 rejected, 0 extra/missing';
END
$assert$;
ROLLBACK;
