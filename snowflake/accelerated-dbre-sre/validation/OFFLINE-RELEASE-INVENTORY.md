# Offline Release-Package Inventory — Snowflake Accelerated DBRE/SRE

**Prepared:** 2026-10-31  
**Audience:** Instructor, DBRE/SRE onboarding lead, independent reviewer and curriculum maintainer.  
**Package scope:** `snowflake/accelerated-dbre-sre/` on draft PR #43, branch `feature/snowflake-7-level-dbre-sre-20261030`. This does **not** revise the 90-chapter canonical curriculum.  
**Release classification:** **DRAFT — OFFLINE TEACHING / AUTHOR QA COMPLETE SUBJECT TO FINAL CI; NOT RUNTIME VALIDATED; NOT PRODUCTION CERTIFIED.**

## Start here — learner and instructor deliverables

| Category | Artifact | Purpose | Readiness |
|---|---|---|---|
| Curriculum index | [README](../README.md) | Seven-course navigation; offline and future runtime rules | Authored |
| L1 | [Fundamentals](../level-01-snowflake-fundamentals.md) | Architecture, objects, synthetic aggregation | Authored; offline teaching |
| L2 | [Administration](../level-02-administration-fundamentals.md) | Warehouses, roles, query evidence | Authored; offline teaching |
| L3 | [Performance](../level-03-performance-query-optimization.md) | Profile/queueing/pruning and controlled comparisons | Authored; offline teaching |
| L4 | [Observability & Cost](../level-04-monitoring-observability-cost.md) | Historical metrics, gross vs billed credits | Authored; offline teaching |
| L5 | [Security & Governance](../level-05-security-rbac-governance.md) | RBAC, access reviews, synthetic-only data | Authored; offline teaching |
| L6 | [Recovery & DR](../level-06-data-recovery-disaster-recovery.md) | Retention, RPO/RTO and recovery tabletop | Authored; offline teaching |
| L7 | [Incident Response](../level-07-production-incident-response.md) | SLO triage, safety, blameless RCA | Authored; offline teaching |
| Instructor activities | [Offline instructor pack](INSTRUCTOR-OFFLINE-ACCEPTANCE.md) | Seven tabletop cases and learner deliverables | Prepared, not yet delivered to learners |
| Teaching answers | [35-question answer key and rubric](INSTRUCTOR-ANSWER-KEY-RUBRICS.md) | Five explained answers per level and per-question 2/1/0 guidance | Author QA complete; independent review pending |
| Assessment record | [Blank scoring sheet](INSTRUCTOR-SCORING-SHEET.md) | Private grading and safety-remediation log | Template only; no learner scores entered |

**Instructional scope:** seven × 60 minutes = **420 minutes**. **No Snowflake account, CLI, or credentials are needed for lectures, worksheets and tabletop assessments.** The offline knowledge-check score (up to 10 per level) and the separate seven-case tabletop score (up to 14) are teaching measures only, not operational validation.

## Source-review, automation and evidence inventory

| Artifact group | Contents / purpose | Status |
|---|---|---|
| Curriculum status | [STATUS.md](../STATUS.md) | Source of truth for V01–V05; V03 NOT RUN, V04 PENDING, V05 NOT CERTIFIED |
| Validation plan | [VALIDATION-PLAN.md](VALIDATION-PLAN.md) | Safety, structural, independent review and runtime acceptance criteria |
| Technical reviews | [Initial V01/V02 review](V01-V02-INITIAL-AUDIT.md), [second pass](V02-SECOND-PASS-REVIEW.md), [L3–L4 review](V02-LEVELS-03-04-REVIEW.md), [L5–L7 review](V02-LEVELS-05-07-REVIEW.md) | Author technical audits; no independent sign-off |
| Parity and teaching reviews | [Cross-level consistency](V02-CROSS-LEVEL-CONSISTENCY-REVIEW.md), [answer-key review](V02-INSTRUCTOR-ANSWER-KEY-REVIEW.md), [documentation/prerequisite review](V02-DOCS-PREREQUISITES-REVIEW.md) | Author QA |
| Static gate and regression tests | [validate_courses.py](validate_courses.py), [test_validator.py](test_validator.py), [test_curriculum_consistency.py](test_curriculum_consistency.py), [test_instructor_answer_keys.py](test_instructor_answer_keys.py), [test_docs_prerequisites.py](test_docs_prerequisites.py) | CI checks for structural/content contracts, not Snowflake execution |
| Seven manual SQL smoke files | [runtime scripts and scope](runtime/README.md) | **Authored, 0/7 executed. Do not run for offline training.** |
| V03 safety/connection handoff | [V03 runbook](V03-EXECUTION-RUNBOOK.md), [preflight readiness](V03-PREFLIGHT-STATUS.md), [PowerShell preflight](run-training-preflight.ps1) | Deferred until owner explicitly resumes V03 in an authorized account |
| V03 evidence templates/checker | [evidence template](RUNTIME-EVIDENCE-TEMPLATE.md), [offline evidence checker](validate_runtime_evidence.py), [blank NOT_RUN example](V03-NOT-RUN-TEMPLATE.json) | Template and static schema only; no real query IDs/results |
| Independent approval handoff | [V04/V05 checklist](V04-V05-REVIEWER-HANDOFF.md) | Reviewer package prepared, **no approvals** |

## Offline deliverable gate / handoff decisions

| Gate | Meaning | State |
|---|---|---|
| Course structure and duration | All 7 lessons with 60-minute agendas and navigation | Completed by author; automated gate required |
| Offline technical source QA | Synthetic arithmetic, safety patterns, answer-key parity, documentation and per-level prerequisites | Author corrections committed; CI verification required |
| External Snowflake documentation | Current official references spot-checked as described in [audit](V02-DOCS-PREREQUISITES-REVIEW.md) | Selected URLs verified; external links may change |
| Instructor usability review | Real novice learner and independent instructor check materials and timing | **PENDING** — cannot self-sign |
| V03 live SQL tests | Real nonproduction account tests, actual results, query IDs, costs and cleanup | **USER-DEFERRED / NOT RUN (0/7)** |
| V04 acceptance | Independent DBA/DBRE, Security and Data Owner sign-offs | **PENDING** |
| V05 production enterprise certification | SLOs, performance baselines, DR evidence, cost/security controls, operational approvals | **NOT CERTIFIED** |
| GitHub PR #43 | Merge | **DRAFT, NOT MERGED** |

## Handoff sequence

1. **Offline instructor:** use the [seven lessons](../README.md), the [instructor pack](INSTRUCTOR-OFFLINE-ACCEPTANCE.md) and [answer key](INSTRUCTOR-ANSWER-KEY-RUBRICS.md). Record **only fictional results** until live runtime testing is explicitly resumed.
2. **Private grading:** use the [blank scoring template](INSTRUCTOR-SCORING-SHEET.md) in a permitted private workspace. Never commit real learner identifiers, patient information or secrets.
3. **Independent reviewers:** inspect [V04/V05 handoff](V04-V05-REVIEWER-HANDOFF.md), technical reviews and approval requirements. Do not mark content independently approved because GitHub Actions passed.
4. **When authorized to resume V03:** verify account identity, role, scratch schema, cost cap and owner ticket; follow the [runbook](V03-EXECUTION-RUNBOOK.md) beginning with L1. Keep sanitized genuine evidence in an approved private store.
5. **Only after V03 and V04:** consider release/certification decisions with named accountable owners. Do not automatically merge draft PR #43.

**Evidence hygiene:** No live Snowflake connection, Snowflake query or real query ID is claimed anywhere in this inventory. Any automatic test count refers to **offline Python/static/mock verification only**.
