\set ON_ERROR_STOP on
DO $$
BEGIN
 IF EXISTS(SELECT 1 FROM pg_replication_slots WHERE slot_name='ch047_lab_physical' AND active) THEN
   RAISE EXCEPTION 'Lab slot active; cleanup refused';
 END IF;
 IF NOT EXISTS(SELECT 1 FROM pg_replication_slots WHERE slot_name='ch047_lab_physical' AND slot_type='physical') THEN
   RAISE EXCEPTION 'Expected lab physical slot not found; cleanup refused';
 END IF;
END $$;
SELECT pg_drop_replication_slot('ch047_lab_physical');
DROP SCHEMA IF EXISTS ch047 CASCADE;
