# PostgreSQL DBRE V08 — Actual Staging Execution & Evidence Collection

**Document ID:** PG-DBRE-QA-V08 | **Status: EXECUTION PACKAGE, NOT EXECUTED**  
**Owner:** DBRE plus independent APP, DATA, PLT, SEC, FIN and Change Management reviewers  
**Date:** 2026-11-01 UTC | **Scope:** Exact authorized PostgreSQL environment and provider only

## 1. Scope and existing reusable lab

V08 transitions the V01–V07 documentation reviews into **real controlled staging tests** and independently verified proof. There is no available staging hostname, authorization, PostgreSQL runtime, recoverable backup or cloud account connection in this request. Therefore **no real staging tests were performed**, no independent approval obtained and certification remains NOT_CERTIFIED_FOR_PRODUCTION.

Reuse [Chapter 004 lab](../../chapters/004-build-a-reproducible-postgresql-operations-lab.md) and [Chapter 050 HA/DR acceptance](../../chapters/050-high-availability-and-disaster-recovery-acceptance-project.md) rather than building duplicates. Chapter 004 has PostgreSQL 18 primary and two standbys on one disposable host (127.0.0.1:55432–55434); it is useful for exercises but **does not prove HA across failure domains or provider-specific production safety**.

## 2. Mandatory pre-execution approval

| Gate | Owner | Required proof |
|---|---|---|
| P01 | DBRE | Explicit staging cluster/provider/region/major+minor, source and destination identities |
| P02 | PLT/SEC | Isolated non-production network and synthetic data only; cannot write to production |
| P03 | SM | Approved time-window/change ticket, named operator and independent witness |
| P04 | DBRE | Valid backup, needed WAL/timeline or provider latest restorable point |
| P05 | SEC | Restricted monitoring role, secret handling, TLS, evidence privacy |
| P06 | APP/DATA | Approved RPO/RTO and business recovery checks |
| P07 | PLT/DBRE | Independent old-primary fencing and stop/rollback design (HA scope) |
| P08 | DBRE/PLT | CPU/disk/WAL budget and safe abort thresholds |

**Any missing P01–P08 requirement blocks the affected execution.** Do not run a generic failover, session termination, WAL exhaustion, VACUUM FULL, disk filling, backup restore or destructive fault-injection action.

## 3. Phase A — Identity-gated read-only execution

Artifacts:
- [V08-safe-preflight.py](V08-safe-preflight.py): read-only Python 3.10+ launcher, no database library dependency; uses existing psql; preflight refuses unapproved/mismatched target; stores private local output.
- [V08-readonly-staging-preflight.sql](V08-readonly-staging-preflight.sql): query-only PostgreSQL 14–18 identity, aggregates of connections, replication, slots, archive, XID/MXID and logical size.
- [V08-execution-register.csv](V08-execution-register.csv): initially NOT_RUN for all test/approval milestones.
- [V08-independent-review-handoff.md](V08-independent-review-handoff.md): independent reviewers and evidence acceptance.

### Required operator settings (only after approval)

~~~~bash
export V08_EXECUTION_APPROVED=YES
export V08_CHANGE_TICKET=https://internal-approved-change.example/CHG-XXXX
export V08_ALLOWLIST_FILE=/secure/approved-targets.txt
export V08_EXPECT_DATABASE=staging_db
export V08_EXPECT_ROLE=staging_readonly_role
export V08_EXPECT_SERVER_VERSION_NUM=180001
export V08_EXPECT_IS_STANDBY=f
export V08_EVIDENCE_DIR=/secure/v08-evidence

# Separately supply PGHOST, PGPORT, PGDATABASE, PGUSER,
# PGSSLMODE=verify-full, PGSSLROOTCERT and protected PGPASSFILE.
# Allowlist file exact line format: hostname|5432|staging_db.
python3 postgresql/dbre-responsibility-for-postgresql/qa/V08-safe-preflight.py
~~~~

These are **placeholders**, not valid real approvals. Expectation variables must agree with the actual approved connection identity. Configure protected allowlist (0600), protected password file (0600), and pre-existing evidence directory (0700). Outside the Chapter 004 loopback-only lab, enforce verified TLS using PGSSLMODE=verify-full. The local lab explicitly disables TLS and needs a separate narrow opt-in; results are LAB_PASS only.

The launcher requires Linux or WSL for POSIX file-permission enforcement (do not use native Windows for this script). It rejects PGHOSTADDR/PGSERVICE overrides so the reviewed PGHOST tuple remains meaningful. The tool performs one identity query, confirms observed database/role/version/primary-vs-standby role, then a bounded READ ONLY SQL pack. It does not connect to cloud APIs, run backups, restore, promote, change grants or approve tests. Results are written in the **operator's private directory**, not to GitHub. Even read-only SQL can cause load, so stop if the staging owner identifies adverse impact.

