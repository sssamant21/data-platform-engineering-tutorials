# Page 06 — PostgreSQL Backup, High Availability, Disaster Recovery & Restore Testing

**Document ID:** PG-DBRE-OPS-006 | **Owner:** PostgreSQL DBRE  
**Status:** DRAFT — NOT CERTIFIED FOR PRODUCTION  
**Platforms:** Self-managed PostgreSQL; AWS RDS/Aurora, Azure Flexible Server, Google Cloud SQL  
**Stakeholders:** DBRE, APP, DATA, PLT, SEC, Incident and Change Management  
**Cadence:** Daily backup/replication checks; monthly controlled restore; quarterly DR rehearsal

> **Safety:** Promotion, fencing, pg_rewind, replication-slot changes, PITR, data-directory replacement and client cutover are high-risk. None is authorized by publishing this document. No executable promotion or destructive restore command is included.

## 1. Purpose and objectives

**RPO** is the maximum acceptable loss of committed business data, measured from the incident boundary to a **demonstrated recoverable business commit/watermark**. **RTO** is time from an agreed outage start to full, business-accepted read/write functionality, including provisioning, application routing and data reconciliation. A successful backup, enabled HA, last archived WAL filename or read replica alone does not prove these objectives.

**Recovery-time caution:** On self-managed systems, the archiver normally processes **completed** WAL segments; low-write traffic can delay archival of a recent commit. The archive_timeout setting can bound segment-switch waiting at the cost of additional full-size WAL archive segments, but it does not alone guarantee a business RPO. Record actual latest restorable point and completed WAL/timeline coverage. Async replica receive/replay lag, especially on an idle source, cannot be interpreted directly as minutes of data loss.

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
| pg_basebackup | Physical base backup | Must preserve all required WAL and compatible tablespaces/config; restore must match the source PostgreSQL major version |
| Base backup + continuous WAL archive | Cluster point-in-time recovery | Continuous WAL/timeline chain; validate restore from actual archive |
| PostgreSQL 17+ incremental physical backup | More efficient changed-block backup | Requires dependent full/incremental chain, WAL summaries and pg_combinebackup reconstruction plus required WAL/history; back up and test the entire chain |
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
       confirmed_flush_lsn, wal_status, safe_wal_size,
       xmin, catalog_xmin
FROM pg_replication_slots;

-- On a standby, WAL receiver metadata without conninfo or credentials.
SELECT status, flushed_lsn, received_tli,
       latest_end_lsn, latest_end_time, slot_name
FROM pg_stat_wal_receiver;

-- On a standby; timestamps can remain old when no new commits occur.
SELECT pg_last_wal_receive_lsn() AS received_lsn,
       pg_last_wal_replay_lsn() AS replayed_lsn,
       pg_last_xact_replay_timestamp() AS latest_replayed_commit_time;
~~~~

Use authorized monitoring permissions and the correct primary/standby connection context. A single SQL connection can show a primary-only view as empty on a standby (and vice versa), which is not a complete health verdict. The wal_status of a replication slot and safe_wal_size indicate WAL-replay risk, but do not prove an intact offsite archive. Avoid SELECT * on pg_stat_wal_receiver: conninfo is unnecessary and may expose endpoint information. pg_stat_archiver may be irrelevant to cloud-managed backup/PITR, counters can reset and cannot prove a continuous WAL/timeline chain. A standby's latest replayed commit timestamp can be stale simply because the primary is idle. See [V06 read-only preflight](qa/V06-readonly-recovery-preflight.sql) for a bounded staging-first diagnostic pack.

### Backup integrity and restore requirements

A successful pg_verifybackup manifest check is a useful integrity step for compatible physical backups, but **even a PASS does not prove the PostgreSQL server can start, WAL will replay to target, or APP data will be correct**. The tool's WAL parsing support differs by backup format (for example, tar-format backup requires no-parse-wal mode); use exact supported tool/backup formats and capture evidence. External tools (pgBackRest, Barman) require their own chain validation and retention controls. For PostgreSQL 17+ incremental backups, preserve the full dependency chain and check pg_combinebackup output and follow-on recovery.

Record **successful backup completion**, object-storage integrity, timeline history, a verified reachable recovery target and missing/failed WAL segments. A manifest or backup dashboard green status is not a substitute for isolated restore and business reconciliation.

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

