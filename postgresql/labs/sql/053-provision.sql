\set ON_ERROR_STOP on
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
