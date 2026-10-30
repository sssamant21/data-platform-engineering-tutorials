\set ON_ERROR_STOP on
DO $$
BEGIN
 IF (SELECT count(*) FROM pg_roles
     WHERE rolname IN ('ch051_reader','ch051_writer','ch053_tenant_a','ch053_tenant_b')) <> 4 THEN
   RAISE EXCEPTION 'FAIL: required security lab identities are missing; not accepted';
 END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_hba_file_rules) THEN
   RAISE EXCEPTION 'FAIL: no readable HBA rules; cannot accept this inspection';
 END IF;
 IF EXISTS (SELECT 1 FROM pg_hba_file_rules WHERE error IS NOT NULL) THEN
   RAISE EXCEPTION 'FAIL: pg_hba.conf parse errors detected';
 END IF;
 IF EXISTS (
  SELECT 1 FROM pg_roles
  WHERE rolname IN ('ch051_reader','ch051_writer','ch053_tenant_a','ch053_tenant_b')
    AND (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb)
 ) THEN
   RAISE EXCEPTION 'FAIL: privileged lab runtime identity detected';
 END IF;
 RAISE NOTICE 'PASS: HBA file parse and mandatory lab role metadata; live TLS, HBA reload, audit and tenant checks still required';
END $$;
SELECT name,setting,source,pending_restart
FROM pg_settings
WHERE name IN ('ssl','password_encryption','log_destination','logging_collector')
ORDER BY name;
