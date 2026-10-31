# Level 3 — Snowflake Performance Tuning and Query Optimization

**Track:** Snowflake Accelerated DBRE/SRE | **Duration:** 60 minutes | **Status:** DRAFT — V01/V02 automated static QA PASS; independent content review PENDING; Snowflake runtime validation NOT RUN (deferred)  
**Audience:** DBRE/SRE, data engineering and reporting teams  
**Prerequisites:** Authorized Snowflake training account; basic SQL recommended for Levels 2–7.

## Learning objectives
Differentiate execution, queueing and provisioning delays; inspect Query Profile and propose measured SQL/warehouse tuning.

## 60-minute lesson plan
| Topic | Time |
|---|---:|
| Query lifecycle and latency components | 10 min |
| Query Profile, scan and joins | 15 min |
| Queueing, sizing and workload isolation | 10 min |
| Guided query comparison and diagnosis | 20 min |
| Review | 5 min |
| **Total** | **60 min** |

## Core concepts
### Diagnose before scaling
Total latency can include compilation, provisioning, overload queueing, execution and transaction blocking. A large warehouse helps only when compute is the constraint. High queued-overload time indicates concurrency pressure. High bytes scanned can signal broad filters; spill-to-remote-storage can indicate pressure from joins, sorts or aggregations.

### Snowflake storage and pruning
Table data is organized into micro-partitions. Snowflake uses micro-partition metadata to skip partitions that do not match a query. Pruning can be weakened by unselective predicates, transformations of filter columns, and unsuitable access patterns. Inspect Query Profile rather than assuming an index will fix it: conventional user-managed B-tree indexes are not the default design for standard Snowflake tables.

### Query Profile reading order
1. Compare query IDs with the same SQL shape and similar parameters.
2. Inspect scan nodes: partitions scanned versus total partitions, bytes and rows.
3. Review join strategy, output cardinality, data redistribution and spills.
4. Separate overload queueing from query execution time.
5. Check result reuse/caching when benchmarking, and run several comparable samples.

### Tuning decisions
| Evidence | First response |
|---|---|
| Broad scan | Select needed columns, filter earlier, review pruning |
| Join explosion | Recheck join keys and many-to-many cardinality |
| High remote spill | Reduce intermediate data, optimize joins; then assess compute |
| Overload queue time | Isolate workloads or evaluate multi-cluster |
| High provisioning time | Assess auto-resume patterns and startup expectations |
| One expensive query | Optimize SQL and compare warehouse sizes with controlled tests |

Always record baseline, intervention, elapsed/exec time, workload and cost before declaring success.

## Hands-on lab and expected results
### Step 1 — Generate a small reproducible dataset in a scratch schema
Run only against your dedicated training scratch schema and small warehouse. Before the CREATE, confirm there is no other table of this name (including permanent tables): a temporary table may shadow another table with the same name.
~~~sql
CREATE TEMP TABLE DBRE_SRE_L3_SALES AS
SELECT ORDER_ID,
       MOD(ORDER_ID, 10) AS REGION_ID,
       10 + MOD(ORDER_ID, 90) AS AMOUNT
FROM (
    SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) AS ORDER_ID
    FROM TABLE(GENERATOR(ROWCOUNT => 1000))
);
-- This creates one deterministic numeric ID per synthetic row.
~~~
The ROW_NUMBER result creates 1,000 contiguous synthetic identifiers; deriving REGION_ID and AMOUNT from the same identifier avoids unrelated SEQ4() calls. This is a teaching dataset, not a representative performance benchmark.

### Step 2 — Compare a broad and selective query
~~~sql
SELECT COUNT(*) AS N, SUM(AMOUNT) AS TOTAL
FROM DBRE_SRE_L3_SALES;
SELECT COUNT(*) AS N, SUM(AMOUNT) AS TOTAL
FROM DBRE_SRE_L3_SALES
WHERE REGION_ID = 1;
~~~
Expected: the broad count is **1,000** with SUM(AMOUNT) = **54,110**; filtering on REGION_ID = 1 returns **100** rows with SUM(AMOUNT) = **5,060**. These figures come from the deterministic generator, not a Snowflake execution result. This tiny temporary table is for *concept demonstration*, not credible evidence of Snowflake tuning gains. A real performance finding requires representative data sizes, warmed/cold cache awareness, and repeated measurements.

