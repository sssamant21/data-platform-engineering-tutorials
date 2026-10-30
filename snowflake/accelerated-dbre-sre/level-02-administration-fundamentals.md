# Level 2 — Snowflake Administration Fundamentals

**Track:** Snowflake Accelerated DBRE/SRE | **Duration:** 60 minutes | **Status:** DRAFT — static review pending; live Snowflake validation NOT RUN  
**Audience:** New Snowflake administrators, DBRE/SRE and platform operations  
**Prerequisites:** Authorized Snowflake training account; basic SQL recommended for Levels 2–7.

## Learning objectives
Inspect warehouse state, administrative boundaries, users/roles and recent query activity using safe SQL.

## 60-minute lesson plan
| Topic | Time |
|---|---:|
| Administrative responsibilities and ownership | 10 min |
| Warehouses and lifecycle | 15 min |
| Users, roles and privileges | 10 min |
| Read-only operational lab | 20 min |
| Check and review | 5 min |
| **Total** | **60 min** |

## Core concepts
### Snowflake versus the DBRE/SRE team
Snowflake owns underlying infrastructure, storage internals, and managed service operations. Administrators own approved account configuration, role and privilege hygiene, warehouse configuration, performance visibility, cost controls, and documented incident response.

### Warehouse operations
Virtual warehouses are independently scalable compute resources; choose a size based on measured workload. AUTO_SUSPEND avoids unnecessary idle runtime and AUTO_RESUME makes subsequent queries start the warehouse. Resume/startup time and billing minimums matter. Multi-cluster warehouses address concurrency, whereas larger warehouse sizes can improve compute capacity for individual workloads. Neither replaces SQL optimization.

~~~sql
SHOW WAREHOUSES;
SELECT CURRENT_WAREHOUSE(), CURRENT_ROLE(), CURRENT_USER();
~~~

### Lifecycle and change safety
\`ALTER WAREHOUSE ... RESUME\`, \`... SUSPEND\`, and \`... SET WAREHOUSE_SIZE\` are change operations. In production, capture active workloads, owner approval, rollback size, SLOs, and a monitoring window before making changes. Never suspend a production warehouse simply to test a command.

**Illustrative, not automatically run:**
~~~sql
-- On an approved training warehouse only:
-- ALTER WAREHOUSE DBRE_SRE_LAB_WH SET WAREHOUSE_SIZE = 'SMALL';
-- ALTER WAREHOUSE DBRE_SRE_LAB_WH SET WAREHOUSE_SIZE = 'XSMALL';
~~~

### Access model
RBAC is central to Snowflake operations. Users assume roles; roles hold privileges such as USAGE, SELECT or OPERATE. A role needs appropriate access to database and schema objects as well as any compute needed to run queries. Prefer dedicated read-only monitoring roles over permanent use of ACCOUNTADMIN.

### Key operational surfaces
Snowsight Query History is good for recent troubleshooting. Account Usage views (where grants allow) are good for longer-term historical analysis but have latency. Query IDs, warehouse names and query tags make incident evidence auditable.

## Hands-on lab and expected results
### Prerequisites
An existing authorized account and approved training warehouse. Most steps are read-only; no administrator privilege escalation is required.

### Step 1 — Inventory your context
~~~sql
SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE();
SHOW WAREHOUSES;
SHOW ROLES;
~~~
Expected: visible warehouses and roles, restricted by current role visibility.

### Step 2 — Inspect grants safely
~~~sql
SHOW GRANTS;
~~~
Expected: grants or roles visible to the current user; do not share identifying user information outside approved channels.

### Step 3 — Tag and run a tiny training query
~~~sql
ALTER SESSION SET QUERY_TAG = 'snowflake_dbre_sre_level_02';
SELECT COUNT(*) AS N FROM TABLE(GENERATOR(ROWCOUNT => 100));
~~~
Expected: N = 100. QUERY_TAG identifies the training activity.

### Step 4 — Locate the query
With an accessible database selected:
~~~sql
SELECT QUERY_ID, QUERY_TAG, EXECUTION_STATUS,
       TOTAL_ELAPSED_TIME, START_TIME
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_USER(RESULT_LIMIT => 30))
ORDER BY START_TIME DESC;
~~~
Expected: recent visible queries; confirm a completed training query. The Information Schema table function covers a shorter history than Account Usage.

### Step 5 — Clean up session state
~~~sql
ALTER SESSION UNSET QUERY_TAG;
~~~
**Pass:** explain your active role, warehouse, a query ID, and when a warehouse change would require an approved maintenance process.

## DBRE/SRE troubleshooting quick reference
| Symptom | First evidence | Safe next action |
|---|---|---|
| Query waits | Query History queue fields | Measure concurrency before scaling |
| Warehouse suspended | SHOW WAREHOUSES | Confirm expected auto-resume settings |
| Privilege denied | CURRENT_ROLE and grants | Owner-driven least-privilege grant review |
| Credits increasing | Warehouse Metering History | Identify running workloads and idle windows |

An unexpected production query failure after a warehouse change requires rollback evaluation and application-owner involvement.

## Knowledge check (with answers)
1. **Who manages Snowflake's underlying servers?** Snowflake.
2. **What is warehouse auto-suspend?** Idle compute suspension.
3. **When is resizing appropriate?** After measuring the cause and getting approval.
4. **What identifies a query for triage?** QUERY_ID.
5. **Should all operators use ACCOUNTADMIN?** No; use least privilege.

## Operational safety and validation
- Use a **designated lab account/warehouse** and synthetic data. Protect query-history text and any personal or customer information.
- SQL that creates/changes warehouse, roles, objects, retention or data requires appropriate role, approval and isolated test scope.
- Expected outcomes describe intended behavior, **not proof of execution**. No SQL was run against live Snowflake when authoring this lesson.
- If a command is not applicable to the account edition or current role, document the limitation rather than escalating privileges.
- **Acceptance:** instructor checks concepts, learner documents observed output, and a separate runtime review confirms SQL syntax/permissions and clean-up.

## Continue into the full 90-chapter curriculum
[43 Warehouse Sizing](../43-warehouse-sizing-scaling.md), [46 Account Usage](../46-account-usage-information-schema.md), [75 Production Admin Runbook](../75-snowflake-production-administration-runbook.md)

## Official documentation
- https://docs.snowflake.com/en/user-guide/warehouses-overview
- https://docs.snowflake.com/en/user-guide/security-access-control-overview
- https://docs.snowflake.com/en/sql-reference/functions/query_history

[Back to accelerated track index](README.md) | [Validation tracker](STATUS.md)
