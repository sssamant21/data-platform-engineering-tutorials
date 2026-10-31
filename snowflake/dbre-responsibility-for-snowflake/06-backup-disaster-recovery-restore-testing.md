# Page 06 — Snowflake Backup, Disaster Recovery & Recovery Validation

**Document ID:** SF-DBRE-OPS-006 | **Owner:** Snowflake DBRE | **Status:** DRAFT — Not recovery-certified  
**Dependencies:** Edition/feature availability, account/region/cloud, database types, supported objects, SEC/DATA-approved recovery objectives.

> **Safety:** Time Travel, Fail-safe, backups, cloning and replication are **different** mechanisms. A supported feature does not prove recovery readiness until it has been configured, tested and evidenced for the account, objects and data tier. All create, restore, failover, or retention-lock changes require change approval and are NOT performed by publishing this runbook.

## 1. Recovery mechanisms and limits

| Mechanism | Purpose | Critical limitations |
|---|---|---|
| Time Travel | Query, clone or UNDROP historical data within configured retention | Retention depends on table type/edition/parameter; disabled if zero |
| Fail-safe | Snowflake-managed emergency best-effort recovery after Time Travel | Not self-service, seven-day window for eligible permanent data, support case; may take hours/days |
| Zero-copy CLONE | Efficient point-in-time logical copy in same account/region as supported | Shares underlying storage initially; clones are not independent off-region backups; retention/permissions apply |
| **Snowflake backup sets/policies** | Scheduled/manual recoverable backups of supported tables/schemas/databases | Check object/edition support, storage cost, policy privileges, expiry, actual recovery testing |
| Replication groups | Read-only copies for approved objects across accounts/regions | Scheduled/asynchronous refresh; no automatic writable promotion |
| Failover groups / client redirect | Business continuity with controlled promotion and endpoint routing | Business Critical or higher required for failover, feature-specific eligibility and dependencies |
| Upstream re-ingestion/rebuild | Reconstruct derived analytics from retained source | Depends on source log, transformation code, keys, data integrity and RTO |

**Snowflake native backup sets are a distinct capability** from Time Travel. Policies can schedule backups and govern expiry. Some editions support additional retention locks/legal holds. Retention locks can be irreversible; **never enable an irreversible lock without Security/Legal and cost approval**.

### Edition and feature qualification

- Time Travel commonly has 1-day retention by default; extended retention up to 90 days for eligible permanent objects requires Enterprise or higher. Transient and temporary objects have stricter limits.
- Permanent table Fail-safe generally provides seven additional days after Time Travel; transient/temporary tables do **not** have Fail-safe.
- Backup sets/policies are available across Snowflake editions; retention locks and legal holds require Business Critical or higher. Confirm current account feature availability, supported backup subject and privileges.
- Database/share replication has broader edition availability; **failover groups and account-object replication** require Business Critical or higher.
- Not all account objects or workload features replicate. Validate tasks, dynamic tables, shares, security integrations, external stages, network and identity configurations independently.

## 2. Roles and authorization

| Decision/action | Accountable | Responsible |
|---|---|---|
| Business recovery priority and data completeness | DATA / APP service owner | APP, DATA |
| Time Travel configuration and tested restore operations | DBRE | DBRE, DATA |
| Backup policy/set and scheduled backup monitoring | DBRE | DBRE, DATA, SEC |
| Backup retention lock and legal hold approval | SEC + legal/business authority | SEC, DATA |
| Replication/failover strategy and group readiness | DBRE | DBRE, PLT, DATA |
| DR business RPO/RTO and client recovery acceptance | APP service owner | APP, DATA, DBRE |
| Disaster incident command/cutover authorization | SM | DBRE, APP, DATA, PLT |
| Platform-internal Fail-safe recovery | Snowflake Support | Vendor; DBRE coordinates business case |

Assign a primary/backup DR owner for each Snowflake account, failover group, backup set, source pipeline and application endpoint.

## 3. Recovery inventory per workload

