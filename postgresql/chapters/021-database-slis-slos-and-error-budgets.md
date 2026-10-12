# 021 — Database SLIs, SLOs and Error Budgets

Audience: DBRE and SRE only. PostgreSQL 18 baseline.
Status: authored/static reviewed; live PostgreSQL lab execution pending.

[Previous: Concurrency Incident Lab](020-safe-cancellation-termination-and-concurrency-incident-lab.md) · [Hands-on measurement lab](../labs/021-database-slis-slos-and-error-budgets-lab.md) · [Master plan](../MASTER-PLAN.md)

## Operational outcome

Define a database service promise that matches a consumer operation, measure it at a declared boundary, calculate its budget and use the result to prioritize reliability work. A healthy PostgreSQL process does not establish that a service can complete useful transactions.

Distinguish three terms: an SLI is the measured indicator; an SLO is its target over a stated window; an SLA is a contractual commitment with consequences. This chapter creates internal operational objectives, not a customer contract.

## Define the consumer and operation first

Choose one service and operation class before selecting numbers. An interactive lookup, a durable write and a nightly data load have different deadlines and outcomes. Separate production from staging and separate read endpoints from write endpoints. A fleet-wide average can hide a failing tenant or critical workload.

A DBRE-managed database service can expose a component SLO measured from application infrastructure to the database endpoint. The owning application still needs its end-to-end SLO. Pool checkout, network paths, routing, authentication and transaction handling can fail while the database is locally healthy.

| Dimension | Good-event definition | Measurement boundary |
|---|---|---|
| Availability | Eligible logical operation completes with its required result | Client operation start through result/commit acknowledgment |
| Timely success | Eligible operation succeeds within its deadline | Same boundary, including declared waits and retries |
| Freshness | Relevant response contains data within its age bound | Business watermark at consumer read |
| Correctness | Result satisfies a declared invariant | Validated application outcome |
| Durability/recovery | Acknowledged data survives the declared failure scenario | Controlled recovery and reconciliation evidence |

Select the smallest useful set of objectives. CPU utilization, connection occupancy, lock queues and disk latency explain failures and warn about capacity; they are not direct substitutes for successful consumer operations.

## Write an SLI contract

Document service, environment, endpoint, operation class, eligible events, good-event predicate, clock boundary, source, aggregation, exclusions and owner. Include a version for the contract so a change in definition does not masquerade as reliability improvement.

Example only: primary lookup operations initiated by service X, excluding documented invalid input before database work, must return a validated result; timely success additionally requires completion within 250 ms. A not-found response may be good if that is a valid application outcome. Wrong data is not good merely because SQL completed.

Measure one logical operation, not every retry as a new success opportunity. Record the final outcome and the elapsed duration across all attempts when that is the contract. Attempt metrics remain useful for diagnosis. A timeout without a final known result is not a good event.

Define treatment of maintenance in advance. If users still need the operation during a maintenance window, excluding that window can hide actual impact. Do not change exclusions during an incident. A deployment, tenant or endpoint label must have bounded cardinality; do not export request IDs or SQL text as metric labels.

## Calculate the budget consistently

For N eligible events, G good events and target S:

~~~text
SLI = G / N
bad events = N - G
allowed bad events = N × (1 - S)
budget consumed = bad events / allowed bad events
remaining budget = allowed bad events - bad events
burn rate = (bad events / N) / (1 - S)
~~~

Budget consumed is a ratio: 1 means 100% consumed. Burn rate is normalized to the allowed bad fraction for the same SLI. A negative remaining budget is meaningful; do not clamp it to zero in the source report.

With 200,000 eligible operations and a 99.9% availability objective, allowance is 200 bad events. If 80 failed, availability is 99.96%, 40% of budget is consumed and burn rate is 0.4. Another 150 failures in that same event population would put the total at 230, above the allowance.

Event budgets can be fractional for small populations. One failure among ten requests at a 99.9% target consumes far more than the small allowance. Do not round allowance upward to manufacture room for failures. With no eligible events, the ratio is undefined: report no data rather than 100% success.

A time-based objective uses good time intervals and eligible time intervals instead. A 30-day time budget at 99.9% permits 43.2 bad minutes. This is not automatically equivalent to an event budget: an outage during peak traffic consumes more events than the same duration at night.

## Keep availability and latency definitions aligned

The supplied calculator defines availability as successes/all eligible operations and timely success as successful operations at or below the latency threshold/all eligible operations. Failed operations are bad for both. This prevents a fast failure from appearing as good latency.

You may choose a separate latency-only metric over successful operations, but label that denominator explicitly and retain availability alongside it. A p99 computed only from successful calls can look better during an outage when slow calls all fail.

