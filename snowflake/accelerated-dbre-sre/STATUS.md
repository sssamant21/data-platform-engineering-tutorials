# Snowflake Accelerated DBRE/SRE — Validation Tracker

**Last authored:** 2026-10-30  
**Source:** seven-course onboarding request  
**Scope:** `snowflake/accelerated-dbre-sre/` only; canonical 90-chapter curriculum unchanged.

| Level | File | Authored | Markdown/static QA | Snowflake runtime lab | Independent tech review | Production certification |
|---|---|---|---|---|---|---|
| 1 | [Snowflake Fundamentals](level-01-snowflake-fundamentals.md) | DRAFT | V01/V02 automated PASS; independent review pending | NOT RUN | PENDING | NOT CERTIFIED |
| 2 | [Snowflake Administration Fundamentals](level-02-administration-fundamentals.md) | DRAFT | V01/V02 automated PASS; independent review pending | NOT RUN | PENDING | NOT CERTIFIED |
| 3 | [Snowflake Performance Tuning and Query Optimization](level-03-performance-query-optimization.md) | DRAFT | V01/V02 automated PASS; independent review pending | NOT RUN | PENDING | NOT CERTIFIED |
| 4 | [Snowflake Monitoring, Observability, and Cost Optimization](level-04-monitoring-observability-cost.md) | DRAFT | V01/V02 automated PASS; independent review pending | NOT RUN | PENDING | NOT CERTIFIED |
| 5 | [Snowflake Security, RBAC, and Governance](level-05-security-rbac-governance.md) | DRAFT | V01/V02 automated PASS; independent review pending | NOT RUN | PENDING | NOT CERTIFIED |
| 6 | [Snowflake Data Recovery and Disaster Recovery](level-06-data-recovery-disaster-recovery.md) | DRAFT | V01/V02 automated PASS; independent review pending | NOT RUN | PENDING | NOT CERTIFIED |
| 7 | [Snowflake Production Troubleshooting and Incident Response](level-07-production-incident-response.md) | DRAFT | V01/V02 automated PASS; independent review pending | NOT RUN | PENDING | NOT CERTIFIED |

## Initial V01/V02 CI gate

