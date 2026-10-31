# Instructor Scoring Sheet — Offline Snowflake DBRE/SRE Curriculum

**Template only — NO learner has been assessed; NO instructor has signed off.** This is not live SQL evidence, V03 verification or production certification. Store completed evaluations only in an approved private location; do not commit names or sensitive learner details to GitHub.

| Session metadata | Fill in locally |
|---|---|
| Learner alias (non-identifying) | `[enter privately]` |
| Instructor alias | `[enter privately]` |
| Session date (UTC) | `[enter]` |
| Lesson material revision / git SHA | `[enter]` |
| Review ticket / private evidence location | `[enter]` |
| Assessment type | `OFFLINE_ONLY` |
| V03 runtime | `NOT RUN — DEFERRED` |
| V04 independent sign-off | `PENDING` |
| V05 production certification | `NOT CERTIFIED` |

## Per-level knowledge-check scoring (each of five questions is 0, 1 or 2)

Use the [question-specific answer key](INSTRUCTOR-ANSWER-KEY-RUBRICS.md). Score 2 only for correct reasoning plus its essential distinction or safety implication; 1 for an incomplete but non-dangerous answer; 0 for wrong/unsafe. Mark **REMEDIATION_REQUIRED** for any critical safety miss regardless of total.

| Level | Q1 (0–2) | Q2 | Q3 | Q4 | Q5 | Total /10 | Provisional >=8/10? | Critical safety error? |
|---|---:|---:|---:|---:|---:|---:|---|---|
| 1 — Fundamentals | — | — | — | — | — | — | Not assessed | Not assessed |
| 2 — Administration | — | — | — | — | — | — | Not assessed | Not assessed |
| 3 — Performance | — | — | — | — | — | — | Not assessed | Not assessed |
| 4 — Observability/Cost | — | — | — | — | — | — | Not assessed | Not assessed |
| 5 — Security/Governance | — | — | — | — | — | — | Not assessed | Not assessed |
| 6 — Recovery/DR | — | — | — | — | — | — | Not assessed | Not assessed |
| 7 — Incident Response | — | — | — | — | — | — | Not assessed | Not assessed |

## Seven-case tabletop scoring (separate assessment: 14 total)

| Case | Score 0/1/2 | Missing reasoning or misconception | Safety concern / follow-up |
|---|---|---|---|
| A — Synthetic aggregation | — | — | — |
| B — Least-privilege access | — | — | — |
| C — Query overload | — | — | — |
| D — Credits vs. billing | — | — | — |
| E — Security audit privacy | — | — | — |
| F — Historical Time Travel | — | — | — |
| G — Data freshness incident | — | — | — |

**Tabletop total:** `[not assessed] / 14`  
**Provisional comprehension target:** `[not assessed]` (12/14 or higher **and** zero critical safety errors)

## Remediation and sign-off (must remain blank until a real review)

| Check | Outcome |
|---|---|
| Critical safety errors? | `NOT ASSESSED` |
| Inaccurate/ambiguous answers requiring teaching follow-up | `NOT ASSESSED` |
| Remediation owner and target date | `[not assigned]` |
| Reassessment completed? | `NO` |
| Instructor's offline teaching assessment | `NOT ASSESSED` |
| Independent security/DBRE acceptance | `PENDING` |
| Actual Snowflake query evidence verified? | `NO — V03 DEFERRED` |
| Production certification | `NOT CERTIFIED` |

**Important:** Even if a learner later meets 8/10 on every level and 12/14 on tabletop, those are teaching scores only. Do not update V03/V04/V05 status from this sheet.

References: [all 35 question rubrics](INSTRUCTOR-ANSWER-KEY-RUBRICS.md), [offline instructor pack](INSTRUCTOR-OFFLINE-ACCEPTANCE.md), [V04/V05 handoff](V04-V05-REVIEWER-HANDOFF.md).