**pg_rewind** requires either enabled data checksums or wal_log_hints on the target, full_page_writes enabled, and enough target-side WAL to locate divergence. The rewind target must be safely shut down; replay and recovery configuration are still necessary before rejoining. If pg_rewind fails partway through, treat that target's data directory as potentially unrecoverable and plan a clean rebuild rather than trying an unreviewed restart. Rewind may copy source configuration: validate secrets, replication settings, archive and recovery configuration again. Never rewind an active/wrong target. Promotion and failback are not one-step reversible changes.

**Extra gate for logical replication/CDC:** With PG17+ slot synchronization where configured, verify required synchronized logical slots are actually failover-ready before client or subscriber cutover. Otherwise, plan a controlled resubscription/rebootstrap, no missed or duplicated data. This is a version- and topology-dependent feature, not an assumed default.

## 8. Managed-cloud backup/PITR/HA matrix

| Service | Supported pattern | Critical distinction |
|---|---|---|
| AWS RDS PostgreSQL | Automated backups + transaction logs | PITR creates a **new DB instance**; verify LatestRestorableTime, backup retention, resulting subnet/security/parameter groups, encryption and HA before client cutover |
| Amazon Aurora PostgreSQL | Cluster storage/backups, writer/reader endpoints | PITR creates a **new DB cluster**; inspect its instances, endpoint, parameter/security groups, restore window and failover/read-replica design separately |
| Azure PostgreSQL Flexible Server | Managed server backup/logs | PITR creates a **new server**; HA is **not automatically restored**; verify parameters, firewall/private network, client endpoint, role/grants and alerts |
| Google Cloud SQL for PostgreSQL | Managed backup/PITR when enabled | PITR **always creates a new instance**, not an in-place overwrite; edition/creation method can change default PITR enablement; verify connectivity, IAM, data and HA |
| Self-managed | Physical base/WAL and/or approved operator tooling | DBRE/PLT responsible for OS/filesystem, backups, WAL and fencing |

Managed services are not full OS/root environments. Do not reuse self-managed file-level restore commands in RDS/Aurora/Azure/Cloud SQL. **PITR is not identical to an ordinary backup-snapshot restore:** Cloud SQL can restore an ordinary backup to an existing instance in some workflows, but Cloud SQL PITR creates a new instance. For managed services, get the provider's actual earliest/latest restorable point and document time zone/clock skew. Network identity, private endpoints, DNS, secrets, extensions, server settings, read replicas and HA often need post-restore work. Region/network permissions and service tier eligibility must be tested before claiming DR capability.

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

Use sanitized staging data and independent observers. Do not simulate destructive failure in production without a separately approved exercise. Each DR01–DR12 scenario maps to a negative test and pass/no-go criteria in the [V06 acceptance matrix](qa/V06-DR-exercise-acceptance.md). Tabletop evidence is not equivalent to actually observed recovery times or fencing; mark each scenario as TABLETOP, EXECUTED, BLOCKED or NOT_RUN.

## 10. Measure RPO and RTO

**T_failure:** approved outage start. **T_recovered_commit:** latest verified business commit/watermark surviving recovery (not a lag interval alone). **T_business_accept:** when APP and DATA confirm correct, usable business service.

- **Observed potential data-loss window:** T_failure minus T_recovered_commit, conservatively accounting for missing/wrong clock source, unknown commits and uncertainty. Require a validated APP/DATA commit marker or business-source watermark, not just replay_lag or a replica timestamp.
- **Observed RTO:** T_business_accept minus T_failure, including provisioning, replay, credentials, cutover, application functional/data reconciliation, and dependent pipelines.
- **Separate technical database-ready from business-service accepted:** a database accepting psql connections is NOT proof that business service has recovered.
- Record authoritative clock source/time zone (UTC), failover authorization and test dataset with no PHI. If a watermark cannot be substantiated, report RPO UNKNOWN / NO-GO, not zero.

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

## 12. V06 acceptance, rollback and no-go controls

**Independent recovery certification gate:** Technical DR operator, APP service owner, DATA owner and PLT/SEC as applicable must sign the evidence. An incident commander authorizes production changes and documented potential data loss.

