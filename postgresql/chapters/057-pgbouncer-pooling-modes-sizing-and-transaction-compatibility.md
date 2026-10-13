# Chapter 057 — PgBouncer Pooling Modes, Sizing and Transaction Compatibility

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 and a recent, explicitly versioned PgBouncer · **Status:** Authored; runtime validation pending

## 1. Mission

Select the correct PgBouncer pooling mode for each application, calculate aggregate backend capacity, identify transaction-pooling incompatibilities, and prove that a proposed pool configuration meets availability and latency objectives. This chapter follows [Chapter 056 — Connection Management and PgBouncer Fundamentals](056-postgresql-connection-management-and-pgbouncer-fundamentals.md).

## 2. Pooling architecture and lifetime

```text
Application clients (many)
         |
         v
    PgBouncer clients
         |
         +--> database/user pool --> PostgreSQL backend A
         |                     \--> PostgreSQL backend B
         |
         +--> another database/user pool --> separate backend budget
```

PgBouncer multiplexes client connections onto a smaller number of PostgreSQL server connections. Pool identity depends on database/user mapping and configuration. More accepted client connections do not create more database execution capacity; saturated pools queue requests.

| Mode | Server released | Suitable for | Principal risk |
|---|---|---|---|
| Session | Client disconnect | Session-affine applications | Backend retained during client idle time |
| Transaction | Transaction completion | Short, independent transactions | Session state and backend affinity are not guaranteed |
| Statement | Statement completion | Simple autocommit statements | Multi-statement transactions are incompatible |

Transaction pooling **does not split a transaction** across servers; a transaction retains its backend until completion. A long transaction therefore monopolizes a server connection.

## 3. Session-affine features: compatibility matrix

| Feature | Transaction pooling behavior | Safe approach |
|---|---|---|
| Session-level `SET` | Value not guaranteed across transactions | `SET LOCAL` inside each explicit transaction |
| `SET ROLE` / `SET SESSION AUTHORIZATION` | Session affinity and identity risks | Authenticate with intended role; avoid session-level identity switching |
| Temporary tables | Persist on a particular backend; next transaction may use another | Prefer session pooling or redesign |
| SQL `PREPARE` / `EXECUTE` | Session-specific state | Use supported protocol prepared statements or session mode |
| Protocol prepared statements | Recent PgBouncer releases can track named statements when configured | Verify `max_prepared_statements`, driver and installed version |
| Session-level advisory locks | Lock remains on original backend | Use transaction-level `pg_advisory_xact_lock` |
| `LISTEN/NOTIFY` listener | Listener needs stable backend session | Dedicated direct/session connection |
| Session cursors / holdable cursors | Backend affinity matters | Redesign or use session mode |
| Tenant GUC `app.tenant_id` | May be absent or stale | Trusted context + `SET LOCAL` per transaction; never treat client-writable GUC as identity proof |

**Key rule:** do not enable transaction pooling for a workload until the application has passed an explicit feature-by-feature compatibility test. Server reset behavior and supported features differ by PgBouncer release.

## 4. Aggregate sizing model

For every PgBouncer instance, estimate the number of distinct database/user pools and their configured server capacity:

```text
worst_case_pooler_backends =
  sum_over_pooler_instances(
    sum_over_active_pools(default_pool_size + reserve_pool_size)
  )

cluster_peak_backends =
  worst_case_pooler_backends
  + direct_application_connections
  + maintenance_and_monitoring_connections
  + other_nonpooled_clients
```

This is a conservative planning upper bound, **not a promise that every pool reaches that size**. Include configured `max_db_connections`, `max_user_connections`, per-database overrides, replicas and failover paths. Compare against PostgreSQL `max_connections` minus superuser/reserved slots and operational headroom.

**Worked example:** 2 PgBouncer replicas × 3 active pools × (20 default + 5 reserve) = 150 potential pooled backends. Add 25 direct/operational connections = 175. If the approved PostgreSQL application budget is 180, only five connections remain as unallocated capacity; reduce the ceiling or increase validated headroom before rollout.

## 5. Queueing and saturation

`SHOW POOLS;` exposes client/server state such as `cl_active`, `cl_waiting`, `sv_active`, `sv_idle`, `sv_used` and waiting age where supported. `SHOW STATS;` provides throughput and timing counters; PgBouncer field names depend on version.

