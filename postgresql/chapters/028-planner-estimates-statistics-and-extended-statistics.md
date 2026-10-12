# Chapter 028 — Planner Estimates, Statistics and Extended Statistics

**Audience:** DBRE and SRE. **Baseline:** PostgreSQL 18. **Outcome:** identify an estimate failure, choose a scoped statistics change, and prove its effect without treating maintenance as an emergency cure-all.

## 1. Operational purpose

Cardinality estimates influence join order, scan selection, aggregation strategy and memory expectations. A small error near a scan can amplify through a join. A slow query with accurate estimates can still have an I/O, contention, indexing or capacity problem.

Start with Chapter 026 evidence and Chapter 027 execution safeguards. Preserve the query shape, parameter values in a restricted evidence channel, role, settings, schema version, plan mode and measurement time. Generic prepared plans and parameter-specific plans may estimate differently. Statistics cannot make an unknown parameter behave like a known literal.

## 2. Locate the estimate failure

Compare Plan Rows with Actual Rows at the same node, per invocation. Actual Rows in EXPLAIN ANALYZE is an average per loop; multiply by loops only when estimating total work. Inspect the earliest substantial divergence feeding the expensive operation. The top aggregate of count(*) usually returns one row and hides a scan's error.

For positive estimates and actual counts, q-error is max(actual/estimate, estimate/actual). A 2-row estimate against 200 actual rows has q-error 100. Record zero actual rows separately rather than dividing by zero. LIMIT, EXISTS, cancelled execution and nodes never executed can prevent complete cardinality observations. Parent and child buffer counts are inclusive: do not sum them.

A better estimate does not guarantee a faster plan. Compare the same workload, SLO impact, resource use and plan stability after the change.

## 3. What the planner knows

Planner statistics are distribution summaries maintained by ANALYZE. They are distinct from the cumulative activity counters in Chapter 022. Resetting activity statistics does not refresh distributions. ANALYZE collects statistics; EXPLAIN ANALYZE executes a statement and reports execution.

| Evidence | Meaning | Operational caution |
|---|---|---|
| pg_class.reltuples / relpages | Approximate row and page counts | Planner may scale counts for current physical size |
| pg_stats.null_frac | Estimated NULL fraction | NULL predicates differ from ordinary equality |
| pg_stats.n_distinct | Positive distinct count; negative fraction of row count | -1 means distinct count scales approximately with rows |
| most-common values and frequencies | Common values and their estimated shares | Values may contain customer data |
| histogram_bounds | Distribution of remaining values | Finite sampling can miss skew or new ranges |
| avg_width | Average stored column width | Wide intermediates affect resource needs |
| correlation | Relationship between column order and physical row order | This is not cross-column dependency |

Inspect only relevant relations and columns. pg_stats exposes statistics for tables the caller can read; PostgreSQL 18 pg_stats_ext restricts rows to tables the caller owns. An empty result can be an access issue. Do not grant broad catalog access just to fill a dashboard.

## 4. Freshness and sampling

Review last_analyze, last_autoanalyze and n_mod_since_analyze with collection time and the Chapter 022 counter limitations. These are clues, not proof that every relevant distribution is current. A bulk import, tenant migration or newly dominant value can make old summaries misleading.

Use explicitly scoped ANALYZE after a material distribution change. Autovacuum analyzes ordinary tables according to configured thresholds and activity; partitioned parents require an intentional manual ANALYZE policy. Fresh leaf statistics do not prove parent hierarchy statistics are current.

ANALYZE permits ordinary concurrent DML but can conflict with maintenance or DDL and consumes I/O and CPU. Use lock and statement budgets, a maintenance-capable role and a defined relation list. SKIP_LOCKED can skip work and does not eliminate every possible wait; a command completing is not proof every target was refreshed. Track warnings and progress, then inspect results.

## 5. Choose the smallest useful change

The default statistics target is 100. A higher per-column target can represent more common values and histogram detail, at increased sampling, storage and maintenance cost. It does not teach the planner that two columns are related.

