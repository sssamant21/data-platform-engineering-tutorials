# Instructor Answer Keys and Assessment Rubrics — Snowflake DBRE/SRE Accelerated Track

**Review date:** 2026-10-31  
**Curriculum:** Seven independent 60-minute workshops; 35 knowledge-check questions and seven offline tabletop assessments.  
**Scope:** Instructor-facing *offline* answer guidance only. Source lesson questions and expanded beginner answers are in the linked lessons.  
**Evidence boundary:** **NOT RUN (V03)** — no Snowflake CLI/SQL, query IDs, cost, role/permission results or live recovery tests were performed. **V04 independent review PENDING; V05 NOT CERTIFIED.**

## How to grade a learner fairly

For each of the five knowledge-check questions per level, assign:

- **2 — Correct plus reasoning:** The learner states the essential answer and its listed explanation, distinction or safe consequence.
- **1 — Partially correct:** The learner recalls the keyword or one correct fact but omits an important limitation or applied explanation; no unsafe operational recommendation.
- **0 — Incorrect or unsafe:** The answer is wrong, reverses the distinction, recommends a privileged/destructive action without approval, or claims hypothetical results are actual Snowflake evidence.

**Level score:** 5 questions × 2 points = **10 maximum**. A provisional instructional comprehension threshold is **8/10**, provided there are **no critical safety errors**. A quiz score does not satisfy any V03, V04 or V05 gate. Instructor may allow an oral explanation rather than requiring exact Snowflake keywords when the underlying concept is correct.

**Seven tabletop cases:** 7 × 2 = **14 maximum**. The separate teaching rubric target is **12/14** plus **zero critical safety errors**. These are *two distinct scores*: do not add them, average them, or mistake them for operational readiness.

**A critical safety miss overrides numerical scores:** Recommending real patient data in lab queries, unapproved admin role elevation, exposing credentials/PII/raw query text in public outputs, destructive production changes without authorization, assuming a synthetic number is a runtime result, or asserting an untested restore/failover is certified. Require correction and re-assessment. Record `REMEDIATION_REQUIRED` regardless of total.

## Level 1 — [Snowflake Fundamentals](../level-01-snowflake-fundamentals.md)

| Question | Full credit (2) — essential reasoning | Partial (1) | Incorrect/unsafe (0) |
|---|---|---|---|
| 1. Three architectural layers | Storage holds data; warehouse compute runs warehouse-backed SQL; cloud services coordinate metadata/auth/query planning | Names all three without roles, or correctly describes two | Treats cloud services as a user-managed database server |
| 2. Schema | Namespace *inside database* organizing tables/views; understands database.schema.table hierarchy | Says "container for tables" only | Says schema = user, row, server or warehouse |
| 3. Compute runs SQL | Virtual warehouse supplies compute for regular warehouse-backed SQL; serverless exceptions exist | Names warehouse only | Says every Snowflake operation must use a user-selected warehouse |
| 4. Standard view | Stores query definition, not another ordinary table's row copy; contrasts materialized view | "Does not store rows" only | Treats standard and materialized views as identical |
| 5. GROUP BY | Explains grouping and calculates EAST 2 / 170 and WEST 1 / 80 using three **synthetic** rows | Describes grouping correctly but omits/incorrectly calculates one total | Says it sorts rows without grouping, or calls results a live Snowflake test |

## Level 2 — [Administration Fundamentals](../level-02-administration-fundamentals.md)

| Question | Full credit (2) | Partial (1) | Incorrect/unsafe (0) |
|---|---|---|---|
| 1. Infrastructure ownership | Snowflake operates managed infrastructure; DBRE/SRE owns allowed configuration, access boundaries and operations | Says Snowflake manages servers only | Assumes users have no configuration or security responsibility |
| 2. Auto-suspend | Explains idle suspension, lower idle credits, auto-resume and possible delay | Says idle suspension saves credits | Claims zero restart impact or universal cost guarantee |
| 3. Resizing | Measured baseline, performance/cost diagnosis, approval, success/rollback plan | Says only "when slow" but acknowledges measurement | Changes production size without evidence or approval |
| 4. Query identity | Actual `QUERY_ID` correlates history/profile/timing/incident evidence | Names QUERY_ID without explanation | Invents a query ID and claims runtime acceptance |
| 5. Administrative roles | Least-privilege custom roles, controlled use of ACCOUNTADMIN | Says "not everyone" | Recommends routine account-admin access to fix a lab denial |

## Level 3 — [Performance and Query Optimization](../level-03-performance-query-optimization.md)

