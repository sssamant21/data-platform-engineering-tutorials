# 108 — Backup, Recovery, and Restore-Validation Concepts

**Part 11 — Security, Data Quality & DBRE/SRE Operations** · **60 minutes** · PostgreSQL 18 baseline · Beginner-friendly

[Master TOC](../MASTER-TOC.md) · [Tutorial index](../README.md) · [Lab 108 SQL](../labs/108-backup-recovery-restore-validation.sql) · [Previous: 107](107-data-quality-assertions-and-reconciliation-queries.md) · Next: 109 — Slow-query investigation, monitoring, and incident runbooks (planned)

## 1. Outcomes and operational scenario (0–5 minutes)

After this chapter, you can distinguish backups from recovery, explain RPO and RTO, select a backup strategy, identify prerequisites for point-in-time recovery (PITR), define restore acceptance checks, and produce an evidence-based recovery go/no-go decision. Prerequisites: [transactions (038)](../part-04-transactions/038-begin-commit-rollback-and-savepoint.md), [data-quality reconciliation (107)](107-data-quality-assertions-and-reconciliation-queries.md).

**Scenario:** A fictional retail order service suffers a storage failure at 10:30 UTC. A backup finished at 09:00, WAL archiving covers subsequent changes, and the business requests recovery to 10:25. Can we claim the service is recoverable? **No**—backup existence and WAL coverage alone do not establish a successfully restored, usable service.

## 2. Concepts and recovery objectives (5–15 minutes)

- **Backup:** A recoverable copy or collection of database artifacts. A backup job marked successful is not proof of a successful restore.
- **Restore:** Reconstructing database files/data from backup artifacts. **Recovery:** Bringing the restored database to a consistent, usable state, potentially replaying WAL to a target.
- **RPO (recovery point objective):** Maximum tolerable data loss measured in time. If the incident is at 10:30 and the recovered state is 10:25, the *illustrative* recovery gap is 5 minutes. The business-approved RPO must be specified separately.
- **RTO (recovery time objective):** Maximum acceptable elapsed time until service restoration. Database startup alone is not sufficient: applications must reconnect and critical workflows must pass.
- **PITR:** Recovery to a supported target within the backup/WAL chain. Requires a usable base backup, continuous WAL coverage, correct recovery configuration, and a verified target.
- **Retention:** How long backups/WAL remain available. Design for recovery needs, legal policy, storage budget, and deletion protection; retention without restoration testing is not assurance.

**PostgreSQL 18 specifics:** Physical base backups plus WAL archiving support PITR. A logical `pg_dump` is useful for logical exports but **is not a substitute for a physical base backup plus WAL chain for arbitrary PITR**. `pg_verifybackup` checks supported backup manifest/file consistency; it does not prove that a restored server starts or that application data is correct. Replication is not a backup: accidental deletes and corruption can replicate.

**Portability:** RPO/RTO, backup immutability, restore rehearsal, checksums, and application acceptance are vendor-neutral. PostgreSQL WAL, `pg_basebackup`, `pg_verifybackup`, `restore_command`, and recovery target settings are PostgreSQL-specific. Cloud-managed snapshots, continuous backups, and PITR differ by provider, retention tier, and service settings; verify the actual service contract.

## 3. Worked recovery design (15–30 minutes)

A hypothetical recovery record:

| Field | Example | Interpretation |
|---|---|---|
| Incident detected | 10:30 UTC | Start of business-impact window |
| Target recovery point | 10:25 UTC | Five-minute recovery gap |
| Last complete base backup | 09:00 UTC | Starting point, **not** necessarily the recovery point |
| WAL coverage | 09:00–10:27 UTC | Covers requested target, subject to continuity/integrity checks |
| Recovery service ready | 11:05 UTC | 35-minute elapsed restoration, if application acceptance also passed |
| Approved RPO / RTO | 10 / 45 minutes | Hypothetical objectives, not measured service guarantees |

Calculated results: 5-minute gap <= 10-minute RPO; 35-minute elapsed <= 45-minute RTO. But **do not mark the restore accepted** until manifest checks, WAL continuity, startup, data reconciliation, application smoke tests, access controls, and authorized sign-off are evidenced. In the lab, one fictional drill lacks application sign-off and is therefore blocked despite meeting both numerical targets.

### A. Choose the appropriate backup method

| Requirement | Candidate approach | Critical caveat |
|---|---|---|
| Whole PostgreSQL cluster with PITR | Physical base backup + WAL archive | Verify timeline, archive continuity, recovery configuration |
| Selected objects or portability | `pg_dump` / `pg_restore` | Logical restore may be slow; no arbitrary physical PITR |
| Managed database service | Provider backups/snapshots and PITR | Validate retention, region/account recovery, IAM, service limits |
| Fast failover | Replication/standby | Does not replace independently recoverable backups |

### B. Recovery runbook phases

