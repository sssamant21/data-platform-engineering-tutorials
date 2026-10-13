# Chapter 097 — PostgreSQL Production Incident Simulation, Root Cause Analysis and Corrective Actions

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Rehearse a complete production-style PostgreSQL incident, from alert to application recovery, then produce a blameless, evidence-backed RCA and corrective action plan. Build on [Chapter 096 — Incident Response and Operational Command](096-postgresql-enterprise-incident-response-escalation-and-operational-command.md).

**Safety:** all fault injection must use an isolated disposable PostgreSQL instance. Read-only diagnostics may be used in production with approved privileges; cancellation, termination, failover and DDL require explicit change authorization.

## 2. Scenario: transaction blocking causes application timeouts

A transaction holds a row lock while a second application transaction attempts to update the same record. Waiting requests accumulate, client pools saturate, and p95/p99 latency and errors rise. This is a **simulated hypothesis** until supported by SQL and application evidence. The initiating long transaction is not automatically the root cause; missing transaction timeouts, retry storms, pool sizing, weak alerting and workflow design may contribute.

```text
Long transaction -> blocked writes -> request queue -> pool pressure
                                              |
                                     p99 latency + errors
                                              |
                                 alert -> incident command
                                              |
                         diagnose -> bounded mitigation -> verify
                                              |
                             RCA -> COA -> retest -> signoff
```

## 3. Learning outcomes

- Detect incident onset and measure customer-facing impact.
- Identify blocking sessions using `pg_stat_activity`, `pg_locks` and `pg_blocking_pids`.
- Correlate database wait events with application traces, pooler telemetry and deployments.
- Evaluate reversible mitigation and protect transaction integrity.
- Produce a UTC timeline separating observations, hypotheses, decisions and actions.
- Distinguish trigger, contributing conditions, detection gaps and systemic causes.
- Create corrective actions with owner, due date, measurable verification and rollback.
- Demonstrate recurrence prevention through repeat testing and alert acceptance.

## 4. Incident roles and severity

Assign incident commander, DBRE lead, SRE/application lead, communications owner and scribe. Define severity using real impact, not simply the number of blocked sessions. Confirm affected services, tenant scope, duration, error rate, p95/p99 and critical transaction success rate. Record an explicit next-update time and escalation thresholds.

## 5. Reproducible lab design

Use PostgreSQL 18 and two `psql` sessions connected to a **disposable** database. Create an isolated test table:

```sql
CREATE SCHEMA IF NOT EXISTS incident097;
CREATE TABLE IF NOT EXISTS incident097.accounts (
  id bigint PRIMARY KEY,
  balance numeric(12,2) NOT NULL
);
INSERT INTO incident097.accounts(id,balance)
VALUES (1,100.00) ON CONFLICT (id) DO NOTHING;
```

Session A:

```sql
BEGIN;
UPDATE incident097.accounts SET balance=balance+1 WHERE id=1;
-- Keep the transaction open temporarily in the disposable lab.
```

Session B:

```sql
SET lock_timeout='5s';
UPDATE incident097.accounts SET balance=balance+2 WHERE id=1;
-- Expect lock timeout while A holds the row lock.
```

Session C runs [097 read-only diagnostic SQL](../labs/sql/097-incident-rca-inspect.sql) while B waits. Record PID, blocker, wait event, query age, transaction age, timestamp and application impact. In Session A, use `ROLLBACK` to release the test lock; verify B's outcome and that a new test write succeeds. Never terminate unknown production sessions.

## 6. Detection and diagnosis workflow

1. Capture baseline application latency, errors, throughput, pool wait and active connections.
2. Start the bounded disposable fault and note UTC time.
3. Observe database wait events and blocker/waiter relationship.
4. Check recent releases, migrations, batch jobs and pool retries.
5. Establish evidence supporting or rejecting each hypothesis.
6. Request approval for the smallest scoped mitigation.
7. Execute, monitor, and roll back if acceptance fails.
8. Confirm app read/write recovery and database health.

A single `pg_stat_activity` snapshot is not a complete causal history; correlate with historical metrics, logs and traces.

## 7. Root cause analysis framework

Separate:
- **Impact:** what customers experienced and for how long.
- **Trigger:** immediate event that preceded degradation.
- **Mechanism:** how lock waits or retries produced latency.
- **Contributing conditions:** transaction duration, missing timeout, pool behavior, workload shape.
- **Detection gap:** why monitoring did not catch it sooner.
- **Response gap:** what slowed diagnosis or mitigation.
- **Evidence and uncertainty:** observed data, timestamps, alternative hypotheses and limits.

Use counterfactual checks: would the incident still occur if the long transaction ended promptly, or if pool retries were bounded? Do not attribute human fault without evidence.

## 8. Corrective and preventive actions

| Action type | Example | Acceptance test |
|---|---|---|
| Prevention | Bound transaction lifetime with approved `idle_in_transaction_session_timeout` policy | Long idle transactions terminated in disposable test without application regression |
| Prevention | Shorten transaction scope in application code | No sustained blocker under peak workload |
| Protection | Bounded pool sizes and retry jitter | No cascading retry storm in load test |
| Detection | Alert on blocked critical transactions and app p99 | Alert fires within policy and pages correct owner |
| Response | Blocking-chain runbook and scoped cancel/rollback | On-call identifies blocker within target time |
| Recovery | Application transaction reconciliation | No missing or duplicate critical updates |

Avoid deploying timeouts blindly: they can abort legitimate work. Validate with application owners and representative tests.

## 9. RCA evidence and publication

Use [RCA template](../labs/incident/097-blameless-rca-template.md), [incident event timeline](../labs/incident/097-incident-simulation-timeline.csv) and [COA tracker](../labs/incident/097-corrective-action-tracker.csv). Preserve original evidence, anonymize SQL samples and customer details, and explicitly label simulated values.

## 10. Acceptance gates

- Incident commander and severity established.
- Application impact quantified from real test metrics.
- Blocker/waiter chain observed and correlated with symptoms.
- Scoped mitigation approved, executed and measured.
- Database and application recover without integrity violations.
- RCA distinguishes facts, hypotheses and systemic contributors.
- Preventive, detective and recovery COAs assigned and verified.
- Repeat fault test demonstrates improvement.
- Independent reviewer signs off.

Use [097 scorecard](../labs/acceptance/097-incident-rca-scorecard.csv). An authored RCA without an executed drill is **NOT VERIFIED**.

## 11. References

- https://www.postgresql.org/docs/18/monitoring-stats.html
- https://www.postgresql.org/docs/18/explicit-locking.html
- https://www.postgresql.org/docs/18/runtime-config-client.html
- https://www.postgresql.org/docs/18/functions-admin.html

**Next:** Chapter 098 — PostgreSQL Reliability Automation, Continuous Validation and Operational Excellence.
