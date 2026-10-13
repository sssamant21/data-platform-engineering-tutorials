# Chapter 092 — PostgreSQL Cross-Region Backup, Restore and Disaster Recovery Automation

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Design and verify an independent cross-region PostgreSQL recovery capability that remains usable when the primary region, streaming replica or regional control plane fails. Integrate [Chapter 090 — Multi-Region DR Design](090-postgresql-multi-region-architecture-geo-replication-and-disaster-recovery-design.md) and [Chapter 091 — Fencing and Split-Brain Prevention](091-postgresql-cross-region-failover-fencing-and-split-brain-prevention.md).

**Acceptance rule:** backup job success is not restore proof. A restore must complete, replay WAL to an approved recovery target, pass consistency and application checks, and demonstrate measured RPO/RTO.

## 2. Recovery architecture

```text
Region A: PostgreSQL primary
  ├─ physical base backups
  ├─ continuous WAL archive
  └─ immutable metadata / backup manifest
             |
     encrypted cross-region copy
             v
Region B: isolated object storage + independent IAM/KMS
  ├─ base backup generations
  ├─ complete WAL chain + timeline history
  ├─ catalog / retention / integrity evidence
  └─ automated isolated restore environment
             |
     controlled DR restore and validation
             v
Region B: restored PostgreSQL candidate (quarantined)
             |
      fencing + writer authority gate
             v
      approved application cutover
```

A replica is not a backup. Logical replication and ordinary replication may propagate destructive changes; independently retained backups and WAL enable recovery to an earlier point.

## 3. Backup methods

| Method | Recovery property | Operational considerations |
|---|---|---|
| `pg_basebackup` + WAL archive | Physical cluster restore and PITR | Matching major version, WAL continuity, archive correctness |
| Backup manager (e.g., pgBackRest, Barman) | Scheduling, catalogs, retention, verification | Tool-specific supported configuration and restore procedures |
| Managed service automated backups | Provider-integrated snapshots/PITR | Region, service tier, retention and cross-region feature limits |
| `pg_dump` / `pg_restore` | Logical object/data recovery | Not physical PITR; roles/globals and large restore time |
| Storage snapshots | Potential fast volume restore | Must ensure database-consistent snapshots and required WAL |

Use vendor/provider documentation for actual cross-region and encryption support. A cloud snapshot is not automatically a transactionally consistent PostgreSQL backup.

## 4. Physical backup and WAL correctness

For self-managed PostgreSQL, `pg_basebackup` creates a physical backup while WAL archiving or streaming supplies required recovery records. Track backup start/end, system identifier, timeline, backup manifest, checkpoint, WAL start/end and checksum verification where supported.

PostgreSQL WAL archive must preserve exact files and timeline history, be idempotent, and never overwrite a different existing file with the same name. `archive_command` must report success **only after durable archive completion**. A broken archiver can accumulate WAL and exhaust disk.

`pg_verifybackup` verifies backup manifest and file integrity but is **not** a substitute for starting PostgreSQL and validating recovered application data.

## 5. Cross-region storage and independence

Protect recovery copies from primary-region failures and credential compromise:
- Cross-region storage with independently tested access and replication status.
- Encryption at rest and in transit; DR-accessible KMS keys and key policy.
- Least-privilege identities, separate backup writer and restore reader, MFA/break-glass controls.
- Immutable/object-lock retention where required, deletion protection and audit logging.
- Capacity and egress planning for full backup, incremental chains and WAL.
- Verified restore bootstrap independent of the original region's DNS, network, IAM and CI/CD services.

Cross-region copy success does not guarantee the latest WAL required by the target was transferred. Verify recovery-chain completeness.

## 6. PITR and timelines

Choose a recovery target using `recovery_target_time`, `recovery_target_lsn`, or a named restore point, based on incident evidence. On a self-managed restore, supply `restore_command` and `recovery.signal` using supported PostgreSQL 18 configuration. Recovery targets must be reachable from the available backup and WAL timeline chain.

**Do not overwrite a running primary or point a restored node at production write traffic.** Restore into a new isolated data directory/instance. Promote or expose writes only after authoritative-writer fencing and DR approval.

