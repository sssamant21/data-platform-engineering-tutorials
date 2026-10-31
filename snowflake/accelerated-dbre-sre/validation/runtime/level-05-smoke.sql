-- Snowflake Accelerated DBRE/SRE Level 5: RBAC and security audit smoke
-- MANUAL / NONPRODUCTION / READ-ONLY. Never switch to ACCOUNTADMIN.
-- Run statements separately with the explicitly approved least-privilege training role.
-- Do not export user names, IP addresses, credential details, or raw error messages.

-- 1. Current user and roles. CURRENT_SECONDARY_ROLES returns JSON-encoded VARCHAR.
SELECT CURRENT_ROLE() AS ACTIVE_ROLE,
       CURRENT_SECONDARY_ROLES() AS ACTIVE_SECONDARY_ROLES,
       CURRENT_DATABASE() AS DATABASE_CONTEXT;

-- 2. SHOW GRANTS without arguments lists roles granted to the current user.
SHOW GRANTS;

-- 3. Role metadata visible to the active role (not an account-wide access inventory).
SHOW ROLES;

-- 4. OPTIONAL security-audit view. Run only with approved read-only grants on
-- SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY. Records can lag up to 2 hours.
-- Aggregate event status only: do not select USER_NAME, CLIENT_IP or raw errors.
SELECT DATE_TRUNC('day', EVENT_TIMESTAMP) AS DAY_UTC,
       IS_SUCCESS AS LOGIN_SUCCESS_STATUS,
       COUNT(*) AS ATTEMPT_COUNT
FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
WHERE EVENT_TIMESTAMP >= DATEADD('day', -7, CURRENT_TIMESTAMP())
GROUP BY 1, 2
ORDER BY 1, 2;

-- Acceptance is evidence-based: current role; JSON-encoded secondary-role result;
-- SHOW GRANTS role visibility; optional login aggregate or documented BLOCKED state.
-- No GRANT, REVOKE, USE ROLE or security policy changes are part of this lab.
