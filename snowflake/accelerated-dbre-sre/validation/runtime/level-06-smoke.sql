-- Snowflake Accelerated DBRE/SRE Level 6: Recovery readiness smoke
-- MANUAL / TRAINING ACCOUNT / READ-ONLY ONLY. No DROP, DELETE, UPDATE or failover.
-- Check the exact approved training database and scratch table before proceeding.
-- If the named objects do not exist in your environment, STOP and replace names
-- with explicitly approved nonproduction identifiers; do not use production data.

-- 1. Identity and Snowflake object context.
SELECT CURRENT_ROLE() AS ACTIVE_ROLE,
       CURRENT_DATABASE() AS DATABASE_CONTEXT,
       CURRENT_SCHEMA() AS SCHEMA_CONTEXT;

-- 2. Account minimum retention. Privileges and visibility are account-specific.
SHOW PARAMETERS LIKE 'MIN_DATA_RETENTION_TIME_IN_DAYS' IN ACCOUNT;

-- 3. Database configured retention. Requires existing approved DBRE_SRE_LAB.
SHOW PARAMETERS LIKE 'DATA_RETENTION_TIME_IN_DAYS' IN DATABASE DBRE_SRE_LAB;

-- 4. Optional: only if approved permanent lab table exists and is visible.
SHOW PARAMETERS LIKE 'DATA_RETENTION_TIME_IN_DAYS'
IN TABLE DBRE_SRE_L6_RECOVERY;

-- 5. Optional: ONLY IF the lab table and its two rows existed at least 60 seconds
-- ago and the historical point is within effective table retention.
-- Record observed actual output, do not assert PASS without executing.
SELECT COUNT(*) AS HISTORICAL_ROWS
FROM DBRE_SRE_L6_RECOVERY AT (OFFSET => -60);

-- Teaching check: AT OFFSET is negative seconds, relative to each statement time.
-- A historical point at/before table creation or outside retention can error.
-- Also examine MIN_DATA_RETENTION_TIME_IN_DAYS: effective retention for
-- permanent tables can exceed DATA_RETENTION_TIME_IN_DAYS.
-- If the table is absent, mark steps 4/5 BLOCKED, not PASS.
-- This lab NEVER changes retention, creates objects or restores production data.
