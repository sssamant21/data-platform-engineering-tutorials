# V06 — PostgreSQL DR Exercise Acceptance Matrix

**Status:** READY FOR STAGING PLAN REVIEW — **NOT RUN / NOT CERTIFIED**  
**Scope:** PostgreSQL 14–18 self-managed and AWS RDS/Aurora, Azure Flexible Server, Google Cloud SQL  
**Safeguards:** Synthetic non-PHI data; isolated destination; reviewed rollback; named incident commander/DBRE/APP/DATA approvers. No destructive operations authorized by this checklist.

## 1. Mandatory preparation gates

| Gate | Evidence |
|---|---|
| P01 | Named source and isolated restore target, exact database engine major/minor, role, cloud region and identity |
| P02 | Signed target RPO/RTO, business service owner, test data classification and test window |
| P03 | Complete backup/version/retention and WAL/timeline chain or provider recoverable-point metadata |
| P04 | Fencing actuator design and independent verification, no production network/write path to test target |
| P05 | Dependencies: client endpoints, TLS/SSO/roles, connection pool, extensions, CDC/subscribers, jobs |
| P06 | Change/incident approval with safe abort, restore location, rollback/failback and evidence destination |

**No-go** if source identity differs, data isolation cannot be proven, restored data would overwrite production, backup/WAL is incomplete or primary fencing cannot be independently verified.

## 2. Per-scenario acceptance matrix

| Test | Exercise in controlled staging | Independent PASS criteria | Current |
|---|---|---|---|
| DR01 | Restore synthetic logical dump in isolated DB | Schemas, constraints, grants, markers, checksums and APP read/write pass | NOT_RUN |
| DR02 | Verify physical full backup and restore | pg_verifybackup compatible format, PostgreSQL starts and query/roles/checks pass | NOT_RUN |
| DR03 | Recover to time before known synthetic bad transaction | Complete WAL/history, verified pre-incident marker present, post-target marker absent | NOT_RUN |
| DR04 | Missing WAL segment or archive permission scenario | Restore fails closed, detection and recovery gap escalated; never silently skip missing WAL | NOT_RUN |
| DR05 | Standby lag / WAL receiver disconnect | Receive vs replay LSN and latency, RPO risk recorded; idle timestamp not misused | NOT_RUN |
| DR06 | Primary failure and approved promotion | Old writer independently fenced; new writer alone; client routing and APP/DATA accepted | NOT_RUN |
| DR07 | Former primary returns unexpectedly | Does not rejoin as writable; approved rebuild/rewind and no divergent writes | NOT_RUN |
| DR08 | Managed PITR to newly created instance/server/cluster | Provider restore-point verified, new destination isolated, network/HA/APP reconfiguration accepted | NOT_RUN |
| DR09 | Region outage / offsite recovery | Off-region backup/data access actually tested or documented as tabletop only; dependencies accepted | NOT_RUN |
| DR10 | Logical replication/CDC recovery | Consumer/slot owner approves; source marker count, deduplication, no missing events | NOT_RUN |
| DR11 | Large dataset restore under realistic capacity | Measured provisioning, replay, data checks and business RTO target; no disk exhaustion | NOT_RUN |
| DR12 | Failback with writes since promotion | Old primary fenced until rebuilt, correct timeline, zero dual-write window, APP/DATA reconcile | NOT_RUN |

**Allowed recorded state:** NOT_RUN, BLOCKED, TABLETOP_PASS, STAGING_PASS, STAGING_FAIL. A TABLETOP_PASS is NOT a restore/failover runtime PASS. To certify a given runtime scenario, require STAGING_PASS and signed evidence.

## 3. Checkpoints and UTC timestamps

| Field | Required record |
|---|---|
| Test/incident ID, source, target and UUID/instance identity | |
| PostgreSQL version/provider/region and backup ID | |
| Backup completion and available archive/WAL history | |
| Latest proven recoverable *committed business* marker and UTC timestamp | |
| T_failure (agreed incident start) | |
| T_authorized / T_fenced / T_restore_started | |
| T_database_ready / T_replication_reconciled | |
| T_endpoint_changed / T_app_data_accepted | |
| Approved RPO, observed worst-case data-loss window | |
| Approved RTO, observed end-to-end time | |
| Physical/managed provider latest restorable time | |
| Independent evidence: fenced old writer and only one production writer | |
| User auth, grants, TLS, network, connection pools and alerts | |
| DATA transaction/CDC consistency and APP p95/p99/read-write checks | |
| Abort/rollback/failback, issues and attached logs | |
| DBRE lead, APP and DATA review, SEC/PLT where required, SM ticket | |

**RPO measured:** difference between incident start and latest **proven** business commit/marker recoverable after restore; if not provable, record UNKNOWN/NO-GO. **RTO measured:** incident start to actual APP/DATA business acceptance including endpoint switch and replay. Store UTC timestamps and authoritative clock source; a query returning pg_is_in_recovery=false does NOT prove old primary was fenced.

## 4. Failure triggers and safety gates

| Trigger | Required response |
|---|---|
| Old primary can still accept writes | ABORT promotion/cutover, incident escalation |
| Unknown/mismatched target identity or credentials | ABORT restore |
| WAL segment/history missing or incomplete base backup | ABORT PITR; preserve evidence |
| CDC/source watermark disagreement | Do not claim RPO; DATA reconciliation |
| Restore succeeds but app cannot connect or authenticate | RTO continues; APP/PLT repair |
| Test uses real PHI or affects business services | ABORT, SEC/incident response |
| Cannot rebuild/rewind source safely | Keep fenced; rebootstrap with approved plan |
| No independent reviewer or change authority | Not certified |

## 5. Provider-specific restore matrix

| Platform | Recovery object | Key post-restore validations |
|---|---|---|
| Self-managed | Isolated full cluster from physical base/WAL, or logical DB | Correct major version, WAL history, roles/tablespaces/config, host storage, fenced writer |
| AWS RDS PostgreSQL | New DB instance | IAM/security group/subnets/parameter group, backups, HA, DNS and app data |
| Amazon Aurora PostgreSQL | New DB cluster | Writer/reader instances, endpoints, security/parameter groups and replica topology |
| Azure PostgreSQL Flexible Server | New server; HA not automatically present | Public/private networking restrictions, firewall, configuration, HA re-enable, APP endpoints |
| Google Cloud SQL PostgreSQL | New instance for PITR | PITR enabled/earliest/latest window, IAM, networking, edition and read replica/HA |

## 6. Sign-off and result register

| Test | State | UTC date | Evidence URL | DBRE reviewer | APP/DATA sign-off | Issue |
|---|---|---|---|---|---|---|
| DR01–DR12 | NOT_RUN | TBD | TBD | TBD | TBD | TBD |

**V06 readiness verdict:** NO RUNTIME DR CERTIFICATION. The matrix is a plan and evidence contract only. Do not populate PASS values without actual witnessed results.
