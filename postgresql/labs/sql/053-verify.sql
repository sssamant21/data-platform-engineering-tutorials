\set ON_ERROR_STOP on
DO $$
BEGIN
 IF current_database() <> 'ch053_lab' THEN RAISE EXCEPTION 'Wrong database'; END IF;
END $$;
SELECT current_setting('server_version') AS version;
SELECT schemaname,tablename,policyname,roles,cmd,qual,with_check
FROM pg_policies WHERE schemaname='ch053';
SELECT rolname,rolsuper,rolbypassrls FROM pg_roles
WHERE rolname IN ('ch053_tenant_a','ch053_tenant_b');
SET SESSION AUTHORIZATION ch053_tenant_a;
DO $$
DECLARE n integer;
BEGIN
 SELECT count(*) INTO n FROM ch053.orders;
 IF n <> 1 THEN RAISE EXCEPTION 'Tenant A visibility failed: %',n; END IF;
 IF EXISTS(SELECT 1 FROM ch053.orders WHERE tenant_id<>101) THEN
   RAISE EXCEPTION 'Tenant A cross-tenant read';
 END IF;
 IF has_table_privilege(current_user,'ch053.tenant_mapping','SELECT') THEN
   RAISE EXCEPTION 'Tenant A can read protected mapping';
 END IF;
 IF has_schema_privilege(current_user,'ch053','CREATE') THEN
   RAISE EXCEPTION 'Tenant A can create schema objects';
 END IF;
 BEGIN
   INSERT INTO ch053.orders VALUES (3,202,'forbidden');
   RAISE EXCEPTION 'Tenant A cross-tenant insert unexpectedly succeeded';
 EXCEPTION WHEN insufficient_privilege THEN NULL;
 END;
 INSERT INTO ch053.orders VALUES (3,101,'allowed');
 UPDATE ch053.orders SET note='updated A' WHERE id=3;
 DELETE FROM ch053.orders WHERE id=3;
END $$;
RESET SESSION AUTHORIZATION;
SET SESSION AUTHORIZATION ch053_tenant_b;
DO $$
DECLARE n integer;
BEGIN
 SELECT count(*) INTO n FROM ch053.orders;
 IF n <> 1 THEN RAISE EXCEPTION 'Tenant B visibility failed: %',n; END IF;
 IF EXISTS(SELECT 1 FROM ch053.orders WHERE tenant_id<>202) THEN
   RAISE EXCEPTION 'Tenant B cross-tenant read';
 END IF;
 BEGIN
   UPDATE ch053.orders SET tenant_id=101 WHERE id=2;
   RAISE EXCEPTION 'Tenant B cross-tenant update unexpectedly succeeded';
 EXCEPTION WHEN insufficient_privilege THEN NULL;
 END;
END $$;
RESET SESSION AUTHORIZATION;
SELECT 'PASS: tenant A/B isolation assertions' AS result;
