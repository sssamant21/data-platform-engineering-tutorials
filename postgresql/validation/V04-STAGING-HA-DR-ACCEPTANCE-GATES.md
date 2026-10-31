# PostgreSQL V04 — Independently Fenced Staging HA/DR Acceptance Gates

**State:** PLAN ONLY · **No staging tests executed** · **NOT CERTIFIED**  
**Dependency:** V03 PostgreSQL 18 disposable HA, PITR, and actual-rewind evidence  
**Scope:** Chapter 049 failover/rejoin and Chapter 050 end-to-end acceptance

## Purpose and constraints

Disposable CI exercises establish specific PostgreSQL mechanics, **not** that real infrastructure keeps an old primary from becoming writable again. The staging rehearsal must use an **explicitly approved, non-production** cluster with an application-compatible routing path, an independently provisioned fencing control, backups, WAL archive and rollback plan.

**Do not run this checklist in production.** The following are evidence-gating steps, **not executable promotion or infrastructure-disabling commands**. Do not proceed without identified owners and an approved maintenance/change window.

## Pre-authorized conditions (all mandatory)

| Gate | Evidence to preserve | Pass/Fail |
|---|---|---|
| Change / test ticket, environment and authorization | Ticket, environment owner, UTC start/end, approvers | |
| Disaster and data-loss objectives | Approved HA RPO, HA RTO, PITR RPO and PITR RTO in explicit units | |
| Identity and safety boundary | Exact cluster IDs, PostgreSQL major, node roles, endpoints, data directories, environment tags | |
| Healthy baseline | Replica replay gaps, network health, application error rates, WAL capacity, archive/backup status | |
| Fencing design | Controls that deny old-primary **write and restart** paths even after a failed service stop; independent observer/owner | |
| Verified independent recovery | Manifest-verified base backup and tested off-node WAL continuity, separate restore destination | |
| Rollback/no-go decision maker | Named incident commander, DBRE, application owner, and recovery path | |

## Phase 1 — Baseline and candidate freshness

1. Record source and candidate identities, timelines, LSNs, replay progress, sync mode, and role from separate observation channels.
2. Establish a uniquely identified *synthetic* business transaction with client acknowledgment timestamp and immutable trace ID.
3. Observe the candidate's durable/replayed transaction and capture the acknowledged marker position.
4. If recovery gap exceeds approved business RPO, **NO-GO**; do not promote.
5. Record UTC timestamps for detection and the expected service recovery boundary; establish unchanged routing before the test.

## Phase 2 — Independent fencing proof (**hard NO-GO** if unproven)

Independent fencing is **not** the same as stopping PostgreSQL. Verify that a separate control denies the former primary's write service and that the control remains effective if the old OS/service/HA agent attempts to restart or another client reaches its prior IP, DNS, proxy or storage path.

| Attack/path to block | Independent observation |
|---|---|
| Old primary restarts as writable | Fence remains enforced, status and system evidence captured |
| Client connects directly to old endpoint (not just proxy) | Write path denied, connection result and credential scope recorded |
| HA controller reschedules old instance | Controller cannot restore writable old-primary without explicit rejoin approval |
| Misconfigured DNS/proxy sends writes to old instance | Route cannot deliver successful writes |
| Shared storage/storage attachment bypass | Storage-level ownership/exclusivity verified where relevant |
| Monitoring blind spot | Two different observation channels confirm fence effectiveness |

Require a named, independent approver to sign off before proceeding. **If any path remains ambiguous, STOP before promotion.**

## Phase 3 — Controlled candidate promotion and application validation

Only with approved fencing and an acceptable candidate replay position, a human operator can carry out the pre-approved platform-specific promotion procedure. Verify new timeline, writable state on exactly one approved endpoint, recorded client failover behavior, and application health.

Do not equate database SQL readiness with application service restoration. Measure actual client transaction success, correctness, retry/idempotency behavior, queue and connection pool recovery, observed error rates and rollback safeguards.

## Phase 4 — Rewind/rebuild decision

1. Preserve the former primary's original data directory, logs, identity, target backup and WAL ancestry evidence.
2. Confirm former primary **stopped and fenced**, clean shutdown status, page checksums or `wal_log_hints`, `full_page_writes`, consistent binary versions and WAL history availability.
3. Confirm approved source/target directions and execute a dry-run before any actual rewind; **on any failure, do not start the old writer**. A partially failed rewind may require rebuilding.
4. Require approval for actual rewind or choose a fresh `pg_basebackup` to a newly empty path, never overwrite an unverified existing PGDATA.
5. Before startup require `standby.signal` and correct upstream `primary_conninfo`, then verify streaming, replay catch-up and single-writer invariant from outside the database.