| Gate | Must be independently verified | Result if missing |
|---|---|---|
| G01 — Recovery scope | Exact primary, standby, instance/cluster, major version, backup and restore destination | NO-GO |
| G02 — Backup + WAL | Successful complete backup, full WAL segment/history chain or provider latest restorable point | NO-GO |
| G03 — Identity/network | Secure connection, credentials, TLS, roles, DNS/endpoint and client routing | NO-GO |
| G04 — Single writer | Independently fenced old primary; approved new primary; no hidden write paths | NO-GO for promotion/cutover |
| G05 — RPO | Demonstrated business commit/replay watermark and acknowledged lost-data estimate | UNKNOWN/NO-GO without DATA approval |
| G06 — RTO | UTC incident-to-business-acceptance timing; APP validates functionality and throughput | NO PASS without APP |
| G07 — CDC/subscribers | WAL slots, replication, subscribers, replay idempotency and data reconciliation | NO-GO if unowned |
| G08 — Fallback | Tested stop/rollback/rebuild/failback authority and capacity | NO-GO |
| G09 — Isolation | DR exercise target cannot accept production writes inadvertently | NO-GO |
| G10 — Evidence | Signed technical + APP/DATA + change tickets, sanitized logs and retention | NOT_CERTIFIED |

**Abort triggers:** fencing failure, stale identity/timeline, missing WAL, unexpected source writes, unapproved data-loss estimate, target restoration onto existing production data, unexpected security-policy change, untested client reroute, or inability to preserve recovery evidence.

## 13. Staging-readiness artifacts and review

- [V06 source/compatibility review](qa/V06-backup-HA-DR-review.md): verified backup, WAL, rewind, managed-provider restore distinctions and known gaps.
- [V06 read-only SQL preflight](qa/V06-readonly-recovery-preflight.sql): diagnostics for PostgreSQL 14–18, with explicit primary/standby interpretations, no mutation.
- [V06 DR exercise acceptance register](qa/V06-DR-exercise-acceptance.md): 12 cases, fail/no-go criteria, exact evidence and independently signed recovery gate. No exercises performed by publication.

## 14. Acceptance criteria

- [ ] Every production service has approved RPO/RTO, owner, method and backup coverage.
- [ ] Physical, logical, managed and replica capabilities distinguished.
- [ ] Self-managed base backup and continuous archive chain tested where applicable.
- [ ] Cloud provider latest restorable time, retention, networking and HA restrictions verified.
- [ ] Isolated PITR/restore demonstrates data and APP correctness.
- [ ] Recovery of credentials/config/extensions and endpoints tested.
- [ ] Independent fencing and only-one-writer demonstrated.
- [ ] Failover/failback/rewind dependencies and slots/CDC reviewed.
- [ ] Timed recovery includes service validation and end-to-end RTO.
- [ ] G01–G10 recovery, fencing, RPO/RTO and post-restore authorization gates assessed and signed.
- [ ] DR01–DR12 staged cases marked EXECUTED PASS or appropriate BLOCKED; tabletop does not substitute for runtime proof.
- [ ] No executable promotion, destructive restore, backup deletion or role bypass was introduced through V06.
- [ ] All major stakeholders sign off; evidence retained.

**Completion:** Documentation plus a successful backup alone are insufficient. Approved, timed, witnessed restore and HA/DR exercises are mandatory.

## References

- [PostgreSQL continuous archiving/PITR](https://www.postgresql.org/docs/18/continuous-archiving.html)
- [PostgreSQL standby failover / former primary isolation](https://www.postgresql.org/docs/18/warm-standby-failover.html)
- [PostgreSQL 14 and 18 WAL receiver view](https://www.postgresql.org/docs/14/monitoring-stats.html)
- [Incremental backup combination PG17+](https://www.postgresql.org/docs/18/app-pgcombinebackup.html)
- [Aurora restore to PITR creates new cluster](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-pitr.html)
- [AWS RDS restore to PITR creates new instance](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PIT.html)
- [Cloud SQL PostgreSQL PITR creates new instance](https://docs.cloud.google.com/sql/docs/postgres/backup-recovery/pitr)
- [pg_basebackup](https://www.postgresql.org/docs/current/app-pgbasebackup.html)
- [pg_verifybackup](https://www.postgresql.org/docs/current/app-pgverifybackup.html)
- [pg_rewind](https://www.postgresql.org/docs/current/app-pgrewind.html)
- [AWS RDS backups](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html)
- [Azure PostgreSQL backup/restore](https://learn.microsoft.com/en-us/azure/postgresql/backup-restore/concepts-backup-restore)
- [Cloud SQL PITR](https://cloud.google.com/sql/docs/postgres/backup-recovery/pitr)

Related repository tutorials: [Backup architecture](../chapters/041-postgresql-backup-architecture-and-recovery-objectives.md) · [Replication slots and WAL](../chapters/047-postgresql-replication-slots-wal-retention-and-failure-modes.md).