| Question | Full credit (2) | Partial (1) | Incorrect/unsafe (0) |
|---|---|---|---|
| 1. Elapsed versus execution | Differentiates total elapsed from compilation, provisioning, overload waiting and execution | Notes only that times differ | Claims elapsed always equals execution |
| 2. Overload metric | Correctly names `QUEUED_OVERLOAD_TIME` and distinguishes provisioning or transaction blocking | Names field without distinguishing causes | Equates overload with all queues/locks |
| 3. Fair benchmark | Controls SQL, data, warehouse, concurrency and cache; repeats samples; records latency and cost | Gives two or three controls only | Treats the tiny 1,000-row sample as production improvement proof |
| 4. Query Profile | Identifies Query Profile and scan/join/spill or partitions metrics | Names Query Profile only | Suggests a conventional B-tree index as default fix |
| 5. Larger warehouse | Explains that size cannot fix SQL design/joins; queueing case should investigate concurrency and isolation | Says "no" and gives one possible cause | Resizes automatically or without approved impact assessment |

## Level 4 — [Monitoring, Observability and Cost](../level-04-monitoring-observability-cost.md)

| Question | Full credit (2) | Partial (1) | Incorrect/unsafe (0) |
|---|---|---|---|
| 1. Account Usage timeliness | Historical view latency varies by view; cannot rely on a missing recent row to prove no incident | Says "not real time" only | Calls Account Usage live, complete alert telemetry |
| 2. `AVG_QUEUED_LOAD` | Explains aggregate queued-time / window-time ratio (may exceed 1 with concurrency), *not* unique users/requests | Says "queued load" without units or denominator | Describes as exact queue length or distinct users |
| 3. Credit drivers | Warehouse size × running time drives compute credits; distinguish gross warehouse usage from adjusted billed credits | Mentions size/running time only | Equates `CREDITS_USED` with invoice total in all cases |
| 4. p95 SLO | Workload-specific SLO with baseline/owner; p95 is latency percentile | Says threshold depends on workload | Enforces one arbitrary limit for all production workloads |
| 5. Serverless coverage | Resource monitors cover warehouses, not serverless features/AI services; evaluate budget and relevant metering | Says resource monitors don't cover everything | Claims one resource monitor limits all Snowflake spend |

## Level 5 — [Security, RBAC and Governance](../level-05-security-rbac-governance.md)

| Question | Full credit (2) | Partial (1) | Incorrect/unsafe (0) |
|---|---|---|---|
| 1. Least privilege | Grants only required purpose-specific privileges, scope and time; avoids broad roles | Defines minimal access only | Advises routine admin privilege |
| 2. SELECT prerequisites | Explains database/schema USAGE + table SELECT; warehouse USAGE for warehouse-backed compute | Names SELECT and parent USAGE but omits warehouse | Treats table SELECT alone as universally enough |
| 3. Sensitive columns | Masking protects columns; row access filters rows; secure view/aggregates are distinct designs | Says "masking" only | Conflates row filtering with column masking; suggests unrestricted PII |
| 4. Real patient data | Prohibits real patient data; synthetic fixtures only; restrict sensitive query history/evidence | Says "no real patients" only | Uses actual PHI or exports identities in training evidence |
| 5. Access approval | Verifies data-owner approval, scope, role inheritance and audit path before any grant | Says approval required only | Runs `GRANT`/elevates privileges as an unapproved lab step |

## Level 6 — [Data Recovery and Disaster Recovery](../level-06-data-recovery-disaster-recovery.md)

| Question | Full credit (2) | Partial (1) | Incorrect/unsafe (0) |
|---|---|---|---|
| 1. RPO | Max *acceptable data-loss interval*; a target set by business, measured separately | Says "acceptable data loss" | Confuses with time to restore |
| 2. RTO | Max acceptable *service restoration time* including dependencies and validation | Says "time to recover" | Confuses with data-loss window |
| 3. Time Travel | Bounded by effective retention, object type, permission and historical point after creation | Says "retention limited" only | Promises arbitrary past recoverability |
| 4. Fail-safe | Snowflake-operated last resort, best-effort for qualifying data; not routine customer restore | Says "not self-service" only | Suggests a user can query Fail-safe like Time Travel |
| 5. Clone versus DR | Cloning helps inspect/copy an isolated state; DR needs tested data integrity, replication/failover and RPO/RTO | Says "clone not enough" with one reason | Treats a never-tested clone as sufficient DR certification |

## Level 7 — [Production Incident Response](../level-07-production-incident-response.md)

