\set ON_ERROR_STOP on
DO $$
BEGIN
 IF EXISTS(SELECT 1 FROM pg_replication_slots WHERE slot_name='ch047_lab_physical') THEN
   RAISE EXCEPTION 'Lab slot already exists; do not overwrite';
 END IF;
END $$;
SELECT slot_name,lsn FROM pg_create_physical_replication_slot('ch047_lab_physical',false);