| Required attribute | Example / field |
|---|---|
| Account/region/edition/cloud | Explicit source and target |
| Database/schema/table type | Permanent, transient, temporary, dynamic, Iceberg/hybrid where applicable |
| Effective Time Travel retention | Days, inherited parameters and minimum account retention |
| Backup set/policy | Scope, schedule, expiry, lock/hold, status |
| Replication/failover group | Included object list and last successful refresh |
| RPO/RTO | Data Owner + APP approved |
| Source of truth | Upstream system, ingestion/replay offsets and lineage |
| Account objects | Users/roles/warehouses/integrations/network policies included in DR |
| Security controls | Key recovery, identity provider, grants and auditing |
| Last exercise | Recoverable timestamp, measured RTO, evidence URL |
| Uncovered features | Explicit exception/mitigation and owner |

### Read-only inventory examples

~~~~sql
-- Object type and retention settings (review privileges)
SHOW DATABASES;
SHOW SCHEMAS IN DATABASE EXAMPLE_DB;
SHOW PARAMETERS LIKE 'DATA_RETENTION_TIME_IN_DAYS' IN ACCOUNT;
SHOW TABLES IN SCHEMA EXAMPLE_DB.EXAMPLE_SCHEMA;

-- If enabled in the account, inspect backup catalog
SHOW BACKUP POLICIES;
SHOW BACKUP SETS;

-- Replication/failover groups: requires appropriate privileges/edition
SHOW REPLICATION GROUPS;
SHOW FAILOVER GROUPS;
~~~~

SHOW commands display only objects visible to the active role; lack of rows is not proof that no protected object exists.

## 4. Backup-set design and governance

Snowflake supports policies attached to backup sets. An approved backup policy can define backup **schedule** and **expiration**. Retention locks are not general reversible on/off controls. Retention lock, legal hold and expiry changes must go through change/recovery governance and cost modeling.

### Example authorized staging backup policy — no retention lock

~~~~sql
-- CHANGE-CONTROLLED STAGING EXAMPLE: DO NOT RUN DIRECTLY IN PRODUCTION
CREATE BACKUP POLICY staging_hourly_policy
  SCHEDULE = '60 MINUTE'
  EXPIRE_AFTER_DAYS = 7
  COMMENT = 'staging-only recovery testing';

CREATE BACKUP SET staging_table_backups
  FOR TABLE STAGING_DB.DBRE_LAB.RECOVERY_TEST_TABLE
  WITH BACKUP POLICY staging_hourly_policy;

-- READ ONLY inventory after authorized creation:
SHOW BACKUPS IN BACKUP SET staging_table_backups;
~~~~

Prerequisites: backup policy and backup set created in the intended schema context, required CREATE/APPLY and SELECT/USAGE privileges, and the source test table exists. Backup compatibility/restore behavior and required compute costs must be tested before adoption.

### Backup operational checks

- Scheduled backup is actually created; check BACKUP_OPERATION_HISTORY and backup set object status, not just policy existence.
- Latest usable backup age is within the business objective, and permissions to restore have been tested.
- Coverage includes every required data object; feature-specific exclusions are documented.
- Storage growth, backup expiry and retention locks/holds follow approved data policies.
- Credentials, encryption/audit and data classification are reviewed by SEC.
- Unauthorized backup deletion/expiry action is blocked; recovery is rehearsed with a sanitized staging object.

**Fail-safe is not a substitute for backups:** it is Snowflake Support best-effort and is intended for extraordinary failure rather than routine user restoration.

## 5. Time Travel recovery and isolated test

With Time Travel active for the supported object, a data owner can investigate a known bad statement timestamp/query ID and preserve a pre-change version. The safe pattern is **inspect history → create authorized isolated copy in staging → validate business records → approve targeted recovery**.

~~~~sql
-- READ ONLY: inspect effective retention and table metadata
SHOW PARAMETERS LIKE 'DATA_RETENTION_TIME_IN_DAYS'
  IN TABLE STAGING_DB.DBRE_LAB.RECOVERY_TEST_TABLE;

