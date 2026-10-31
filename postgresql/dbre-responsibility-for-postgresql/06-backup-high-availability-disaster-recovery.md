# Page 06 — PostgreSQL Backup, High Availability, Disaster Recovery & Restore Testing

**Document ID:** PG-DBRE-OPS-006 | **Owner:** PostgreSQL DBRE  
**Status:** DRAFT — NOT CERTIFIED FOR PRODUCTION  
**Platforms:** Self-managed PostgreSQL; AWS RDS/Aurora, Azure Flexible Server, Google Cloud SQL  
**Stakeholders:** DBRE, APP, DATA, PLT, SEC, Incident and Change Management  
**Cadence:** Daily backup/replication checks; monthly controlled restore; quarterly DR rehearsal

> **Safety:** Promotion, fencing, pg_rewind, replication-slot changes, PITR, data-directory replacement and client cutover are high-risk. None is authorized by publishing this document. No executable promotion or destructive restore command is included.

## 1. Purpose and objectives

**RPO** is the maximum acceptable loss of committed business data, measured from the incident boundary to a demonstrated recoverable commit/watermark. **RTO** is time from an agreed outage start to full, business-accepted read/write functionality. A successful backup, enabled HA, or read replica alone does not prove these objectives.

| Service tier | Candidate RPO | Candidate RTO | Evidence |
|---|---|---|---|
| Critical transactional | 5 min | 1 hr | Fencing, replay, HA and end-to-end measured restoration |
| Important application | 1 hr | 4 hr | Recoverable base/WAL and APP validation |
| Rebuildable/reporting | 24 hr | 24 hr | Tested backup/replay and completeness |

Examples are not organization-approved targets; owners must sign actual requirements.

## 2. Ownership and RACI

| Activity | Accountable | Responsible and consulted |
|---|---|---|
| Backup strategy/retention and technical test | DBRE | DBRE, PLT, APP/DATA |
| Backup storage, encryption/IAM and offsite access | PLT | PLT, DBRE, SEC |
| Data priority/retention and tolerated loss | DATA | DATA, APP, SEC |
| Application RPO/RTO and recovery acceptance | APP service owner | APP, DATA, DBRE |
| Replica/slot/WAL/archive technical design | DBRE | DBRE, PLT |
| Independent primary fencing infrastructure | PLT | PLT, DBRE, incident commander |
| Failover and recovery execution | DBRE | DBRE, PLT |
| Incident decision/production cutover | Incident Management | DBRE, APP, DATA, PLT |
| Recovery security, credentials and legal compliance | SEC | SEC, PLT, DBRE |

An approved HA topology register must list the authoritative primary, standbys, replication mode, slots and downstream owners, quorum/fencing mechanism, client endpoint, alternative recovery plan, RPO/RTO and on-call contacts.

## 3. Compare backup and recovery methods

| Method | Purpose | Limit |
|---|---|---|
| pg_dump/pg_dumpall | Logical database/roles/data restoration | Not a physical base backup; cannot participate in WAL replay for cluster PITR |
| pg_basebackup | Physical base backup | Must preserve all needed WAL, supported exact major-version restore |
| Base backup + continuous WAL archive | Cluster point-in-time recovery | Continuous WAL/timeline chain; validate restore from actual archive |
| PostgreSQL 17+ incremental physical backup | More efficient changed-block backup | Requires backup manifest/WAL summaries and pg_combinebackup dependencies |
| Read replica / standby | Read scale or HA | Does not prevent bad writes/deletes from propagating; not a backup |
| Managed backup/PITR | Provider-supported service recovery | Retention, latest restorable point, new instance/network permissions differ |
| Filesystem snapshot | Component of supported backup design | Do not assume a live filesystem copy without WAL consistency is restorable |

**Important version note:** PostgreSQL 18 is current in October 2026, PostgreSQL 19 is still prerelease, and PostgreSQL 14 reaches EOL November 12, 2026. Use exact installed version and provider support information.

## 4. Mandatory recovery inventory

| Attribute | Requirement |
|---|---|
| Instance, region, version, provider and backup owner | Exact identifiers |
| Logical/physical/provider backup type, schedule and expiry | Signed retention |
| Latest complete base snapshot and WAL coverage | File/backup ID, timestamps |
| Last proven recoverable commit/LSN | RPO evidence |
| Archive storage location, encryption, IAM, offsite protection | PLT/SEC validation |
| Primary/replica/slot architecture and consumers | Exact owners |
| Node configs, extensions, roles, TLS keys, pg_hba or managed equivalents | Secure secondary recovery procedure |
| Last restore test, RPO/RTO and APP/DATA acceptance | Drill ticket |
| Maintenance/exceptions/legal hold | Risk owner |

## 5. Read-only inspection SQL — self-managed reference

~~~~sql
SELECT current_setting('server_version') AS version,
       pg_is_in_recovery() AS standby;