1. **Declare and contain:** record incident ID, symptoms, affected service, authorization, and last known-good timestamp. Do not delete the failed environment or overwrite evidence.
2. **Select target:** identify approved RPO/RTO, recovery target, backup set, WAL archive, timeline, encryption keys, access paths, and dependency owners.
3. **Restore to isolation:** use an independently provisioned nonproduction environment with distinct endpoints, credentials, storage, and network boundaries. Never point a rehearsal at production.
4. **Validate artifacts:** inspect backup manifest/checksums, archive continuity, versions/extensions, tablespaces, roles, secrets availability, and startup logs. Confirm the target was actually reached.
5. **Validate data:** check critical row counts, aggregates, referential integrity, sample business transactions, and reconciliation against an approved snapshot/watermark; note expected post-target data loss.
6. **Validate service:** application connectivity, read/write behavior where authorized, permissions, monitoring, dependent jobs, and rollback/failback readiness.
7. **Record evidence and approve:** timestamps, measured RPO/RTO, checks performed, discrepancies, owner approvals, and go/no-go decision. A successful database start is not equivalent to application recovery.

**Operational command references (do not run on production as part of this tutorial):**

```bash
# Illustrative only; requires a separately authorized, isolated PostgreSQL 18 environment.
# pg_verifybackup /isolated/backup-set
# pg_restore --list /isolated/export.dump
# Neither command alone proves a successful service restore.
```

No real backup, archive, recovery, or failover commands are executed by the accompanying lab.

## 4. Hands-on synthetic lab (30–50 minutes)

From repository root, against a disposable PostgreSQL 18 database named `sql_tutorials`:

```bash
psql -X -v ON_ERROR_STOP=1 -d sql_tutorials \
  -f sql-tutorials/labs/108-backup-recovery-restore-validation.sql
```

The [lab](../labs/108-backup-recovery-restore-validation.sql) is a **read-only decision model**, not a backup/restore test. It uses inline fictional recovery-drill evidence, checks the PostgreSQL major version and database name, bounds execution with transaction-local timeouts, and rolls back. It does not access backup files, create databases, write data, or change recovery configuration.

**Expected results (calculated, not observed):** Three fictional drills: `drill_a` passes all gates with 5-minute RPO gap and 35-minute RTO; `drill_b` fails the RPO threshold (15 > 10 minutes); `drill_c` meets numerical objectives but fails application sign-off. Exactly **one** drill is accepted and **two** are blocked. The lab asserts this expected classification.

Practice: (1) explain why `drill_c` is blocked; (2) tighten the RTO objective to 30 minutes and recalculate acceptance; (3) add an archive-continuity failure; (4) propose independent evidence for application recovery; (5) distinguish backup integrity from recovery success; (6) write a one-page rehearsal report with target, start/end times, data checks, decision, and approvers.

## 5. Troubleshooting, safety, and acceptance (50–55 minutes)

| Symptom | Possible cause | Safe response |
|---|---|---|
| Backup exists but restore fails | Missing files, keys, incompatible configuration | Verify manifests, restore logs, version/extension compatibility |
| PITR cannot reach requested timestamp | WAL gap, wrong timeline, target outside archive | Inspect archive coverage and timeline history; do not guess |
| Server starts but application fails | Credentials, endpoints, missing roles/extensions, permissions | Run application smoke tests in isolation |
| RTO exceeds objective | Large data volume, slow restore, dependency recovery | Measure phases and improve rehearsal capacity/process |
| Counts differ | Wrong target, incomplete replay, concurrent snapshot mismatch | Compare against target-aware baseline and reconcile |
| Backup copies disappear together | Shared credentials, region, lifecycle policy | Separate failure domains, least privilege, immutable/offline copies |

**Guardrails:** This chapter never authorizes recovery against production. Physical restores can overwrite files and logical restores can modify objects. Require change approval, a documented target, isolated infrastructure, backup retention protections, restricted access, and named DBRE/application/security sign-off. Do not expose backup secrets, customer data, or credentials in lab logs. Read-only SQL still consumes resources; use a disposable database.

**Validation status:** Authored with calculated examples; targeted static checks only. Independent editorial review, comprehensive SQL parser/link QA, actual PostgreSQL 18 lab execution, and genuine restore acceptance remain pending. The model is **not** evidence of a completed backup or recovery rehearsal.

## 6. Review questions and answers (55–60 minutes)

1. **What is RPO?** Maximum tolerable age of recovered data relative to incident time.
2. **What is RTO?** Maximum acceptable time to restore usable service.
3. **Is a green backup job enough?** No; independently restore and validate.
4. **Does streaming replication replace backups?** No; it can replicate data loss/corruption.
5. **Can `pg_dump` alone provide arbitrary PITR?** No; PostgreSQL physical base backup plus WAL chain is the standard PITR mechanism.
6. **Does `pg_verifybackup` certify application correctness?** No.
7. **Why test in isolation?** To avoid altering live services and to prove independently recoverable artifacts.
8. **Why block a drill meeting RPO/RTO?** Missing integrity, application, or approval evidence makes it unaccepted.

**Next:** Chapter 109 — Slow-query investigation, monitoring, and incident runbooks.

## References

- [PostgreSQL 18 — Backup and Restore](https://www.postgresql.org/docs/18/backup.html)
- [PostgreSQL 18 — Continuous Archiving and Point-in-Time Recovery](https://www.postgresql.org/docs/18/continuous-archiving.html)
- [PostgreSQL 18 — pg_basebackup](https://www.postgresql.org/docs/18/app-pgbasebackup.html)
- [PostgreSQL 18 — pg_verifybackup](https://www.postgresql.org/docs/18/app-pgverifybackup.html)
- [PostgreSQL 18 — pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html)
- [PostgreSQL 18 — Recovery Configuration](https://www.postgresql.org/docs/18/runtime-config-wal.html#RUNTIME-CONFIG-WAL-RECOVERY)
