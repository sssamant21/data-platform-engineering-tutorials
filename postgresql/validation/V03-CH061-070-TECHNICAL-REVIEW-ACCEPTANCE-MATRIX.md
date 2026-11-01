# PostgreSQL Chapters 061–070 — Technical Evidence Review and Acceptance Matrix

**Milestone:** V03 technical-evidence reconciliation following the disposable PostgreSQL 18 exercises  
**Review performed:** Repository-owned technical cross-check of existing code, labs, and CI outcome claims. **Not an independent review or enterprise acceptance.**  
**Decision:** PARTIAL_DISPOSABLE_RUNTIME_VERIFIED · EXTERNAL_REVIEW_PENDING · CH070_HA_FENCING_NO_GO · ENTERPRISE_NOT_CERTIFIED.

## Evidence provenance

Use the following GitHub Actions as **disposable laboratory evidence only**. A green workflow does not attest to production or staging safety, business objectives, owner identity, independent approval, or source evidence outside GitHub Actions.

| Evidence | GitHub Actions run | Observed coverage |
|---|---|---|
| One-time fixture and slot guard tests | [#41312015668](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41312015668) | Chapter 064, 066 and 070 fixture safety, Chapter 068 1,000-row WAL/slot create/cleanup; 51 checks |
| Logical backup and restore | [#41312015742](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41312015742) | Chapter 061/062/065 backup, restore, constraints and overwrite refusal; 29 runtime + 9 offline retention checks |
| Physical backup, corrupted-copy refusal and historical PITR | [#41307579380](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41307579380) | Chapter 063/064/066 physical backup and separate paused historical recovery; 21 checks; successful older head (latest-head PITR rerun should be checked separately) |
| Streaming and synchronous commit | [#41312015791](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41312015791) | Chapter 067/069 shared-host physical streaming, FIRST 1 / ANY 2 / remote_apply / external client deadline and unique-ID reconciliation; 42 checks |
| V01/V02 safety and navigation | [#41312015784](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41312015784) and [#41312015795](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41312015795) | Syntax, chapter navigation, static safety patterns; no runtime proof |

**Boundary:** Docker `--network none` means isolated from external hosts; it does **not** make the multiple PostgreSQL processes separate hosts or independent failure domains. CI runner identities and self-reported evidence files cannot replace independently authenticated approval records.

## Chapter-by-chapter acceptance matrix

| Chapter | Verified in disposable PostgreSQL 18 | Critical evidence NOT verified | Current disposition |
|---|---|---|---|
| **061 — Backup strategy** | Actual custom-format dump, TOC, isolated restore, known rows/values | Business-approved RPO/RTO, timed recovery, Windows instructions, off-host recoverability | DISPOSABLE_RUNTIME_PARTIAL |
| **062 — Logical backup/restore** | Custom and directory dump, clean restore, count/total, PK/unique constraint, identity sequence, duplicate rejection; globals **inventory only** | Restoring global roles/security in an isolated approved environment, secret handling, Windows, application permissions | DISPOSABLE_RUNTIME_PARTIAL |
| **063 — Physical backup** | Physical base backup + manifest and corrupted-copy rejection in shared Chapter 064/066 harness | Windows service/account parity, independent off-host storage, encryption and recovery permissions | DISPOSABLE_RUNTIME_PARTIAL |
| **064 — Continuous archive/PITR** | Local WAL archive, target-time PITR, before/after commit outcome, separate paused read-only PGDATA | Off-host WAL chain and timeline continuity, latest recoverable point, actual RPO/RTO | DISPOSABLE_RUNTIME_PARTIAL |
| **065 — Retention/automation** | Isolated logical restore; backup filename overwrite refusal; self-attested CSV rejection tests | Real immutable storage, legal hold authority, dependency graph/WAL retention provenance, authorized deletion policy | DISPOSABLE_RUNTIME_PARTIAL / DELETE_NO_GO |
| **066 — DR acceptance** | Restored deleted reference row and excluded later writes; local PITR fixture | Business RPO/RTO thresholds, independent DR environment, application access, negative-path acceptance, reviewer signatures | DISPOSABLE_RUNTIME_PARTIAL / DR_NO_GO |
| **067 — Physical replication** | Two named physical standbys, active WAL receivers, 201-row propagation, replay LSN observations | Independent hosts/failure domains, network/security, lag SLO under sustained load, DCS and routing | DISPOSABLE_RUNTIME_PARTIAL |
| **068 — Slots/WAL retention** | Guarded physical slot creation, 1,000-row WAL workload, inactive-slot cleanup and refusal checks | **Active consumer slot cannot be dropped** test, ownership/CDC isolation, prolonged WAL growth and safe-size alerts | DISPOSABLE_RUNTIME_PARTIAL |
| **069 — Synchronous durability** | FIRST 1/ANY 2, remote_apply, observed SyncRep wait, external deadline, commit reconciliation, default-setting rollback | remote_write/on latency distributions, service availability impact, nondefault prior config restoration, independent reviewer | DISPOSABLE_RUNTIME_PARTIAL |
| **070 — HA/failover** | One-time marker guard, standby read-only state and streaming observations only | **Independent old-primary fencing, quorum/HA manager, failover, application routing, rejoin, RPO/RTO and negative safety scenarios** | **NO_GO / HA_NOT_VERIFIED** |

**No chapter is fully enterprise-certified.** The entries identify the subset actually exercised, not a completion percentage.

## Technical findings and changes

### PG-REV-069 — HIGH: client timeout must not imply rollback

A blocked `COMMIT` waiting for synchronous acknowledgement may outlive an assumed server-side statement timeout. In earlier CI this caused the workflow to stall until cancellation. The corrected V03 harness observes `pg_stat_activity.wait_event='SyncRep'`, uses a separate bounded **client** deadline, then checks the unique transaction ID on the primary and restored standby. The Chapter 069 lab now explicitly warns that termination of the client does not prove the transaction was rolled back. In production, design idempotent application writes and reconcile ambiguous commits rather than blindly retrying. The corrected [runtime evidence](V03-CH067-070-STREAMING-SYNC-EVIDENCE.md) is **42/42 PASS**.

Official PostgreSQL 18 references: [synchronous_standby_names FIRST/ANY](https://www.postgresql.org/docs/18/runtime-config-replication.html), [statement_timeout](https://www.postgresql.org/docs/18/runtime-config-client.html), [SyncRep wait event](https://www.postgresql.org/docs/18/monitoring-stats.html).

### PG-REV-068 — MEDIUM: inactive-slot lifecycle is not active-owner acceptance

The Chapter 068 disposable test shows safe refusal of invalid states and cleanup of a known inactive slot. It does **not** exercise a slot held active by a replication consumer; the risk of affecting CDC and WAL retention at real scale remains unvalidated. **No active slot should be dropped** to complete this curriculum. Add only a disposable, independent active-consumer refusal experiment, not a general-purpose cleanup script.

### PG-REV-066 — HIGH: a historical PITR PASS is not a business DR PASS

Historical point-in-time correctness was demonstrated, but actual accepted backup retention duration, maximum data-loss exposure, restore time and application cutover were not. Approved **four separate business RPO/RTO objectives**, source-system evidence, operator and independent reviewer sign-off remain mandatory.

### PG-REV-070 — CRITICAL: absence of independent fencing and management quorum

The shared Docker process lab cannot establish split-brain prevention. There has been **no promotion or failover**, no independently observed old-primary write fence and no application writer endpoint test. Chapter 070 remains **NO_GO**. Do not implement a `pg_promote` or improvised service-stop test on a shared environment to bypass this gate.

## Required independent review (not yet performed)

An appointed **independent DBRE technical reviewer** should verify commands, flags, scopes, data and expected outputs for 061–069 against the original GitHub Actions run evidence and official PostgreSQL 18 documentation. Security and backup owners should review global role handling, archive offload, restore credentials, policy controls and slot safety. The application/DR owners should separately approve RPO/RTO and test business recovery.

Record **private** source references, accountable reviewers, dates, decisions and exceptions in an approved change system, not as fabricated fields in public CI. Mark a gate PASS only after independent original-evidence confirmation; an empty reviewer field, green synthetic job, or this matrix is **not** a sign-off.

**Exit criteria for the next technical acceptance:** (1) close high-impact technical exceptions, (2) complete missing safe disposable tests where relevant, (3) have independent DBRE/security review of verified source results, (4) keep unresolved enterprise-specific gates classified PENDING, and (5) maintain a separate explicit **NO_GO** for Chapter 070 until a genuine fenced HA topology is available.

**Related blockers:** [PR #46](https://github.com/sssamant21/data-platform-engineering-tutorials/pull/46) remains **draft/unmerged**; [PR #44](https://github.com/sssamant21/data-platform-engineering-tutorials/pull/44) and [Issue #45](https://github.com/sssamant21/data-platform-engineering-tutorials/issues/45) track separate Chapter 050 staging/enterprise readiness. No production or staging change is authorized.
