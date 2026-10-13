# Chapter 066 — PostgreSQL Backup and Disaster Recovery Acceptance Lab

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime acceptance pending

## 1. Mission

Prove that PostgreSQL can recover from a destructive incident within declared RPO and RTO, with correct data, secure artifacts, observable failures, and controlled cutover/rollback. This capstone integrates [Chapter 061](061-postgresql-backup-strategy-rpo-and-rto-fundamentals.md), [062](062-postgresql-logical-backups-with-pg-dump-pg-restore-and-pg-dumpall.md), [063](063-postgresql-physical-backups-with-pg-basebackup-and-backup-verification.md), [064](064-postgresql-wal-archiving-and-point-in-time-recovery.md), and [065](065-postgresql-backup-retention-automation-and-restore-testing.md).

## 2. Safety boundary and architecture

```text
Disposable PostgreSQL 18 source -- physical base backup --> protected backup
                 |                                   |
                 +-- continuous WAL --> archive ------+
                                                     |
                                 isolated recovery PGDATA (new identity/port)
                                                     |
                                    verify PITR -> read-only application checks
                                                     |
                                     evidence -> decision -> controlled cutover
```

Use a dedicated lab cluster, isolated restore host or container, independent storage, unique port, protected credentials and verified backup retention. **Never run destructive injection or recovery over production data, live PGDATA or production routing.** Test cutover with a lab-only endpoint. If no actual HA/region-failover environment exists, mark that scenario NOT VERIFIED rather than PASS.

## 3. Recovery objectives and incident definition

Choose explicit service objectives before the test. **Illustrative only:** RPO <= 15 minutes; RTO <= 120 minutes, measured from declared incident start to validated application availability. Record detection, authorization, provisioning, transfer, WAL replay, validation and cutover separately.

Incident: a controlled deletion of a known lab row after a documented recovery target. The recovery target must be between two known committed transactions. Verify PostgreSQL clock synchronization, UTC timestamps and recovery_target_inclusive behavior. Do not infer commit order solely from the time a SQL command was issued.

## 4. Prerequisite acceptance

| Gate | Evidence |
|---|---|
| Source inventory | Version, system ID, database sizes, tablespaces, extensions, roles |
| Backup strategy | Logical and physical scope, WAL policy, schedule and retention |
| Integrity | pg_verifybackup success, manifests/checksums, offsite copy |
| Security | Least privilege, TLS, protected storage, encryption keys and audit trail |
| Archive health | WAL chain continuity, timeline history, no missing required segments |
| Operational readiness | Runbook, escalation, isolation, backup storage, spare capacity |
| Observability | Backup age, archive failures, disk/WAL growth, restore drill status |

Run [Chapter 066 inspection SQL](../labs/sql/066-dr-inspect.sql) and preserve its output. A green archive metric alone does not establish recoverability.

## 5. End-to-end test sequence

1. **Preflight:** snapshot configuration, backup inventory, capacity, clocks and baseline application results. Record incident commander, restore operator and verifier.
2. **Fixture:** create a dedicated lab database and schema, seed a stable reference row and verify its checksum.
3. **Backup:** run pg_basebackup -Fp -X stream into an unused location, then pg_verifybackup. Confirm offsite copy and keys are recoverable.
4. **PITR event:** commit a pre-target marker; record UTC recovery point after the commit; commit a post-target marker and a controlled destructive change in separate autocommit transactions. Force/await archiving in the lab.
5. **Recovery:** copy base backup to a new isolated PGDATA, set restore_command, recovery_target_time and recovery.signal; use a unique port and localhost-only listener. Review copied configuration, tablespaces and replication settings.
6. **Verification:** inspect logs for target reached and WAL replay completion/pause. Verify pre-target marker present, post-target marker absent, reference row present, constraints and roles correct.
7. **Operational recovery:** measure total time to validated lab application access; compare to RTO, calculate achieved recoverable point against RPO and document any missing WAL or manual work.
8. **Rollback and cleanup:** return lab routing to original source, retain artifacts/evidence, shut down recovered lab server and remove only confirmed lab-owned resources.

