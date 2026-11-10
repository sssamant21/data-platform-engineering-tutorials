-- Chapter 045: CROSS JOIN and SELF JOIN. Synthetic data only.
-- Execute ONLY in disposable PostgreSQL 18+ database named sql_tutorials.
-- psql -X -v ON_ERROR_STOP=1 -d sql_tutorials -f sql-tutorials/labs/045-cross-join-self-join.sql
BEGIN;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '2s';
DO $guard$
BEGIN
  IF current_setting('server_version_num')::integer < 180000
     OR current_database() <> 'sql_tutorials'
     OR pg_is_in_recovery() THEN
    RAISE EXCEPTION 'Requires isolated writable sql_tutorials database on PostgreSQL 18+';
  END IF;
END
$guard$;

CREATE TEMP TABLE lab045_regions (
  region text PRIMARY KEY
) ON COMMIT DROP;
CREATE TEMP TABLE lab045_modes (
  shipping_mode text PRIMARY KEY
) ON COMMIT DROP;
CREATE TEMP TABLE lab045_employees (
  employee_id integer PRIMARY KEY,
  employee_name text NOT NULL,
  manager_id integer REFERENCES lab045_employees(employee_id)
) ON COMMIT DROP;

INSERT INTO lab045_regions VALUES ('East'), ('West'), ('Central');
INSERT INTO lab045_modes VALUES ('Standard'), ('Express');
INSERT INTO lab045_employees VALUES (1, 'Avery', NULL);
INSERT INTO lab045_employees VALUES (2, 'Blake', 1), (3, 'Casey', 1), (4, 'Drew', 2);

-- Expected six combinations; order deterministic.
SELECT r.region, m.shipping_mode
FROM lab045_regions AS r CROSS JOIN lab045_modes AS m
ORDER BY r.region, m.shipping_mode;

-- Expected four employees, including director Avery with NULL manager.
SELECT e.employee_id, e.employee_name, m.employee_name AS manager_name
FROM lab045_employees AS e
LEFT JOIN lab045_employees AS m ON e.manager_id = m.employee_id
ORDER BY e.employee_id;

-- Expected Blake and Casey.
SELECT e.employee_name
FROM lab045_employees AS e
JOIN lab045_employees AS m ON e.manager_id = m.employee_id
WHERE m.employee_name = 'Avery'
ORDER BY e.employee_name;

DO $verify$
DECLARE
  combinations bigint;
  employees bigint;
  manager_matches bigint;
  top_level bigint;
  direct_reports bigint;
  left_rows bigint;
  missing_manager bigint;
BEGIN
  SELECT count(*) INTO combinations
  FROM lab045_regions r CROSS JOIN lab045_modes m;
  SELECT count(*) INTO employees FROM lab045_employees;
  SELECT count(*) INTO manager_matches
  FROM lab045_employees e JOIN lab045_employees m
    ON e.manager_id = m.employee_id;
  SELECT count(*) INTO top_level FROM lab045_employees
  WHERE manager_id IS NULL;
  SELECT count(*) INTO direct_reports
  FROM lab045_employees e JOIN lab045_employees m
    ON e.manager_id = m.employee_id
  WHERE m.employee_name = 'Avery';
  SELECT count(*) INTO left_rows
  FROM lab045_employees e LEFT JOIN lab045_employees m
    ON e.manager_id = m.employee_id;
  SELECT count(*) INTO missing_manager
  FROM lab045_employees e LEFT JOIN lab045_employees m
    ON e.manager_id = m.employee_id
  WHERE e.manager_id IS NOT NULL AND m.employee_id IS NULL;
  IF (combinations, employees, manager_matches, top_level, direct_reports, left_rows, missing_manager)
     IS DISTINCT FROM
     (6::bigint, 4::bigint, 3::bigint, 1::bigint, 2::bigint, 4::bigint, 0::bigint) THEN
    RAISE EXCEPTION 'Chapter 045 cardinality assertions failed';
  END IF;
  RAISE NOTICE 'PASS: combinations=6, employees=4, manager_matches=3, top_level=1, direct_reports_to_avery=2';
END
$verify$;
ROLLBACK;
-- Expected final command tag: ROLLBACK. No persistent objects.
