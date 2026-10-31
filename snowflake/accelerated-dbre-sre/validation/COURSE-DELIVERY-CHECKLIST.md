# Snowflake DBRE/SRE — Seven-Session Offline Delivery Checklist

**Audience:** Instructor, training coordinator and new DBRE/SRE learners  
**Mode:** **OFFLINE / PAPER / TABLETOP ONLY** — the seven SQL labs are **not executed**.  
**Total time:** **7 sessions × 60 minutes = 420 minutes**. Use the time breakdown in the source lessons; this checklist follows each lesson's exact agenda.  
**Account requirements:** **No Snowflake account, CLI, warehouse, password, production access or special permission is needed for the offline course.**

**Do not execute live SQL during offline teaching.** Explain example statements on paper or screen without connecting to Snowflake.

**Approval and evidence boundary:** V03 live SQL **USER-DEFERRED / NOT RUN (0/7)**. V04 independent review **SKIPPED BY OWNER / NOT APPROVED**. V05 production **NOT CERTIFIED**. Teaching completion is different from tested operations or production change authorization. No session, grading, or human sign-off is being claimed by this blank checklist.

## Before the course series — facilitator setup

- [ ] Share the [course index](../README.md), [learner workbook](LEARNER-OFFLINE-WORKBOOK.md) and [beginner glossary](BEGINNER-SNOWFLAKE-GLOSSARY.md). For closed-answer assessments, withhold the glossary until after assessment if desired.
- [ ] **Keep the [instructor answer key](INSTRUCTOR-ANSWER-KEY-RUBRICS.md), [instructor guide](INSTRUCTOR-OFFLINE-ACCEPTANCE.md) and [private scoring sheet](INSTRUCTOR-SCORING-SHEET.md) separate** from the learner-only workbook until grading.
- [ ] Explain that SQL snippets are examples to **read**, not commands to run; expected counts, costs and timings are hypothetical unless separately validated later.
- [ ] Use only the synthetic orders and fictional scenarios already included. No customer/patient records, usernames, raw IP addresses, access tokens, real query text or internal secrets in public workbooks.
- [ ] Prepare a whiteboard or shared screen and a private place for any learner responses. Do not put filled-in worksheets or attendee identities into GitHub.
- [ ] Remind learners that operational controls vary by role, edition, account and supported feature. Not knowing a setting is an invitation to ask, **not** to escalate privileges.
- [ ] Leave the review-approval field blank. The owner has chosen to skip V04 human review for now; do not imply that instruction is independently endorsed.

## Standard session procedure

**Start (each session):** Introduce the relevant level and its learning goal; confirm the fictional-data/no-execution rule. Follow the original lesson's five-block, 60-minute agenda below.

**Activity:** Facilitate paper reasoning, diagrams and projected (non-executed) SQL. Distinguish a real `QUERY_ID` from a clearly hypothetical placeholder. Ask learners to state uncertainty and safer next action.

**Finish:** Review the five questions, record only a privately assessed response if an instructor actually graded it, list misconceptions and assign remediation if necessary. Never record `V03_PASS`, `APPROVED`, `CERTIFIED` or `TESTED` from this offline course.

## Level 1 — Fundamentals

**Reference:** [lesson](../level-01-snowflake-fundamentals.md) · [learner exercise](LEARNER-OFFLINE-WORKBOOK.md)

| Original lesson agenda | Minutes | Facilitation checkpoint |
|---|---:|---|
| What Snowflake is and OLAP vs OLTP | 10 | [ ] Contrast analytical and transactional workload needs |
| Storage, compute and cloud services | 10 | [ ] Diagram the three layers and who operates them |
| Accounts, databases, schemas, objects and SQL | 15 | [ ] Label a fictional database.schema.table, row and column |
| Guided beginner lab | 20 | [ ] Group three synthetic orders **by hand**; explain the SELECT/GROUP BY syntax without executing SQL |
| Knowledge check and recap | 5 | [ ] Collect five conceptual answers and distinguish view/table/materialized view |

