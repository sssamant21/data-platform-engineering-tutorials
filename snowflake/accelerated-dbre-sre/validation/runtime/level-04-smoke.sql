-- Snowflake Accelerated DBRE/SRE — Level 4 monitoring / FinOps smoke
-- MANUAL / READ-ONLY. Never grant ACCOUNTADMIN merely to run these queries.
-- Run with a monitoring role granted the necessary SNOWFLAKE.ACCOUNT_USAGE views.
-- Account Usage can be delayed: absence of rows is not proof of account health.

SELECT CURRENT_ROLE() AS ROLE_NAME, CURRENT_WAREHOUSE() AS WH_NAME;

-- Hourly warehouse credits for 7 days; this is NOT final billed credits.
-- Compute and cloud-services credits are separate. Cloud-services billing
-- adjustments are reflected in other metering views (e.g. METERING_DAILY_HISTORY).
SELECT WAREHOUSE_NAME,
       ROUND(SUM(CREDITS_USED), 2) AS GROSS_CREDITS_7D,
       ROUND(SUM(CREDITS_USED_COMPUTE), 2) AS COMPUTE_CREDITS_7D,
       ROUND(SUM(CREDITS_USED_CLOUD_SERVICES), 2) AS CLOUD_SERVICES_CREDITS_7D
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE START_TIME >= DATEADD('day', -7, CURRENT_TIMESTAMP())
GROUP BY WAREHOUSE_NAME
ORDER BY GROSS_CREDITS_7D DESC;

-- 5-minute historical load snapshots, delayed up to approx. three hours.
-- Values represent aggregate query-time ratio, not unique users/query count.
SELECT WAREHOUSE_NAME, START_TIME,
       ROUND(AVG_RUNNING, 2) AS RUNNING_LOAD,
       ROUND(AVG_QUEUED_LOAD, 2) AS QUEUED_LOAD,
       ROUND(AVG_QUEUED_PROVISIONING, 2) AS PROVISIONING_LOAD,
       ROUND(AVG_BLOCKED, 2) AS BLOCKED_LOAD
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY
WHERE START_TIME >= DATEADD('day', -1, CURRENT_TIMESTAMP())
ORDER BY START_TIME DESC LIMIT 50;

-- ACCOUNT_USAGE.QUERY_HISTORY uses 'fail' (not 'failed_with_error').
SELECT DATE_TRUNC('hour', START_TIME) AS HOUR,
       COUNT(*) AS QUERY_COUNT,
       COUNT_IF(EXECUTION_STATUS = 'fail') AS FAIL_COUNT,
       COUNT_IF(EXECUTION_STATUS = 'incident') AS INCIDENT_COUNT
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD('day', -1, CURRENT_TIMESTAMP())
GROUP BY 1 ORDER BY 1;

-- Revenue/billing note: WAREHOUSE_METERING_HISTORY.CREDITS_USED may differ
-- from CREDITS_BILLED; the following daily billing view is account-level and
-- includes adjustments and other billable service types.
SELECT USAGE_DATE,
       SUM(CREDITS_BILLED) AS ACCOUNT_CREDITS_BILLED
FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_DAILY_HISTORY
WHERE USAGE_DATE >= DATEADD('day', -7, CURRENT_DATE())
GROUP BY USAGE_DATE ORDER BY USAGE_DATE;

-- Pass criteria are evidentiary: SQL runs under approved monitoring role,
-- metrics/latency/empty-window caveats recorded, no grants or writes performed.
