# Chapter 071 — PostgreSQL HA Automation, Leader Election and Failover Orchestration

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Design and operate automated PostgreSQL HA using a tested orchestrator, quorum-backed leader selection, leader leases, fencing, routing and controlled rejoin. Validate failover behavior under node, network and coordination failures without split-brain. Builds on [Chapter 070](070-postgresql-planned-switchover-failover-and-split-brain-prevention.md).

## 2. Reference architecture

```text
                         Application / connection pool
                                     |
                         Writer routing / HAProxy
                                     |
                         Patroni REST leader check
                                     |
           +-------------------------+-------------------------+
           |                         |                         |
      PostgreSQL A              PostgreSQL B              PostgreSQL C
      Patroni agent             Patroni agent             Patroni agent
           |                         |                         |
           +-------------------------+-------------------------+
                                     |
                       DCS: etcd quorum (3 or 5 members)
                                     |
                        Monitoring + backup/PITR + fencing
```

**Patroni is an illustrative orchestrator, not built into PostgreSQL.** Its DCS (etcd/Consul/Kubernetes, as supported by the installed Patroni version) coordinates leadership. A DCS majority is needed to safely maintain or acquire leadership. Deploy DCS voters across failure domains; two voters do not tolerate one voter failure. Avoid co-locating all voters on the same host or AZ. HAProxy or another proxy can use an authenticated/restricted leader health endpoint; routing alone is not fencing.

## 3. Core concepts

| Concept | Meaning | Failure risk |
|---|---|---|
| Leader lease / lock | Time-bounded authority to serve as primary | Expiry/renewal failure |
| DCS quorum | Majority agrees on coordination state | Minority partition cannot elect safely |
| Patroni loop | Periodic health/leadership evaluation | Delayed response or stalled process |
| TTL, loop_wait, retry_timeout | Lease, polling and retry behavior | Poor tuning increases failover time or unsafe assumptions |
| Watchdog / STONITH | Independent enforcement of demotion or isolation | Old primary may remain writable if enforcement fails |
| Leader endpoint | Routes writes to confirmed leader | Stale proxy connections |
| Replica eligibility | Candidate replay position and health | Data loss or bad promotion |
| Reinitialization | Rewind/rebuild old leader as replica | Timeline divergence |

Do not treat DCS quorum as proof that an isolated former leader has already stopped writing. Validate actual watchdog/fencing guarantees, lease enforcement and fail-closed routing. In a DCS partition, the safe outcome may be **temporary write unavailability**, not promotion.

## 4. Control plane and data plane

Patroni agents coordinate leader state via DCS and manage PostgreSQL start, stop, promotion and follow behavior. PostgreSQL streams WAL to replicas. A proxy queries leader state and routes writes only to the elected primary. The application must handle connection failures and ambiguous COMMIT outcomes with idempotency keys and reconciliation.

**Do not run two independent failover controllers against the same cluster.** Disable conflicting cloud, operator, script or manual promotion mechanisms unless explicitly coordinated.

## 5. HA policy and safety configuration

Define RPO, RTO, failover eligibility, maximum lag, synchronous mode, DCS availability, fencing mechanism, failover cooldown and operational approvals before deploying automation. Patroni supports options such as `maximum_lag_on_failover`, `synchronous_mode`, `synchronous_mode_strict` and `watchdog`; exact settings and safety depend on installed Patroni version. Do not blindly copy a sample configuration to production.

A strict synchronous policy can block writes when no eligible synchronous replica exists. A non-strict policy may favor availability with data-loss exposure. Document this tradeoff with application owners.

## 6. Health checks and routing

A proxy should use the HA manager's leader/readiness endpoint and reject a node that is not the current writable leader. Validate on **every** cutover: DCS leader identity, Patroni role, `pg_is_in_recovery()`, proxy backend selection, stale connections, write success and transaction reconciliation. Health endpoints must not expose administrative operations publicly.

Example read-only PostgreSQL verification:

```sql
SELECT pg_is_in_recovery() AS is_standby, clock_timestamp() AS checked_at;
SELECT application_name,state,sync_state,flush_lsn,replay_lsn
FROM pg_stat_replication;
```

Use [071 HA inspection SQL](../labs/sql/071-ha-automation-inspect.sql) to collect PostgreSQL state. DCS and orchestrator status must also be collected from their **version-specific** CLIs/APIs.

## 7. Failover state machine

```text
Healthy leader
    |
    v
Failure detected -> confirm leader lease / quorum / failure scope
    |
    +-- no safe authority or fencing -> FAIL CLOSED; page operator
    |
    +-- old leader fenced and candidate eligible
                    |
                    v
             acquire leader lock
                    |
                    v
              promote candidate
                    |
                    v
          update writer routing + verify
                    |
                    v
          reconcile commits + restore replicas
```

Never promote solely because one monitoring agent cannot reach the leader. The old leader may be healthy in another partition. If fencing is uncertain, halt promotion.

## 8. Failure-injection matrix

| Test | Expected safe outcome |
|---|---|
| Primary PostgreSQL process crash | Eligible replica promoted if leader loss and fencing are proven |
| Primary host loss | Single new leader, bounded RTO and documented RPO |
| DCS single voter loss | Majority remains, stable leadership |
| DCS quorum loss | Fail closed; no competing leader |
| Primary-to-DCS partition | Old leader demotes/fences when lease cannot be renewed |
| Replica network partition | Replica excluded until caught up |
| Proxy stale connection | Old writer disconnected; clients reconnect to leader |
| Former primary returns | Rewind/rebuild as replica, never independent writer |
| All replicas lag beyond policy | No unsafe automatic promotion; alert |

Simulate only in a disposable environment with independent fencing. A test that does not exercise a partition cannot validate split-brain prevention.

## 9. Observability and runbook

Monitor leader changes, DCS health/quorum, lease renewal failures, watchdog/fencing outcomes, promotion duration, eligible replicas, WAL receive/replay lag, replication slots, synchronous commit waits, proxy backend status, client reconnect/error rate, backup/archive health, and achieved RPO/RTO.

**Incident response:** freeze manual promotion; identify authoritative leader; verify fencing and quorum; capture timelines/LSNs; verify routing; reconcile ambiguous writes; rejoin former primary safely; restore HA redundancy and backups; document timeline and corrective actions.

## 10. Acceptance gates

- Exactly one writable primary throughout every tested scenario.
- Quorum and lease state observable and consistent with leader identity.
- Fencing verified independently; partition test cannot create two writers.
- Only eligible replica promoted within signed data-loss policy.
- Application writer endpoint follows elected leader; stale sessions handled.
- Client transaction reconciliation and idempotency demonstrated.
- Failover RPO/RTO measured; former primary safely rejoined.
- DCS and backup/WAL archive availability restored after drill.

Use the [Chapter 071 lab](../labs/071-postgresql-ha-automation-leader-election-and-failover-orchestration-lab.md), [inspection SQL](../labs/sql/071-ha-automation-inspect.sql) and [HA acceptance scorecard](../labs/acceptance/071-ha-automation-scorecard.csv). **An untested fencing or quorum gate is NOT VERIFIED, not PASS.** Runtime validation pending.

## References

- https://www.postgresql.org/docs/18/warm-standby-failover.html
- https://www.postgresql.org/docs/18/app-pgrewind.html
- https://patroni.readthedocs.io/
- https://etcd.io/docs/

**Next:** Chapter 072 — PostgreSQL High Availability Observability and Failure Recovery.
