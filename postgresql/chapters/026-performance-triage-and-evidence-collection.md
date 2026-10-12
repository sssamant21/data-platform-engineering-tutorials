# 026 — Performance Triage and Evidence Collection

Audience: DBRE and SRE only. PostgreSQL 18 baseline.
Status: authored/static reviewed; PostgreSQL incident-lab execution pending.

[Previous: Monitoring Acceptance](025-prometheus-grafana-and-actionable-alert-acceptance.md) · [Hands-on triage lab](../labs/026-performance-triage-and-evidence-collection-lab.md) · [Master plan](../MASTER-PLAN.md)

## Operational outcome

Turn “the database is slow” into an observed service symptom, a bounded evidence set and a testable hypothesis. Preserve the original state before intervention and demonstrate recovery without collecting unrestricted SQL or running expensive diagnostics during an incident.

Triage prioritizes service restoration and evidence sufficient for a decision. It does not require proving every mechanism before acting through an approved incident procedure. It also does not justify changing several database settings because a dashboard looks unusual.

## Establish the impact and boundary

Record the affected service, environment, endpoint, operation class, onset, comparison window and consumer symptom. Is the problem latency, errors, pool queuing, throughput collapse or incorrect/stale data? Which tenants or request paths remain healthy?

Use application SLIs and traces from Chapters 021/024. Separate pool checkout, connection establishment, SQL, result consumption and retries. A locally successful SELECT 1 is narrow connection evidence, not a demonstration that the affected request succeeds.

Verify the physical PostgreSQL node and its role. A reader endpoint, proxy or failover can route observations to another backend. Record version, postmaster start, recovery state and database identity before comparing samples.

## Collect before changing

The [metadata snapshot](../scripts/026-triage-snapshot.sql) records source identity, selected effective settings, database counters/reset marker, session state/clocks/waits and direct blockers. Query text, parameters, client addresses and application-table reads are excluded.

The [lab bundle wrapper](../scripts/026-collect-lab-triage.sh) connects only to the guarded Chapter 004 primary. It uses short read-only SQL, external process deadlines, private directories and explicit collection status. Optional host observations have separate exit records. Missing commands or failed SQL become incomplete evidence, not invented zero values.

This wrapper is deliberately lab-scoped. Production adaptation requires approved source/role/secret handling and reviewed deployment paths; do not relax its guard to point it at production.

Collect a few snapshots tied to meaningful phases. Repeated high-frequency inspection can compete with the workload. A snapshot is not an atomic photograph of activity, lock state, cumulative counters and host metrics.

## Read state before interpreting age

| Evidence | What it supports | What it does not establish |
|---|---|---|
| active plus Lock wait and blocking PIDs | Lock acquisition is delayed | Root ownership or permission to terminate |
| active plus another wait event | A backend is waiting at that observation | Full request-time distribution |
| active with no reported wait | No instrumented wait was reported then | CPU saturation or useful progress |
| idle in transaction with old xact_start | Client retains an open transaction | Every resource it retains or application intent |
| idle outside a transaction | Connection awaits another request | A database incident by itself |
| ClientRead / ClientWrite | Client/server communication boundary needs investigation | Network fault alone |
| High session occupancy with retries | Concurrency/admission may be amplifying demand | That max_connections should be raised |

query_start is the current or last statement start. Its age is not a running duration when the session is idle. Use state_change for idle age and xact_start for transaction age. backend_start helps distinguish a replacement backend from a reused PID.

When inspecting blockers, walk upstream. A queued strong lock can block later requests; not every direct blocker is a holder of a granted lock. Prepared transactions can appear as PID zero. A limited actor list can omit an upstream node; report that boundary and investigate instead of selecting an unreviewed target.

## Build a hypothesis with independent evidence

| Hypothesis | Database evidence | Independent check |
|---|---|---|
| Lock contention | Stable lock wait chain, transaction owners | Request/transaction boundaries and retry pressure |
| CPU demand | Active workload, expensive families, parallel demand | Interval host/container CPU, throttling, runnable work |
| I/O limitation | Relevant I/O waits and compatible interval counters | Storage latency/queue/throughput, device mapping |
| Memory pressure | Temporary work, concurrency, memory symptoms | Host/cgroup limits, OOM events and swap behavior |
| Connection/pool pressure | Sessions and activity patterns | Pool queue/checkout duration, client limits |
| Workload/query regression | Calls, rows and execution deltas by family | Deployment/input changes and representative safe plans |
| Replica freshness or recovery delay | Recovery role, receive/replay observations | Consumer watermark and routing policy |

