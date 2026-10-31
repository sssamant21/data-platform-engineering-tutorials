# Snowflake DBRE/SRE — Offline Learner Workbook

**Seven 60-minute workshops | Learner edition | No answer key**

Use this workbook alongside the [seven-lesson course index](../README.md). It is designed for **offline teaching without a Snowflake account, CLI, warehouse, or real data**. All scenarios, datasets, timing, identities, and incidents are fictional. **Do not execute SQL or collect credentials.** The instructor uses a separate [answer key and rubric](INSTRUCTOR-ANSWER-KEY-RUBRICS.md); the workbook intentionally supplies questions and answer spaces, **not solutions**.

**Assessment boundary:** Any notes below are learner responses, not actual Snowflake query evidence. No runtime validation has been performed (V03 **USER-DEFERRED / NOT RUN, 0/7**). Independent review V04 **SKIPPED BY OWNER / NOT APPROVED**; production certification V05 **NOT CERTIFIED**. Keep private learner responses out of public GitHub commits.

## Learner instructions

Read the specified lesson and complete each section by explaining **why**, not just writing a Snowflake keyword. Mark uncertainty plainly. Use fictional object names and sanitized examples. An instructor may discuss model answers *after* completing the exercise. Treat account- and edition-dependent questions as design hypotheses until authorized runtime verification. Store completed worksheets in an approved private location.

Each course has five short knowledge questions, one applied exercise, and one safety check. The instructor grades five knowledge questions (0–2 each; **10 points per level**) and separately scores the seven final scenarios (0–2 each; **14-point tabletop**). Do not add the two scores or treat either as proof of production readiness.

---

## Level 1 — Fundamentals

**Reference:** [Level 1 course](../level-01-snowflake-fundamentals.md)  
**Learning goal:** Explain platform components, database objects and a synthetic aggregation.

### Five learner questions

1. Name the three core parts of Snowflake's architecture. What does each part do?
2. In `PRACTICE_DB.LEARNING.ORDERS`, what is the database, schema and table? Explain a row versus a column.
3. What provides compute for typical warehouse-backed SELECT queries? What does this not imply about *all* Snowflake features?
4. How does a standard view differ from a table and from a materialized view?
5. Explain what `GROUP BY REGION` would do to the synthetic orders below; work out the result on paper.

### Applied offline exercise

Assume the three **fictional** orders below. Compute each region's order count and total amount **by hand**, then describe how a `GROUP BY` query could express the calculation. Do not execute SQL.

| Order ID | Region | Amount |
|---|---|---:|
| 1 | EAST | 120 |
| 2 | WEST | 80 |
| 3 | EAST | 50 |

**My grouped output / explanation:** `[write here privately]`  
**Safety check:** Why must the example stay synthetic rather than use identifiable customer or patient records? `[answer]`

## Level 2 — Administration Fundamentals

**Reference:** [Level 2 course](../level-02-administration-fundamentals.md)  
**Learning goal:** Understand managed-service ownership, warehouses, permissions and query evidence.

### Five learner questions

1. What does Snowflake operate, and what remains the DBRE/SRE team's responsibility?
2. Explain `AUTO_SUSPEND` and `AUTO_RESUME`. What cost and latency tradeoff should an operator consider?
3. What measurements and approvals would you require before changing a warehouse size?
4. What is a `QUERY_ID` and how would it support an investigation?
5. Is `ACCOUNTADMIN` a good default role for training and day-to-day operations? Explain.

### Applied offline exercise

An analyst has a permitted training role but gets a simulated query permission error. Draw the object/role permission path (warehouse, database, schema and table). Write the least-privilege access request you would submit instead of escalating your role. Describe how a **hypothetical** query tag and query ID could link a worksheet exercise to history. Do **not** invent an ID and claim it was executed.

**Role path / approval request:** `[write here privately]`  
**Safety check:** What would you do if the lab asks for privileges you do not have? `[answer]`

## Level 3 — Query Performance and Optimization

**Reference:** [Level 3 course](../level-03-performance-query-optimization.md)  
**Learning goal:** Separate queue time, execution time and possible SQL-design problems.

### Five learner questions

1. Why can total elapsed query time differ from execution time?
2. What does `QUEUED_OVERLOAD_TIME` measure? How does it differ from resource provisioning or transaction blocking?
3. What controls make before/after query measurements fair and repeatable?
4. What kinds of evidence can a Query Profile expose?
5. Why can't warehouse resizing fix every slow query?

### Applied offline exercise

A fictional analytics request spends **40 seconds waiting for overload** and **12 seconds executing**. Calculate the combined waiting-plus-execution interval (other components are unspecified); identify the largest contributor, propose two hypotheses and explain what you would measure before changing compute. Discuss why an illustrative **1,000-row synthetic table** is not enough to prove production-scale performance gains.

**Hypotheses / measurable next steps:** `[write here privately]`  
**Safety check:** What additional approval and rollback are needed for a real production capacity change? `[answer]`

## Level 4 — Monitoring, Observability and Cost

**Reference:** [Level 4 course](../level-04-monitoring-observability-cost.md)  
**Learning goal:** Interpret historical warehouse metrics without overclaiming cost or freshness.

### Five learner questions

1. Are `SNOWFLAKE.ACCOUNT_USAGE` views instantaneous? What does a delayed or empty result mean?
2. What does `AVG_QUEUED_LOAD` represent? Why is it not simply the number of users?
3. Which factors affect warehouse credits? How does gross warehouse usage differ from final billed account credits?
4. How would you set a useful p95 latency alert for two applications with different SLOs?
5. Do warehouse resource monitors cover all serverless/AI feature spending? What else should the team check?

### Applied offline exercise

