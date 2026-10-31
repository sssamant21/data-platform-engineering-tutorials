# Page 07 — Snowflake Data Lifecycle Management & Safe Maintenance Automation

**Document ID:** SF-DBRE-OPS-007 | **Owner:** Snowflake DBRE + Data Owner | **Status:** DRAFT — No destructive automation authorized  
**Scope:** Tables, schemas, databases, stages, tasks, streams, Snowpipe, dynamic tables, grants, shares and recovery storage.

> **Non-negotiable:** An apparently unused warehouse, table, schema or database is **only a review candidate**. Zero rows, old creation date, missing recent query history, no direct accesses or high cost do NOT authorize deletion, retention shortening or task suspension.

## 1. Two distinct automation classes

**A. Preapproved retention/lifecycle automation:** Runs only on explicitly scoped, approved data classes with agreed retention, backup/DR and legal requirements. Snowflake does not use Elasticsearch ILM; implement retention through governed data engineering processes, approved Snowflake tasks/policies where supported and change-managed SQL procedures.

**B. Candidate discovery/reporting:** Read-only metadata and telemetry joins identify possible unused tables, abandoned warehouses, stale streams or stages; results create owner-review tickets. **No DROP/DELETE/TRUNCATE/ALTER warehouse commands** are executed by the discovery job.

**C. Operational optimization:** Warehouse auto-suspend, scaling, clustering, storage retention, task scheduling and share control use risk-based approval, performance validation and billing measurement.

## 2. Data/asset ownership register

| Field | Required value |
|---|---|
| Account/region/edition | Object location and supported features |
| Database/schema/object identity and type | Table/stream/task/stage/warehouse; stable ID if available |
| DATA business owner / APP consuming owner | Primary, backup, use case |
| Sensitivity/classification | PHI/PII, tags, masking, row access, classification |
| Source-of-truth and replay strategy | Data correctness and recovery |
| Business retention and legal holds | Approved period and evidence |
| Time Travel/Fail-safe/backup policy | Effective recovery options and expiry |
| Scheduled usage | Jobs, tasks, shares, quarterly/annual reports |
| Access/change history coverage | Time window, gaps, role privileges and data freshness |
| Estimated cost | Active storage, retained clone bytes, warehouses/serverless |
| Candidate and change-ticket state | Review, approvals, expiry, evidence |

**Unknown owner, unknown legal hold, unknown dependency or missing telemetry = HOLD, not deletion.**

## 3. Candidate heuristics are not sufficient evidence

| Candidate signal | Why it is ambiguous |
|---|---|
| Table has zero rows | Required schema or future/batch ingestion target |
| No query observed for X days | ACCOUNT_USAGE delayed/limited and queries can use views/shares/services |
| No recent writes | Monthly/quarterly/annual loads, DR or disaster replay |
| Warehouse suspended for weeks | Dedicated month-end/DR or scheduled workloads |
| Stage unchanged | Replay/recovery/archive requirement |
| Stream apparently unused | Consumer lag/replay or required stream offset |
| Old transient table | Recovery risk if dropped after short Time Travel |
| Clone appears duplicate | Zero-copy clone can share data and have unique downstream dependencies |
| No visible grants | Access via ownership/inherited roles, shares or procedures |
| High storage cost | Time Travel, Fail-safe, clone-retained bytes may persist after DROP |

**X-day window:** set by each approved data class and periodic workload; 90 days is only an example candidate period. Weekly automation must preserve the telemetry coverage and owner attestation, not infer usage from a single query-history window.

## 4. Data governance and safety boundaries

**BLOCK any candidate involving:**
- Security, auditing, finance, regulated/PHI data with unknown retention or legal hold.
- Shared databases, reader accounts, shares/listings or downstream BI dependencies.
- Source-of-truth tables and active ingestion/CDC, task graphs or dynamic-table inputs.
- Unfinished migration/backfill/replay/DR or incident evidence.
- Clone/time-travel/backup sets under active recovery or retention lock.
- Warehouses used for emergency, periodic or compliance jobs.
- Stale/missing Account Usage/ACCESS_HISTORY data or incomplete privilege coverage.
- Objects whose business owner or application dependency has not been confirmed.

**Security/privacy:** do not export row-level records, patient identifiers, full SQL containing PHI or secrets into the cleanup report. Use object identifiers and approved audit metadata.

## 5. Read-only candidate discovery SQL and metadata

~~~~sql
-- Warehouse inventory and state, subject to SHOW privilege
SHOW WAREHOUSES;