### Step 3 — Inspect history
~~~sql
SELECT QUERY_ID, TOTAL_ELAPSED_TIME, EXECUTION_TIME,
       QUEUED_OVERLOAD_TIME, BYTES_SCANNED
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION(RESULT_LIMIT => 1000))
ORDER BY START_TIME DESC;
~~~
Expected: recent queries from **this session**, with actual execution metrics when available; zero queue time is normal in a lightly loaded lab. `RESULT_LIMIT` is applied by the table function before any outer SQL filters, and the function has a seven-day history window. The lesson and the [Level 3 QA smoke script](validation/runtime/level-03-smoke.sql) now both use session isolation. The two files use different scratch-table identifiers deliberately; do not mix their table names within one session.

### Step 4 — Open Query Profile in Snowsight
Find the query by QUERY_ID; inspect Scan and Aggregate operators. Document partitions scanned, time, rows and spills when reported.

### Step 5 — Mini case study
A production query has 12 seconds execution and 40 seconds overload queueing. **Answer:** queueing dominates; investigate concurrent workload and warehouse isolation before rewriting a fast-enough query.

**Pass:** cite one measured performance field, explain its meaning, and propose a reversible change with success criteria.

## DBRE/SRE troubleshooting quick reference
| Problem | Evidence to capture | Change guardrail |
|---|---|---|
| Slow only at peak | Overload queue time by hour | Separate ETL/reporting or evaluate multi-cluster |
| Slow after data growth | Profile scans and partition pruning | Validate same data volume and filter |
| High memory spill | Profile remote spill bytes | Tune data reduction before resizing |
| Intermittent blocking | Transaction blocked time | Identify transactions and owner before cancellation |

Never use \`ALTER WAREHOUSE\` in the lab without explicit authorization.

## Knowledge check (with answers)
1. **Does total elapsed equal execution time?** Not necessarily.
2. **Which metric identifies overload waiting?** QUEUED_OVERLOAD_TIME.
3. **What makes a fair benchmark?** Comparable SQL, data, caching and load.
4. **What tool shows costly operators?** Query Profile.
5. **Can increasing warehouse size fix every query?** No.

## Acceptance and runtime validation
Run the [Level 3 SQL smoke](validation/runtime/level-03-smoke.sql) in a dedicated training scratch schema. Confirm the 1,000/100 row counts, the 54,110/5,060 totals, unique IDs, an actual query ID, and that the temporary table does not collide with any existing object. Record warehouse credits, Query Profile screenshots with sensitive information redacted, and cleanup evidence. This is **NOT RUN**, and the tiny synthetic dataset cannot establish production-scale performance.

## Operational safety and validation
- Use a **designated lab account/warehouse** and synthetic data. Protect query-history text and any personal or customer information.
- SQL that creates/changes warehouse, roles, objects, retention or data requires appropriate role, approval and isolated test scope.
- Expected outcomes describe intended behavior, **not proof of execution**. No SQL was run against live Snowflake when authoring this lesson.
- If a command is not applicable to the account edition or current role, document the limitation rather than escalating privileges.
- **Acceptance:** instructor checks concepts, learner documents observed output, and a separate runtime review confirms SQL syntax/permissions and clean-up.

## Continue into the full 90-chapter curriculum
[36 Query Internals](../36-snowflake-query-processing-internals.md), [37 Query Profile](../37-query-profile-deep-dive.md), [38 Micro-partitions](../38-micro-partitions-pruning.md), [45 Performance Troubleshooting](../45-performance-troubleshooting.md)

## Official documentation
- https://docs.snowflake.com/en/sql-reference/functions/query_history
- https://docs.snowflake.com/en/user-guide/ui-query-profile

[Back to accelerated track index](README.md) | [Validation tracker](STATUS.md)
