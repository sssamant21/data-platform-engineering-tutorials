# 019 — Long Transactions, Idle Sessions and Transaction Timeouts

Audience: DBRE and SRE. Baseline: PostgreSQL 18. Status: authored and statically reviewed; runtime lab verification pending.

[Previous: Locks and Deadlocks](018-locks-blocking-chains-and-deadlocks.md) · [Lab](../labs/019-long-transactions-idle-sessions-and-timeouts-lab.md) · [Master plan](../MASTER-PLAN.md)

## Operational outcome

Identify a transaction that outlived its useful work, distinguish client inactivity from server execution, and choose a workload-specific timeout without confusing statement cancellation with connection loss. Explain who owns recovery and demonstrate rollback after a timeout.

A connection can be inexpensive while idle outside a transaction and disruptive while idle inside one. A request handler that updates a row, calls an external API and forgets to commit can retain locks throughout the network delay. A report with a long-lived snapshot can delay removal of obsolete row versions even when it never writes.

## Interpret the clocks before intervening

| Activity state | Meaning | Useful clock | Operational question |
|---|---|---|---|
| active | Executing a statement, possibly waiting | query_start and wait_event | Is it working, waiting for a lock, or waiting elsewhere? |
| idle | Waiting for client input outside a transaction | state_change | Is this expected pool capacity? |
| idle in transaction | Waiting for input with an open transaction | xact_start and state_change | Which application path failed to finish? |
| idle in transaction (aborted) | Waiting after an error in a transaction block | state_change; inspect transaction context | Why has the client not rolled back? |

Use backend_start with PID: operating systems can reuse a PID. For an idle backend, query_start describes the last statement, not an actively running query. Transaction age and idle interval answer different questions. A sequence of short statements can have a large total transaction age.

backend_xmin helps identify an advertised snapshot horizon; a NULL value does not prove the session has no operational impact. Read Committed does not retain the same statement snapshot between every command. A transaction can still retain locks, and an assigned transaction ID can matter independently of a snapshot. An aborted transaction needs client recovery; do not infer its remaining resources from its display label alone.

The [metadata collector](../scripts/019-transaction-age-inspection.sql) reports these clocks without reading application tables or exporting query text. Run it through an approved monitoring connection with suitable visibility, such as pg_monitor in this lab. A restricted role can see incomplete information. Collect a few bounded samples rather than continuously scanning every backend.

## Diagnose the service effect

Connect age to evidence: blocked request count, oldest relevant snapshot, dead-tuple trend, vacuum progress, connection occupancy and application deadlines. One long transaction is not automatically an incident. Establish the expected transaction duration for this service and whether the backend is preventing useful work.

Investigate application request IDs through approved observability channels. Query text can contain credentials or customer data and is unnecessary for the first metadata snapshot. application_name is a correlation aid supplied by clients, not a trusted identity.

Old snapshots can prevent vacuum from removing versions still needed by readers. Transaction-ID age measures a different risk than elapsed wall time. Replication slots, prepared transactions and standby feedback can also hold retention horizons; terminating one ordinary backend does not resolve all causes of vacuum delay.

## Know the timeout boundary

| Parameter | Budget applies to | Result on expiry | Expected server SQLSTATE |
|---|---|---|---|
| statement_timeout | One statement, including its waits | Statement canceled | 57014 |
| lock_timeout | Each lock acquisition attempt | Statement canceled | 55P03 |
| idle_in_transaction_session_timeout | Client inactivity inside a transaction | Session terminated | 25P03 |
| idle_session_timeout | Client inactivity outside a transaction | Session terminated | 57P05 |
| transaction_timeout | Total explicit or implicit transaction duration | Session terminated | 25P04 |

Zero disables each setting. Use explicit units. transaction_timeout was introduced in PostgreSQL 17; older servers need a different policy. Prepared transactions are excluded from this timeout and need separate ownership and monitoring.

A lock budget does not cap overall statement duration. Repeated acquisitions can consume multiple lock budgets. Set a lock budget below the statement budget when you want a distinguishable lock error. transaction_timeout can end a transaction while a statement is active. When it is less than or equal to statement_timeout or idle_in_transaction_session_timeout, the longer competing timeout is ignored. Do not model all settings as independent timers that always produce separate errors.

