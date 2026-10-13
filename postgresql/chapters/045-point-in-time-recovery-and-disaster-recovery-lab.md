# Chapter 045 — Point-in-Time Recovery and Disaster Recovery Lab

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Authored; runtime verification pending

## 1. Mission

Execute a disaster-recovery tabletop and an isolated PostgreSQL point-in-time recovery (PITR) drill. Simulate accidental modification of application data, select a recovery point, restore a verified physical base backup, replay archived WAL to a safe target, validate the recovered state and measure achieved RPO/RTO. This capstone integrates [Chapter 041](041-postgresql-backup-architecture-and-recovery-objectives.md), [042](042-logical-backups-with-pg_dump-pg_restore-and-pg_dumpall.md), [043](043-physical-backups-with-pg_basebackup-and-backup-manifests.md) and [044](044-wal-archiving-restore-commands-and-pitr-foundations.md).

**Safety:** use a dedicated self-managed PostgreSQL 18 lab cluster, an isolated restore host/container, an empty restore data directory, and test-only data. Never overwrite production PGDATA or run intentional destructive drills on a shared database.

## 2. Incident scenario

A service stores critical order records. After a known-good base backup and verified WAL archiving, a test operator commits an accidental update that corrupts order status. The DBRE must identify a recovery target **before** the unwanted commit, restore an isolated cluster, verify that good records remain and the accidental change is absent, and propose a safe reconciliation/cutover plan.

**Important:** a timestamp sampled before a transaction is not proof of the exact commit boundary. Record UTC timestamps, WAL LSNs, application markers and logs. If possible, use a PostgreSQL named restore point or an independently verified LSN/transaction boundary for precise drills. Do not claim zero loss without measuring the recovered commit state.

## 3. Architecture

```text
Disposable PG18 primary
   |-- pg_basebackup + backup_manifest --> protected base backup
   |-- continuous WAL archive ----------> protected WAL + timeline history
   |-- before marker -> incident marker -> unwanted transaction
                                               |
                              isolated restore PG18 instance
                              base backup + restore_command
                              recovery.signal + target
                                               |
                              replay -> pause -> verify -> promote only if approved
```

A backup manifest can verify file integrity, but only a successful restore/replay and application validation demonstrates recoverability.

## 4. Recovery objectives and measurement

| Objective | Example target | Evidence |
|---|---|---|
| RPO | 5 minutes | Last good committed event recovered versus incident/recovery decision time |
| RTO | 60 minutes | Detection + authorization + provisioning + restore + replay + validation + cutover |
| Retention | 7 days PITR window | Base backup + uninterrupted WAL and history |
| Integrity | No unapproved corrupt updates | Row-level verification and business invariants |

These are **illustrative** targets. Document the workload, failure domain and actual achieved values. A PITR target before the bad transaction may intentionally exclude legitimate transactions committed afterward; plan reconciliation.

## 5. Preflight and readiness gates

1. Confirm PostgreSQL 18 major version, compatible binaries, replication permissions, archiving and `full_page_writes`.
2. Confirm a recent physical base backup, successful `pg_verifybackup`, and independently verified archive continuity to the intended recovery target.
3. Check backup/restore host disk, tablespace mapping, WAL transfer, encryption, access controls and timeline history.
4. Check primary WAL archiver health, failed attempts, replication slots and `pg_wal` headroom.
5. Confirm test data ownership, restore isolation, recovery target approval, operator roles and stop conditions.

Run [preflight SQL](../labs/sql/045-preflight.sql) read-only on the disposable primary.

## 6. Drill sequence

### A. Prepare test data and a base backup

Run [fixture SQL](../labs/sql/045-fixture.sql) on the disposable primary. Create and verify a physical base backup while continuous WAL archiving is enabled. Verify backup files and WAL retention before introducing the incident.

```bash
pg_basebackup -h 127.0.0.1 -p 5432 -U backup_user -D /secure/lab/ch045-base -Fp -Xs -P
pg_verifybackup /secure/lab/ch045-base
```

The destination must be new, empty and outside a live PGDATA. Use approved credentials and protected storage. If the base backup finishes before the marker, it can be used to replay through that marker and toward the chosen recovery target.

### B. Establish a known-good boundary

