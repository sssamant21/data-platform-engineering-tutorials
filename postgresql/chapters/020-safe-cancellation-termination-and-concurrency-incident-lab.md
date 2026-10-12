# 020 — Safe Cancellation, Termination and Concurrency Incident Lab

Audience: DBRE and SRE only. PostgreSQL 18 baseline.
Status: authored/static reviewed; PostgreSQL execution pending.

[Previous: Transaction Timeouts](019-long-transactions-idle-sessions-and-transaction-timeouts.md) · [Hands-on incident lab](../labs/020-safe-cancellation-termination-and-concurrency-incident-lab.md) · [Master plan](../MASTER-PLAN.md)

## Operational outcome

Choose a specific intervention from a blocking graph, preserve evidence, verify the target immediately before signaling, and prove application recovery afterward. This chapter closes the concurrency sequence from MVCC through transaction timeouts. It is an incident procedure, not an age-based session eviction policy.

A canceled waiter can reduce demand without removing the root blocker. A terminated blocker can release a queue but also interrupt legitimate work and trigger retries. Successful recovery means useful requests resume with correct outcomes, not merely that a signaling function returned true.

## Choose the smallest useful intervention

| Situation | First operational choice | What to verify |
|---|---|---|
| Owner can finish an open transaction promptly | Owner COMMIT or ROLLBACK according to application intent | Outcome, released locks and downstream progress |
| An active request exceeded its usefulness | Cancel that statement if justified | Original error, transaction recovery and request outcome |
| Idle transaction retains a harmful lock and owner cannot recover it | Terminate the specifically approved session | Original backend disappearance and pool recovery |
| A queued maintenance lock delays normal traffic | Review the maintenance owner and its queued request | Whether removing that request restores traffic |
| Prepared transaction holds a lock | Escalate to transaction coordinator/DBRE ownership | Durable transaction decision, not a PID |
| Retrying clients recreate the queue | Control request admission and retry behavior | Recovery rate, concurrency and correctness |

Do not automatically escalate cancellation to termination after a fixed sleep. Reassess the state and incident effect. A statement can finish between inspection and cancellation; an application can issue its next statement on the same connection.

## Understand the signal boundary

pg_cancel_backend targets a current query. Its true return means the signal was sent, not that application recovery is complete. In an explicit transaction, a cancellation error normally requires client ROLLBACK or deliberate savepoint recovery. A canceled autocommit statement has no surrounding transaction block to repair.

pg_terminate_backend ends a session. With a positive timeout in milliseconds, it waits for termination and can return false with a warning if the wait expires. With the default zero timeout, true acknowledges signal delivery only. A false result or interrupted administrative call does not prove the backend survived; observe again before taking another action.

The client commonly receives 57014 for cancellation and 57P01 for administrative termination. A client library may instead expose a connection failure depending on delivery and its state. Retain the original server/client evidence. A downstream 25P02 says the client is still in a failed transaction block; it does not identify the original cause.

An idle-in-transaction backend is waiting for client input, so cancellation is not a transaction-closing mechanism. A failed transaction's locks and other resources depend on error and savepoint handling; do not equate a persistent aborted prompt with proof that every earlier lock is still retained. Termination discards the session, rolls back its uncommitted work and removes session state, including session advisory locks.

Do not use an operating-system kill as the normal runbook. In particular, SIGKILL can force cluster-wide crash recovery when PostgreSQL treats an unexpected backend death as potentially corrupting shared memory. Session signaling functions are not server restart commands.

## Establish authority separately from visibility

An observer with pg_monitor can diagnose; monitoring privileges alone do not authorize signaling every backend. Function privileges, target-role membership and predefined signaling roles determine what the caller may do. pg_signal_backend does not permit signaling superuser backends. PostgreSQL 18 also has a distinct pg_signal_autovacuum_worker capability; this lab does not grant it.

Grant operational roles through approved access management rather than making the monitoring account a superuser. Review role membership, function grants and service scope. The lab uses the existing disposable lab_admin for actuation and lab_observer for metadata; it makes no new privilege grants.

A production authorization should name the affected service, target transaction, reason, action, operator and incident reference. Existing emergency procedures determine whether additional incident approval is required. A database permission is not proof that an action is operationally appropriate.

## Build and review the graph

Capture time, server identity, database, PID, backend_start, role, state, xact_start, query_start, state_change and wait events. Capture direct blocking edges and inspect upstream nodes before choosing a target. Query text is excluded from the supplied collector; application identifiers and sanitized traces usually provide the first correlation.