-- READ ONLY: compare historical row count using Time Travel.
-- Must be within retention; use an approved timestamp and dataset.
SELECT COUNT(*) AS historical_rows
FROM STAGING_DB.DBRE_LAB.RECOVERY_TEST_TABLE
  AT (TIMESTAMP => '2026-10-30 12:00:00'::TIMESTAMP_LTZ);
~~~~

**Do not** run UNDROP, CREATE OR REPLACE, DELETE, DROP or a production clone as a diagnosis shortcut. Restoring a dropped table can conflict with an identically named new table; resolve naming, dependencies and grants with DATA/APP in an approved procedure. A retention period of zero may make self-service recovery impossible.

### Recovery test acceptance

- Correct object, time boundary and retention verified.
- Restored/historical data counts and sample keys reconcile to business source.
- Privileges, masking/row-access policies and client queries remain correct.
- Data quality checks pass and change/incident timestamps preserved.
- No unapproved overwrite or collision of an active table/schema.

## 6. Cross-region/cross-cloud disaster recovery

**Replication and failover are distinct capabilities.** A secondary replication group is generally read-only. A failover group in an eligible Business Critical+ account supports authorized promotion, subject to all object coverage and target prerequisites.

### DR design sequence

1. List critical source databases and necessary account objects: users, roles, warehouses, network/integrations, shares and any features not supported for replication.
2. Confirm edition, region-group restrictions, replication group/failover group privileges, target account and key management.
3. Create authorized group(s) and refresh secondary via approved configuration; record exact allowlist.
4. Ensure read-only secondary refresh status and lag is monitored; determine worst-case recovery-point exposure.
5. Test APP client connections, account identifiers, client redirect (where supported), credential and network policy access.
6. Test scheduled/manual failover in staging with a defined **single-writer** plan and no active conflicting ingestion.
7. Measure source isolation/fencing, promotion, replay, pipeline recovery, read/write validation and failback with data reconciliation.
8. Record remaining unsupported objects, source lag, cost of replication/network/storage and approval record.

Snowflake replication is asynchronous. A recent target refresh does not guarantee that every last source write has arrived. RPO must use confirmed secondary data watermark and tested lag characteristics.

**Promotion is a change-controlled disaster recovery operation**; do not promote a secondary just because a dashboard is red.

## 7. RPO, RTO and DR evidence

- **T_failure:** agreed business outage start.
- **T_recoverable:** newest proven recoverable business-data watermark (from Time Travel, completed backup, replication or source replay).
- **Observed data-loss interval:** T_failure − T_recoverable (state uncertainty if watermark cannot be verified).
- **T_service_recovered:** APP/DATA acceptance of authentication, queries, writes, fresh pipelines and endpoint function.
- **Observed RTO:** T_service_recovered − T_failure.

### Example only

Approved RPO = 1 hour; RTO = 4 hours. Incident 12:00 UTC, valid recovered watermark 11:35 UTC, APP sign-off 14:30 UTC → observed RPO window **25 minutes** and RTO **2 hours 30 minutes**. PASS only if data completeness, access and workload SLOs also pass.

## 8. DR test matrix

| Test ID | Scenario | Required evidence |
|---|---|---|
| DR01 | Time Travel update/recovery in isolated staging | Historical row/keys and permissions |
| DR02 | UNDROP eligibility check and recovery drill | Retention and object-name collision safety |
| DR03 | Backup set/policy scheduled backup | BACKUP_OPERATION_HISTORY and backup restore |
| DR04 | Backup expired/missing permission | Alert and safe failure handling |
| DR05 | Retention lock/legal hold design review | No irreversible setting without approval |
| DR06 | Secondary replication refresh lag | RPO exposure and stale watermark |
| DR07 | Cross-region failover tabletop | Editions, permissions and activation |
| DR08 | Full compatible account-object failover drill | Identity/network/warehouse/APP validation |
| DR09 | Source pipeline replay | Correctness and idempotence |
| DR10 | Time Travel expiry / Fail-safe escalation | Support workflow and expected uncertainty |
| DR11 | Regional connection failover | Client endpoint and app restore time |
| DR12 | Failback with new writes | Data reconciliation and single-writer proof |