Run [good-marker SQL](../labs/sql/045-good-marker.sql), then capture the committed marker and UTC time. Ensure the WAL containing the marker has been archived. For a precise exercise, record a named restore point using `pg_create_restore_point` on a suitable primary after the marker commits and verify that WAL is archived. The named restore point is a server-side WAL record and requires appropriate privileges; the lab script does not create one automatically.

### C. Simulate the incident

On the disposable primary **only**, run [incident SQL](../labs/sql/045-incident.sql). It marks test rows as `corrupted` and commits. Record incident time, affected row count, and the approximate observed WAL LSN. Preserve evidence; do not repeat the operation against a shared system.

### D. Restore to an isolated cluster

1. Copy the verified base backup to an **empty, isolated** PGDATA on a separate PostgreSQL 18 instance, with correct ownership and tablespace paths.
2. Configure a tested `restore_command` to fetch WAL from the protected archive.
3. Set `recovery_target_time` to an approved point after the good marker but before the incident commit, or select a verified named restore point/LSN; set `recovery_target_action='pause'`.
4. Create `recovery.signal` in the isolated restored PGDATA. Start PostgreSQL and monitor logs until the requested target is reached.
5. Validate before promotion. Do not open application writes or promote automatically.
6. If the target is wrong or a WAL segment is missing, stop, preserve logs and restart the rehearsal from a clean restore—not by improvising on production.

```conf
# Illustrative settings for the isolated restore instance only
restore_command = 'cp /secure/lab/wal-archive/%f %p'
recovery_target_time = 'REPLACE_WITH_APPROVED_UTC_TIMESTAMP'
recovery_target_action = 'pause'
```

The `restore_command` shown assumes a POSIX isolated lab host and a fully populated local archive; adapt to the actual tested storage system. Do not use the placeholder timestamp literally.

### E. Verify and decide

Run [verification SQL](../labs/sql/045-verify.sql) against the recovered instance **while queries are permitted at the paused recovery point**. Confirm the good marker exists, corrupt rows are absent, expected row counts match and application invariants hold. Document timeline, achieved RPO/RTO and any legitimate post-target transactions needing reconciliation. Only then consider controlled promotion and cutover.

## 7. Disaster recovery cutover plan

**Decision:** business owner approves recovered state and expected data loss. **Fence:** prevent split-brain writes and stop competing primary traffic. **Provision:** establish isolated target credentials, extensions, roles, DNS and networking. **Validate:** checks, query latency, replica topology, job state, sequence values and application smoke tests. **Cutover:** switch application connections under change control; monitor errors and data freshness. **Rollback:** preserve the original source and logs; define a reconciliation strategy rather than assuming reverse failover is trivial.

## 8. Failure drills and troubleshooting

| Failure | Evidence | Response |
|---|---|---|
| Missing WAL segment | Recovery log requests unavailable file | Verify archive chain; select another valid base backup |
| Target before base backup | Recovery never reaches requested point | Choose backup preceding target |
| Wrong timezone | Unexpected recovered rows | Normalize to UTC, verify commit boundary |
| Wrong timeline | Timeline history and replay divergence | Select correct recovery timeline |
| WAL archive backlog | pg_stat_archiver failures, disk growth | Fix archival, preserve WAL, avoid manual deletion |
| Manifest passes but restore fails | Startup errors or missing tablespaces | Test actual restore and dependencies |
| Bad update still present | Verification query | Reject target, restore again from clean backup |
| Excess data loss | Missing good transactions | Revisit target, reconcile with business approval |

## 9. Acceptance and evidence

Record base backup manifest, archive continuity proof, recovery target, restore logs, row-level validation, actual recovered timestamp/LSN, measured RPO/RTO, security controls, approval, stop conditions and post-incident actions.

**Pass:** isolated recovery reaches a verified point, preserves good records, excludes test corruption and documents realistic cutover/reconciliation. **Runtime status:** not executed; PostgreSQL 18 PITR drill pending.

## Official references

- [Continuous archiving and PITR](https://www.postgresql.org/docs/18/continuous-archiving.html)
- [pg_basebackup](https://www.postgresql.org/docs/18/app-pgbasebackup.html)
- [pg_verifybackup](https://www.postgresql.org/docs/18/app-pgverifybackup.html)
- [Recovery target settings](https://www.postgresql.org/docs/18/runtime-config-wal.html#RUNTIME-CONFIG-WAL-RECOVERY-TARGET)

**Next:** Chapter 046 — Backup Monitoring, Restore Validation and Recovery Automation.