**Deliverable:** Labeled architecture/schema diagram and synthetic grouped-orders calculation (not SQL output).  
**Safety prompt:** No actual patient/customer data and no live warehouse.

## Level 2 — Administration Fundamentals

| Original lesson agenda | Minutes | Facilitation checkpoint |
|---|---:|---|
| Administrative responsibilities and ownership | 10 | [ ] Separate Snowflake-managed infrastructure from customer DBRE operations |
| Warehouses and lifecycle | 15 | [ ] Explain auto-suspend/auto-resume and cost/startup implications |
| Users, roles and privileges | 10 | [ ] Draw USAGE/SELECT path and least-privilege role assignment |
| Read-only operational lab | 20 | [ ] Walk through read-only warehouse/role SQL and a **hypothetical** query tag, not live execution |
| Check and review | 5 | [ ] Have learner explain why ACCOUNTADMIN is not a training workaround |

**Deliverable:** Role-access checklist plus a fictional query-history investigation plan.  
**Safety prompt:** Do not grant access or elevate role merely to demonstrate the course.

## Level 3 — Performance and Query Optimization

| Original lesson agenda | Minutes | Facilitation checkpoint |
|---|---:|---|
| Query lifecycle and latency components | 10 | [ ] Define elapsed, execution, provisioning and overload waiting |
| Query Profile, scan and joins | 15 | [ ] Sketch scan/join/aggregation and partition pruning |
| Queueing, sizing and workload isolation | 10 | [ ] Explain overload, concurrency and measured sizing decisions |
| Guided query comparison and diagnosis | 20 | [ ] Diagnose a fictional 40-second overload wait + 12-second execution; plan fair measurements and rollback |
| Review | 5 | [ ] Ask why a 1,000-row lab is not production performance proof |

**Deliverable:** Annotated latency breakdown and two hypotheses with safe measurements.  
**Safety prompt:** Never scale or cancel production queries during an offline exercise.

## Level 4 — Monitoring, Observability and Cost

| Original lesson agenda | Minutes | Facilitation checkpoint |
|---|---:|---|
| Golden signals and Snowflake telemetry | 10 | [ ] Separate query latency, freshness, errors and credits |
| Query, warehouse and pipeline monitoring | 15 | [ ] Explain historical Account Usage lag and metric coverage |
| Metering and credit economics | 10 | [ ] Contrast gross credits, billed credits and warehouse/serverless limits |
| Read-only dashboard query lab | 20 | [ ] Design fictional daily/weekly alerts and an investigation for 40% credit growth without SQL execution |
| Review | 5 | [ ] Identify `AVG_QUEUED_LOAD` as time ratio, not a number of users |

**Deliverable:** Hypothetical monitoring scorecard, alert owner and cost-reconciliation plan.  
**Safety prompt:** Never treat `CREDITS_USED` as a complete invoice or stale views as live telemetry.

## Level 5 — Security, RBAC and Governance

| Original lesson agenda | Minutes | Facilitation checkpoint |
|---|---:|---|
| Identity and authentication patterns | 10 | [ ] Identify identities versus roles |
| Roles and least privilege | 15 | [ ] Explain effective privilege and parent-object dependencies |
| Data masking, row policies and audits | 10 | [ ] Differentiate masking from row filtering and privacy-safe aggregates |
| Read-only RBAC investigation lab | 20 | [ ] Trace a fictional access denial and draft an authorized access request |
| Review | 5 | [ ] Ask how to handle raw identity/IP fields in a hypothetical audit export |

**Deliverable:** Least-privilege triage/approval checklist; fictional audit privacy response.  
**Safety prompt:** No sensitive records, broad grants, or ACCOUNTADMIN escalation.

## Level 6 — Data Recovery and Disaster Recovery

| Original lesson agenda | Minutes | Facilitation checkpoint |
|---|---:|---|
| Recovery goals: RPO, RTO and ownership | 10 | [ ] Distinguish lost-data window versus time to usable service |
| Time Travel, UNDROP, cloning, Fail-safe | 15 | [ ] Explain effective retention and last-resort Fail-safe limitations |
| Cross-region/cross-account replication and failover | 10 | [ ] List replication coverage and dependency questions |
| Recovery planning lab | 20 | [ ] Analyze fictional table creation 10:15 versus historical request 10:14; draft recovery decision tree |
| Review | 5 | [ ] Explain why a clone does not certify DR readiness |