## 4. Phase B — Test plan and ownership

| ID | Activity | Required witnessed outcome |
|---|---|---|
| A01 | Read-only preflight | Authorized identity, role and SQL result, no unexpected privileges |
| A02 | Prometheus/Grafana | Exporter metric labels, missing data and incident paging tested |
| A03 | APP observability | Successful user synthetic operation and correct p95/p99 |
| A04 | Incident safety | Bounded lock, connection, WAL slot, vacuum and freeze tests/tabletop |
| A05 | Capacity/FinOps | 14+ actual daily physical disk samples, reserve and invoice checks |
| C01 | Isolated physical/managed PITR | Real restored synthetic data, WAL/restore point evidence |
| C02 | DATA integrity | Source-recovery marker reconciliation and CDC completeness |
| C03 | Independent old-primary fencing (HA) | Old primary provably rejects writes before new primary |
| C04 | Single-writer failover (HA) | Exactly one writer, correct timeline and routing |
| C05 | APP service recovery | Real authentication, read/write, latency and business workflows |
| C06 | RPO/RTO | UTC proof of last recoverable business commit and APP acceptance |
| C07 | SEC/PLT | Secure network, roles, secrets, TLS and no PHI in records |
| C08 | FIN/DBRE | Backup/restore storage headroom and actual provider billing |
| C09 | Failback | Safely rebuild or rewind old primary and prove no dual writer |

Run C01–C09 under **separate approved Chapter 050/vendor-specific procedures**, not from the read-only preflight launcher. For HA, no promotion unless independent fencing has passed. Cloud-managed HA and self-managed failover require different methods and qualified reviewers.

## 5. Phase C — Evidence and certification handoff

1. Capture real environment ID, reviewed code SHA, test ID, UTC timestamp, operator, outcome, sanitized logs, data watermark, SLO target and independent reviewer.
2. Keep actual test logs, potentially sensitive metrics and private endpoint identifiers in the approved restricted evidence system. Do **not** commit private evidence into the public GitHub repository.
3. Update a **private copy** of the [V07 evidence template](V07-evidence-template.json) and run [V07 offline gate](V07-evidence-gate.mjs) in your authorized environment.
4. The gate only checks format: READY_FOR_INDEPENDENT_REVIEW never means CERTIFIED, and fabricated URLs/approval labels can pass it. Reviewers authenticate all claims independently.
5. DBRE, APP, DATA, PLT, SEC and SM must independently verify actual restore, fencing if HA, data integrity, RPO/RTO and client functionality. FIN validates capacity/cost. Formal organizational certification requires a separate approval process.

**Evidence status distinctions:** NOT_RUN, BLOCKED, TABLETOP_PASS, LAB_PASS, STAGING_FAIL, STAGING_PASS. No automatic promotion from local lab or tabletop to staged production-equivalent PASS.

## 6. No-go and rollback

Stop on wrong target identity, missing change ticket, exposure to real patient data, missing WAL archive, unusable restore target, unapproved RPO exposure, unsafe disk/WAL growth, unexpected source writes, inability to fence the old writer, missing independent witnesses, or app/data validation failure.

A restored PostgreSQL server accepting connections is not full service RTO. RPO requires a **business-committed watermark**, not just a replica lag field. Both use UTC and require APP/DATA acceptance.

## 7. Actual completion checklist

- [ ] Approved real staging target, owner and change record supplied.
- [ ] P01–P08 satisfied.
- [ ] Identity-gated read-only SQL executed on approved staging.
- [ ] PostgreSQL version and cloud/provider privileges verified.
- [ ] Prometheus/APP/incident tests actually executed with evidence.
- [ ] Capacity/storage/cost readings and safe workload tests collected.
- [ ] PITR restored in an isolated target; backup/WAL chain proven.
- [ ] HA fencing and one-writer failover witnessed if applicable.
- [ ] RPO/RTO and business correctness formally accepted.
- [ ] SEC, PLT, APP, DATA, DBRE, FIN and SM approvals authenticated.
- [ ] Independent certification authority approves exact service/version/topology.

**Current factual status: V08 execution plan published, zero runtime staging tests completed, zero production certifications granted.**

## Sources

- [PostgreSQL 18 psql options](https://www.postgresql.org/docs/18/app-psql.html)
- [PostgreSQL 18 monitoring views](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [PostgreSQL 18 archiving and PITR](https://www.postgresql.org/docs/18/continuous-archiving.html)
- [PostgreSQL 18 TLS libpq settings](https://www.postgresql.org/docs/18/libpq-ssl.html)
