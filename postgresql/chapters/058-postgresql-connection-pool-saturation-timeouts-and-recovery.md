# Chapter 058 — PostgreSQL Connection Pool Saturation, Timeouts and Recovery

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 and versioned PgBouncer · **Status:** Authored; runtime validation pending

## 1. Mission

Diagnose and recover from PostgreSQL connection exhaustion and PgBouncer pool saturation while protecting in-flight transactions, application availability and administrator access. Build a measurable response based on queueing, wait events, backend budgets and transaction duration rather than reflexively increasing connection limits. This chapter follows [Chapter 057 — PgBouncer Pooling Modes and Sizing](057-pgbouncer-pooling-modes-sizing-and-transaction-compatibility.md).

## 2. Failure domains

```text
Application threads / client pool
        |
        | client acquisition timeout
        v
PgBouncer client slots -> pool waiting queue -> PgBouncer server slots
                                                |
                                                | authentication / TCP / TLS
                                                v
                                      PostgreSQL backend slots
                                                |
                                    CPU / I/O / locks / long transactions
```

A request can time out at the application pool, PgBouncer waiting queue, TCP/TLS handshake, PostgreSQL backend allocation or SQL execution. **Timeout messages alone do not identify the bottleneck.** Correlate the hop and its timestamps.

## 3. Symptoms and distinctions

| Symptom | Likely layer | Verify |
|---|---|---|
| `remaining connection slots are reserved` | PostgreSQL connection ceiling | `max_connections`, reserved slots, `pg_stat_activity` |
| `too many clients already` | PostgreSQL or PgBouncer client cap (context-dependent) | Endpoint, pooler logs and connection counters |
| PgBouncer `cl_waiting` rises | Pool queue | `SHOW POOLS`, `SHOW STATS`, queue age |
| Client-side pool acquisition timeout | App pool | Thread count, active/idle/leaked clients |
| Many `idle in transaction` sessions | App transaction lifecycle | `pg_stat_activity`, transaction age, locks |
| High `sv_active` and long waits | Busy server connections | Lock/I/O/CPU diagnosis |
| Backend count normal, latency high | Query/lock/IO bottleneck | Wait events, pg_stat_statements, traces |
| Repeated reconnects | Network, failover or credentials | Pooler/server logs and TLS errors |

## 4. First five minutes: evidence before intervention

1. Confirm incident scope: affected applications, error rates, p95/p99, deployment and failover history.
2. Identify the exact endpoint clients use: direct PostgreSQL, PgBouncer, cloud proxy or application pool.
3. Preserve a separate administrator connection and do not consume reserved slots with broad troubleshooting.
4. Capture PostgreSQL sessions by database/user/application/state, long transactions and wait events using the [diagnostic SQL](../labs/sql/058-diagnostics.sql).
5. Capture PgBouncer `SHOW POOLS;`, `SHOW STATS;`, `SHOW CLIENTS;`, `SHOW SERVERS;`, `SHOW DATABASES;` and `SHOW CONFIG;` through the `pgbouncer` admin database.
6. Correlate application connection-acquisition latency with PgBouncer waiting age and PostgreSQL execution latency.

## 5. Capacity math and backpressure

```text
available_application_backends =
 max_connections
 - superuser_reserved_connections
 - reserved_connections
 - operational_headroom
 - nonapplication_connections
```

`reserved_connections` and `superuser_reserved_connections` have distinct role eligibility rules. The formula is a **planning model**: actual usable slots also depend on PostgreSQL role and reservation semantics.

**Example:** 200 max connections, 3 superuser reserved, 5 general reserved, 20 operational headroom and 12 other connections yields 160 budgeted application backends. Two PgBouncer instances each configured with 4 user/database pools and 25 server connections can demand 200 server slots before accounting for direct clients. Reduce aggregate pool caps or redesign topology.

A growing queue means arrival rate exceeds effective service rate over the observation window. Increasing pool size helps only if PostgreSQL has spare execution and memory capacity; otherwise it can amplify overload.

## 6. Timeouts: choose the correct layer

| Timeout | Layer | Purpose |
|---|---|---|
| App pool acquisition timeout | Client library | Bound waiting for app-owned connection |
| PgBouncer `query_wait_timeout` | Pooler | Bound client wait for a server connection |
| PgBouncer `server_connect_timeout` | Pooler | Bound connection establishment to PostgreSQL |
| `connect_timeout` | libpq | Bound client connection attempt |
| `statement_timeout` | PostgreSQL | Bound statement execution |
| `lock_timeout` | PostgreSQL | Bound lock acquisition waits |
| `idle_in_transaction_session_timeout` | PostgreSQL | Terminate idle-in-transaction sessions |
| `transaction_timeout` | PostgreSQL 17+ | Bound transaction lifetime |