**Deliverable:** Paper recovery timeline, permission/retention checklist, RPO/RTO interpretation.  
**Safety prompt:** No restoration, failover or destructive change; do not claim a real restore.

## Level 7 — Production Incident Response

| Original lesson agenda | Minutes | Facilitation checkpoint |
|---|---:|---|
| Incident scope, severity and SLO | 10 | [ ] State user impact, owner, relevant SLI/SLO |
| Five incident failure modes | 10 | [ ] Separate query slowness, warehouse overload, access, cost and stale ingestion |
| SQL evidence capture and triage | 15 | [ ] Describe *real* evidence needed later; hypothetical query IDs are labeled simulated |
| Tabletop runbook exercise | 20 | [ ] Investigate fictional dashboard freshness of 75 minutes vs 15-minute SLO; propose approved rollback and communications |
| Review | 5 | [ ] Produce concise blameless RCA and prevention actions |

**Deliverable:** Fictional incident timeline, impact statement, hypotheses, owner-approved mitigation and action owners.  
**Safety prompt:** Do not cancel unknown production queries or mutate data during teaching.

## After each session — blank private tracking template

| Field | Value / guidance |
|---|---|
| Level and date | `[fill in privately when actually taught]` |
| Instructor/learner identifiers | `[use approved private aliases only]` |
| Actual minutes delivered | `[not recorded]` |
| Workbook activity completed | `NOT ASSESSED` |
| Five-question knowledge check | `NOT ASSESSED /10` |
| Critical safety issues | `NOT ASSESSED` |
| Remediation, owner and reassessment | `[not assigned]` |
| Snowflake runtime executed? | `NO — V03 DEFERRED` |
| Independent approval? | `NO — V04 SKIPPED / NOT APPROVED` |
| Production certification? | `NO — V05 NOT CERTIFIED` |

**Scoring guardrail:** Each level has a separate 10-point knowledge check (suggested 8/10 teaching threshold) and a separate 14-point A–G tabletop (suggested 12/14). Neither score is a production release decision. Any critical safety miss requires remediation, irrespective of the number of points.

## End of seven sessions — final coordinator checklist

- [ ] Seven **60-minute** agendas were used or deviations documented (do not mark complete before actual delivery).
- [ ] The learner workbook was distributed without instructor answers; completed responses remain private.
- [ ] Instructor reviewed 35 questions and used the separate seven-case tabletop rubric, if actual assessments were administered.
- [ ] Every safety-critical misconception is addressed; any follow-up has an assigned teaching owner.
- [ ] Learners can distinguish an example, a query ID placeholder and real authenticated SQL evidence.
- [ ] Completed training records (if any) are retained in the approved private system, **not** GitHub.
- [ ] Any later **live** nonproduction SQL practice is explicitly authorized in a new V03 runbook activity.
- [ ] This draft package remains marked **NOT RUN / V04 NOT APPROVED / V05 NOT CERTIFIED**.

## Reference handoff

- [Seven-course navigation](../README.md)
- [Beginner glossary](BEGINNER-SNOWFLAKE-GLOSSARY.md)
- [Answer-free learner workbook](LEARNER-OFFLINE-WORKBOOK.md)
- [Instructor teaching pack](INSTRUCTOR-OFFLINE-ACCEPTANCE.md)
- [Instructor-only answer key](INSTRUCTOR-ANSWER-KEY-RUBRICS.md)
- [Blank private scoring template](INSTRUCTOR-SCORING-SHEET.md)
- [Offline release inventory](OFFLINE-RELEASE-INVENTORY.md)

**Document status:** Prepared for offline teaching; **no training has been delivered or graded by creating this checklist**. No SQL runtime executed; no V04 approval; no V05 certification.