A **fictional** dashboard shows gross warehouse credits increasing by 40%, while the query count is unchanged and queued load is low. Draft an investigation plan distinguishing runtime, warehouse size, billing adjustments and telemetry lag. Design two alerts and state who would own them.

**Metric interpretation / candidate alerts:** `[write here privately]`  
**Safety check:** Why shouldn't the team call a seven-day `CREDITS_USED` total an exact invoice amount? `[answer]`

## Level 5 — Security, RBAC and Governance

**Reference:** [Level 5 course](../level-05-security-rbac-governance.md)  
**Learning goal:** Explain least privilege and privacy-preserving investigation.

### Five learner questions

1. Define least privilege in terms of task, scope and duration.
2. Which object privileges may be needed for a role to SELECT from a table using warehouse-backed compute?
3. Distinguish column masking, row access policies and controlled aggregate/secure views.
4. Why must exercises and exported query history exclude real patient/customer data?
5. What approvals and evidence are necessary before granting or changing access?

### Applied offline exercise

A fictional analyst role can see a database name but gets a permission denial on a specific table. Write a read-only triage and access-review checklist. A second hypothetical audit export contains raw user names, IP addresses and messages: describe how you would handle the export safely without changing production security controls.

**Least-privilege checklist / privacy response:** `[write here privately]`  
**Safety check:** Why is switching to `ACCOUNTADMIN` not an appropriate workaround? `[answer]`

## Level 6 — Data Recovery and Disaster Recovery

**Reference:** [Level 6 course](../level-06-data-recovery-disaster-recovery.md)  
**Learning goal:** Apply Time Travel constraints and recovery objectives safely.

### Five learner questions

1. Define RPO, including what the business owner needs to decide.
2. Define RTO and explain what makes the recovered service usable.
3. What limits historical reads and Time Travel recovery? Consider object type, creation time, retention and permissions.
4. Why is Fail-safe not a routine self-service backup mechanism?
5. Why is an untested zero-copy clone not a complete disaster recovery plan?

### Applied offline exercise

A **fictional scratch table** was created at **10:15**. Someone proposes an `AT` snapshot for **10:14**. Evaluate this proposal without executing SQL, then outline a safe recovery decision tree covering table existence, historical timestamp, effective retention, owner approval, data verification, RPO and RTO. Explain when an actual restored object requires a separate controlled rehearsal.

**Recovery feasibility / decision tree:** `[write here privately]`  
**Safety check:** Which real-data changes must never be run just to complete this offline workbook? `[answer]`

## Level 7 — Incident Response and Troubleshooting

**Reference:** [Level 7 course](../level-07-production-incident-response.md)  
**Learning goal:** Investigate impact and choose owner-approved, reversible actions.

### Five learner questions

1. What should an incident commander establish before deciding on mitigation?
2. Why should the team capture genuine query IDs, timestamps and warehouse context?
3. What can large overload queueing indicate and what other wait categories must be ruled out?
4. May an operator cancel unknown production queries without an impact assessment and authorization? Explain.
5. What makes an RCA blameless, evidence-based and useful for prevention?

### Applied offline exercise

A fictional dashboard is **75 minutes** behind its source; the agreed freshness SLO is **15 minutes**. Write a short incident record including impact, severity, evidence to collect, owner, possible ingestion and downstream causes, proposed reversible mitigation, stakeholder communications and preventive follow-ups. Query identifiers used here must be clearly **simulated placeholders**.

**Incident timeline / hypotheses / approval plan:** `[write here privately]`  
**Safety check:** Why can't you infer that the Snowflake query engine is responsible for every stale dashboard? `[answer]`

---

## Final integrated tabletop — seven cases (score separately from knowledge checks)

For each case, write your *reasoning, assumptions, safer next action and evidence needed*. Use the [instructor-led scoring sheet](INSTRUCTOR-SCORING-SHEET.md) to record results privately after review. **These questions do not include their solutions.**

| Case | Scenario to analyze | Learner response prompt |
|---|---|---|
| A — SQL fundamentals | Three fictional orders above | Explain how to aggregate by region without a live query |
| B — Access | Analyst sees a schema but cannot query a table | Draw privilege dependencies and write a least-privilege request |
| C — Query latency | Fictional 40-second overload wait and 12-second execution | Propose measured hypotheses and reversible mitigation |
| D — Credit reporting | Gross warehouse credits differ from account billed credits | List at least three reasons and propose a reconciliation method |
| E — Audit privacy | Raw login usernames and IP addresses appear in an export | Explain safe handling and what to avoid |
| F — Historical recovery | Fictional table creation 10:15 and historical request 10:14 | Explain feasibility, retention and owner approval |
| G — Freshness incident | Fictional dashboard lag 75 minutes vs SLO 15 minutes | Draft triage and communication, separating pipeline and query concerns |

**My separate tabletop notes:** `[write here privately; do not put personal or real system identifiers in GitHub]`  
**Unknowns or questions for instructor:** `[write here]`

## Learner completion checklist

- [ ] Finished five conceptual questions in each of the seven courses.
- [ ] Completed the seven applied exercises with **fictional** data.
- [ ] Answered seven safety checks and the seven final tabletop cases.
- [ ] Distinguished hypothetical outputs from live evidence.
- [ ] Did **not** execute SQL, upload sensitive datasets or request privileged roles.
- [ ] Shared completed worksheet only in the approved private teaching channel.

**Instructor-only materials:** [grading rubrics](INSTRUCTOR-ANSWER-KEY-RUBRICS.md) and [instructor pack](INSTRUCTOR-OFFLINE-ACCEPTANCE.md). Do not use those documents while independently completing the workbook. All grading thresholds are instructional only.

**End-of-workbook state:** `NOT ASSESSED / OFFLINE TRAINING ONLY`. A real instructor must score learner responses; this manuscript does not count as completed training or a Snowflake runtime check.