SELECT current_setting('wal_level') AS wal_level,
       current_setting('archive_mode') AS archive_mode,
       current_setting('max_wal_size') AS max_wal_size;

SELECT archived_count, last_archived_wal, last_archived_time,
       failed_count, last_failed_wal, last_failed_time, stats_reset
FROM pg_stat_archiver;

SELECT application_name, state, sync_state,
       sent_lsn, write_lsn, flush_lsn, replay_lsn,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;

SELECT slot_name, slot_type, active, restart_lsn,
       confirmed_flush_lsn
FROM pg_replication_slots;
~~~~

Use authorized monitoring permissions. pg_stat_archiver may be irrelevant to cloud-managed backup/PITR; counters can reset and cannot prove WAL chain integrity. On standby, primary-only replication sender stats may be empty. Large lag intervals can mislead on idle systems.

### Backup integrity and restore requirements

A successful pg_verifybackup manifest check is a useful integrity step for compatible physical backups but cannot prove WAL replay or APP restore success. External tools (pgBackRest, Barman) require their own chain validation and retention controls. Record last successful backup **completion**, latest recoverable point and failed/missing WAL segments.

## 6. Self-managed physical backup and PITR process — staging only

1. Approve backup policy, frequency, encryption, separate storage location and needed WAL retention.
2. Confirm WAL archival mode/command/library, network and IAM/filesystem permissions, archive integrity and backup role.
3. Generate a qualified base backup with pg_basebackup or approved backup manager and preserve required WAL/history and tablespaces.
4. Validate backup manifests using pg_verifybackup where available and applicable.
5. Create an **isolated restore target** with compatible PostgreSQL major version, secure server config and no production endpoint.
6. Restore the base and archived WAL chain, select a known synthetic recovery target timestamp/LSN and let PostgreSQL replay.
7. Inspect target timeline, recovered tables, business keys, transactions, permissions and application read/write tests.
8. Record UTC duration from failure simulation to APP acceptance and compare RPO/RTO.
9. Retain evidence and clean up only after approval.

Do not restore physical data files onto an active production data directory. Do not manually delete live pg_wal content to free disk. Do not confuse pg_dump with cluster PITR.

Safe offline utility version checks:

~~~~bash
pg_basebackup --version
pg_verifybackup --version
pg_restore --version
psql --version
~~~~

## 7. Failover, fencing and single-writer requirements

**Highest-risk failure:** split brain (two simultaneously writable primaries) or promotion of a lagging standby with unexpected lost commits.

### Mandatory promotion authorization gate

- [ ] Named incident commander and DBRE technical lead.
- [ ] **Independent fencing**: old primary cannot accept writes; evidence retained.
- [ ] Source and standby identities, recovery timeline and LSNs recorded.
- [ ] Valid quorum/leader orchestration and candidate promotion order.
- [ ] DATA and APP accept known or uncertain missing commits against RPO.
- [ ] Endpoint, DNS, load balancer, pooler and CDC routing ready.
- [ ] Replay catch-up and post-promotion recovery plan assessed.
- [ ] Old primary return, rewind/rebuild and failback procedures approved.
- [ ] Emergency change and communication recorded.

### Post-promotion checks

- Exactly one authoritative writable primary, and old primary independently fenced.
- Correct timeline and standby/slot/replication state.
- APP client endpoints/poolers point to the new primary and reject stale writers.
- DATA reconciles committed business transactions and CDC offsets.
- Backup/WAL archive coverage resumed and p95/p99 application SLO restored.
- RTO and conservative RPO window measured with UTC evidence.

**pg_rewind** can require data checksums or wal_log_hints and sufficient WAL. Never run against a running/incorrect target or assume diverged timelines can be merged without data loss. Promotion and failback are not single-step reversible actions.

## 8. Managed-cloud backup/PITR/HA matrix

| Service | Supported pattern | Critical distinction |
|---|---|---|
| AWS RDS PostgreSQL | Automated backups and transaction logs for PITR | Check LatestRestorableTime and backup retention; PITR creates a **new DB instance** |
| Amazon Aurora PostgreSQL | Cluster-native backup/restore, writer/reader instance topology | Aurora cluster storage, endpoints and failover differ from regular RDS |
| Azure PostgreSQL Flexible Server | Managed server backups/logs and PITR | Restore creates **new server**; restored server may need HA and firewall/network reconfiguration |
| Google Cloud SQL for PostgreSQL | Automated backup and PITR when enabled; HA option | PITR creates a **new instance**; enablement/default depends on edition and provisioning mode |
| Self-managed | Physical base/WAL and/or approved operator tooling | DBRE/PLT responsible for OS/filesystem, backups, WAL and fencing |

