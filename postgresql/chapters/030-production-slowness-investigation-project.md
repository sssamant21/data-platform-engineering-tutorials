# Chapter 030 — Production Slowness Investigation Project

**Audience:** DBRE and SRE only. **Baseline:** PostgreSQL 18. **Project:** investigate a database-backed request regression, contain impact, test a durable correction, and demonstrate recovery with retained evidence.

## 1. Project brief

An application reports slower requests and intermittent database timeouts after a maintenance change. Host CPU appears normal. The workload also has a recurring planner-estimate problem. Your assignment is to determine what is affecting requests now, distinguish it from background weaknesses, and propose changes supported by evidence.

The lab reproduces this with synthetic data in the Chapter 004 environment. Production is the operating model, not the execution target. Do not inject faults into a live service.

| Deliverable | Required evidence |
|---|---|
| Incident scope | UTC window, affected operation, workload/deployment change and customer impact |
| Baseline versus incident | Identical request probe, successful result validation, failures and timing boundaries |
| Causal diagnosis | Wait/blocker identity plus evidence supporting or rejecting CPU, memory, I/O and planner hypotheses |
| Containment | Smallest action, owner, expected effect, rollback and observed result |
| Durable correction | Before/after plans and representative workload checks |
| Recovery acceptance | Correct results, errors/latency, resource behavior, sustained coverage and remaining gaps |
| Follow-up | Blameless mechanism, contributing conditions, owners and acceptance criteria |

## 2. Establish impact and measurement boundaries

Use real application telemetry for customer-facing SLIs. Request latency includes admission/pool wait, database execution, commit, result transfer and application work. SQL execution time alone is not end-to-end latency.

Define the time window, deployment identity, traffic volume and affected tenants/operations without exporting sensitive parameters. State whether requests are read-only or write transactions and whether retries can duplicate effects. Restrict retry amplification during an incident using the service's established policy.

The lab's serial psql probe includes connection startup and one bounded synthetic read. It is a diagnostic proxy, not a connection-pool benchmark or production SLO measurement. Eight attempts cannot support stable tail-percentile or error-budget claims.

## 3. Triage with ranked hypotheses

Before a change, preserve a small, time-correlated window from the database and host. Follow [Chapter 026](026-performance-triage-and-evidence-collection.md) and [Chapter 029](029-cpu-memory-io-and-wait-event-diagnosis.md).

| Hypothesis | Supporting observation | What would weaken it |
|---|---|---|
| Lock blocking | Matching waiter/blocker identities, Lock samples, query fails within lock budget | No observed edge is only weak contrary evidence if sampling misses it |
| CPU demand or quota | Backend CPU, runnable pressure or container throttling aligned with impact | Low host average alone is insufficient |
| Storage pressure | IO observations aligned with device latency/queues and allocation limits | Cached reads and unsupported timing can hide the relevant path |
| Memory pressure/spill | Host pressure or OOM evidence; node-level spill and temp growth | A spill alone does not prove host exhaustion |
| Estimate/plan regression | Same query shape/settings, changed cardinality estimates and plan work | Inaccurate estimates without a measured latency effect do not establish incident cause |
| Connection/delivery problem | Pool queue, authentication/connect timing, Client waits, trace boundaries | A healthy isolated SQL probe does not prove application health |

Record the strongest hypothesis, confidence, counter-evidence and the next bounded observation. Separate **observed facts**, **inferences**, **confirmed mechanisms** and **unknowns** in the report. Several problems can coexist.

## 4. Observe first; make the incident no worse

Use a monitoring role and metadata-only activity/lock evidence. Identify a backend with PID, backend_start, role, database, application, transaction age and current state. Retain identity at observation time; PID alone can be reused.

Cumulative counters need matching reset epochs, database/cluster identity and elapsed timestamps. Do not reset them to simplify comparisons. Query statistics, logs and traces are complementary; their visibility and retention must be recorded.

Use plain EXPLAIN first where appropriate. It still needs planning locks. EXPLAIN ANALYZE executes the query and adds overhead; do not replay arbitrary production writes or expensive reads. Reproduce representative parameters in an approved safe environment. [Chapter 027](027-explain-and-explain-analyze-safely.md) provides execution safeguards.

