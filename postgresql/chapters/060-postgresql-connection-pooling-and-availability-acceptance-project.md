# Chapter 060 — PostgreSQL Connection Pooling and Availability Acceptance Project

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 and versioned PgBouncer · **Status:** Authored; runtime acceptance pending

## 1. Mission

Prove that an application's connection-pooling design meets availability, correctness, security and operational capacity requirements during normal traffic and controlled failure. This capstone integrates [Chapter 056 — Fundamentals](056-postgresql-connection-management-and-pgbouncer-fundamentals.md), [Chapter 057 — Pooling Compatibility](057-pgbouncer-pooling-modes-sizing-and-transaction-compatibility.md), [Chapter 058 — Saturation and Recovery](058-postgresql-connection-pool-saturation-timeouts-and-recovery.md), and [Chapter 059 — Monitoring and Alerting](059-postgresql-connection-pool-monitoring-capacity-and-alerting.md).

**Scope:** isolated PostgreSQL 18 + PgBouncer lab. Never run deliberate exhaustion or failover tests against production without a separately approved change window, workload impact analysis and rollback.

## 2. Reference topology

```text
Synthetic workload / app
      |
 app connection pool
      |
  PgBouncer A  <-->  PgBouncer B (independent instances / routing)
      |                   |
      +------ secure PostgreSQL endpoint -------+
                      |
             PostgreSQL 18 primary
                      |
           optional managed failover target
                      |
       metrics + logs + alerts + incident record
```

A pair of PgBouncer instances does **not** by itself provide high availability: test health checks, load balancer routing, DNS, credentials, backend reconnect, session draining and application retry semantics. If the lab has no HA PostgreSQL target, treat database failover as **not tested** rather than claiming success.

## 3. Acceptance contract

Capture baseline versions, architecture, client/driver pool settings, PostgreSQL max/reserved slots, PgBouncer pool mode and pool cardinality, approved connection budget, transaction behavior, TLS/auth configuration, traffic profile, SLOs and escalation contacts.

| Gate | Required proof | Mandatory |
|---|---|---|
| Connection budget | Aggregate backend ceiling below approved budget | Yes |
| Normal load | Throughput and p95/p99 within agreed SLO | Yes |
| Burst handling | Bounded queue age and error budget | Yes |
| Transaction correctness | No lost/duplicated committed operations | Yes |
| Session compatibility | Driver/ORM features verified | Yes |
| Security | SCRAM/TLS verified on both hops | Yes |
| Pooler disruption | Routing/recovery within recovery objective | Yes |
| PostgreSQL disruption | Reconnect and data correctness verified, if HA in scope | Conditional |
| Observability | Pool queue, backend headroom, errors and alerts visible | Yes |
| Rollback | Safe reversion and post-rollback verification | Yes |

**NOT VERIFIED is not PASS.** Record explicit acceptance thresholds before testing; sample thresholds in this chapter are illustrative.

## 4. Connection-budget design

```text
postgres_app_budget =
 max_connections
 - superuser_reserved_connections
 - reserved_connections
 - operational_headroom
 - nonpooled_clients

aggregate_pgbouncer_ceiling =
 sum across pooler instances and active database/user pools
    (default_pool_size + reserve_pool_size)
```

Adjust for per-database/per-user limits, per-database overrides and nonapplication clients. Example: 250 PostgreSQL slots, 3 superuser reserved, 5 reserved, 25 headroom and 17 direct/operational clients -> 200 available for pooled backends. Two PgBouncer instances × four pools × (20 + 5) = 200 potential backends: this consumes the full allowance and leaves **zero unallocated buffer** inside that budget; consider reducing caps and measuring actual peaks.

## 5. Workload and evidence design

Use a disposable table with a unique idempotency key, request ID and committed timestamp. Run fixed-duration baseline and controlled burst workloads. Record successful/failed request IDs, committed rows, duplicate key attempts, client-side acquisition latency, PostgreSQL backend count, PgBouncer queue age, transaction duration and p95/p99 response time.

For ambiguous failures after COMMIT, a client cannot assume whether the transaction committed. Resolve by querying the idempotency key or using an application-level idempotent retry strategy; **never retry a non-idempotent write blindly**.

## 6. Test matrix