Managed services are not full OS/root environments. Do not reuse self-managed file-level restore commands in RDS/Aurora/Azure/Cloud SQL. Provider restrictions on cross-region backups, private-network restore, extensions and HA settings must be tested.

## 9. Disaster recovery test matrix

| ID | Scenario | Evidence |
|---|---|---|
| DR01 | Logical restore of synthetic data | Schema, roles and APP verification |
| DR02 | Full base backup and manifest check | Backup chain integrity and restore |
| DR03 | PITR before a synthetic bad transaction | Correct recovered commit and timeline |
| DR04 | Missing archived WAL | Alert, stop and recovery gap response |
| DR05 | Standby replication lag | RPO warning and replay rate |
| DR06 | Primary failure and fencing | Independent fenced old writer |
| DR07 | Old primary returns | No dual writer; approved rebuild/rewind |
| DR08 | Managed PITR to isolated instance | Provider restore, network/auth, APP validation |
| DR09 | Regional outage tabletop | Secondary region/backup viability |
| DR10 | Logical CDC replay and slot dependency | No missing/duplicate business events |
| DR11 | Large workload restore | Disk, IO, provisioning and RTO |
| DR12 | Failback | Single writer, APP success and DATA reconciliation |

Use sanitized staging data and independent observers. Do not simulate destructive failure in production without a separately approved exercise.

## 10. Measure RPO and RTO

**T_failure:** approved outage start. **T_recovered_commit:** latest verified business commit/watermark surviving recovery (not a lag interval alone). **T_business_accept:** when APP and DATA confirm correct, usable business service.

- **Observed RPO window:** T_failure minus T_recovered_commit, accounting for uncertainty.
- **Observed RTO:** T_business_accept minus T_failure, including provisioning, cutover, authentication and replay.

Example only: RPO target 15 minutes, RTO target 2 hours, outage at 12:00 UTC, proven recovered commit 11:52 UTC and APP acceptance 13:35 UTC → 8 minutes data-loss window, 1 hour 35 minutes RTO. Pass only if data checks, single-writer and app SLO all pass.

## 11. Monitoring, evidence and reporting

| Signal | Response |
|---|---|
| Backup completion missing | Check task/provider and escalate |
| WAL archive failures, gaps, stale backup age | Risk to recoverable PITR point |
| Physical/logical slot retaining WAL | Investigate consumer/storage; never blindly drop |
| Replica lag and missing writer proof | DR/RPO and split-brain review |
| Latest provider restore point too old | Escalate to cloud support and DBRE |
| Scheduled restore drill overdue | Owner/ticket |
| Measured RTO/RPO failure | Critical reliability backlog |

### Monthly restore record

| Field | Value |
|---|---|
| Account/instance/provider/version and restore target | |
| Backup ID and archive/LSN coverage | |
| Latest recoverable commit UTC and RPO | |
| Failure, fencing, recovery and APP acceptance UTC | |
| Single-writer validation and source data reconciliation | |
| APP p95/p99 and transaction/CDC behavior | |
| RTO target vs observed | |
| Approvers, evidence link and remediation actions | |

## 12. Acceptance criteria

- [ ] Every production service has approved RPO/RTO, owner, method and backup coverage.
- [ ] Physical, logical, managed and replica capabilities distinguished.
- [ ] Self-managed base backup and continuous archive chain tested where applicable.
- [ ] Cloud provider latest restorable time, retention, networking and HA restrictions verified.
- [ ] Isolated PITR/restore demonstrates data and APP correctness.
- [ ] Recovery of credentials/config/extensions and endpoints tested.
- [ ] Independent fencing and only-one-writer demonstrated.
- [ ] Failover/failback/rewind dependencies and slots/CDC reviewed.
- [ ] Timed recovery includes service validation and end-to-end RTO.
- [ ] All major stakeholders sign off; evidence retained.

**Completion:** Documentation plus a successful backup alone are insufficient. Approved, timed, witnessed restore and HA/DR exercises are mandatory.

## References

- [PostgreSQL continuous archiving/PITR](https://www.postgresql.org/docs/current/continuous-archiving.html)
- [pg_basebackup](https://www.postgresql.org/docs/current/app-pgbasebackup.html)
- [pg_verifybackup](https://www.postgresql.org/docs/current/app-pgverifybackup.html)
- [pg_rewind](https://www.postgresql.org/docs/current/app-pgrewind.html)
- [AWS RDS backups](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html)
- [Azure PostgreSQL backup/restore](https://learn.microsoft.com/en-us/azure/postgresql/backup-restore/concepts-backup-restore)
- [Cloud SQL PITR](https://cloud.google.com/sql/docs/postgres/backup-recovery/pitr)

Related repository tutorials: [Backup architecture](../chapters/041-postgresql-backup-architecture-and-recovery-objectives.md) · [Replication slots and WAL](../chapters/047-postgresql-replication-slots-wal-retention-and-failure-modes.md).
