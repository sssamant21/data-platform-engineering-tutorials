-- Snowflake Accelerated DBRE/SRE — Level 2 runtime smoke
-- ENVIRONMENT: authorized nonproduction account and small approved training warehouse.
-- Run in a fresh worksheet with a database selected, using a least-privilege training role.
-- All queries are read-only except for session-scoped QUERY_TAG configuration.

SELECT CURRENT_USER() AS USER_NAME,
       CURRENT_ROLE() AS ROLE_NAME,
       CURRENT_WAREHOUSE() AS WH_NAME;

SHOW WAREHOUSES;
SHOW ROLES;
SHOW GRANTS;

-- Expected: query tag set for this session only.
ALTER SESSION SET QUERY_TAG = 'snowflake_dbre_sre_l2_runtime_smoke';

-- Expected: 100.
SELECT COUNT(*) AS ROW_COUNT FROM TABLE(GENERATOR(ROWCOUNT => 100));

-- Expected: a recently completed tagged query, typically with EXECUTION_STATUS='success'.
-- Must have a database selected; the Information Schema table function returns up to 7 days.
SELECT QUERY_ID, QUERY_TAG, EXECUTION_STATUS, TOTAL_ELAPSED_TIME, START_TIME
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_USER(RESULT_LIMIT => 100))
WHERE QUERY_TAG = 'snowflake_dbre_sre_l2_runtime_smoke'
ORDER BY START_TIME DESC;

-- Restore default session setting; this step still runs if an earlier statement failed.
ALTER SESSION UNSET QUERY_TAG;

-- Record role visibility, query ID, expected/actual status, and authorized training cost.
-- Never resize or suspend a production warehouse during this smoke test.