~~~sql
-- Illustrative production change: review object, ownership and maintenance budget first.
SET lock_timeout = '1s';
SET statement_timeout = '30s';
ALTER TABLE app.events ALTER COLUMN tenant_id SET STATISTICS 250;
ANALYZE app.events;
~~~

Record the previous target before changing it. Restore that exact value when rolling back; -1 means inherit the default, not retain the latest collected sample. Re-analyze to regenerate summaries after restoring configuration. Avoid changing the cluster-wide default to solve one query. Target zero disables column statistics collection.

## 6. Extended statistics: three different questions

| Kind | Best starting use | Boundary |
|---|---|---|
| dependencies | Related columns with compatible equality/constant IN predicates | Does not enforce a constraint; not a general fix for ranges, LIKE or contradictory combinations |
| mcv | Common combinations whose joint frequencies differ from independent marginals | Represents sampled combinations; not exhaustive truth for rare values |
| ndistinct | Number of distinct combinations for multi-column grouping | Does not by itself fix WHERE selectivity |

CREATE STATISTICS defines the object; ANALYZE populates it. Explicit kinds make a hypothesis easier to review. Creating the object requires table ownership; its ownership is subsequently independent. PostgreSQL 18 does not use extended statistics for table-join selectivity estimates.

~~~sql
CREATE STATISTICS app.events_tenant_state (mcv)
    ON tenant_id, state FROM app.events;
ANALYZE app.events;
~~~

For perfectly related columns a and b, each with 100 equally common values, independence predicts 20,000 × 0.01 × 0.01 = 2 matching rows for a=7 AND b=7. The fixture actually has 200. Dependencies can recognize redundant compatible conditions. For a=7 AND b=8, dependencies may still predict matching rows although none exist; MCV can model common combinations more directly. Plans often clamp positive row estimates to at least one, so do not demand an estimated zero.

Expression statistics can model a predicate expression without building an expression index. They provide distribution information, not an index access path. Match the query expression and validate the actual plan. Raising a sample target, adding dependencies and building an index solve different problems.

## 7. Change acceptance and rollback

Capture before/after plans for representative values, including common, rare, NULL and incompatible combinations where applicable. Keep plan mode and session settings fixed. Validate row counts independently on safe fixtures; do not run unbounded COUNT scans on a production incident path.

Accept a change only when relevant estimates improve and representative latency/resource behavior remains acceptable. Record maintenance duration, locks, new objects/targets, owner, rollback steps and the next distribution-change trigger. Drop only the statistics object introduced by the change; restore original targets and ANALYZE if targets changed. Dropping an object changes future planning, not an already running query.

## 8. Hands-on lab and completion

Run the [lab](../labs/028-planner-estimates-statistics-and-extended-statistics-lab.md). It compares independence, dependencies, contradictory predicates, MCV and grouping estimates one kind at a time. It also demonstrates why a larger single-column target does not fix cross-column correlation.

Deliver a restricted evidence bundle with plans, summary outputs, recorded exact fixture counts, estimate comparisons, maintenance results and successful cleanup. Explain one improvement and one remaining limitation.

**Authoring validation:** shell syntax, links, fences and SQL structure reviewed. PostgreSQL execution remains pending; no runtime verification is claimed.

## Official PostgreSQL 18 references

- [Planner statistics](https://www.postgresql.org/docs/18/planner-stats.html)
- [Row estimation examples](https://www.postgresql.org/docs/18/row-estimation-examples.html)
- [CREATE STATISTICS](https://www.postgresql.org/docs/18/sql-createstatistics.html)
- [ALTER STATISTICS](https://www.postgresql.org/docs/18/sql-alterstatistics.html)
- [ANALYZE](https://www.postgresql.org/docs/18/sql-analyze.html)
- [pg_stats](https://www.postgresql.org/docs/18/view-pg-stats.html)
- [pg_stats_ext](https://www.postgresql.org/docs/18/view-pg-stats-ext.html)

**Next:** Chapter 029 — CPU, Memory, I/O and Wait Event Diagnosis.