pg_blocking_pids includes conflicting holders and conflicting requests ahead in the queue. Parallel execution can produce repeated client-visible PIDs; deduplicate edges. A blocker of zero represents a prepared transaction. Never call a signaling function on zero or invent a replacement PID.

The [scoped lab snapshot](../scripts/020-concurrency-incident-snapshot.sql) limits actor enumeration before requesting blocker information. Edges can point outside that actor set. Treat those as boundaries requiring investigation, not permission to act on unreviewed sessions. Graph cycles and changing observations require diagnosis; PostgreSQL deadlock detection is a separate mechanism.

Activity and lock observations are not an atomic photograph. Take fresh bounded samples, record differences, and avoid sustained high-frequency polling that adds lock-manager overhead.

## Verify one target immediately before acting

The [lab signal script](../scripts/020-reviewed-session-signal.sql) requires an explicit action, confirmation, target PID/start time, state, query start and application label. It fixes the database to ops_lab, role to lab_app and backend type to client backend; it excludes self and superuser targets. Cancellation additionally requires active state. It refuses an identity or state mismatch by producing no signal row.

The helper is deliberately scoped to this disposable lab. It is not a generic production auto-remediation tool. Its application label is a guardrail, not authenticated identity. Its shell caller verifies the Chapter 004 directory before any connection; SQL does not independently verify that filesystem marker.

Even combined filters and a single signaling SELECT cannot eliminate the race between observation and a PID-based signaling API. backend_start helps detect PID reuse before the call, but the API itself accepts no backend generation or query token. query_start narrows the chance of canceling subsequent work; it cannot make that race impossible. If work changes rapidly, use the application's own cancellation contract or coordinated connection ownership.

Preview, decide, act once, then observe. Never wrap the signal in a transaction and expect ROLLBACK to retract it: signals are external effects. Do not repeatedly signal a cached PID.

## Verify the service, connection and data outcomes

After cancellation, confirm that the intended wait or execution stopped and the client performed recovery. The connection can remain alive. The root blocker may remain; recheck the graph rather than declaring the incident resolved.

After termination, confirm the original PID/backend_start pair disappeared. Application names can survive automatic reconnection. Compare connection identities, discard stale pool entries, recreate required session settings and assess reconnect/retry pressure.

Validate data with application-specific invariants. The lab uses rollback-only fixture mutations so its expected final balances remain 100 and 200. Production requests may involve external side effects or an uncertain COMMIT outcome. Do not assume that connection loss proves a request was uncommitted; reconcile durable request IDs before retrying.

A positive termination wait describes process termination, not restored application availability, completed replica replay or vacuum recovery. Check the affected request path, queue depth, latency, error rate and resource trend. Maintain controlled admission while recovery capacity is limited.

## Incident record and prevention

Retain a compact record:

- Impact: affected service, request failure/latency, onset and observation window.
- Evidence: sanitized graph, target identity and transaction/request ownership.
- Decision: why owner recovery, cancellation or termination was chosen.
- Action: operator, time, requested function, result and warnings.
- Recovery: target disappearance or transaction recovery, graph changes and data invariants.
- Follow-up: transaction boundaries, batching, lock order, timeout scopes and retry controls.

Avoid storing raw credentials, parameter values or customer SQL in the record. An application transaction spanning an external call needs boundary redesign, not only a smaller database timeout. A migration that queues a strong lock needs scheduling and lock-acquisition policy. A retry wave needs bounded backoff, jitter and admission control.

The integrated lab requires you to cancel a middle waiter, show that the upstream holder remains, reject a stale target, distinguish idle cancellation from termination and prove rollback. Re-running a stale action after a client reconnects is an acceptance failure.

## Official references

- [Server signaling functions](https://www.postgresql.org/docs/18/functions-admin.html#FUNCTIONS-ADMIN-SIGNAL)
- [Predefined operational roles](https://www.postgresql.org/docs/18/predefined-roles.html)
- [Blocking PID semantics](https://www.postgresql.org/docs/18/functions-info.html)
- [Activity statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [Explicit locks and deadlocks](https://www.postgresql.org/docs/18/explicit-locking.html)
- [Error codes](https://www.postgresql.org/docs/18/errcodes-appendix.html)
- [Prepared transaction recovery](https://www.postgresql.org/docs/18/sql-rollback-prepared.html)

Next: Chapter 021 — Database SLIs, SLOs and Error Budgets.
