-- Snowflake Accelerated DBRE/SRE Level 7: Incident investigation smoke
-- MANUAL / READ-ONLY / TRAINING ACCOUNT. Avoid patient identifiers and raw SQL text.
-- Run first section with an approved training role; account-level query history
-- requires an independently approved monitoring role with access to ACCOUNT_USAGE.

SELECT CURRENT_ROLE() AS ACTIVE_ROLE,
       CURRENT_WAREHOUSE() AS WAREHOUSE_CONTEXT,
       CURRENT_DATABASE() AS DATABASE_CONTEXT;

-- 1. Current-session recent query evidence. This is not all-account incident
-- coverage. Function RESULT_LIMIT is applied before any outer SQL filtering.
SELECT QUERY_ID, WAREHOUSE_NAME, EXECUTION_STATUS,
       ERROR_CODE, TOTAL_ELAPSED_TIME, EXECUTION_TIME,
       QUEUED_OVERLOAD_TIME, QUEUED_PROVISIONING_TIME,
       TRANSACTION_BLOCKED_TIME, START_TIME
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION(RESULT_LIMIT => 1000))
ORDER BY START_TIME DESC;

-- 2. OPTIONAL historical account trend, only with approved read-only grants.
-- The ACCOUNT_USAGE status values are success/fail/incident, not the
-- Information Schema failed_with_error/failed_with_incident values.
-- This view can lag ~45 minutes. Use a recent source during an active outage.
SELECT DATE_TRUNC('hour', START_TIME) AS HOUR,
       WAREHOUSE_NAME,
       COUNT(*) AS QUERY_COUNT,
       COUNT_IF(EXECUTION_STATUS = 'fail') AS FAILURES,
       ROUND(AVG(TOTAL_ELAPSED_TIME) / 1000, 2) AS AVG_ELAPSED_SECONDS,
       ROUND(AVG(QUEUED_OVERLOAD_TIME) / 1000, 2) AS AVG_OVERLOAD_SECONDS
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD('hour', -24, CURRENT_TIMESTAMP())
GROUP BY 1, 2
ORDER BY 1 DESC, 2;

-- Record incident impact/SLO and a measured baseline before mitigation.
-- Never cancel queries, change warehouses, grant access, recover or failover
-- as part of this smoke test. Tabletop scenarios are in the lesson.
