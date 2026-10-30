\set ON_ERROR_STOP on
-- Mutations allowed only on the independently verified Chapter 004 disposable PG18 primary.
\if :{?expected_system_id}
\else
 \echo 'REFUSED: expected_system_id required'
 \quit 3
\endif
\if :{?confirm_stage}
\else
 \echo 'REFUSED: confirm_stage required'
 \quit 3
\endif
SELECT CASE WHEN current_database()='ch053_lab'
 AND current_user='lab_admin'
 AND inet_server_addr()=inet '127.0.0.1' AND inet_server_port()=55432
 AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
 AND current_setting('data_directory') ~ '^/tmp/postgresql-dbre-lab\.[A-Za-z0-9]+/primary$'
 AND NOT pg_is_in_recovery()
 AND EXISTS(SELECT 1 FROM pg_control_system() c
            WHERE c.system_identifier::text=:'expected_system_id')
 AND :'confirm_stage'='053-PROVISION'
 AND to_regnamespace('ch053') IS NULL
 THEN 'true' ELSE 'false' END AS stage_permitted
\gset
\if :stage_permitted
 \echo 'Verified disposable Chapter 004 lab identity and initial state.'
\else
 \echo 'REFUSED: wrong database, cluster identity, role, stage or existing lab fixture'
 \quit 3
\endif
BEGIN;
SET LOCAL statement_timeout='30s';
SET LOCAL lock_timeout='1s';
DO $$
BEGIN
 IF current_database() <> 'ch053_lab' THEN RAISE EXCEPTION 'Use isolated ch053_lab database only'; END IF;
 IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname IN ('ch053_owner','ch053_tenant_a','ch053_tenant_b')) THEN
   RAISE EXCEPTION 'Lab role collision; refusing to modify existing roles';
 END IF;
END $$;
CREATE ROLE ch053_owner NOLOGIN;
CREATE ROLE ch053_tenant_a LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
CREATE ROLE ch053_tenant_b LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
CREATE SCHEMA ch053 AUTHORIZATION ch053_owner;
REVOKE ALL ON SCHEMA ch053 FROM PUBLIC;
GRANT USAGE ON SCHEMA ch053 TO ch053_tenant_a,ch053_tenant_b;
CREATE TABLE ch053.tenant_mapping (
 db_role name PRIMARY KEY,
 tenant_id integer NOT NULL UNIQUE
);
REVOKE ALL ON ch053.tenant_mapping FROM PUBLIC;
INSERT INTO ch053.tenant_mapping VALUES ('ch053_tenant_a',101),('ch053_tenant_b',202);
CREATE FUNCTION ch053.current_tenant_id() RETURNS integer
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $f$
 SELECT m.tenant_id FROM ch053.tenant_mapping m WHERE m.db_role = session_user
$f$;
REVOKE ALL ON FUNCTION ch053.current_tenant_id() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ch053.current_tenant_id() TO ch053_tenant_a,ch053_tenant_b;
SET ROLE ch053_owner;
CREATE TABLE ch053.orders(
 id integer PRIMARY KEY,
 tenant_id integer NOT NULL,
 note text NOT NULL
);
RESET ROLE;
INSERT INTO ch053.orders VALUES (1,101,'tenant A'),(2,202,'tenant B');
ALTER TABLE ch053.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE ch053.orders FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON ch053.orders
 FOR ALL TO ch053_tenant_a,ch053_tenant_b
 USING (tenant_id = ch053.current_tenant_id())
 WITH CHECK (tenant_id = ch053.current_tenant_id());
GRANT SELECT,INSERT,UPDATE,DELETE ON ch053.orders TO ch053_tenant_a,ch053_tenant_b;

COMMIT;
