-- Snowflake Accelerated DBRE/SRE — Level 3 performance foundation smoke
-- MANUAL ONLY. Never run in production. Use a small, approved training warehouse and
-- a dedicated, verified-empty scratch schema. TEMP tables can shadow permanent names.
-- No benchmark claim can be made from this 1,000-row dataset.
-- Stop if DBRE_SRE_L3_QA_20261030 already exists in the scratch schema.

SELECT CURRENT_ROLE() AS ROLE_NAME,
       CURRENT_WAREHOUSE() AS WH_NAME,
       CURRENT_DATABASE() AS DB_NAME,
       CURRENT_SCHEMA() AS SCHEMA_NAME;

-- Verify the schema is the approved scratch environment.
-- Results may be empty if no table uses this name, but do not assume SHOW proves
-- the absence of objects hidden by your role. The instructor owns namespace safety.
SHOW TABLES LIKE 'DBRE_SRE_L3_QA_20261030';

CREATE TEMP TABLE DBRE_SRE_L3_QA_20261030 AS
SELECT ORDER_ID, MOD(ORDER_ID, 10) AS REGION_ID,
       10 + MOD(ORDER_ID, 90) AS AMOUNT
FROM (
    SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) AS ORDER_ID
    FROM TABLE(GENERATOR(ROWCOUNT => 1000))
);

-- Expected: total N = 1000 and total amount = 54110.
SELECT COUNT(*) AS N, SUM(AMOUNT) AS TOTAL_AMOUNT
FROM DBRE_SRE_L3_QA_20261030;

-- Expected: N = 100 and total amount = 5060.
SELECT COUNT(*) AS N, SUM(AMOUNT) AS TOTAL_AMOUNT
FROM DBRE_SRE_L3_QA_20261030
WHERE REGION_ID = 1;

-- Deterministic result assertion; this is an output check, not query optimization proof.
-- Expected: PASS.
SELECT IFF(
    COUNT(*) = 1000
    AND COUNT(DISTINCT ORDER_ID) = 1000
    AND MIN(ORDER_ID) = 1 AND MAX(ORDER_ID) = 1000
    AND COUNT_IF(REGION_ID = 1) = 100
    AND SUM(AMOUNT) = 54110
    AND SUM(IFF(REGION_ID = 1, AMOUNT, 0)) = 5060,
    'PASS', 'FAIL'
) AS LEVEL_03_SMOKE_RESULT
FROM DBRE_SRE_L3_QA_20261030;

-- Query history captures real timings but results depend on account activity.
-- With a database selected, confirm this statement and an earlier SELECT appear.
SELECT QUERY_ID, EXECUTION_STATUS, TOTAL_ELAPSED_TIME, EXECUTION_TIME,
       QUEUED_OVERLOAD_TIME, BYTES_SCANNED, START_TIME
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION(RESULT_LIMIT => 1000))
ORDER BY START_TIME DESC;

-- Instructor: open Query Profile by an actual captured QUERY_ID. Record scans
-- and note that a tiny dataset does not prove performance gain. Session close
-- disposes of the temporary table; record the cleanup in the evidence form.