Interpret patterns:
- `cl_waiting > 0` with all server connections busy: real pool saturation, possibly long transactions or slow queries.
- Many `sv_idle` and few waiting clients: potentially oversized pool.
- Large `cl_active` but low `sv_active`: clients may be idle or between transactions.
- Growing queue wait with low PostgreSQL CPU: inspect locks, I/O, idle-in-transaction sessions and pool mapping before raising pool sizes.

Set a bounded `query_wait_timeout` based on application SLOs. Queueing is backpressure, not a substitute for capacity planning.

## 6. Production-oriented configuration

```ini
[databases]
appdb = host=db.internal port=5432 dbname=appdb pool_size=20 reserve_pool_size=5

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432
pool_mode = transaction
max_client_conn = 400
default_pool_size = 20
reserve_pool_size = 5
reserve_pool_timeout = 5
query_wait_timeout = 15
server_tls_sslmode = verify-full
```

This excerpt is **not deployable as-is**: configure authentication, both TLS hops, certificate trust, PgBouncer admin access, secret handling, logs and network exposure. Check installed PgBouncer documentation for parameter support. `pool_size` and `reserve_pool_size` can be overridden per database. `max_client_conn` is client capacity, not PostgreSQL server capacity.

## 7. Driver and ORM acceptance checklist

1. Inventory driver, ORM, migration tool and pooler versions.
2. Identify SQL-level PREPARE, named protocol prepared statements and automatic statement caching.
3. Detect temporary tables, session settings, advisory locks, `LISTEN`, cursors and multi-statement transactions.
4. Confirm transaction boundaries are explicit and short.
5. Verify reconnect, retry, timeout and failover behavior without unsafe duplicate writes.
6. Test security context isolation between consecutive tenants/requests.
7. Exercise both normal load and server-side connection failures.

## 8. Operational runbook

**Preflight:** capture direct connection baseline, PostgreSQL max/reserved slots, per-pool budgets, PgBouncer `SHOW CONFIG`, `SHOW DATABASES`, `SHOW POOLS`, `SHOW STATS` and application SLOs.

**Canary:** route a small app cohort through PgBouncer; watch queue age, error rate, p95/p99 latency, PostgreSQL backends, long transactions and authentication failures. Increase traffic gradually only if gates pass.

**Rollback:** restore the previous routing or pool mode through an approved drain/reconnect procedure. Avoid killing active transactions unnecessarily. Reverify authentication, prepared statements and application behavior after rollback.

## 9. Troubleshooting decision tree

| Symptom | Verify first | Likely remediation |
|---|---|---|
| Waiting clients rise | Long transactions, backend slots, per-pool caps | Fix query/transaction duration or tune validated capacity |
| `prepared statement does not exist` | SQL vs protocol prepare, driver and `max_prepared_statements` | Compatible driver/config or session pooling |
| Temp table missing | Cross-transaction backend reassignment | Session pool or redesign |
| Tenant identity bleed | Session GUC/role changes | Trusted per-transaction context or dedicated identities |
| Admin cannot connect | Reserved headroom and direct clients | Preserve break-glass connections |
| Failover stalls | Endpoint changes and stale server connections | Controlled reconnect/drain with retry testing |

## 10. Lab and acceptance

[Chapter 057 lab](../labs/057-pgbouncer-pooling-modes-sizing-and-transaction-compatibility-lab.md) includes a read-only PostgreSQL capacity script, PgBouncer administrative probes, controlled transaction/session-state tests, and an aggregate pool-budget worksheet.

**Acceptance:** all transaction-compatibility tests pass, aggregate backend ceiling remains below approved budget, waiting time meets SLO and rollback is demonstrated. **Runtime:** pending.

## Official references

- [PgBouncer configuration](https://www.pgbouncer.org/config.html)
- [PgBouncer usage and SHOW commands](https://www.pgbouncer.org/usage.html)
- [PostgreSQL connection settings](https://www.postgresql.org/docs/18/runtime-config-connection.html)
- [PostgreSQL SET LOCAL](https://www.postgresql.org/docs/18/sql-set.html)

**Next:** Chapter 058 — PostgreSQL Connection Pool Saturation, Timeouts and Recovery.
