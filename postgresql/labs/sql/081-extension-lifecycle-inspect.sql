-- Chapter 081: read-only extension inventory; run in each database.
SELECT current_setting('server_version') AS server_version,
 current_database() AS database_name,clock_timestamp() AS inspected_at;
SELECT e.extname,e.extversion,n.nspname AS extension_schema,e.extrelocatable
FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace
ORDER BY e.extname;
SELECT name,default_version,installed_version,comment
FROM pg_available_extensions ORDER BY name;
SELECT name,version,installed,superuser,trusted,relocatable,requires
FROM pg_available_extension_versions ORDER BY name,version;
SELECT e.extname,d.classid::regclass AS object_catalog,d.objid,d.deptype
FROM pg_depend d JOIN pg_extension e ON e.oid=d.refobjid
WHERE d.refclassid='pg_extension'::regclass
ORDER BY e.extname,d.classid::regclass::text,d.objid;
SELECT name,setting,pending_restart
FROM pg_settings WHERE name='shared_preload_libraries';