- **Automated static validation:** PASS — [GitHub Actions run #41061594991](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41061594991).
- **Reproducible command:** `python3 snowflake/accelerated-dbre-sre/validation/validate_courses.py`.
- **Technical audit:** [V01/V02 initial audit](validation/V01-V02-INITIAL-AUDIT.md).
- **Second-pass technical review:** [V02 findings SF-007–SF-012](validation/V02-SECOND-PASS-REVIEW.md).
- **Level 3–4 follow-on review:** [V02 findings SF-013–SF-017](validation/V02-LEVELS-03-04-REVIEW.md); [Level 3 smoke](validation/runtime/level-03-smoke.sql) and [Level 4 smoke](validation/runtime/level-04-smoke.sql) are prepared for **manual nonproduction** runtime testing.
- **Level 5–7 follow-on review:** [V02 findings SF-018–SF-024](validation/V02-LEVELS-05-07-REVIEW.md); [L5](validation/runtime/level-05-smoke.sql), [L6](validation/runtime/level-06-smoke.sql) and [L7](validation/runtime/level-07-smoke.sql) read-only smoke scripts are authored, **NOT RUN**.
- **SQL safety regression tests:** [test_validator.py](validation/test_validator.py), required by the [CI workflow](../../.github/workflows/snowflake-accelerated-static.yml). The latest V01/V02 and V03 offline/mocked validation passed in [run #156](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41124974600).
- **Test execution plan:** [Validation plan](validation/VALIDATION-PLAN.md); [Levels 1–2 smoke pack](validation/runtime/README.md).
- A CI PASS is an initial authoring/safety filter, not execution evidence or an independent security review.

## Latest verification boundary

- [Run #43 — passed](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41103967587) for the prior seven-course validator and regression-test revision.
- **Previous expanded CI check:** [Run #62 — PASS](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41105075877), for the Levels 1–4 revision. **Levels 5–7 expanded CI:** [Run #83 — PASS](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41106248957), commit `61197443f464b657af0fd5fae3528d59d6479f26`, including the read-only L5/L6/L7 smoke scripts and SQL safety regression tests.
- No Snowflake SQL has been executed; all seven runtime labs remain **NOT RUN**.
- **CLI preflight hardening (2026-10-30):** [Windows operator launcher](validation/run-training-preflight.ps1) defaults to read-only, verifies exact org/account locator/region/role/warehouse/database/schema against operator-approved values, and requires typed authorization before L1/L2. [Latest CI #134 — PASS](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41123715672), including PowerShell parse-only validation. **Script has not executed against Snowflake.**
- **Execution attempt (2026-10-30): BLOCKED — no connected Snowflake training session.** Level 1 and Level 2 actual SQL results and query IDs remain unavailable. Same-session query-history capture added to both smoke scripts. [Static CI run #111 — PASS](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41119260657) does not satisfy V03.
- **V03 readiness package:** [operator runbook](validation/V03-EXECUTION-RUNBOOK.md), [preflight blocker register](validation/V03-PREFLIGHT-STATUS.md), [offline evidence checker](validation/validate_runtime_evidence.py) and [blank NOT_RUN template](validation/V03-NOT-RUN-TEMPLATE.json). The offline evidence checker and mock preflight tests passed their CI gates. **No evidence has been submitted.**

## V03 mock execution safety evidence — 2026-10-30

- [Run #144 — PASS](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41124509495): 48 Python tests and a PowerShell mocked nonproduction preflight suite. The mock rejects incorrect account locator/organization/region, admin role, absent nonproduction owner attestation, missing L1 empty-scratch approval, missing L2 acceptance, and a simulated CLI connection error.
- No live Snowflake account was contacted by the mock tests. **All seven V03 runtime labs remain NOT RUN**, and no genuine query IDs exist.

## Latest V03 preflight CI verification — 2026-10-30

- **PASS:** [GitHub Actions run #156](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41124974600) for commit `206521a9a8e6b4fd01e75b66452d6e668002cc0f`. All **48 Python tests** passed; PowerShell syntax parsing and mock-only preflight integration steps passed.
- The simulated launcher verified **positive** Level 1/Level 2 confirmation, correct SQL file selection, pinned role/warehouse/database/schema options, and negative safeguards (wrong account, admin role, absent approval, wrong typed confirmation and mock connection failure).
- **No live Snowflake access:** No connected Snowflake plugin or local workstation/CLI session was available to this chat. All V03 SQL smoke scripts remain **NOT RUN**. No actual query IDs or outputs have been captured; V04/V05 remain pending.
- **Next actionable dependency:** An approved nonproduction Snowflake connection plus verified scratch namespace, budget and independent reviewer. Run Level 1, retain actual sanitized results/query IDs, obtain acceptance, and only then run Level 2.

## Curriculum completion without Snowflake connectivity — 2026-10-30

**User-directed sequencing:** Defer V03 live Snowflake account configuration and execution. Finish the remaining offline authoring and assessment deliverables now; return to runtime validation only when requested and an approved nonproduction account is available.

| Curriculum deliverable | Status |
|---|---|
| Levels 1–7 lesson manuscripts, including each 60-minute agenda | **7/7 AUTHORED** |
| Lesson navigation, source references, SQL safety guards | **Automated V01/V02 PASS**, independent correctness review pending |
| Offline lecture/tabletop activities and expected reasoning | **PREPARED** — [instructor pack](validation/INSTRUCTOR-OFFLINE-ACCEPTANCE.md) |
| Independent review acceptance and enterprise-release requirements | **CHECKLIST PREPARED** — [V04/V05 handoff](validation/V04-V05-REVIEWER-HANDOFF.md); approvals NOT obtained |
| V03 actual Snowflake runtime labs | **DEFERRED — 0/7 RUN**; no verified query IDs |
| V04 formal independent acceptance | **PENDING** |
| V05 production certification | **NOT CERTIFIED** |

**Resume later:** [nonproduction V03 runbook](validation/V03-EXECUTION-RUNBOOK.md) and [readiness tracker](validation/V03-PREFLIGHT-STATUS.md). No more CLI/account configuration is needed for the **offline curriculum**.

## Cross-level technical parity review — 2026-10-31

- **SF-025–SF-029:** [Lesson versus manual SQL consistency audit](validation/V02-CROSS-LEVEL-CONSISTENCY-REVIEW.md) identifies the L2 query-tag mismatch, L3 session-history mismatch, and L6 configured-versus-effective retention wording; all three corrections were authored. Different L1/L3 scratch table identifiers are deliberate and cannot be mixed.
- [Cross-level contract regression tests](validation/test_curriculum_consistency.py) cover nine offline lesson/smoke relationships across all seven levels. **[CI run #198 PASS](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41171243260): 60 Python tests and mock-only PowerShell checks passed.**
- This remains **documentation and static-source validation** only; V03 live Snowflake remains USER-DEFERRED / 0 of 7 run, V04 reviewer approval pending, V05 not certified.

## Instructor answer-key and rubric review — 2026-10-31

- **[Technical answer-key review SF-030–SF-035](validation/V02-INSTRUCTOR-ANSWER-KEY-REVIEW.md):** seven levels audited for explanation quality, grading consistency, metric semantics, security, RPO/RTO and critical safety overrides.
- **35/35 knowledge-check answers revised** across all seven lessons: expanded beginner explanations, interpretation caveats, operational safety and synthetic-versus-runtime distinctions.
- **[Instructor grading rubric](validation/INSTRUCTOR-ANSWER-KEY-RUBRICS.md) authored** with five question-specific scoring criteria per level (2/1/0), seven tabletop case rubrics (2/1/0), distinct 8/10 lesson and 12/14 tabletop comprehension thresholds, and a critical-safety override.
- **[Blank scoring sheet](validation/INSTRUCTOR-SCORING-SHEET.md)** prepared for recording 7 × 5 question scores, separate A–G tabletop scores, reviewer aliases and safety remediation. **No learner evaluation has been conducted.**
- **[Offline answer-key QA tests](validation/test_instructor_answer_keys.py)** cover the 35 expanded answers, all seven tabletop rubrics, scoring separation, blank scoring template, safety overrides and deferred-runtime status. **[CI run #244 — PASS](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41171730068): 70 Python tests, PowerShell syntax and fake-CLI checks all passed.**
- This is **author review**, not independent instructor sign-off. V03 remains USER-DEFERRED 0/7, V04 approval PENDING, and V05 NOT CERTIFIED.

## Validation gates
- **V01 Structure:** headings, all seven agenda totals = 60 minutes, README navigation, cross-links and status labels.
- **V02 Safety:** SQL syntax and least privilege; no live secrets, no destructive production operations, training account requirements explicit.
- **V03 Runtime:** execute labs with minimal roles in a training account; record actual outputs, account edition, query IDs and costs.
- **V04 Independent review:** Snowflake administrator and application/data-owner approval.
- **V05 Certification:** applicable enterprise SLOs, security controls, operational sign-off and periodic revalidation.

## Initial validation evidence
- Authored seven standalone lessons with objectives, 60-minute agenda, concepts, hands-on lab, expected outcomes, troubleshooting, quiz/answers and official docs.
- Automated CI verified structural checks, lesson durations, navigation, code fences and obvious unsafe-SQL/secret patterns. **No live Snowflake environment was accessed**.
- Do not count the courses as certified or claim runtime results from illustrative expected outputs.
