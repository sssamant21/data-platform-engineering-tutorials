# Snowflake DBRE Responsibility — Validation Register

**Status:** Documentation drafted, **NOT CERTIFIED FOR PRODUCTION**  
**Scope:** All 7 Snowflake DBRE operating guides  
**Latest publication date:** 2026-10-31  
**Owner:** Snowflake DBRE

GitHub commits and read-only syntax review do not prove SQL results, privileges, SLO, cost or DR in a live Snowflake account.

## Milestone status

| Milestone | Documentation | Live/staging validation | Stakeholder sign-off |
|---|---|---|---|
| 01 Ownership and RACI | Drafted | Account/edition and owner inventory pending | Pending |
| 02 Operating cadence | Drafted | Staging SQL/roles, daily/weekly pilot pending | Pending |
| 03 Monitoring, alerts and SLO | Drafted | ACCOUNT_USAGE, Information Schema, SLO and routing pending | Pending |
| 04 Incident runbooks | Drafted | Scenario tabletop and incident escalation pending | Pending |
| 05 Capacity and FinOps | Drafted | Metering/storage reconcile, warehouse benchmark pending | Pending |
| 06 Backup, DR, restore | Drafted | Backup/Time Travel/replication and recovery drill pending | Pending |
| 07 Data lifecycle/maintenance | Drafted | Read-only collector, owner governance and safety tests pending | Pending |

## Validation workstreams

| ID | Workstream | Required proof | Status |
|---|---|---|---|
| V01 | Markdown structure and links | All local links resolve; rendering headings and SQL blocks are correct | Pending systematic audit |
| V02 | SQL syntax & edition support | SQL checked on exact Snowflake account/edition/role | Pending |
| V03 | Privilege and security model | Least-privilege monitoring roles; no PHI/query-text leakage | Pending |
| V04 | SLO and monitoring | Near-current source, delayed Account Usage, warehouse load and pipeline signals tested | Pending |
| V05 | FinOps and growth | Compute/serverless/storage/cost reconcile against billing and 30/60/90-day forecast | Pending |
| V06 | Recovery and lifecycle | Backup/Time Travel/DR exercise plus read-only cleanup negative tests | Pending |

## Technical QA checklist

- [ ] Inventory account regions, editions, warehouse settings and platform owners.
- [ ] Check all SQL names, views, columns and privileges against current Snowflake account.
- [ ] Verify the monitoring role can read required ACCOUNT_USAGE, Information Schema and backup metadata.
- [ ] Validate ACCOUNT_USAGE latency, missing-row handling and source freshness.
- [ ] Check live QUERY_HISTORY and warehouse queue data separate from APP p95/p99 client SLIs.
- [ ] Validate task history, pipe usage, dynamic table freshness and alert history on actual workload.
- [ ] Prevent PHI and secrets in metric labels, logs and reports.
- [ ] Reconcile Snowflake warehouse, serverless, cloud-services and billed credits with FIN.
- [ ] Validate TABLE_STORAGE_METRICS, storage history, Time Travel, Fail-safe, clone-retained numbers.
- [ ] Review warehouse right-sizing under peak concurrency and test rollback.
- [ ] Verify Time Travel and table-type retention; test isolated history recovery.
- [ ] Verify backup sets/policies and locked/held backup governance, privileges, scheduled completion and restore.
- [ ] Verify Fail-safe best-effort role of Snowflake Support and escalation paths.
- [ ] Confirm replication/failover feature and edition availability and object coverage.
- [ ] Run a staged DR simulation and measure RPO/RTO with APP/DATA acceptance.
- [ ] Run candidate discovery with strictly read-only roles and confirm no executable deletion path.
- [ ] Run lifecycle protection tests for shares, clones, streams, tasks, retention locks and legal holds.
- [ ] Review RACI and every change approval gate with DBRE, APP, DATA, PLT, SEC, FIN and SM.
- [ ] Validate local README/Confluence links and final publication index.

## Evidence register

| Validation | Account/environment | Role and edition | Date UTC | Owner | Evidence URL | Result |
|---|---|---|---|---|---|---|
| SQL view/column/privilege tests | TBD | TBD | TBD | TBD | TBD | Pending |
| SLO source and alerts | TBD | TBD | TBD | TBD | TBD | Pending |
| Incident tabletop | TBD | TBD | TBD | TBD | TBD | Pending |
| Billing and growth reconciliation | TBD | TBD | TBD | TBD | TBD | Pending |
| Recovery, backup and DR drill | TBD | TBD | TBD | TBD | TBD | Pending |
| Lifecycle safety negative tests | TBD | TBD | TBD | TBD | TBD | Pending |
| Stakeholder RACI approvals | TBD | TBD | TBD | TBD | TBD | Pending |

## Certification rule

Do not mark any milestone **Approved/Production Ready** until its relevant Snowflake edition, SQL, privileges, safety controls, alert routing, application integration, backup/DR evidence, owner and formal sign-off pass. The documentation may be copied to Confluence as a **draft** while validation proceeds.
