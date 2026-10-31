# Level 6 — Snowflake Data Recovery and Disaster Recovery

**Track:** Snowflake Accelerated DBRE/SRE | **Duration:** 60 minutes | **Status:** DRAFT — V01/V02 automated static QA PASS; independent content review PENDING; Snowflake runtime validation NOT RUN (deferred)  
**Audience:** DBRE/SRE, DR coordinators, data owners and platform leads  
**Prerequisites:** Authorized Snowflake training account; basic SQL recommended for Levels 2–7.

## Learning objectives
Identify the appropriate recovery mechanism, assess retention and practice a safe recovery plan.

## 60-minute lesson plan
| Topic | Time |
|---|---:|
| Recovery goals: RPO, RTO and ownership | 10 min |
| Time Travel, UNDROP, cloning, Fail-safe | 15 min |
| Cross-region/cross-account replication and failover | 10 min |
| Recovery planning lab | 20 min |
| Review | 5 min |
| **Total** | **60 min** |

## Core concepts
### Match the recovery method to the failure
Accidental UPDATE/DELETE can often be investigated with Time Travel inside an object's retention window. UNDROP may recover dropped supported objects while retained. Cloning helps create an isolated point-in-time copy for verification, but it is not automatically a disaster recovery plan. Fail-safe is Snowflake-operated and is not for routine self-service restoration.

### Retention and edition limitations
Time Travel defaults to a one-day standard retention window, with longer retention available according to edition and object type. Effective retention for permanent tables may be governed by the account-level `MIN_DATA_RETENTION_TIME_IN_DAYS`, even when `DATA_RETENTION_TIME_IN_DAYS` is lower. A configured retention of zero does not by itself establish the effective history window. Verify both parameters and the table type before concluding that recovery is possible. Confirm current settings **before an incident**, not during one.

### Regional disaster recovery
A region or account outage requires an approved replication/failover architecture, configured in advance and tested under recovery objectives. RPO (acceptable data loss window) and RTO (acceptable restoration time) must come from the business owner. Replication and failover support, scope and limitations depend on account edition and design.

### Safe recovery procedure
1. Stop or isolate damaging writes **with owner approval**.
2. Identify exact database/schema/object, incident start time, earliest damaging query ID and retention.
3. Determine whether Time Travel, UNDROP, clone, restore from another source, or failover is applicable.
4. Validate recovered rows, counts, important business keys and access controls in isolation.
5. Obtain go/no-go approval for cutover or merge-back; document rollback.
6. Measure actual RPO/RTO and update the runbook.

Never treat Fail-safe as a guaranteed point-in-time backup service.

## Hands-on lab and expected results
### Step 1 — Inspect retention without changing data
In a designated training database:
~~~sql
SHOW PARAMETERS LIKE 'DATA_RETENTION_TIME_IN_DAYS'
IN DATABASE DBRE_SRE_LAB;
~~~
Replace DBRE_SRE_LAB with your existing authorized lab database. Expected: **configured/inherited** retention parameter rows, subject to permissions—not proof of effective historical recoverability. Check the account minimum, object type, privilege visibility, and the actual historical time point before making any recovery claim.

### Step 2 — Create an approved lab table (optional writable branch)
In a dedicated scratch schema only:
~~~sql
CREATE TABLE DBRE_SRE_L6_RECOVERY (
    ID NUMBER, STATUS VARCHAR
);
INSERT INTO DBRE_SRE_L6_RECOVERY VALUES (101, 'OK'), (102, 'OK');
SELECT COUNT(*) AS ROWS_BEFORE FROM DBRE_SRE_L6_RECOVERY;
~~~
Expected: ROWS_BEFORE = 2. This uses a **permanent** lab table to demonstrate Time Travel, and consumes storage. The CREATE command must fail closed if the name already exists; do not use OR REPLACE. Obtain approval for creation, retention and eventual removal in a dedicated scratch schema. Do not create it in production.

### Step 2b — Check account minimum and table retention
After selecting the approved scratch database/schema and creating the table, inspect the table-level setting (which may differ from the database default):
~~~sql
SHOW PARAMETERS LIKE 'MIN_DATA_RETENTION_TIME_IN_DAYS' IN ACCOUNT;
SHOW PARAMETERS LIKE 'DATA_RETENTION_TIME_IN_DAYS' IN TABLE DBRE_SRE_L6_RECOVERY;
~~~
Expected: visible account-minimum and table-retention parameters. For permanent tables, evaluate the effective minimum and configured retention together; for other object types, supported retention rules differ. If effective retention is zero or unknown, stop and review the lab design with the training administrator.