## 7. Automated restore verification

An automation pipeline should:
1. Discover eligible backup generation and expected WAL chain.
2. Verify object inventory, manifest, checksums, decryption and IAM access.
3. Allocate a disposable isolated recovery environment.
4. Restore base backup and WAL to the approved target.
5. Start PostgreSQL and check recovery completion, version and timeline.
6. Run SQL consistency and application smoke tests against synthetic/approved data.
7. Measure elapsed time and last durable transaction recovered.
8. Store redacted evidence and alert on failure or missing runs.
9. Tear down test resources after evidence retention, without deleting source backups.

Avoid publishing sensitive restored production data into an unrestricted lab. Use masking and restricted access.

## 8. Recovery automation safeguards

Use one run ID, idempotent job state, distributed locking/lease if multiple controllers exist, explicit destination and environment allowlist, hard timeouts, least privilege, structured logs, alerts and approval checkpoints. Automation may prepare a recovery candidate automatically, but **production promotion and traffic cutover must honor Chapter 091 fencing gates**.

A failed restore test must be actionable: preserve logs, identify the missing backup/WAL/key/dependency and escalate. Never silently mark it PASS because the backup catalog lists a completed job.

## 9. Retention, cost and compliance

Define base backup retention, incremental dependency chains, WAL retention, immutability, legal holds, deletion approval and periodic restore tests. Estimate cross-region storage, object operations, replication transfer, restore compute, KMS and egress charges. Ensure deleting an old backup cannot orphan newer incrementals or PITR ranges.

## 10. Failure-mode matrix

| Failure | Detection | Response |
|---|---|---|
| Missing WAL segment | Restore replay stops | Investigate archive/copy; choose alternate recoverable target |
| Expired KMS key access | Decryption fails | Restore approved key access; do not disable encryption |
| Corrupt base backup | Manifest/restore failure | Use independent valid backup; preserve evidence |
| Wrong timeline | Replay mismatch | Review timeline history and selected target |
| Archive lag | RPO gap | Quantify last copied durable WAL; alert |
| Backup deletion/retention error | Recovery chain broken | Halt pruning; restore backup inventory |
| DR control-plane dependency | Restore cannot provision | Use documented break-glass/manual bootstrap |
| Restored node exposed as writer | Split-brain risk | Quarantine; fence original writer before cutover |

## 11. Operational recovery runbook

**Detect:** declare incident, freeze unsafe changes and identify desired recovery point.

**Assess:** compare standby promotion versus PITR; determine actual backup and WAL availability, recovery time and potential loss.

**Prepare:** verify independent keys, access, restore infrastructure and application dependencies.

**Restore:** use a new isolated target, capture commands and UTC times, verify recovery to the chosen point.

**Validate:** SQL, data consistency, roles/extensions, app read/write in isolation, security and monitoring.

**Cutover:** require explicit approval and old-primary fencing before routing authoritative writes.

**Close:** rebuild backup/archive and HA, reconcile lost transactions, preserve evidence and perform PIR.

## 12. Lab and acceptance

Use [Chapter 092 lab](../labs/092-postgresql-cross-region-backup-restore-and-disaster-recovery-automation-lab.md), [read-only recovery preflight SQL](../labs/sql/092-cross-region-recovery-preflight.sql), [backup chain manifest](../labs/dr/092-backup-recovery-chain-manifest.csv), [restore automation runbook](../labs/dr/092-isolated-restore-automation-runbook.md), and [acceptance scorecard](../labs/acceptance/092-cross-region-recovery-scorecard.csv).

**PASS requires:** independent backup/WAL copy, accessible keys, verified manifest, successful isolated restore, documented recovered point, measured RPO/RTO, application validation and safe writer fencing before any cutover. Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/continuous-archiving.html
- https://www.postgresql.org/docs/18/app-pgbasebackup.html
- https://www.postgresql.org/docs/18/app-pgverifybackup.html
- https://www.postgresql.org/docs/18/runtime-config-wal.html
- https://www.postgresql.org/docs/18/warm-standby.html

**Next:** Chapter 093 — PostgreSQL Multi-Region Observability, DR Drills and Reliability Testing.