Configure coherent deadlines: an application request deadline should encompass connection acquisition and query execution, with explicit room for cleanup. Avoid setting `lock_timeout` equal to or above `statement_timeout` when both are enabled, because the latter may fire first. `transaction_timeout` can supersede longer session/statement timeout settings; review interactions for the installed PostgreSQL version. Avoid universal timeout values without workload evidence.

## 7. Safe recovery ladder

**A. Stabilize demand.** Pause noncritical batch jobs, lower retry fanout, apply backoff with jitter and reduce application concurrency. Avoid reconnect storms.

**B. Remove root blockers.** Identify blocking chains, long transactions, I/O saturation and runaway queries. Work with application owners to cancel specific queries using `pg_cancel_backend(pid)`; cancellation targets the current query, not necessarily the session.

**C. Terminate only when justified.** `pg_terminate_backend(pid)` ends a session and rolls back its open transaction. Confirm role/permission, workload owner, transaction impact, replica/recovery implications and connection replacement behavior before execution. Never terminate indiscriminately.

**D. Pooler operations.** Use approved PgBouncer `PAUSE`, `RESUME`, `RECONNECT`, `RELOAD` or pool tuning only with version-specific semantics understood. Some commands wait for transactions or close server connections; an incorrect sequence can extend an outage.

**E. Capacity changes last.** Increasing `max_connections` generally requires PostgreSQL restart and may worsen memory contention. Only change after validated capacity assessment and rollback planning.

## 8. Read-only triage SQL

```sql
SELECT datname,usename,application_name,state,count(*) AS sessions
FROM pg_stat_activity GROUP BY 1,2,3,4 ORDER BY sessions DESC;

SELECT pid,usename,application_name,state,wait_event_type,wait_event,
       now()-xact_start AS xact_age, now()-query_start AS query_age
FROM pg_stat_activity
WHERE backend_type='client backend' AND pid<>pg_backend_pid()
ORDER BY xact_start NULLS LAST LIMIT 30;
```

Access to other users' query text and details may require `pg_read_all_stats` or other monitoring privileges. Redact sensitive SQL before sharing. Prefer targeted inspection over unbounded query dumps.

## 9. Incident decision matrix

| Finding | Intervention | Guardrail |
|---|---|---|
| `cl_waiting` high, backend CPU low, locks high | Resolve blocker | Confirm blocking PID and transaction owner |
| `cl_waiting` high, CPU saturated | Reduce concurrency and optimize workload | Do not blindly increase pool |
| App pool exhausted, PgBouncer idle | Inspect app leak/thread starvation | Restart affected workers only if safe |
| Backend slots exhausted by idle sessions | Fix pool sizing and idle cleanup | Preserve admin/replication sessions |
| Burst after failover | Stagger reconnections, verify endpoint | Avoid synchronized retries |
| Bad credentials/TLS after rotation | Restore valid secret/trust chain | Do not weaken auth/TLS |

## 10. Recovery verification and prevention

Verify error rates and queue age return to baseline, connection counts stay under budget, long transactions drain, p95/p99 improve and application requests succeed end-to-end. Monitor PgBouncer `cl_waiting`, maximum wait, server utilization, PostgreSQL backend count, connection failures, transaction age and app acquisition latency. Set alerts with sustained windows and environment-specific thresholds.

Document trigger, detection gap, actions, recovered metrics, data integrity checks, change history, incident timeline, and follow-up owners. Treat repeated saturation as a capacity or workload design issue rather than only a pool configuration issue.

## 11. Hands-on lab

The [Chapter 058 lab](../labs/058-postgresql-connection-pool-saturation-timeouts-and-recovery-lab.md) uses controlled small-scale contention in a disposable PostgreSQL 18 database, read-only diagnostics, and manual PgBouncer queue inspection. It includes safe cancellation and termination decision exercises and a recovery checklist.

**Acceptance:** correct layer identified, bounded queueing, preserved administrative access, no unsafe session kills, and documented rollback. **Runtime:** pending.

## References

- [pg_stat_activity](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [Client connection defaults](https://www.postgresql.org/docs/18/runtime-config-connection.html)
- [Statement and transaction timeouts](https://www.postgresql.org/docs/18/runtime-config-client.html)
- [PgBouncer usage](https://www.pgbouncer.org/usage.html)
- [PgBouncer configuration](https://www.pgbouncer.org/config.html)

**Next:** Chapter 059 — PostgreSQL Connection Pool Monitoring, Capacity and Alerting.