-- Database/schema/table inventory
SHOW DATABASES;
SHOW SCHEMAS IN DATABASE EXAMPLE_DB;
SHOW TABLES IN DATABASE EXAMPLE_DB;

-- Historical table size and retained storage (owner review)
SELECT table_catalog, table_schema, table_name, deleted,
       active_bytes, time_travel_bytes, failsafe_bytes,
       retained_for_clone_bytes
FROM SNOWFLAKE.ACCOUNT_USAGE.TABLE_STORAGE_METRICS
ORDER BY active_bytes DESC LIMIT 200;

-- Historic queries for a given warehouse; visibility/latency applies
SELECT warehouse_name, MAX(start_time) AS latest_query,
       COUNT(*) AS observed_query_count
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE start_time >= DATEADD('day', -90, CURRENT_TIMESTAMP())
  AND warehouse_name IS NOT NULL
GROUP BY warehouse_name ORDER BY latest_query;
~~~~

Note: Lack of direct observed query access to a table is not proof of no usage. Views, UDFs, stored procedures, shares and role privileges complicate lineage. ACCOUNT_USAGE.ACCESS_HISTORY requires an eligible edition, carries latency and does not necessarily prove all consumers; use approved inventory and app-owner attestation.

### Weekly read-only discovery logic

~~~~python
def review_candidate(asset, evidence):
    if evidence.legal_hold or evidence.regulated_without_approval:
        return "BLOCKED"
    if evidence.active_pipeline_or_share or evidence.dr_dependency:
        return "BLOCKED"
    if not evidence.owner_known or not evidence.retention_confirmed:
        return "HOLD"
    if not evidence.complete_monitoring_window:
        return "HOLD"
    if not evidence.app_dependency_reviewed:
        return "HOLD"
    if evidence.possibly_unused_or_expensive:
        return "CANDIDATE_REVIEW"
    return "KEEP"

# Read-only report and ticket creation only.
# There is intentionally no DROP/DELETE/TRUNCATE execution path.
~~~~

Pseudocode is architectural, not a runnable Snowflake SDK implementation. An actual collector requires constrained account roles, validated metadata schemas, pagination, and incident-proof audit.

## 6. Approval state machine

| State | Owner | Gate |
|---|---|---|
| DISCOVERED | DBRE automation | Candidate signal plus coverage evidence |
| HOLD / BLOCKED | DBRE | Unclear owner, dependency, compliance or telemetry |
| UNDER REVIEW | DATA + APP | Business/technical necessity confirmed |
| KEEP / REJECTED | DATA | Retention/recovery or application need |
| APPROVED DISPOSITION | DATA + APP | Written approved object and data treatment |
| SEC REVIEW | SEC/Legal | Privacy, legal hold, recovery/retention constraints |
| CHANGE APPROVED | SM | Exact object ID/name and window, rollback plan |
| PRECHECK | DBRE | Revalidate object identity, active dependencies, permissions, recovery |
| EXECUTED | Restricted operator | Exact-scope operation, immutable audit |
| ACCEPTED | APP + DATA | Business function, data reconciliation and cost verified |

Approval expiry or object identity change **invalidates** the earlier authorization. An account or object can be dropped/recreated with the same name; verify exact identity before action.

## 7. Critical destructive-action safeguards

- No wildcard or database-wide DROP without specific approved disaster/migration playbook.
- Do not reduce Time Travel to zero as an incidental cost reduction.
- Never convert permanent objects to transient tables or alter retention without DATA/SEC approval and explicit recovery impact.
- Never detach/cancel a regulated backup retention lock; some locks are irreversible and cannot be disabled by Snowflake Support.
- Do not suspend a warehouse required for an SLA or suspend-immediate from cost monitors without APP/FIN authority.
- Do not delete internal stages, tasks, streams, dynamic tables, pipes, data shares or clone dependents based on absence of recent activity.
- Use authorized isolated clone/backup/Time Travel recovery rehearsals when appropriate; understand that a clone may not provide independent recovery protection.
- Test an exact-object operator behind a separate restricted executor; discovery roles must not have DROP/TRUNCATE/MODIFY privileges.
- Require a second independent approval and documented change record for permanent data loss.

## 8. Retention and table-type controls