### Step 3 — Read a historical version after sufficient time
Run this **only after more than 60 seconds have elapsed since the INSERT completed**, while still within the effective Time Travel retention:
~~~sql
SELECT * FROM DBRE_SRE_L6_RECOVERY AT(OFFSET => -60);
~~~
Expected: two rows if the table and INSERT were both completed more than 60 seconds ago and data remains within retention. Otherwise, the query may show a prior row state or fail if the requested point predates creation. Record the INSERT completion timestamp. Note that time-based queries are sensitive to the point in time selected and account settings.

### Step 4 — Paper exercise: accidental DELETE
A user mistakenly deletes 5,000 rows at 10:03 and detection occurs at 10:21. Write down the timestamp or statement ID to investigate, the retention deadline, and the owner-approved plan to compare historical and current rows. Do **not** execute DELETE, DROP, or a production restore.

### Step 5 — Plan an outage test
Create a sample RPO/RTO table for a BI workload, including dependency on ingestion, roles, warehouse readiness, downstream dashboards and communications.

**Pass:** select the right recovery mechanism for accidental DML, dropped objects and region outage; describe validation and rollback. Use the [Level 6 read-only readiness smoke](validation/runtime/level-06-smoke.sql) if you have an approved training database/table. When the optional lab object does not exist, explicitly record the historical-query step as **BLOCKED**; do not substitute any production object.

### Lab cleanup (owner-approved, separate step)
The permanent scratch table is intentionally not dropped by the instructional SQL. After retaining evidence and obtaining the lab owner's approval, an authorized operator should verify the fully qualified object name and remove only **DBRE_SRE_L6_RECOVERY** in the training scratch schema. Never run an unqualified DROP against a shared environment.

## DBRE/SRE troubleshooting quick reference
| Event | Preferred investigation | Safety rule |
|---|---|---|
| Accidental delete | Historical SELECT / query ID | Recover in isolation before merge-back |
| Dropped table | SHOW TABLES HISTORY / retention review | UNDROP only with change approval |
| Data corruption | Compare snapshot/time travel and source | Avoid overwriting evidence |
| Regional outage | Approved replication/failover runbook | Enforce RPO/RTO and business go/no-go |

Any recovery claiming production readiness must have demonstrated restore tests and data-owner sign-off.

## Knowledge check (with answers)
1. **What is RPO?** Maximum acceptable data loss window.
2. **What is RTO?** Maximum acceptable restoration time.
3. **Can Time Travel always restore data indefinitely?** No, it is retention-bound.
4. **Is Fail-safe routine self-service backup?** No.
5. **Is an untested clone the same as disaster recovery?** No.

## Operational safety and validation
- Use a **designated lab account/warehouse** and synthetic data. Protect query-history text and any personal or customer information.
- SQL that creates/changes warehouse, roles, objects, retention or data requires appropriate role, approval and isolated test scope.
- Expected outcomes describe intended behavior, **not proof of execution**. No SQL was run against live Snowflake when authoring this lesson.
- If a command is not applicable to the account edition or current role, document the limitation rather than escalating privileges.
- **Acceptance:** instructor checks concepts, learner documents observed output, and a separate runtime review confirms SQL syntax/permissions and clean-up.

## Continue into the full 90-chapter curriculum
[56 Time Travel](../56-snowflake-time-travel.md), [58 Cloning](../58-snowflake-zero-copy-cloning.md), [60 Recovery Runbook](../60-snowflake-accidental-delete-drop-recovery-runbook.md), [70 DR Testing](../70-snowflake-disaster-recovery-runbook-testing.md)

## Official documentation
- https://docs.snowflake.com/en/user-guide/data-time-travel
- https://docs.snowflake.com/en/sql-reference/constructs/at-before
- https://docs.snowflake.com/en/sql-reference/parameters
- https://docs.snowflake.com/en/user-guide/data-failsafe
- https://docs.snowflake.com/en/user-guide/account-replication-intro

[Back to accelerated track index](README.md) | [Validation tracker](STATUS.md)
