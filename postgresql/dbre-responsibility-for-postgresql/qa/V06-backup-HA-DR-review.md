# PostgreSQL DBRE V06 — Backup, HA, DR Source and Safety Review

**Review date:** 2026-11-01 UTC  
**Owner:** PostgreSQL DBRE  
**Disposition:** STATIC SOURCE REVIEW COMPLETE; CONTROLLED STAGING RESTORE, FENCING AND APP VALIDATION PENDING  
**Scope:** PG-DBRE-OPS-006 and PostgreSQL 14–18, self-managed + RDS/Aurora, Azure Flexible Server, Cloud SQL.

## 1. Executive finding

The seven-page PostgreSQL DBRE documentation track now has source-level QA artifacts for V01–V06. **The current V06 review is not a failover certification.** No PostgreSQL cluster, managed-provider backup, WAL archive, database write, client endpoint or other production resources were accessed or modified.

The V06 review refreshed the backup and recovery runbook with verified WAL semantics, vendor-specific PITR behavior, independent fencing/rewind risk, version-aware backup assumptions, read-only diagnostic inventory and an explicit no-go acceptance checklist.

## 2. Confirmed findings and implemented improvements

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| V06-F01 | HIGH | Successful base backup, pg_verifybackup or archiver count might be mistaken for a proven PITR. | Require isolated PostgreSQL startup, continuous WAL and timeline history, replay to a known time and APP/DATA record reconciliation. |
| V06-F02 | HIGH | Last archive timestamp does not establish recoverable commit watermark during quiet/low-write periods. | Document completed-segment archive behavior, archive_timeout tradeoff and measured business data watermark. |
| V06-F03 | HIGH | Failover without independent old-primary fencing can produce split brain; SQL read-only status alone is insufficient proof. | G04 mandatory independent fence before promotion/cutover; explicit abort on dual-writer possibility. |
| V06-F04 | HIGH | pg_rewind prerequisites and failure handling insufficient. | Document checksum or wal_log_hints, full_page_writes, target shutdown, divergence WAL and recovery config; failed rewind requires rebuild consideration. |
| V06-F05 | HIGH | Managed-provider PITR restore objects/networks/HA differ. | Explicit RDS new DB instance, Aurora new DB cluster, Azure new server without auto HA, Cloud SQL new instance and reconfiguration requirements. |
| V06-F06 | MEDIUM | No focused standby receiver and replay diagnostic alongside primary sender view. | Add pg_stat_wal_receiver (excluding conninfo) and pg_last_wal_receive/replay diagnostics; explain NULL/idle time interpretation. |
| V06-F07 | MEDIUM | PG17+ incremental backup prerequisites need dependency reconstruction. | Document required dependent backups, WAL/history and pg_combinebackup; no deletion of needed chain. |
| V06-F08 | HIGH | Business RPO/RTO sign-off could be inferred from DB-ready timestamp. | Require proven commit marker and UTC app/data acceptance, and record uncertainty / UNKNOWN when not proven. |
| V06-F09 | MEDIUM | CDC slot readiness around failover needs explicit owner gate. | Document version/topology-based slot synchronization versus rebootstrap and dedupe. |
| V06-F10 | HIGH | No explicit stop/no-go and 12-case evidence contract. | Publish G01–G10 gates, DR01–DR12 acceptance matrix, preflight role and independent witness fields. |

## 3. Source-confirmed recovery semantics

### PostgreSQL physical backup and WAL

- Physical restore needs compatible **major version**, complete base plus all WAL and timeline history needed by the recovery target; pg_dump is not a WAL-restorable cluster backup.
- WAL archiving normally processes **completed segments**. An inactive database may retain recently committed data in an incomplete local segment until switching or other configured action. A short archive_timeout can force switches but at additional archive volume and without proving the actual latest restorable commit.
- pg_verifybackup validates compatible backup contents/manifest; tar-format WAL parsing is restricted. Even verification PASS cannot guarantee actual PostgreSQL startup or correct APP data; restore and reconcile.
- PostgreSQL 17+ incremental backup chain reconstruction requires pg_combinebackup, prior dependent backups, WAL summaries and full recovery verification; retention logic must preserve every dependency.

### Failover and rewinding

- Independent old-primary write fencing is mandatory before a new primary accepts production writes.
- A standby promoted during an async replication window may be missing recent acknowledged commits.
- pg_rewind requires checksums OR wal_log_hints, full_page_writes enabled, correct stopped target and divergence WAL; it is not an automatically reversible failback. Failed/incomplete rewind may require rebootstrap.
- CDC and logical subscribers need their own last-applied/slot recovery evidence and data reconciliation. Slot sync features are not automatically available on all versions/topologies.
- The time from technical promotion to APP/DATA acceptance is part of RTO, not a postscript.

### Managed-provider PITR distinctions