## Phase 5 — Independent PITR and WAL durability acceptance

- Restore the verified backup and archived WAL onto a **separate** staging recovery target; include off-host / object-store access and archiving-gap test as authorized.
- Prove target point, timeline and exact good/bad marker invariants. Assert **zero unwanted rows** and expected valid records.
- Record backup/WAL manifest, restore log, command failures, byte counts and recovery-point evidence. Recovery target must not receive application writes before validation.
- Simulate one documented archive gap or unavailable backup in an isolated context; verify **nonzero refusal** and safe recovery fallback.

## RPO/RTO computation

| Metric | Required UTC observations | Calculation |
|---|---|---|
| HA RPO | Acknowledged source commits and last recovered/verified candidate commit | Latest acknowledged transaction missing after recovery; report count and elapsed business time |
| HA RTO | Business service failure/detection, failover authorization, fence, promotion, restored **client** transactions | End-to-end actual client outage duration (include delays, not SQL-only readiness) |
| PITR RPO | Last legitimate committed marker and verified recovered last-good point | Difference between required recovery point and actually recovered legitimate data |
| PITR RTO | Detection, approval, backup selection, WAL restore, verification, app recovery | End-to-end detection through validated service restoration |

**Do not fabricate numerical objectives.** Record the actual approved SLA/SLO thresholds and compare measured evidence with those thresholds. If no approved threshold is available, the objective gate is **NOT ASSESSED**, never a pass.


## Offline evidence preflight — V04-A

Before the staging change review, complete the [evidence capture template](v04_staging_evidence.template.json) with **actual, independently retained evidence references** and run the [non-operational checker](v04_staging_readiness.py). It uses only the Python standard library, opens no network connections and **never executes PostgreSQL, cloud, fencing or promotion commands**.

```bash
python3 postgresql/validation/v04_staging_readiness.py \
  --evidence /secure/staging-evidence-review.json \
  --json-out /secure/staging-no-go-screen.json
```

Copy the template to an approved private evidence location; do not check completed change tickets, operator identities, screenshots, secrets or credentials into a public Git repository. This checker is for **metadata and freshness screening only**, not evidence authenticity. Replace placeholders with real staging evidence; the provided template is deliberately incomplete and must yield exit code **2**, `NO_GO`.

A fully populated *self-attested* packet returns exit code **0** and `EVIDENCE_COMPLETE_FOR_INDEPENDENT_REVIEW`. That means only that required metadata fields, timestamp windows, four distinct approvals, objectives, observed replay, reported independent fencing controls, archived backup/restore evidence, application routing, and rollback references are present. It **does not** authenticate those records, prove real fencing, authorize staging changes, or certify RPO/RTO. The output always states `authorization=NONE` and `execution=NEVER`.

The [dedicated V04 CI job](../../.github/workflows/postgresql-v04-staging-readiness.yml) executes synthetic regression cases only; its green status establishes that the checker refuses incomplete evidence, **not** that any actual staging environment is safe. An independent change authority must still verify the source evidence and approve every live step, with a hard NO-GO on ambiguous fencing or unverified rollback.

## Independent evidence review — V04-B

The [V04-B private review process](V04B-INDEPENDENT-STAGING-REVIEW.md) adds four separate independent reviewer attestations and six evidence domains to the existing V04-A staging packet. The [offline checker](v04_independent_review.py) binds the review to the exact V04-A metadata digest, change ticket, cluster identity, and time window. The [public review template](v04_independent_review.template.json) is deliberately incomplete and yields **NO_GO**. The [synthetic CI workflow](../../.github/workflows/postgresql-v04-independent-review.yml) tests program behavior only.

**No genuine staging records, external evidence, operator approvals, or independently observed fencing have been supplied. V04-B remains NO_GO for operations; an evidence-complete packet is not a change authorization.**

## Final decision

All mandatory Chapter 050 rows must be independently signed and reference immutable evidence (commit/SHA, job/workflow ID, UTC logs, system ID, approver), including rollback readiness, alerting and runbook correctness. A green V03 disposable result **cannot waive** a V04 gate.

**Current decision: STAGING_TESTS_PENDING / INDEPENDENT_FENCING_PENDING / ENTERPRISE_NOT_CERTIFIED.**
