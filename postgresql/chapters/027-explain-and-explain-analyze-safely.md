# 027 — EXPLAIN and EXPLAIN ANALYZE Safely

Audience: DBRE and SRE only. PostgreSQL 18 baseline.
Status: authored/static reviewed; actual PostgreSQL plan execution pending.

[Previous: Performance Triage](026-performance-triage-and-evidence-collection.md) · [Hands-on plan lab](../labs/027-explain-and-explain-analyze-safely-lab.md) · [Master plan](../MASTER-PLAN.md)

## Operational outcome

Choose an estimated or executed plan according to the incident question, bound the diagnostic operation and interpret row/loop/buffer evidence without confusing cost with elapsed time or rollback with complete side-effect reversal.

A plan is evidence about one statement under specific schema, parameters, settings and data conditions. It is not an application trace or a production benchmark by itself.

## Choose whether to execute

| Diagnostic | What it does | Appropriate first question |
|---|---|---|
| EXPLAIN without ANALYZE | Plans the supplied statement | Which access/join strategy is estimated? |
| EXPLAIN ANALYZE | Executes the statement and adds observations | Do estimates match this reviewed execution? |
| EXPLAIN EXECUTE | Inspects a prepared statement's selected plan | Is application plan selection represented? |
| EXPLAIN with GENERIC_PLAN | Estimates a parameter-independent plan | How might generic planning differ? |

Plain EXPLAIN still performs planning and can acquire locks, consume resources or evaluate expressions eligible for constant folding. An incorrectly labeled immutable function can be evaluated during planning. It is lower-impact evidence, not a security sandbox for unreviewed SQL.

ANALYZE executes the statement even though normal SELECT results are replaced by plan output. Writes, triggers, sequence changes, locks, WAL work and external function effects can occur. Review the actual statement, called functions, triggers and target objects before deciding it is suitable.

Do not accept a statement merely because its first token is SELECT. A SELECT can call a volatile or externally acting function; a WITH query can contain data modification. Automated lexical “read-only SQL” detection is not a sufficient permission boundary.

## Define an execution envelope

Record physical source, database, role, exact version, schema/statistics state, representative parameter class, settings and intended output. Use a restricted connection and a known statement that addresses the incident hypothesis from Chapter 026.

For a reviewed read against known fixture tables, use an explicit read-only transaction, short lock/statement budgets and SET LOCAL settings. For a deliberately reviewed write experiment, use an isolated fixture and rollback; do not promote that recipe into permission to test arbitrary production writes.

The [read-plan script](../scripts/027-read-plan.sql) accepts only estimated or executed mode and contains one fixed fixture query. The [write-plan script](../scripts/027-write-plan-rollback.sql) executes one known fixture insert inside rollback. Neither accepts arbitrary SQL input.

Timeouts bound waiting/execution imperfectly: statement timeout is not a full connection/pool deadline, and a canceled explicit transaction needs recovery. Session closure rolls back outstanding transactional work, but does not undo all side effects. Plan capture failures may produce partial files; record failure and do not parse them as a valid plan.

## Read the plan in the correct units

| Field | Meaning | Common misinterpretation |
|---|---|---|
| Startup/total cost | Planner cost units for one node invocation | Treating cost as milliseconds |
| Plan Rows | Estimated output rows per invocation | Treating it as table size or rows examined |
| Actual Rows and Loops | Observed average rows per execution and execution count | Ignoring repeated inner work |
| Actual times | Instrumented node elapsed times | Adding parent and child inclusive times |
| Rows removed/filter/recheck | Work discarded at an indicated condition | Assuming every count is a global total |
| Planning/Execution Time | Server planning/execution summaries | Treating them as full application latency |

For a repeated node, actual rows × loops gives approximate output across invocations; averages/rounding and parallel reporting need care. Compare estimated rows with observed rows at the same per-invocation level. A node with zero loops was not executed; its zero rows do not demonstrate a bad cardinality estimate.

Read the tree and dependencies. Parent observations often include child work. Summing all node times or buffer counts double-counts. A nested-loop inner scan with modest per-loop cost can accumulate significant repeated work; that does not automatically make nested loops wrong.

Costs depend on planner settings and estimates. A sequential scan may be appropriate for a small relation or a large fraction of its rows. An index scan is not a certificate of good performance. Start with row-estimate divergence and the incident's resource/wait evidence before proposing a change.

## Select EXPLAIN options deliberately

FORMAT JSON preserves structure for local analysis. TEXT is convenient for interactive reading. Raw plans can expose names, literals, filters, outputs and query context; retain them privately.