Use timestamps and units to connect signals. A filesystem percentage is capacity evidence, not an IOPS measurement. PostgreSQL buffer misses may be served by the OS cache. Zero I/O timing with tracking disabled is unknown timing, not fast storage.

Host commands run from the lab host's namespace. Container data can reflect a cgroup or host differently. ps CPU percentages are not a precise instantaneous demand sample. Prefer interval telemetry and documented storage/container identities for a production conclusion.

## Preserve measurement validity

Use Chapter 022's before/after identity and reset checks for cumulative statistics. Use Chapter 023's retained-entry epochs for query rankings. Do not subtract across restart, source changes, selective reset or retention loss.

Collector activity itself contributes to database counters. Background processes and other clients contribute too. Do not infer exact successful application request counts from xact_commit, nor exact bad requests from xact_rollback.

Record missing visibility, truncation and failed collection. The supplied snapshot caps sessions at 50 and blocker IDs per session at 20. It explicitly marks a clipped session cohort; its bounded blocker arrays can require a separate targeted follow-up. A long collection interval can miss a short burst.

Settings shown in an observer are that session's effective values; privileged actors can override some tracking/timing settings. Record workload policies when evaluating a disputed zero or missing series.

## Decide the next action

Start with the hypothesis that best explains impact and has corroborating evidence. If it is locking, identify the owner and use Chapter 020's reviewed cancellation/termination procedure only when justified. If it is admission overload, coordinate client concurrency and retry control. If a known rollout triggered the regression, evaluate its rollback through the application's change procedure.

Do not raise memory/connections or disable autovacuum from one observation. Do not reset statistics to obtain a clean graph. Do not restart PostgreSQL as a substitute for understanding a pool or authentication issue.

Keep one change and one verification question together. Record what was altered, expected effect, rollback and time. If conditions change, collect fresh evidence rather than applying the next action to a stale PID or query identity.

## Escalate query-plan analysis safely

A query ranking identifies candidates, not a diagnosis. Review parameters, data skew, row counts, waits and the application operation before inspecting a plan.

Plain EXPLAIN reports an estimated plan; EXPLAIN ANALYZE executes the statement and has overhead and side effects. Even a read-only transaction is not a universal sandbox for every callable function or external side effect. Chapter 027 supplies the execution safeguards.

This lab uses a server sleep to demonstrate an active statement that is slow without expensive computation. It deliberately avoids synthetic CPU/disk exhaustion and plan execution against arbitrary application queries.

## Validate recovery at the consumer boundary

After a mitigation, confirm the original impact improves: request success, tail latency, queue depth or throughput, with correct data outcomes. Also verify the database mechanism: blocker disappeared, waiting requests advanced, admission fell or the relevant resource pressure eased.

A transaction rolling back can release a lock while clients still need recovery. An automatically reconnected application name does not prove the old session survived. Retry bursts may continue after the initial blocker is gone.

Compare a post-change interval under declared conditions, with residual risks. A faster warmed-cache query on a quiet database is not automatically proof of a production fix. Record unresolved evidence rather than converting uncertainty into certainty.

## Produce a reviewable incident evidence pack

Use a short narrative: impact/window, verified source, observations, hypothesis, chosen action and recovery. Keep raw private snapshots with provenance and exit status. Separate facts from interpretation and note alternative causes that the data does not resolve.

Include collection timestamps, timezone, version, node/database identity and any reset/start boundary. Include the relevant sanitized trace/error evidence and host/cgroup/storage scope. Retain SQL text only through a separately approved restricted workflow.

The linked lab produces baseline, held-transaction, blocked-request, active-sleep and recovered bundles. It asks for a defensible lock hypothesis and explicitly rejects “active means CPU saturated.” All mutations are isolated fixture updates followed by rollback.

## Acceptance and references

Acceptance requires bounded collection status, interpretable partial evidence, an upstream blocker identified with stable identity, a correct recovery observation and a written hypothesis that respects source/measurement limits.

- [PostgreSQL activity and cumulative statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [Monitoring activity](https://www.postgresql.org/docs/18/monitoring.html)
- [Explicit locks](https://www.postgresql.org/docs/18/explicit-locking.html)
- [Using EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html)
- [EXPLAIN execution behavior](https://www.postgresql.org/docs/18/sql-explain.html)

Next: Chapter 027 — EXPLAIN and EXPLAIN ANALYZE Safely.
