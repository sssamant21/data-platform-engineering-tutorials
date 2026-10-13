# Chapter 056 — PostgreSQL Connection Management and PgBouncer Fundamentals

**Track:** PostgreSQL DBRE/SRE · **Baseline:** PostgreSQL 18 · **Status:** Authored; runtime validation pending

## 1. Mission

Understand PostgreSQL backend connection cost, design safe connection budgets and introduce PgBouncer as a lightweight connection pooler. Diagnose pool exhaustion without blindly increasing `max_connections`. This chapter follows [Chapter 055 — Security Acceptance](055-postgresql-security-hardening-and-access-control-acceptance-lab.md).

## 2. PostgreSQL connection lifecycle

```text
Application / API clients
        |
        +-- direct connection --> PostgreSQL backend per connection
        |
        +-- PgBouncer listener -> client connections
                                  |
                              server pool -> fewer PostgreSQL backends
```

PostgreSQL normally uses a separate backend process for each client connection. Idle sessions still consume process slots and resources; active queries also compete for CPU, memory, locks and I/O. `max_connections` is a ceiling, **not** a throughput target. Raising it can worsen contention and increase memory exposure.

## 3. Capacity planning

Start with a connection budget:

```text
usable_connections =
    max_connections
  - superuser_reserved_connections
  - reserved_connections
  - operational_headroom
```

`reserved_connections` (PostgreSQL 16+) reserves slots for roles with `pg_use_reserved_connections`; `superuser_reserved_connections` reserves final superuser slots. Treat this arithmetic as an **operational planning approximation** and verify actual access rules, pooler behavior and admin headroom.

Example: 300 total, 3 superuser-reserved, 5 reserved, 32 operational headroom -> **260 application slots**. For 20 pods with 25 connections each, the theoretical 500 client sessions exceed that budget. Pooling can limit backend concurrency while accepting more client sessions, but queue latency must be monitored.

## 4. PgBouncer pooling modes

| Mode | Server connection returned | Benefits | Compatibility risk |
|---|---|---|---|
| Session | After client disconnect | Most session features work | Less effective reuse for long-lived clients |
| Transaction | After transaction ends | High reuse for short transactions | Session state cannot be assumed |
| Statement | After statement completes | Aggressive pooling | Not suitable for multi-statement transactions |

**Transaction pooling is not transparent for every workload.** Watch session-level `SET`, temporary tables, advisory locks, `LISTEN/NOTIFY`, cursors, SQL-level `PREPARE`, and application assumptions about backend affinity. PgBouncer versions differ in protocol-level prepared-statement support: recent versions can track named protocol prepared statements with `max_prepared_statements`; verify your installed release and driver behavior rather than making blanket compatibility claims.

## 5. Core configuration example

```ini
[databases]
appdb = host=postgres port=5432 dbname=appdb

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
default_pool_size = 20
reserve_pool_size = 5
reserve_pool_timeout = 5
max_client_conn = 500
server_tls_sslmode = verify-full
```

This is **illustrative, not a complete production configuration**. Supply valid TLS CA/hostname settings, client-side TLS policy, authentication material, administrative users, logging and appropriate listener/firewall restrictions. Do not expose an unauthenticated PgBouncer listener on `0.0.0.0`. Configure `client_tls_sslmode` and certificates where clients connect over untrusted networks. SCRAM authentication across pooler-to-server paths must be tested; do not assume a stored SCRAM verifier can be reused to authenticate upstream under all configurations.

## 6. Key tuning controls

- `default_pool_size`: default server connections per PgBouncer pool (commonly per database/user combination).
- `min_pool_size`: prewarm server connections under documented conditions.
- `reserve_pool_size` and `reserve_pool_timeout`: controlled burst capacity.
- `max_client_conn`: accepted client sessions, **not** PostgreSQL server backend cap.
- `max_db_connections` / `max_user_connections`: optional aggregate limits.
- `query_wait_timeout`: bound how long clients may wait for a server connection.
- `server_idle_timeout` and `server_lifetime`: lifecycle controls; tune with backend churn in mind.

**Capacity trap:** multiplying `default_pool_size` by the number of PgBouncer instances, database/user pools and application replicas can still exhaust PostgreSQL. Calculate the *aggregate* backend ceiling, not just a single pooler's setting.

## 7. Operational metrics

```sql
-- Run against PostgreSQL
SELECT state,count(*) FROM pg_stat_activity GROUP BY state ORDER BY state;
SELECT application_name,usename,datname,state,count(*)
FROM pg_stat_activity GROUP BY 1,2,3,4 ORDER BY 5 DESC;
SELECT current_setting('max_connections') AS max_connections,
 current_setting('superuser_reserved_connections') AS superuser_reserved,
 current_setting('reserved_connections') AS reserved;
```

Connect to PgBouncer's administrative database and run `SHOW POOLS;`, `SHOW STATS;`, `SHOW CLIENTS;`, `SHOW SERVERS;`, and `SHOW DATABASES;`. Track `cl_active`, `cl_waiting`, `sv_active`, `sv_idle`, queue age, average transaction/query time, login errors and disconnects. Column names vary across PgBouncer releases; record your version.

## 8. Failure scenarios

| Symptom | Likely cause | First response |
|---|---|---|
| `too many clients already` | PostgreSQL backend ceiling | Inspect aggregate pools, direct clients, reserved headroom |
| PgBouncer `cl_waiting` grows | Pool saturation or slow transactions | Check server state, locks, long transactions and workload |
| Transaction pool breaks application | Session-affine features | Switch affected workload to session pooling or redesign |
| Authentication failures | SCRAM, auth_file, auth_query or TLS mismatch | Trace both client->pooler and pooler->server |
| High churn | Aggressive connection recycling | Check server lifetime, driver and pod restarts |
| Slow requests despite low backend count | Pool wait time | Compare pool queue latency with PostgreSQL execution |
| Failover causes stale routing | Pooler backend endpoint not updated | Verify DNS/reconnect/PAUSE/RECONNECT workflow |

## 9. Production runbook

1. Baseline peak clients, active queries, connection churn, transaction duration, backend memory and failure rate.
2. Inventory app pools, worker counts, PgBouncer replicas and all direct-to-DB clients.
3. Select pooling mode per application feature requirements; test prepared statements and session state.
4. Configure TLS verification and secret rotation for both connection hops.
5. Stage pool sizes using aggregate server capacity; preserve admin and replication headroom.
6. Roll out gradually; monitor queue time, error rate, PostgreSQL backend count and application latency.
7. Roll back application routing to the known-good endpoint or prior PgBouncer configuration if SLOs regress; preserve credentials and failover behavior.

## 10. Lab and acceptance

The [Chapter 056 lab](../labs/056-postgresql-connection-management-and-pgbouncer-fundamentals-lab.md) provides PostgreSQL diagnostics, PgBouncer administrative queries, a connection-budget worksheet and controlled load/compatibility tests. It intentionally does not deploy an unreviewed PgBouncer configuration to production.

**Acceptance:** total server connections stay within budget, queueing is bounded, authentication/TLS work end-to-end and application session semantics are verified. **Runtime:** pending.

## Official references

- [PostgreSQL connections and authentication settings](https://www.postgresql.org/docs/18/runtime-config-connection.html)
- [Monitoring pg_stat_activity](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [PgBouncer configuration](https://www.pgbouncer.org/config.html)
- [PgBouncer usage](https://www.pgbouncer.org/usage.html)

**Next:** Chapter 057 — PgBouncer Pooling Modes, Sizing and Transaction Compatibility.
