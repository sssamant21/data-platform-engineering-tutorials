# V02 — Instructor Answer Keys and Assessment Rubric Review

**Date:** 2026-10-31  
**Scope:** All seven 60-minute accelerated Snowflake DBRE/SRE lessons (35 knowledge questions), seven offline tabletop assessments and instructor teaching guidance.  
**Review type:** Source/documentation author QA only; no learner assessment or independent human review.  
**V03 runtime:** USER-DEFERRED / NOT RUN (0/7). **V04:** PENDING. **V05:** NOT CERTIFIED.

## Findings and corrections

| ID | Severity | Finding | Correction and teaching benefit | Status |
|---|---|---|---|---|
| SF-030 | P2 | Five-question keys in each lesson consisted of terse one-line answers | Expanded **all 35** into answer plus beginner explanation, operational distinctions and safe limitations | Authored |
| SF-031 | P2 | No per-question full/partial/incorrect credit rules across the 7 lessons | Published [instructor answer keys](INSTRUCTOR-ANSWER-KEY-RUBRICS.md) with **35 explicit 2/1/0 grading anchors** | Authored |
| SF-032 | P1 | Assessment score could be mistaken for proof of SQL/runtime competence or production approval | Explicitly split **10-point per-level quiz** (provisional **8/10**) from **14-point seven-case tabletop** (provisional **12/14**); both are instructional only | Authored |
| SF-033 | P1 | Unsafe operations could receive a passing score when mixed with correct facts | Added **critical safety override:** unapproved privilege escalation, real patient data, raw credential/identity export, destructive production action or fabricated live evidence requires remediation regardless of score | Authored |
| SF-034 | P2 | Some key terms were not sufficiently precise for newer DBRE/SRE staff | Defined query load as a time ratio; separated gross from billed credits; clarified serverless budget vs resource monitors; RPO vs RTO, standard vs materialized view, Fail-safe and role boundaries | Authored |
| SF-035 | P2 | CI did not assert that every lesson had five explained keys and matching scoring coverage | Added [nine offline regression checks](test_instructor_answer_keys.py) across 35 questions, seven rubrics, safety gates and explicit V03 deferral | Automated gate to verify |

## Technical review notes by level

- **L1 architecture:** The virtual warehouse executes *warehouse-backed* queries; Snowflake also has serverless compute features. The three-layer model remains a useful beginner mental model.
- **L2 operations:** Auto-suspend reduces idle compute charges but startup timing and approved change control still matter. `QUERY_ID` must be captured from a real session for V03, not invented.
- **L3 performance:** `QUEUED_OVERLOAD_TIME`, provisioning and blocking have different causes. Fair tuning compares matching SQL/data, concurrency, caching, latency and credits. The synthetic 1,000-row fixture is not representative benchmarking.
- **L4 FinOps:** `AVG_QUEUED_LOAD` is a time-based load ratio, not exact query/users count. Historical Account Usage latency and `CREDITS_USED` vs `CREDITS_BILLED` boundaries must be explicit. Resource monitors do not control serverless/AI spend; Snowflake budgets can support that monitoring.
- **L5 security:** Parent USAGE/SELECT and warehouse permissions, masking vs row access policies and restrictions on raw identity data. Avoid grants in teaching labs.
- **L6 recovery:** RPO = acceptable lost-data interval; RTO = time to usable service. Time Travel has effective retention/creation-time limits; Fail-safe is best-effort Snowflake-operated fallback, not customer self-service.
- **L7 incidents:** Assess impact and assign owner before mitigation. Separate facts from hypotheses, avoid cancelling unknown queries, and require blameless RCA actions with owners and deadlines.

## Instructor scoring and approval boundary

- Each of 7 lessons: **5 × 2 = 10**. Suggested 8/10 is a teaching threshold, *not* independent approval.
- Seven tabletop cases: **7 × 2 = 14**. Suggested 12/14 is a separate threshold, not a combined test score.
- **Critical safety override** always applies; remediation and re-assessment required regardless of point totals.
- Instructor/learner feedback and independent admin/security review have **NOT occurred**. No certification claims may follow automatically from CI or a teaching quiz.
- Return to [V03 runbook](V03-EXECUTION-RUNBOOK.md) only when the user elects to resume real Snowflake validation.

## Source references

- https://docs.snowflake.com/en/user-guide/intro-key-concepts
- https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_load_history
- https://docs.snowflake.com/en/user-guide/resource-monitors
- https://docs.snowflake.com/en/user-guide/security-access-control-overview
- https://docs.snowflake.com/en/user-guide/data-time-travel
- https://docs.snowflake.com/en/user-guide/data-failsafe

**Automated CI:** Pending final branch-head execution as of initial authoring. Do not mark this gate PASS until GitHub Actions confirms.