TIMING OFF reduces node-level clock measurement overhead while retaining row/loop observations and total execution measurement. It does not remove all instrumentation overhead. BUFFERS reports PostgreSQL buffer work; in PostgreSQL 18 ANALYZE includes it by default, but explicitly stating it makes the diagnostic contract clear.

SETTINGS lists relevant planner settings that differ from built-in defaults, not every effective application/role setting. Capture additional context separately when needed. MEMORY describes planner memory, not total peak runtime memory.

WAL requires ANALYZE and reports generation during the operation. Rolling back a write does not erase its generated WAL, consumed CPU or I/O. SERIALIZE TEXT/BINARY can include output-conversion work, but still does not measure actual network transmission to the client. GENERIC_PLAN cannot be combined with ANALYZE.

The lab begins with TIMING OFF and avoids gratuitous options. Use timing or serialization when it answers a defined question and record the changed measurement boundary.

## Understand rollback and read-only limits

Transactional fixture rows can be restored by rollback. Sequence values obtained through nextval are not reclaimed by transaction rollback. A rolled-back insert can therefore leave the table empty while its sequence has advanced.

Read-only mode blocks many write operations, including ordinary nextval use, but it is not complete isolation from arbitrary external effects. Functions, extensions, connections to other services and side effects outside PostgreSQL's transaction model need separate review.

Triggers can run during analyzed writes. Immediate trigger work and deferred behavior differ; a rollback-only experiment need not reproduce commit-time effects. A statement that invokes an external API cannot be made harmless by wrapping it in BEGIN/ROLLBACK.

Prefer representative non-production data and the least invasive diagnostic that resolves the uncertainty. Production execution requires an operationally justified scope, resource budget and change/incident ownership.

## Keep LIMIT and cache effects honest

Adding LIMIT changes the query and can change plan selection. It does not guarantee that a sort, aggregate, join or subquery only processes that many input rows. A root LIMIT can stop producers early, making lower-node actual rows a partial observation of their full-result estimate.

Record cache/load state and repeatability. A second execution can be faster because it benefits from buffers, OS cache or warmed infrastructure. Do not flush caches or restart a production server to make the experiment look controlled.

EXPLAIN ANALYZE has profiling overhead and discards ordinary results. It does not include normal client consumption of the complete result. A faster diagnostic execution is not proof that a user's large result-transfer request has recovered.

## Match prepared-statement behavior

Application drivers may use prepared statements and choose generic or custom plans. A literal SQL test can therefore differ from the application even with the same apparent predicate.

Use EXPLAIN EXECUTE in a reviewed equivalent prepared-statement context when needed. Inspect the current role, search_path, parameter types, data skew and session settings. GENERIC_PLAN gives an estimate independent of particular parameter values; it is not a prediction of every custom execution.

Avoid forcing a planner GUC globally just to reproduce one candidate plan. If a local experiment changes plan_cache_mode or planner switches, use SET LOCAL where applicable, record it and verify restoration. More detailed estimate/statistics work follows in Chapter 028.

## Store evidence without inventing a diagnosis

The [offline JSON summary helper](../scripts/027-plan-summary.py) emits numeric row/loop/cost/buffer observations and node types without filters, outputs or relation names. It explicitly marks unexecuted and missing-execution cases. It does not rank exclusive node time, add buffer totals or choose an index.

Its approximate row products are explanatory fields, not exact business row counts. The raw source remains sensitive; an output allowlist does not sanitize the original file or establish that the supplied SQL was safe.

Retain estimated and executed plans with source/version/role/settings/time context. State what supports the hypothesis and what remains unresolved. Use the application latency/error/correctness boundary to validate a resulting change.

## Acceptance and official references

Complete estimated versus executed capture, repeated-loop interpretation, a bounded lock-wait failure, a rolled-back insert with sequence advancement and fixture cleanup. Do not assert a fixed scan node or timing number across hosts.

- [PostgreSQL 18 EXPLAIN options](https://www.postgresql.org/docs/18/sql-explain.html)
- [Reading execution plans](https://www.postgresql.org/docs/18/using-explain.html)
- [Prepared plan selection](https://www.postgresql.org/docs/18/sql-prepare.html)
- [Sequence nontransactional behavior](https://www.postgresql.org/docs/18/functions-sequence.html)
- [Function volatility and constant folding](https://www.postgresql.org/docs/18/xfunc-volatility.html)
- [Timeouts and read-only settings](https://www.postgresql.org/docs/18/runtime-config-client.html)

Next: Chapter 028 — Planner Estimates, Statistics and Extended Statistics.
