# Level 2 — Snowflake Administration Fundamentals

**Track:** Snowflake Accelerated DBRE/SRE | **Duration:** 60 minutes | **Status:** DRAFT — V01/V02 automated static QA PASS; independent content review PENDING; Snowflake runtime validation NOT RUN (deferred)  
**Audience:** New Snowflake administrators, DBRE/SRE and platform operations  
**Offline prerequisites:** This lesson and the [instructor pack](validation/INSTRUCTOR-OFFLINE-ACCEPTANCE.md); no Snowflake account, CLI, credentials or live database access is required. Basic SQL is recommended for Levels 2–7.  
**Deferred V03 live-lab prerequisites:** Approved nonproduction account, least-privilege role and training warehouse; a selected accessible database for `INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION`; permission to inspect visible role/warehouse metadata. **Do not execute SQL for the offline course.**

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

**Offline teaching only:** Walk through the SQL and expected synthetic, hypothetical or historical-view outcomes **without executing any statement**. Discuss permissions, cost, data sensitivity and what might be unavailable. Any 'Expected' or 'Pass' description is an **instructional target, not an observed result**. The SQL may be run only later under the separate, owner-authorized V03 nonproduction procedure, which remains **NOT RUN**.
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
ALTER SESSION SET QUERY_TAG = 'snowflake_dbre_sre_l2_runtime_smoke';
SELECT COUNT(*) AS N FROM TABLE(GENERATOR(ROWCOUNT => 100));
~~~
Expected: N = 100. QUERY_TAG identifies the training activity.

### Step 4 — Locate the query
With an accessible database selected:
~~~sql
SELECT QUERY_ID, QUERY_TAG, EXECUTION_STATUS,
       TOTAL_ELAPSED_TIME, START_TIME
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION(RESULT_LIMIT => 1000))
WHERE QUERY_TAG = 'snowflake_dbre_sre_l2_runtime_smoke'
ORDER BY START_TIME DESC;
~~~
Expected: recent tagged queries from this worksheet session, subject to the function's retrieval limit. Confirm a completed training query and its actual status. This training tag intentionally matches the [Level 2 validation script](validation/runtime/level-02-smoke.sql); the value is not a production convention. Query-history functions select the newest results up to RESULT_LIMIT **before** applying the outer WHERE filter; they cover up to seven days and are not equivalent to Account Usage.

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
1. **Who manages Snowflake's underlying servers?** **Snowflake operates the managed service infrastructure.** Your DBRE/SRE team still owns approved account configuration, identity/role boundaries, warehouse settings, operational monitoring and incident procedures.
2. **What is warehouse auto-suspend?** **An idle warehouse can suspend automatically after its configured inactivity period**, helping avoid idle compute charges. Auto-resume allows a later compatible query to resume it, with potential startup delay and minimum-billing considerations.
3. **When is resizing appropriate?** **After investigating performance evidence and obtaining owner/change approval.** Compare queue time, execution, concurrency and cost; then test a reversible warehouse-size change against a baseline rather than assuming larger is always faster.
4. **What identifies a query for triage?** **`QUERY_ID` is the unique execution identifier** that connects Query History and Query Profile evidence. Save the actual ID from the approved test session, never invent one for a runtime claim.
5. **Should all operators use ACCOUNTADMIN?** **No.** Use task-specific least-privilege roles; privileged administrative roles require separate controlled workflows. A denied lab query is a request for owner-approved access, not a reason to elevate privileges.

**Instructor grading (offline):** Each answer earns **2 points** for the correct concept **and** its explanation/safety distinction; **1 point** for a correct keyword with incomplete reasoning; **0 points** for an incorrect or unsafe answer. Maximum **10 points** per level. See the [instructor answer key and grading rubric](validation/INSTRUCTOR-ANSWER-KEY-RUBRICS.md) for question-by-question anchors. This is a knowledge check, **not V03 runtime acceptance**.

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