No production destructive failure injection without separate approval.

## 9. Critical alerting and operational cadence

| Signal | Severity consideration | Owner |
|---|---|---|
| Latest usable backup older than approved policy | RPO risk | DBRE |
| Backup creation failed / backup set missing | RPO risk | DBRE / SEC |
| Backup retention lock drift | Compliance risk | SEC |
| Secondary refresh age/lag exceeds objective | Critical business continuity risk | DBRE / DATA |
| No defined recovery strategy for critical table | Governance risk | DATA / DBRE |
| Last DR test stale or failed | Reliability improvement required | DBRE |
| Failover target lacking necessary account objects | No-go for failover | PLT / DBRE |
| Time Travel retention shortened unexpectedly | Data-loss risk | SEC / DATA |

Cadence proposal: daily backup/replication checks; monthly isolated object restore; quarterly DR tabletop; periodic end-to-end failover test based on criticality. Approve and document actual cadence.

## 10. Incident authorization and recovery checklist

1. Incident commander, scope, service tier, approved RPO/RTO and business owners identified.
2. Source and target accounts, region, edition and object capabilities verified.
3. Determine precise recovery source and retention validity.
4. Confirm data completeness, current writes and possible lost transactions.
5. Decide isolation versus live restore/cutover and rollback/failback path.
6. SEC validates grants, encryption, key and sensitive table policies.
7. PLT validates endpoints, integrations and network/auth dependencies.
8. APP/DATA approves functional validation criteria and source reconciliation.
9. SM authorizes production recovery action and communicates.
10. Record timestamps, Snowflake Support cases, approved SQL execution, data-loss window, APP final acceptance and RCA actions.

## 11. Monthly reporting template

| Field | Evidence |
|---|---|
| Account/region/edition and DR tier | |
| Covered databases/tables and exclusions | |
| Time Travel retention and table type | |
| Backup set/policy and last successful completion | |
| Last restore drill, result and runbook link | |
| Primary/secondary group, latest refresh and lag | |
| Approved RPO/RTO versus observed | |
| Access/feature-state/identity dependency | |
| Uncovered objects, owner and action | |
| Data Owner and DBRE approval | |

## 12. Milestone acceptance

- [ ] All production critical datasets have a signed recovery method and RPO/RTO.
- [ ] Time Travel type/edition/retention fully inventoried.
- [ ] Backup policy/set support verified and scheduled completion monitored.
- [ ] Irreversible retention lock/legal hold requires explicit SEC/Legal authorization.
- [ ] Time Travel or backup restore passes isolated data/permission tests.
- [ ] Fail-safe escalation documented as best-effort Snowflake Support recovery.
- [ ] Region/account replication edition support, object coverage and lag validated.
- [ ] DR tabletop and appropriate failover exercise measured end-to-end.
- [ ] APP and DATA certify business service recovery and data completeness.
- [ ] Rollback/failback, retention and audit evidence accepted.

**Completion:** Measured, witnessed recovery drills and required stakeholder sign-off. Draft publication does not certify RPO/RTO.

## References
- [Snowflake Backups for disaster recovery and immutable storage](https://docs.snowflake.com/en/user-guide/backups)
- [CREATE BACKUP POLICY and edition/retention restrictions](https://docs.snowflake.com/en/sql-reference/sql/create-backup-policy)
- [Time Travel](https://docs.snowflake.com/en/user-guide/data-time-travel)
- [Fail-safe](https://docs.snowflake.com/en/user-guide/data-failsafe)
- [Replicating and failing over accounts](https://docs.snowflake.com/en/user-guide/account-replication-intro)
- [Failover groups](https://docs.snowflake.com/en/user-guide/account-replication-failover-failback)
