\set ON_ERROR_STOP on
DO $$
BEGIN
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
 RAISE NOTICE 'PASS: HBA parsing and lab role privilege metadata checks';
END $$;
SELECT name,setting,source,pending_restart
FROM pg_settings
WHERE name IN ('ssl','password_encryption','log_destination','logging_collector')
ORDER BY name;