| Object type | Operational consideration |
|---|---|
| Permanent table | Time Travel and Fail-safe may be available; additional cost and recovery safety |
| Transient table | Reduced Fail-safe protection (none); short Time Travel constraints |
| Temporary table | Session lifetime; not suitable for durable critical data |
| Dynamic table | Refresh/target lag and source dependencies before any change |
| Streams/tasks | Consumption offsets, task dependencies, scheduled runs and replays |
| Zero-copy clones | Retained clone byte attribution; owner/dependency catalog |
| Backup sets/policies | Separate retention, expiry, possible irreversible lock and legal holds |
| Secure shares/listings | Consumer impact, grants and contractual obligations |

Not every data class should use the same retention length. Object format/edition and compliance constraints take precedence over cost goals.

## 9. Weekly reporting template

| Field | Requirement |
|---|---|
| Account/period and telemetry completeness | Exact source and timestamp |
| Inventory | Warehouses, databases, schemas, tables, tasks, streams, stages |
| Candidates | Object ID, owner, candidate signals and evidence |
| HOLD/BLOCKED | Missing retention, legal hold, share or pipeline dependencies |
| Retention violations | Owner, severity, exception and decision |
| Backup/restore posture | Time Travel, backup sets, latest tested recovery |
| Warehouse/serverless costs | Candidate cost, realized savings only after billing |
| Authorized changes | Exact scope, approvals, executor, ticket and expiry |
| After-change checks | APP queries, freshness, cost, data integrity |
| Open actions | Owner, due date and accepted risk |

### Suggested stakeholder wording

This week's read-only review identified potential warehouse and data-object optimization candidates. No automatic data deletion, retention change or service suspension was performed. All candidates require business ownership, application dependency and recovery assessment before a controlled change request.

## 10. Safety test matrix

| ID | Test | Expected |
|---|---|---|
| T01 | Zero-row table needed for a scheduled job | HOLD |
| T02 | Table used through a view/share | BLOCK |
| T03 | ACCOUNT_USAGE unavailable/stale | HOLD |
| T04 | Object under legal hold | BLOCK |
| T05 | Warehouse idle but used only at month end | KEEP |
| T06 | Stream waiting for consumer | BLOCK |
| T07 | Clone with shared storage and dependencies | BLOCK |
| T08 | Permanent table would become transient | Reject without full review |
| T09 | Backup retention lock exists | BLOCK modification |
| T10 | Approver missing or expired | Abort |
| T11 | Object recreated under same name | Abort |
| T12 | Ambiguous database-wide request | Abort |
| T13 | Time Travel recovery is zero days | Require recovery exception |
| T14 | Approved staging object retirement | Audited exact-scope test |
| T15 | Credit reduction causes freshness/SLO regression | Rollback/change review |

## 11. Milestone implementation phases

- M7-A: Inventory and owner/retention/feature registration.
- M7-B: Read-only telemetry and access-history coverage validation.
- M7-C: Weekly candidate discovery and governance reports.
- M7-D: DATA/APP/SEC classification and approval process.
- M7-E: Stage-test retention policies and required recovery protection.
- M7-F: Stage-test the restricted exact-object executor and all negative safety tests.
- M7-G: Approve change workflow; retain no-delete defaults for unreviewed objects.
- M7-H: Month/quarterly FinOps and data lifecycle review with actual billing.

## 12. Acceptance criteria

- [ ] All critical warehouses, tables, schemas and pipelines have named owners.
- [ ] Retention, legal holds, object type and recoverability documented.
- [ ] Weekly discovery is **read-only** and creates tickets rather than issuing destructive SQL.
- [ ] Missing usage and delayed/limited Account Usage data fail closed.
- [ ] Share, view, stream, task, DR and backup dependencies block disposal.
- [ ] DATA, APP, SEC and SM independent approvals required where applicable.
- [ ] Restricted executor validates exact scope and current object identity.
- [ ] 15 negative/positive safety tests performed in staging.
- [ ] Post-change data correctness, app SLO, freshness and cost confirmed.
- [ ] No production data deletion/retention shortening before operational certification.

**Completion:** Ownership inventory, read-only report, approvals, protected data handling and staging safety suite formally accepted. Documentation is not a production authorization.

## References
- [Time Travel](https://docs.snowflake.com/en/user-guide/data-time-travel)
- [Temporary/transient table behavior](https://docs.snowflake.com/en/user-guide/tables-temp-transient)
- [Backups and retention lock](https://docs.snowflake.com/en/user-guide/backups)
- [TABLE_STORAGE_METRICS](https://docs.snowflake.com/en/sql-reference/account-usage/table_storage_metrics)
- [ACCOUNT_USAGE / ACCESS_HISTORY](https://docs.snowflake.com/en/sql-reference/account-usage)
