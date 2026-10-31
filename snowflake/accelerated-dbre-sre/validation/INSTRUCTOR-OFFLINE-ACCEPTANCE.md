# Instructor Pack — Seven Snowflake DBRE/SRE Courses (Offline Track)

**Audience:** DBRE/SRE beginners, Snowflake administrators, data engineering, security, analytics and application owners.  
**Scope:** Seven independent 60-minute lessons, 420 minutes total.  
**State:** Teaching and static-content readiness; **NO live Snowflake labs have been executed**.  
**Delivery policy:** A lesson may be taught as a lecture/tabletop without account access, but **must not** be described as runtime-validated or production-certified.

## Delivery sequence

| Level | 60-minute course | Instructor demonstration without account | Learner deliverable | Acceptance check |
|---|---|---|---|---|
| 1 | [Fundamentals](../level-01-snowflake-fundamentals.md) | Draw users → cloud services → virtual warehouses → managed storage; label account/database/schema/table/column/row | Explain a fictitious schema and the expected 3-row sample result | Identifies storage/compute/cloud services and computes EAST=2/170, WEST=1/80 by hand |
| 2 | [Administration](../level-02-administration-fundamentals.md) | Draw role/privilege boundary and warehouse auto-suspend lifecycle | Least-privilege checklist and a hypothetical tagged-query evidence record | Distinguishes USAGE, warehouse state, owner approval and 100 generated test rows |
| 3 | [Performance](../level-03-performance-query-optimization.md) | Trace broad scan, selective filter, queueing vs execution, Query Profile | Written hypothesis/measurement plan for a 12s-execution/40s-queue case | Explains why queueing is dominant; expected 1,000/54,110 and region-1 100/5,060 |
| 4 | [Observability & Cost](../level-04-monitoring-observability-cost.md) | Draw query → warehouse → Account Usage metrics → billing and dashboards | One-page metrics/ownership design with daily/weekly alert thresholds | Distinguishes gross credits, billed credits, historical lag and missing privileges |
| 5 | [Security & Governance](../level-05-security-rbac-governance.md) | Draw least-privilege role inheritance and access request approval | Nonproduction RBAC request and risk/redaction checklist | Avoids elevated roles; correctly distinguishes current-user role grants from a full account audit |
| 6 | [Recovery & DR](../level-06-data-recovery-disaster-recovery.md) | Create an incident timeline: write → accidental delete → detection → retention cutoff | Paper recovery plan including prerequisites, point in time, RPO/RTO, approvals | Historical point must follow table creation and fall within effective retention; no real restore claimed |
| 7 | [Incident Response](../level-07-production-incident-response.md) | Facilitate queueing and stale-pipeline tabletop scenarios | Blameless incident record with impact, QUERY_ID *placeholder*, rollback and action owners | Separate query slowness from ingestion freshness; no query cancellation without approval |

**Timing:** Each source lesson already contains a 60-minute agenda. Use its breakdown as the teaching schedule; the above activities supplement the lesson rather than creating extra required instructional minutes.

## Offline review workflow

1. **Instructor** opens all seven lesson Markdown files, checks objectives, relevant roles, expected results, knowledge-check answers and cited Snowflake documentation.
2. **Learner** completes each exercise using fictional/synthetic data. Mark each as `OFFLINE_PRACTICE_COMPLETE`, not runtime PASS.
3. **DBRE technical reviewer** checks command intent, status semantics, edition/permission dependencies, alternative read-only path and change-control boundaries.
4. **Security/data owner** verifies least privilege, synthetic-only sample data, absence of credentials and proper handling of query history and audit records.
5. **Owner** files unresolved P0/P1 issues on PR #43; defer runtime-only questions to [V03 readiness](V03-PREFLIGHT-STATUS.md). Do not merge or certify from this pack.

## Reusable offline tabletop assessment

Each learner submits *one* concise answer to each of these cases; the instructor checks against the rubric below.

| Case | Scenario | Expected reasoning (not live evidence) |
|---|---|---|
| A — SQL fundamentals | Three synthetic orders: EAST 120, WEST 80, EAST 50 | Three rows; EAST 2 orders / 170, WEST 1 / 80; warehouse is compute |
| B — Access | Analyst role can see a schema but cannot query a table | Inspect active role and approved grants; request least-privilege SELECT path; do not escalate to ACCOUNTADMIN |
| C — Latency | Total query delay 52 seconds: 40 queue, 12 execute | Queueing dominates; examine concurrency, load isolation and p95/SLO baseline |
| D — Cost | Warehouse gross usage and daily billed credits disagree | Different billing perspectives and adjustments; use comparable time ranges, latency and cost-accounting boundaries |
| E — Governance | Audit query produces raw usernames/IPs | Stop exporting raw fields; use approved aggregated outcomes and access review |
| F — Recovery | Table created at 10:15; requested snapshot 10:14 | A historical query before table creation is invalid; check effective retention and object type first |
| G — Incident | Dashboard freshness 75min versus 15min SLO | Start with pipeline and upstream load dependencies; preserve impact, incident timeline and approved rollback |

## Detailed answer keys and grading

The [35-question instructor answer key and all seven detailed tabletop rubrics](INSTRUCTOR-ANSWER-KEY-RUBRICS.md) provide clear full-credit, partial-credit and incorrect/unsafe examples for each level. Each level uses five questions × two points (10-point quiz maximum), with a provisional 8/10 comprehension threshold. The seven-case tabletop remains a **separate** 14-point assessment with the existing 12/14 target; neither is evidence of SQL execution. A critical safety miss overrides either score and requires remediation, even at an otherwise passing total.

## Instructor scoring

**Offline tabletop assessment**, not production validation: seven cases, each 0–2 points (0 = incorrect/unsafe, 1 = correct keyword but incomplete reasoning, 2 = correct reasoning plus safety). Target 12/14 or higher, with **zero critical safety errors**, and keep its score distinct from each level's five-question 10-point knowledge check. Do not turn this score into V03/V04/V05 acceptance.

A mandatory safety miss (e.g. production data manipulation, recommending broad admin privileges, leaking identities, assuming synthetic numbers prove runtime behavior) requires remediation regardless of score.

## Important differences between lesson examples and QA smoke scripts

The Level 1 course uses `DBRE_SRE_L1_ORDERS` and its dedicated QA script uses `DBRE_SRE_L1_QA_20261030`; Level 3 likewise uses `DBRE_SRE_L3_SALES` versus `DBRE_SRE_L3_QA_20261030`. These are **separate exercise identifiers**; do not create one and expect the other file to query its state. All use synthetic data and must remain scoped to an instructor-confirmed empty training schema. The Level 2 lesson and smoke script deliberately share the same training `QUERY_TAG` string; it does not imply that they share a CLI session.

The [cross-level consistency review](V02-CROSS-LEVEL-CONSISTENCY-REVIEW.md) distinguishes teaching consistency from actual runtime acceptance.

## Curriculum boundaries and handoff

- **Already authored:** Levels 1–7, agendas, core concepts, annotated SQL, troubleshooting, knowledge checks and answers.
- **Suitable without Snowflake access:** lecture, paper exercises, command explanation, source inspection and simulated incident tabletop.
- **Deferred:** actual SQL compilation/execution, query IDs/results, connection/authentication/role testing, credits, cleanup evidence, recovery/failover and independent production acceptance.
- **Return point:** [V03 execution runbook](V03-EXECUTION-RUNBOOK.md) with an approved nonproduction connection and secure evidence storage.
- **Review handoff:** [V04–V05 reviewer checklist](V04-V05-REVIEWER-HANDOFF.md).
