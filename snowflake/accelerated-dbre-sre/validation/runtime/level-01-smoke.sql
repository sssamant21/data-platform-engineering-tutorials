-- Snowflake Accelerated DBRE/SRE — Level 1 runtime smoke
-- ENVIRONMENT: authorized nonproduction account; approved training warehouse + scratch schema.
-- Before executing, select your designated training warehouse, database and schema in Snowsight.
-- IMPORTANT: A TEMP table can shadow an existing permanent/transient table with the same name.
-- Use an instructor-controlled empty scratch schema; verify no collision before proceeding.
-- This command is NOT guaranteed to fail on a collision with a permanent table.
-- Review each statement. This file is NOT executed by the GitHub static CI.

SELECT CURRENT_USER() AS USER_NAME,
       CURRENT_ROLE() AS ROLE_NAME,
       CURRENT_WAREHOUSE() AS WH_NAME,
       CURRENT_DATABASE() AS DB_NAME,
       CURRENT_SCHEMA() AS SCHEMA_NAME;

-- Expected: three rows.
SELECT COLUMN1 AS REGION, COLUMN2 AS AMOUNT
FROM VALUES ('EAST', 120), ('WEST', 80), ('EAST', 50);

-- Requires the approved scratch schema and an unused lab-only object name.
-- Snowflake TEMP TABLE creation does not require schema-level CREATE TABLE privilege.
-- It CAN shadow a permanent table name in the same schema; this is why isolation matters.
CREATE TEMP TABLE DBRE_SRE_L1_QA_20261030 (
    ORDER_ID NUMBER,
    REGION VARCHAR,
    AMOUNT NUMBER(10, 2)
);

INSERT INTO DBRE_SRE_L1_QA_20261030 VALUES
    (1, 'EAST', 120),
    (2, 'WEST', 80),
    (3, 'EAST', 50);

-- Expected two groups: EAST 2/170; WEST 1/80.
SELECT REGION, COUNT(*) AS NUM_ORDERS, SUM(AMOUNT) AS SALES
FROM DBRE_SRE_L1_QA_20261030
GROUP BY REGION ORDER BY REGION;

-- Expected: PASS. Capture QUERY_ID and redacted output for the evidence template.
SELECT IFF(
    COUNT(*) = 3
    AND COUNT_IF(REGION = 'EAST') = 2
    AND COUNT_IF(REGION = 'WEST') = 1
    AND SUM(IFF(REGION = 'EAST', AMOUNT, 0)) = 170
    AND SUM(IFF(REGION = 'WEST', AMOUNT, 0)) = 80,
    'PASS', 'FAIL'
) AS LEVEL_01_SMOKE_RESULT
FROM DBRE_SRE_L1_QA_20261030;

-- Evidence capture: return query IDs/status for this exact connection without raw SQL text.
-- Snowflake CLI executes all statements from one --filename on one connection.
-- Save the IDs of the sample VALUES, CREATE, INSERT, aggregation and PASS assertion.
-- Query History applies RESULT_LIMIT before outer filters; this is session-scoped.
SELECT QUERY_ID, QUERY_TYPE, EXECUTION_STATUS, TOTAL_ELAPSED_TIME,
       WAREHOUSE_NAME, START_TIME
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION(RESULT_LIMIT => 1000))
ORDER BY START_TIME DESC
LIMIT 30;

-- Cleanup: TEMP TABLE goes away when the current session ends.
-- Do not use DROP against shared or production objects.