| Provider | PITR creates | Required independent acceptance |
|---|---|---|
| AWS RDS PostgreSQL | New DB instance | Backup window, security/subnets, parameter groups, app endpoint, Multi-AZ re-evaluation |
| Amazon Aurora PostgreSQL | New DB cluster | Writer/reader topology, endpoint, security and parameter groups, cluster backup window |
| Azure PostgreSQL Flexible Server | New server | HA is not automatically enabled; firewall, private/public networking, params and apps must be reconfigured |
| Google Cloud SQL PostgreSQL | New instance | PITR enabled by edition/creation method; validate IAM/network, APP endpoint and recovered data |

**Nuance:** Cloud SQL ordinary backup restores can target an existing instance in some workflows; its PITR specifically creates a new instance. Do not apply the same rule to all restore types.

## 4. Read-only preflight and evidence design

- [V06 read-only recovery preflight](V06-readonly-recovery-preflight.sql) uses a READ ONLY transaction with 5-second local statement timeout and version/role observation.
- It inspects archive counters, primary sender, standby receiver, WAL slots and last replay LSN/timestamp. No write/failover/restore commands.
- Values alone do not establish backup restorable point, provider backup settings, independent primary fencing or APP service acceptance.
- Inspect vendor control-plane metadata, backup/recovery job results and independently observed service probes.
- Never export WAL receiver conninfo, credentials, business row values, sensitive SQL text or PHI to a shared evidence repository.

## 5. Staging acceptance and negative test suite

- [V06 exercise acceptance matrix](V06-DR-exercise-acceptance.md) defines DR01–DR12 with preparation gates, expected outcomes, test states and evidence.
- Mandatory stop conditions: unverified identity, missing WAL, target overwriting production, unknown old primary state, missing approvals, risk to real patient data and unaccepted lost commits.
- TABLETOP_PASS is NOT STAGING_PASS or RTO/RPO evidence.
- Any RPO without a proven data watermark is UNKNOWN; database SQL availability alone is not service RTO.
- The test record must identify exact PG/provider versions, incident date UTC, backup IDs, timeline/LSN evidence, endpoint and security checks, DATA reconciliation and independent APP acceptance.

## 6. Open execution and certification gates

| Gate | Evidence needed | Status |
|---|---|---|
| V06-T01 | Run preflight with authorized monitoring role on actual staged PG provider/versions | PENDING |
| V06-T02 | Restore physical backup to isolated stage with verified WAL and timeline | PENDING |
| V06-T03 | Execute controlled PITR to known synthetic bad transaction | PENDING |
| V06-T04 | Simulate missing WAL and verify fail closed | PENDING |
| V06-T05 | Independent primary fencing, single-writer and cutover test | PENDING |
| V06-T06 | Old primary rejoin and controlled rewind/rebuild | PENDING |
| V06-T07 | CDC subscriber/slot reconciliation | PENDING |
| V06-T08 | Provider-specific new instance/cluster/server PITR readiness | PENDING |
| V06-T09 | Timed end-to-end APP/DATA recovery with approved RPO/RTO | PENDING |
| V06-T10 | Reproducible security/network/role/secret recovery | PENDING |
| V06-T11 | Large-volume restore and disk/IO recovery headroom | PENDING |
| V06-T12 | Formal incident/change, DBRE, APP/DATA, PLT/SEC independent sign-off | PENDING |

**V06 status:** Static and documentary review completed, no runtime DR acceptance performed. The entire PostgreSQL V01–V06 source documentation QA sequence has been authored; external links, actual SQL, exporter alerts, incident tests, capacity/billing and DR exercises remain pending.

## 7. Authoritative source URLs

- [PostgreSQL 18 continuous WAL archiving and PITR](https://www.postgresql.org/docs/18/continuous-archiving.html)
- [PostgreSQL 18 pg_verifybackup limitations](https://www.postgresql.org/docs/18/app-pgverifybackup.html)
- [PostgreSQL 18 pg_combinebackup](https://www.postgresql.org/docs/18/app-pgcombinebackup.html)
- [PostgreSQL 18 pg_rewind requirements](https://www.postgresql.org/docs/18/app-pgrewind.html)
- [PostgreSQL 18 standby failover](https://www.postgresql.org/docs/18/warm-standby-failover.html)
- [PostgreSQL 14 WAL receiver statistics](https://www.postgresql.org/docs/14/monitoring-stats.html)
- [AWS RDS PITR](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PIT.html)
- [Amazon Aurora PostgreSQL PITR](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-pitr.html)
- [Azure Flexible Server PITR/HA/network](https://learn.microsoft.com/en-us/azure/postgresql/backup-restore/concepts-backup-restore)
- [Cloud SQL PostgreSQL PITR](https://docs.cloud.google.com/sql/docs/postgres/backup-recovery/pitr)