| Question | Full credit (2) | Partial (1) | Incorrect/unsafe (0) |
|---|---|---|---|
| 1. First task | Confirm impact, scope, severity, owner and preserve evidence before risky changes | States "assess impact" only | Cancels/changes unknown production work first |
| 2. Query IDs | Uses actual QUERY_ID to correlate execution, timing and profile; no invented live evidence | Says "trace query" only | Uses synthetic IDs as proof |
| 3. High overload waiting | Capacity/concurrency hypothesis supported by overload/provisioning/blocked distinction | Says "too many queries" only | Assumes immediate warehouse resize is mandatory |
| 4. Cancel unknown query | No; verify owner/impact/privileges, incident approval and rollback | Says "no" only | Cancels unknown production queries without authorization |
| 5. Useful RCA | Blameless impact/timeline/evidence, verified and unknown causes, mitigation, prevention with owners and deadlines | Names root cause or actions alone | Blames individuals or asserts unsupported causes |

## Detailed grading for the seven instructor tabletop cases

The cases below use the same A–G naming as the [offline instructor pack](INSTRUCTOR-OFFLINE-ACCEPTANCE.md). **Do not replace real execution evidence with these illustrative results.**

| Case | 2 points — complete applied reasoning | 1 point — partial reasoning | 0 points — wrong/unsafe |
|---|---|---|---|
| A — Sample orders | Counts three synthetic rows; EAST 2/170, WEST 1/80; warehouse supplies compute | Correct count/sums or architecture, but not both | Wrong grouping or claims actual SQL executed |
| B — Privilege denial | Check active role, secondary roles and database/schema USAGE + table SELECT (plus warehouse for compute); request owner-approved least privilege | Mentions a role/SELECT check but not full path | Escalates to ACCOUNTADMIN or grants broadly without approval |
| C — Query delay | 40s overload queue plus 12s execution; compare total 52s, concurrency, isolation, SLO and reversible changes | Identifies queueing but omits diagnosis/rollback | Declares SQL query itself is 52s execution or blindly scales |
| D — Usage versus billed credits | Compare metric definitions, time window, data lag and cloud-services/adjustment accounting; don't call gross warehouse usage an invoice | Notes billing views can differ but no concrete reconciliation | Equates `CREDITS_USED` with all billed credits |
| E — Audit export | Stop sharing raw identity fields, aggregate outcomes only with approved privilege and secure handling | Notes privacy risk without remediation | Exports usernames, IPs, tokens or raw errors |
| F — Time Travel | Table created at 10:15 cannot yield table state at 10:14; check creation point, effective retention, table type and approved scratch scope | Notes "too early" but not retention/permission context | Promises recovery before creation or runs unapproved destructive test |
| G — Data freshness | 75-minute lag violates 15-minute freshness SLO (60 minutes over); investigate source, ingestion, tasks, dashboard dependencies; evidence and owner-approved rollback | Recognizes breach but omits pipeline/dependency investigation | Assumes query latency only, or modifies production data unapproved |

## Example instructor feedback and remediation

**Complete (2/2):** “You correctly distinguished queued overload from execution time and proposed checking concurrency before a reversible change. Your answer cites the case's measurements rather than inventing SQL results.”

**Partial (1/2):** “You named the correct Snowflake view, but explain the metric's units and why its delayed data is not a real-time incident indicator.”

**Remediation required (0/2 / critical safety):** “Do not use ACCOUNTADMIN or production patient records to demonstrate a tutorial. Rework the response using a dedicated synthetic nonproduction account and owner-reviewed roles.”

For a level scoring below 8/10, revisit the indicated lesson and reattempt those questions with the instructor; do not automatically retry any SQL. For a tabletop score below 12/14, repeat relevant cases. A critical safety error requires remediation and reassessment even at a passing score.

## Source documentation and independent-review boundary

Sources used for authoring; an independent Snowflake administrator/security reviewer must still verify environment-dependent statements before certification.

- [Architecture and key concepts](https://docs.snowflake.com/en/user-guide/intro-key-concepts)
- [Virtual warehouse basics](https://docs.snowflake.com/en/user-guide/warehouses-overview)
- [Query history table functions](https://docs.snowflake.com/en/sql-reference/functions/query_history)
- [Warehouse load definition](https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_load_history)
- [Working with resource monitors](https://docs.snowflake.com/en/user-guide/resource-monitors)
- [RBAC overview](https://docs.snowflake.com/en/user-guide/security-access-control-overview)
- [Time Travel](https://docs.snowflake.com/en/user-guide/data-time-travel)
- [Fail-safe recovery](https://docs.snowflake.com/en/user-guide/data-failsafe)

**Validation state:** Offline answer-key review and grading rubric authored. **No independent approval or learner grading conducted.** No Snowflake runtime tests were executed; V03 is deferred, V04 pending, V05 not certified.