Aggregate good and total counts across matching sources, then divide. Do not average host percentages or per-minute ratios without weighting. Histogram buckets support threshold counting; averaging p99 values from multiple servers does not recover a fleet p99.

## Declare windows and telemetry quality

Choose a calendar or rolling reporting window and a timezone. The lab uses UTC half-open intervals: start included, end excluded, assigned by operation completion time. A production contract may instead use start time; specify how outstanding operations are accounted for.

Declare how resets, delayed events, duplicate delivery, partial scrape coverage, time skew and source changes are handled. An empty file and a missing instrumentation path are not proof of zero failures. Compare captured logical operations with independent admitted/completed counts where possible and monitor the telemetry pipeline itself.

The [offline evaluator](../scripts/021-slo-evaluate.py) rejects malformed records and duplicate IDs. It distinguishes empty and low-volume samples. It cannot infer unrecorded requests, unbiased sampling or production coverage. A valid CSV is arithmetic input, not proof of telemetry completeness.

For cumulative counters, calculate deltas/rates with reset handling in the monitoring system. PostgreSQL statistics resets, restarts and extension resets require explicit measurement-window handling; Chapter 022 develops that topic.

## Separate endpoint readiness from successful work

pg_isready reports connection readiness, not whether your application's authentication, permissions, queries or transaction contract succeed. SELECT 1 validates a narrow path but cannot establish fixture correctness, write ability, replica freshness or recovery safety.

The lab's probe opens a connection, locks and reads one isolated row, validates its value and rolls back. Its elapsed time includes launching psql, connection establishment and commands. It excludes an application pool and uses a local endpoint. Its row-lock behavior is chosen to reproduce contention, not to represent every production read.

A rollback-only probe does not prove COMMIT durability. Use a separate bounded, authorized synthetic write and reconciliation design when the contract requires durable commit evidence. Do not let a health check compete aggressively with real traffic or allocate unbounded synthetic data.

PostgreSQL transaction counters are diagnostic: commits and rollbacks do not map one-to-one to application good and bad logical requests. Read-only successes, deliberate rollbacks and retries make that mapping unreliable.

## Alert on sustained budget risk

Use short and long observation windows for the same SLI to distinguish a current problem from old damage. A page should connect to actionable consumer impact and a runbook. Keep diagnostic alerts for conditions such as disk exhaustion even when there are too few requests to estimate a stable burn rate.

For a 30-day event SLO, a 14.4 burn rate sustained for one hour consumes about 2% of the budget only when that hour has its proportional share of total traffic. Under uniform traffic, a one-hour long window paired with a five-minute short window is one illustrative fast-burn design; a 6 burn rate over six hours corresponds to about 5%. These are teaching examples, not recommended thresholds for every database.

Under changing traffic, compute actual bad counts and reporting-window volume as well as normalized burn. Distinguish low traffic from missing telemetry. Avoid silently suppressing an outage because no successful events arrived.

Review alert precision, recovery behavior, volume thresholds and telemetry-loss alerts using historical incidents before paging. The offline lab does not implement production Prometheus rules.

## Turn the budget into an operational decision

Agree on the policy before an incident: who owns the objective, which changes can proceed during depletion, which reliability fixes are prioritized, how emergency/security work is handled and when restrictions are lifted.

A depleted budget should trigger a review of the dominant failure causes and planned change risk. A policy might defer discretionary migrations while lock-contention remediation is underway, while still allowing an approved security fix. Record decisions and exceptions; the calculator does not automatically freeze deployments.

Use separate durability, backup-restore and recovery requirements. An availability budget does not authorize losing acknowledged data. RPO/RTO promises need failure-mode-specific recovery evidence. Asynchronous replicas can be behind the primary; low connection error rate alone says nothing about recoverable data loss.

## Acceptance and references

Complete the lab with baseline, slow-success, lock-timeout and recovery samples. Preserve denominators, window boundaries, good predicates, budget calculations and telemetry limitations. Propose one component SLO and its relationship to the application SLO.

- [PostgreSQL activity monitoring](https://www.postgresql.org/docs/18/monitoring.html)
- [Statistics views and counters](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [pg_isready scope](https://www.postgresql.org/docs/18/app-pg-isready.html)
- [Replication and recovery context](https://www.postgresql.org/docs/18/warm-standby.html)
- [Google SRE: implementing SLOs](https://sre.google/workbook/implementing-slos/)
- [Google SRE: alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)
- [Example error-budget policy](https://sre.google/workbook/error-budget-policy/)

Next: Chapter 022 — Statistics Views, Resets and Measurement Windows.