## 6. Scenarios and pass/fail

| ID | Scenario | Expected result |
|---|---|---|
| DR01 | Physical backup + manifest verification | Artifact complete, verified and protected |
| DR02 | Continuous WAL archiving | Required segments and history accessible |
| DR03 | PITR before accidental delete | Pre-target row present; post-target change absent |
| DR04 | Isolated recovery startup | PostgreSQL 18 starts without production connectivity |
| DR05 | Logical selective recovery | Isolated pg_restore restores object and permissions as designed |
| DR06 | Retention dry run | No required WAL/base backup selected for deletion |
| DR07 | Missing-WAL failure rehearsal | Recovery failure detected and not falsely accepted |
| DR08 | Backup corruption rehearsal | Verification rejects modified lab copy |
| DR09 | Key/offsite recovery | Copy and encryption keys independently available |
| DR10 | Monitoring and alert delivery | Archive failure and missed backup alerts routed |
| DR11 | Timed service recovery | Achieved RPO/RTO meet signed objectives |
| DR12 | Rollback | Original lab service restored without data loss |

**Never intentionally corrupt the sole good backup.** For DR08, modify only a disposable *copy* of the artifact. For DR07, hide a segment only in a cloned lab archive, never the authoritative archive.

## 7. Recovery time and point calculations

```text
Actual RTO = validated application recovery time - incident start time
Actual data-loss window = incident time - latest consistent recoverable commit time
Total restore = provisioning + transfer + replay + validation + routing
```

Do not equate RPO with age of last base backup: the usable WAL chain determines the latest recoverable point. A successful PITR to a chosen historical point demonstrates precision, but it does not by itself prove that the newest recoverable point meets the RPO. Test both historical PITR and latest-possible recovery coverage.

## 8. Operational failure modes

| Failure | Investigation | Response |
|---|---|---|
| pg_verifybackup failure | Missing/changed files, WAL, manifest | Quarantine backup; use verified alternative |
| WAL archive gap | archive_command failures, retention, timeline | Stop promotion and investigate chain |
| Recovery target not reached | Missing WAL, wrong UTC, timeline | Preserve logs, select valid target |
| Startup fails | Permissions, config, extensions, tablespaces | Correct isolated restore only |
| Backup inaccessible | Credentials, KMS, region outage | Test independent key and storage recovery |
| RTO exceeded | Slow provisioning, transfer or replay | Measure bottleneck and revise architecture |
| Data mismatches | Wrong recovery target or application reconciliation | Fail acceptance; do not cut over |

## 9. Evidence and signoff

Use the [lab runbook](../labs/066-postgresql-backup-and-disaster-recovery-acceptance-lab.md), [inspection SQL](../labs/sql/066-dr-inspect.sql), [fixture SQL](../labs/sql/066-dr-fixture.sql) and [scorecard CSV](../labs/acceptance/066-dr-acceptance-scorecard.csv). Attach timestamps, commands, exit codes, manifest hashes, archive inventory, recovery logs, SQL results, metrics screenshots, RPO/RTO calculation, deviation log and named approvers.

**PASS requires all mandatory gates proven, no unresolved critical findings, achieved RPO/RTO within signed limits, and explicit signoff.** Any unexecuted mandatory test is NOT VERIFIED and cannot count as PASS. GitHub publication is not runtime acceptance.

## Official references

- https://www.postgresql.org/docs/18/backup.html
- https://www.postgresql.org/docs/18/continuous-archiving.html
- https://www.postgresql.org/docs/18/app-pgbasebackup.html
- https://www.postgresql.org/docs/18/app-pgverifybackup.html

**Next:** Chapter 067 — PostgreSQL Streaming Replication and High Availability Architecture.