Server timeout coverage begins in server processing. Connection establishment, pool queuing and portions of the end-to-end request lie outside these budgets. Client deadlines must include those costs and leave enough time to receive an error and recover. Choose numbers from the service latency objective, observed work and operational exceptions; the lab values intentionally accelerate failures.

## Recovery is part of the policy

After a canceled statement inside an explicit transaction, the usual transaction block remains failed until ROLLBACK. Subsequent ordinary commands return 25P02. A savepoint can support deliberate local recovery, but applications must implement that contract. An autocommit statement failure does not leave a surrounding explicit transaction block open.

After session termination, the original connection cannot be reused. Discard it from the pool, reconnect if appropriate, and rebuild required session state. Interactive psql may reconnect automatically after detecting failure: compare backend PID and backend_start before claiming a transaction or setting survived. The client may discover an idle timeout only on its next operation.

A timed-out uncommitted transaction is rolled back. That does not justify replaying an arbitrary request after every lost connection. If connection loss occurs around COMMIT, the client may not know whether it committed. Resolve outcome through idempotency keys or application reconciliation before retrying. External API side effects do not roll back with PostgreSQL.

idle_session_timeout requires special care with pools that expect parked connections to remain usable. Exercise connection checkout validation, stale socket handling and reconnect storms. Every policy needs an owner for exceptions such as migrations and legitimate batch workloads.

## Apply settings at the intended scope

Use SET LOCAL inside an explicit transaction for a bounded operation; its setting ends with that transaction. Session SET applies to that connection and can be rolled back if issued within a transaction. A pool must reset session state correctly.

For an approved production role and database, the following is an illustrative policy, not a lab instruction or universal recommendation:

~~~sql
ALTER ROLE service_role IN DATABASE service_db
  SET statement_timeout = '8s';
ALTER ROLE service_role IN DATABASE service_db
  SET lock_timeout = '1s';
ALTER ROLE service_role IN DATABASE service_db
  SET idle_in_transaction_session_timeout = '30s';
ALTER ROLE service_role IN DATABASE service_db
  SET transaction_timeout = '45s';
~~~

Role/database defaults take effect on new connections, without a server reload. SET ROLE does not apply the target role's login defaults. Inspect effective SHOW values on a real fresh service connection, including connection startup options. SHOW in the observer reports the observer's values, not another backend's session overrides.

Before changing defaults, record existing pg_db_role_setting entries at the exact scope. Roll back to those recorded values; RESET only restores absence of an override when absence was the original state. Recycle connections in controlled batches and monitor error classes, reconnections and latency. These user-adjustable settings are operational guardrails, not security boundaries. Avoid a broad global default that accidentally captures backups, maintenance or all pooled clients.

## Incident workflow

1. Establish database, service, backend PID/start time, transaction age, state and wait event.
2. Confirm the impact and locate the transaction owner. Check whether the session is performing approved work.
3. Ask the owner to complete or roll back when feasible; fix the application path that retained the transaction.
4. If emergency intervention is justified, follow Chapter 020's identity checks and cancellation/termination procedure. A cancellation aimed at an idle client does not close its transaction.
5. Validate lock release, vacuum horizon changes, pool recovery and application outcomes. Record the original error rather than only downstream 25P02.
6. Review batching, transaction boundaries, external calls, timeout scopes and exception ownership.

Never terminate every session above an arbitrary age. Prepared transactions are not ordinary backends and require separate analysis.

## Acceptance evidence

Complete the linked lab. Retain sanitized metadata and original SQLSTATEs showing active versus idle states, canceled statement versus terminated session, rollback of uncommitted writes, restoration after SET LOCAL and detection of a replacement connection. Include the exact server version and effective actor settings.

Static review is not completion evidence. A production rollout additionally requires driver/pool integration tests and measured service recovery.

## Official references

- [PostgreSQL 18 client timeouts](https://www.postgresql.org/docs/18/runtime-config-client.html)
- [Activity statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [Routine vacuuming](https://www.postgresql.org/docs/18/routine-vacuuming.html)
- [SET and SET LOCAL](https://www.postgresql.org/docs/18/sql-set.html)
- [Role configuration defaults](https://www.postgresql.org/docs/18/sql-alterrole.html)
- [Error codes](https://www.postgresql.org/docs/18/errcodes-appendix.html)
- [PostgreSQL 17 release notes](https://www.postgresql.org/docs/17/release-17.html)

Next: Chapter 020 — Safe Cancellation, Termination and Concurrency Incident Lab.