| Test | Injection | Expected result |
|---|---|---|
| T01 baseline | Stable low load | SLOs met, no sustained waiters |
| T02 burst | Bounded increase in clients | Queue drains, backends within budget |
| T03 long transaction | Hold a row lock briefly | Alert/diagnosis identifies blocker; no unsafe kills |
| T04 client pool leak simulation | Retain a few lab client sessions | Acquisition delay visible at app layer |
| T05 PgBouncer restart | Restart one isolated pooler with traffic routed safely | Requests recover per agreed objective |
| T06 database restart | Controlled PostgreSQL restart in disposable lab | Connections reestablish, transactions reconciled |
| T07 TLS/auth error | Incorrect lab credential or CA | Connection fails securely; alert fires |
| T08 compatibility | Session state, temp tables, prepared statements | Transaction mode approved only when compatible |
| T09 telemetry loss | Stop test exporter briefly | Missing telemetry detected |
| T10 rollback | Restore previous routing/config | Service and correctness verified |

T05/T06 may interrupt sessions and roll back open transactions. Run only after preserving a known-good state and informing lab participants. If a test cannot be safely executed, mark it NOT VERIFIED with a reason.

## 7. Phased execution

**Phase A — Preflight:** verify topology, backups, monitoring, credentials, break-glass access and stop conditions. Run [preflight SQL](../labs/sql/060-preflight.sql) and snapshot PgBouncer admin SHOW output.

**Phase B — Baseline:** capture 10–15 minutes of steady traffic with defined throughput and latency; ensure exporter/alert health.

**Phase C — Compatibility:** test protocol prepared statements, temporary tables, session GUCs, advisory locks and transaction boundaries under chosen pooling mode.

**Phase D — Controlled failures:** inject bounded bursts, one supervised lock wait, pooler restart and database restart only where approved. Capture client errors and pooler recovery.

**Phase E — Correctness:** reconcile request IDs and committed rows. Check duplicates, missing commits and application error semantics.

**Phase F — Rollback:** restore original routing and configuration; validate auth, TLS, connection counts, latency and transaction correctness.

## 8. Metrics and alert acceptance

Collect PgBouncer `SHOW POOLS`, `SHOW STATS`, `SHOW DATABASES`, `SHOW SERVERS`; PostgreSQL `pg_stat_activity`, waits and backend limits; application acquisition p95/p99, timeouts, retries and transaction outcomes. Test alerts for sustained waiters, critical backend utilization, acquisition timeouts, exporter loss and repeated auth errors. Verify notification delivery and on-call ownership.

Use workload-specific thresholds. A transient queue is not necessarily a failure if latency and error objectives remain met; sustained wait plus customer-impacting errors is actionable.

## 9. Safe recovery ladder

1. Confirm the failure layer and preserve metrics/logs.
2. Stop new load and reduce retry fanout; protect administrative access.
3. Resolve blocking transactions or slow queries with application owner approval.
4. Use PgBouncer reconnect/drain/reload procedures appropriate to the installed version.
5. Verify endpoint routing and PostgreSQL primary identity before resuming writes.
6. Reconcile ambiguous commits using idempotency keys.
7. Roll back to the known-good topology if SLOs do not recover within the agreed objective.

Avoid indiscriminate `pg_terminate_backend`, unbounded connection storms, automatic promotion of an unverified standby, and increasing `max_connections` without memory analysis.

## 10. Acceptance scorecard

| Category | Weight |
|---|---:|
| Connection budgeting and capacity | 20 |
| Performance and burst behavior | 20 |
| Transaction and session correctness | 20 |
| Recovery, security and failover | 20 |
| Monitoring, alerting and rollback | 20 |

**PASS requires 100/100 evidence points, all mandatory gates verified, no unresolved critical/high findings, and explicit signoff.** A skipped mandatory test is NOT ACCEPTED, not a partial PASS. Conditional HA tests must be documented as out of scope if no HA topology exists.

## 11. Deliverables

- Architecture and connection budget worksheet.
- Versioned PgBouncer/PostgreSQL configuration inventory (sanitized).
- Workload results and client request reconciliation.
- Failure-injection timeline with before/during/after metrics.
- Alert acceptance evidence and runbook links.
- Rollback proof, residual risks, owner approvals and retest date.

## 12. Hands-on lab

See [Chapter 060 lab](../labs/060-postgresql-connection-pooling-and-availability-acceptance-project-lab.md), [preflight SQL](../labs/sql/060-preflight.sql) and [idempotency fixture SQL](../labs/sql/060-fixture.sql). These are safe starting materials, not an executed acceptance result.

**Runtime status:** pending.

## References

- [PostgreSQL connection settings](https://www.postgresql.org/docs/18/runtime-config-connection.html)
- [PostgreSQL monitoring](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [PgBouncer configuration](https://www.pgbouncer.org/config.html)
- [PgBouncer usage](https://www.pgbouncer.org/usage.html)

**Next:** Chapter 061 — PostgreSQL Backup Strategy, RPO and RTO Fundamentals.
