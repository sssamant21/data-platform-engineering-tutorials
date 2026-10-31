# V04 — Independent Review Packet and Decision Register

**Prepared:** 2026-10-31  
**PR:** [#43 (draft)](https://github.com/sssamant21/data-platform-engineering-tutorials/pull/43)  
**Review scope:** The [seven-course accelerated Snowflake DBRE/SRE track](../README.md) — 7 × 60 minutes, 35 written answer keys, 7 offline tabletop cases, and training-only SQL examples.  
**Current state:** **AWAITING REVIEWER ASSIGNMENT. NO INDEPENDENT REVIEWS HAVE BEEN SUBMITTED OR APPROVED.** This file is an author-prepared request, not a reviewer verdict.

**V03 is explicitly USER-DEFERRED / NOT RUN (0/7). V04 is PENDING. V05 is NOT CERTIFIED.** No one should treat passing Python tests, authored examples, unexecuted SQL, or a review-request comment as real Snowflake runtime evidence.

## How to use this packet

1. Curriculum owner selects **real, independent** reviewers, confirms appropriate organizational authority and records their GitHub handles/team assignments privately or in the PR. No reviewers were invented or auto-assigned when this packet was authored.
2. Reviewers can perform an **offline documentation-only review now**. A documentation approval means exactly that; it does not approve Snowflake role privileges, actual SQL execution, costs, production deploys, restore/failover or data correctness.
3. For every finding, leave a GitHub PR review comment or an issue with a source file/line, severity P0/P1/P2/P3, impact, proposed correction and an accountable owner.
4. Each real reviewer submits an actual GitHub **APPROVED / CHANGES_REQUESTED** review or a documented **BLOCKED / PENDING** disposition. Record a link to the review and its commit SHA. Do not invent reviewers, IDs or decisions.
5. The curriculum owner reconciles all P0/P1 findings. Keep PR #43 **DRAFT** until an explicit owner go/no-go decision; do not infer that a passing CI or blank checklist authorizes a merge.
6. **When V03 is later resumed by the owner**, review verified results/query IDs in the secured evidence store; only then can V04 consider runtime-dependent conclusions and V05 enterprise certification.

## Reviewer assignments and offline decisions

**Decision values:** `NOT_ASSIGNED`, `PENDING`, `CHANGES_REQUESTED`, `BLOCKED`, `OFFLINE_DOCS_APPROVED_ONLY`, `V04_APPROVED_WITH_VERIFIED_RUNTIME_EVIDENCE`. Only a named authorized human reviewer can enter an approval; the last decision also requires independently confirmed V03 evidence.

| Area | Independent human reviewer required | Offline document review | Runtime-dependent acceptance | Reviewer/approval evidence |
|---|---|---|---|---|
| R1 — Instructor/novice learner | Training lead **and** beginner learner | **NOT_ASSIGNED** | Not applicable to teaching-only materials; does not replace V03 | `[no reviewer/review URL]` |
| R2 — Snowflake DBRE/administrator | Senior Snowflake DBA/DBRE | **NOT_ASSIGNED** | **BLOCKED: V03 0/7** | `[no reviewer/review URL]` |
| R3 — Security/IAM and data owner | Independently authorized Security/IAM reviewer **and** data owner | **NOT_ASSIGNED** | **BLOCKED: V03 0/7** | `[no reviewer/review URL]` |
| R4 — Application/FinOps | Data/application owner or FinOps lead | **NOT_ASSIGNED** | **BLOCKED: V03 0/7** | `[no reviewer/review URL]` |
| R5 — DR/incident operations | DR lead **and** incident response owner | **NOT_ASSIGNED** | **BLOCKED: V03 0/7** | `[no reviewer/review URL]` |

## Independent review questions and minimum evidence

### R1 — Beginner teaching quality and course usability

- [ ] Are all seven 60-minute agendas realistic, comprehensible and usable **without a Snowflake login**?
- [ ] Do all 35 knowledge answers explain the *why*, not simply a keyword? Is the 2/1/0 scoring clear and fair?
- [ ] Are the 8/10 per-lesson and 12/14 separate tabletop scores plainly **instructional**, not a production readiness claim?
- [ ] Can an actual beginner complete the seven offline tabletop tasks and explain safe/unsafe outcomes? Record real instructor/learner feedback and defects, **not a fabricated score**.
- [ ] Are offline teaching scripts, expected arithmetic and QA SQL distinguished adequately? Check [instructor pack](INSTRUCTOR-OFFLINE-ACCEPTANCE.md), [answer key](INSTRUCTOR-ANSWER-KEY-RUBRICS.md) and [blank scoring sheet](INSTRUCTOR-SCORING-SHEET.md).

### R2 — Snowflake technical accuracy, scope and SQL safety

- [ ] Cross-check architecture, virtual-warehouse/session concepts and role/privilege prerequisites against current official Snowflake documentation and actual supported features.
- [ ] Inspect all seven [manual SQL smoke scripts](runtime/README.md) for unsupported syntax, result-set behavior, account edition/privilege gaps, name collisions, TEMP scope, time-based retention constraints and query-history semantics.
- [ ] Confirm Level 2 `QUERY_TAG` cleanup, Level 3 tiny synthetic fixture limitations, and Level 4 Account Usage lag/credit definitions; identify any future tests that require separate CLI sessions.
- [ ] Confirm L6 Time Travel cannot query before table creation, requires effective retention, and has an optional approved writable setup/cleanup distinct from the read-only readiness smoke.
- [ ] List **unverified** runtime assertions separately. Until account-approved V03 execution they are **BLOCKED / NOT RUN**, even if documentation looks correct.

### R3 — Security, patient/customer data and access governance

- [ ] Confirm synthetic-only fixtures; no real patient/customer identifiers, usernames, IPs, credentials, private keys or sensitive query text in teaching artifacts or exported evidence.
- [ ] Review role inheritance, database/schema/table privileges, secondary roles, `SHOW GRANTS` interpretation, and monitoring/audit access boundaries.
- [ ] Verify the safety policy: no casual `ACCOUNTADMIN` escalation, grants, production object manipulation or unexplained code execution.
- [ ] Check that the optional Login History exercise is approved/aggregated and access denial is recorded as blocked instead of bypassed.
- [ ] Ensure independent security approval is not inferred from a synthetic CI pass.

### R4 — Application operational usefulness, telemetry and cost

- [ ] Check that each performance example separates execution, provisioning, overload queueing and blocking; `AVG_QUEUED_LOAD` is a time-ratio, **not user count**.
- [ ] Confirm `CREDITS_USED` (gross warehouse usage) is separated from `CREDITS_BILLED` (account billing), that view latency and privilege limitations are stated, and that serverless/budgets are not mislabeled as resource monitors.
- [ ] Review practical ownership/escalation, real workload SLO definitions and dashboard alerts as conceptual examples only. No credits or performance gains were measured.

### R5 — Disaster recovery and incident response

- [ ] Distinguish Time Travel, Fail-safe, UNDROP, clone, replication and failover; explain applicability and edition/object-type limits.
- [ ] Confirm RPO = acceptable data-loss window; RTO = acceptable time to restore a **usable** service, including dependencies.
- [ ] Review incident table-top exercises for impact, timestamps, queueing vs ingestion freshness, owner-approved reversible mitigations, evidence hygiene and blameless RCA.
- [ ] No production cancellation, restore, failover, data-loss exercise or operational drill was completed; a document review cannot certify DR readiness.

## Defect and follow-up register (blank by design)

Use this sample schema for *actual* reviewer findings. **No defects or reviewer decisions have been recorded by independent reviewers.**

| ID | Reviewer/review URL | File/line | Severity | Issue/impact | Owner | Fix commit / retest | State |
|---|---|---|---|---|---|---|---|
| `[assigned after review]` | `[not supplied]` | `[not supplied]` | `[P0–P3]` | `[not supplied]` | `[not assigned]` | `[not available]` | `NOT_REVIEWED` |

Severity and gates are defined in [validation plan](VALIDATION-PLAN.md): P0/P1 items block their relevant acceptance until corrected and independently rechecked. An empty reviewer-defect register means **no independent review evidence**, not "zero defects."

## Review handoff evidence to record after actual review

| Evidence | Current value |
|---|---|
| Reviewer identity and GitHub review link(s) | `NOT PROVIDED` |
| Commit SHA reviewed | `NOT RECORDED` |
| Instructor/beginner usability decision | `NOT_ASSIGNED` |
| DBRE technical documentation decision | `NOT_ASSIGNED` |
| Security/IAM/data-owner documentation decision | `NOT_ASSIGNED` |
| FinOps/app-owner documentation decision | `NOT_ASSIGNED` |
| DR/incident documentation decision | `NOT_ASSIGNED` |
| Remaining reviewer P0/P1 findings | `NOT ASSESSED` |
| V03 live Snowflake SQL evidence | `USER-DEFERRED / 0 of 7 NOT RUN` |
| V04 independent runtime acceptance | `PENDING / BLOCKED ON V03` |
| V05 enterprise certification | `NOT CERTIFIED` |
| PR #43 merge decision | `DRAFT / NOT AUTHORIZED` |

## Quick handoff links

- [Offline release inventory](OFFLINE-RELEASE-INVENTORY.md) — seven lessons, 35 answers and evidence/CI boundary.
- [Latest status](../STATUS.md) — V01 through V05 tracking.
- [Seven-course README](../README.md) — offline-first teaching entry point.
- [V04/V05 reviewer acceptance](V04-V05-REVIEWER-HANDOFF.md) — role ownership and future release requirements.
- [V03 readiness and runbook](V03-PREFLIGHT-STATUS.md) — **deferred** runtime work only; do not resume without user authorization.

**This packet is ready to send to selected reviewers, but no review request was assigned to a named GitHub user or team at creation.**