## 5. Contain the confirmed mechanism

For lock incidents, coordinate with the transaction owner. A transaction-scoped lock normally releases when the transaction ends. Cancelling a statement may leave the session or transaction needing recovery; termination has broader consequences. Follow [Chapter 020](020-safe-cancellation-termination-and-concurrency-incident-lab.md) for a justified single-target signal.

Prefer ending the known lab blocker in its own session. The project deliberately uses a timed holder that rolls back and exits, so no broad cancellation is necessary. Recovery after rollback supports the controlled blocking mechanism; it does not establish how a production maintenance transaction was left open.

For other incidents, choose a matching intervention: reduce admitted concurrency, revert a query/deployment, defer competing work or revise allocation after capacity review. Define the expected metric change and abort threshold before applying it. Avoid cluster-wide restarts, fsync changes, cache dropping or global memory increases as exploratory actions.

## 6. Investigate the remaining planner weakness separately

After blocking clears, compare estimates to actual rows for the fixed synthetic query. The fixture's correlated predicates can remain underestimated even with fresh individual-column statistics. Use [Chapter 028](028-planner-estimates-statistics-and-extended-statistics.md) to test a targeted dependency object and populate it with ANALYZE.

The fixture is small and has no predicate index. An improved estimate may leave the sequential scan and measured time unchanged. Report that result accurately. Do not call the statistics object an incident fix if requests recovered before it was created.

In production, test common, rare, NULL and contradictory parameter combinations as relevant. Extended statistics do not directly fix table-join selectivity in PostgreSQL 18. Durable changes need a representative workload, maintenance budget, ownership, rollback and regression checks.

## 7. Recovery acceptance

Evaluate recovery against the original impact boundary:

1. The same request operation returns correct results with acceptable failure rate and latency.
2. Queues and retry backlog drain without renewed overload.
3. Relevant waits and resource pressure return to a healthy envelope.
4. Replication, maintenance and unrelated workloads remain healthy.
5. The observation window covers enough representative traffic, including previously affected parameters.

The lab demonstrates three separate states: baseline, blocked requests, and recovered requests before the statistics experiment. Its timed blocker and short probe cannot establish long-term production recovery. Fill a production acceptance plan with the actual observation duration, traffic volume, SLO thresholds and monitoring owner.

## 8. Blameless incident report and prevention

Use the [report template](../templates/030-slowness-investigation-report.md). Describe the triggering change, mechanism, impact, detection, containment and validation without assigning personal blame. Explain which controls allowed the condition and how future acceptance will detect it.

Examples of concrete follow-ups include a maintenance transaction duration budget, lock acquisition deadline, change-window admission policy, parameter-aware plan regression coverage, distribution-change ANALYZE policy and missing host/trace telemetry. Every action needs an owner, due date and testable completion criterion.

## 9. Project lab and scoring

Run the [project lab](../labs/030-production-slowness-investigation-project-lab.md). Submit the completed report and restricted evidence directory.

| Criterion | Passing standard |
|---|---|
| Scope and truth | Correct fixture counts; incident described as a lab simulation |
| Diagnosis | Live lock evidence with identities; alternative resource hypotheses evaluated without fabricated observations |
| Containment/recovery | Blocker finishes; same probe succeeds before planner change |
| Planner experiment | Comparable bounded plans; estimate improvement distinguished from latency gain |
| Safety | No broad signals/resets/global changes; scoped rollback and cleanup |
| Evidence quality | Failures retained, timestamps/reset boundaries checked, missing coverage explicit |
| Operations | Action owners and measurable production acceptance plan |

**Validation status:** content and static checks reviewed; actual PostgreSQL project execution remains pending.

## Official PostgreSQL 18 references

- [Explicit locking](https://www.postgresql.org/docs/18/explicit-locking.html)
- [Monitoring statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [EXPLAIN](https://www.postgresql.org/docs/18/sql-explain.html)
- [CREATE STATISTICS](https://www.postgresql.org/docs/18/sql-createstatistics.html)
- [ANALYZE](https://www.postgresql.org/docs/18/sql-analyze.html)

**Next:** Chapter 031 — B-tree and Other Index Types: Operational Tradeoffs.
