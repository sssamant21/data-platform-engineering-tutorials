# Chapter 073 — PostgreSQL Multi-Zone High Availability and Disaster Recovery Design

**Track:** PostgreSQL DBRE/SRE | **Baseline:** PostgreSQL 18 | **Status:** Authored; runtime validation pending

## 1. Mission

Design PostgreSQL availability across independent failure domains, withstand a single availability-zone outage where the architecture permits, and distinguish **in-region HA** from **cross-region disaster recovery**. Specify RPO/RTO, quorum, fencing, replication, application routing, backup isolation, operational cost and acceptance tests. Builds on [Chapter 072 — HA Observability](072-postgresql-high-availability-observability-and-failure-recovery.md) and [Chapter 066 — DR Acceptance](066-postgresql-backup-and-disaster-recovery-acceptance-lab.md).

## 2. Reference architecture

```text
                          Region A — production
              +----------------+----------------+----------------+
              | Zone A         | Zone B         | Zone C         |
              | Primary PG     | Standby PG     | Standby PG     |
              | Patroni        | Patroni        | Patroni        |
              | DCS voter 1    | DCS voter 2    | DCS voter 3    |
              +----------------+----------------+----------------+
                       |                 |                 |
                       +------- regional writer endpoint -+
                                        |
                          applications / connection pool

               WAL archive + verified backups in independent storage
                                        |
                            Region B — DR isolation
                           restore target / optional DR replica
                           separate access + tested cutover
```

This is a **logical design**, not an assertion that putting a DCS voter in each zone guarantees safety. The HA manager must enforce lease loss, old-primary demotion/fencing, safe leader election and route updates. Region B needs its own independently recoverable control plane; a single stretched DCS across distant regions may create latency, availability and quorum hazards.

## 3. Failure-domain analysis

| Failure | Expected local HA behavior | DR implications |
|---|---|---|
| Primary node crash | Eligible standby promoted after fencing | Usually no regional DR |
| Primary AZ unavailable | Surviving zones keep DCS majority and promote eligible standby | Check actual RPO and capacity |
| Standby AZ unavailable | Primary remains writable; redundancy reduced | Restore standby promptly |
| One DCS voter lost | 2/3 quorum remains | Observe and replace voter |
| Two DCS voters lost | Quorum lost; fail closed | Restore quorum through documented DCS recovery |
| Regional network or storage failure | Local HA may be unavailable | Invoke cross-region DR decision |
| Corruption / accidental DELETE | Replication can propagate damage | Use independent PITR or immutable backup |
| Credentials/control-plane outage | May block HA and DR tooling | Independent break-glass access required |

**Zone labels alone are not sufficient:** confirm physical isolation of power, network, storage, load balancer, DCS and backup paths. A shared dependency can invalidate assumed fault tolerance.

## 4. Replication policy

### In-region synchronous replication

A synchronous standby in another AZ can reduce acknowledged-transaction loss on primary failure, but introduces cross-zone commit latency and can block writes when no required acknowledgment is available. Test `synchronous_commit=on`, `remote_apply` and `synchronous_standby_names` policies from [Chapter 069](069-postgresql-synchronous-replication-and-commit-durability.md). If strict synchronous mode is enabled, write unavailability under standby loss may be the intended safety outcome.

### Cross-region asynchronous replication

Often preferred for long-distance links due to latency and availability constraints. Recent acknowledged writes may not yet exist in Region B when Region A fails. Measure WAL generation, replication delay and the actual last durable/replayed LSN before asserting RPO. A cross-region replica is **not** a replacement for archived WAL and tested backups.

### Slots and WAL retention

Size `max_slot_wal_keep_size`, archive capacity, network throughput and standby disk for outages and bursts. An inactive cross-region slot can fill primary `pg_wal`; a bounded slot can become `lost` and require reseeding. Apply [Chapter 068](068-postgresql-replication-slots-wal-retention-and-lag-management.md) capacity modeling.

## 5. Quorum and fencing design

For a three-voter DCS distributed one per AZ, loss of one AZ leaves two voters; losing two AZs removes majority. A surviving isolated primary **must not continue writes** without valid leadership authority. Validate HA manager lease handling and watchdog/fencing under partitions. Never promote a regional DR target while the original region might still accept writes unless fencing and authoritative cutover are proven.

## 6. Application and infrastructure dependencies

- Writer endpoint and connection pools must follow the elected leader and drain stale sessions.
- DNS TTL is not a guarantee that clients immediately stop using old connections.
- Maintain zone-independent capacity for the surviving primary and replicas, including storage IOPS, CPU, memory and WAL throughput.
- Review cross-zone and cross-region egress charges, synchronous latency, storage duplication and recovery infrastructure cost.
- DR needs independent secrets, certificates, IAM, DNS, network routes, deployment artifacts, observability and operator access.
- Use unique transaction IDs to reconcile ambiguous COMMIT outcomes after a cutover.

## 7. Backup and regional DR strategy

Define a backup policy independent of replication: periodic verified base backups, continuous WAL archive, retention chain, immutable/offsite copies, key recovery, regular isolated PITR and regional restore tests. Protect against correlated operator error and credential compromise. Record region-specific backup freshness and time to restore.

## 8. DR activation decision tree

1. Confirm incident scope: node, zone, region, network partition or corruption.
2. Verify original writer status and whether it can be **fenced**.
3. Check DCS quorum, healthy standby candidates, replay/flush LSNs and expected RPO.
4. Prefer safe in-region HA for single-zone incidents.
5. For regional loss, invoke approved DR incident command and validate Region B readiness.
6. Promote/recover Region B only after authoritative cutover and fencing conditions are met.
7. Switch writer routing, verify transaction correctness and application SLOs.
8. Restore backups, archive continuity and replication redundancy; plan controlled failback rather than automatic reverse promotion.

**STOP** if two writable regions are possible, backup chain is uncertain, or RPO/RTO assumptions cannot be substantiated.

## 9. Observability and alerting

Track leader identity per zone, DCS quorum, fencing, replica eligibility, replay/flush LSN, slot WAL retention, cross-zone latency, cross-region WAL lag, archive success, backup age, zone capacity, writer routing, synthetic transaction results and DR access readiness. Alert on missing independent failure-domain capacity and on **time to WAL/disk exhaustion**, not just raw lag.

## 10. Hands-on design and failure simulation

Use [Chapter 073 lab](../labs/073-postgresql-multi-zone-high-availability-and-disaster-recovery-design-lab.md), [read-only SQL](../labs/sql/073-multi-zone-ha-inspect.sql) and [failure-domain scorecard](../labs/acceptance/073-multi-zone-dr-scorecard.csv). Lab zones are **simulated** unless infrastructure separation is independently verified; a local Docker test cannot prove physical AZ independence.

### Acceptance gates

- Failure domains and shared dependencies inventoried.
- Loss of one simulated AZ retains quorum, when architecture claims it should.
- Old primary fenced before any new writer accepts traffic.
- Exactly one writable primary across all tested failure scenarios.
- In-region HA RPO/RTO measured; cross-region DR RPO/RTO measured separately.
- Regional backup/PITR and credentials independently recoverable.
- Application routing, commit reconciliation and capacity validated.
- Failback/rejoin documented with timeline and fencing checks.

**Runtime validation pending.** Unexecuted regional DR or fencing tests are **NOT VERIFIED**, not PASS.

## References

- https://www.postgresql.org/docs/18/warm-standby.html
- https://www.postgresql.org/docs/18/warm-standby-failover.html
- https://www.postgresql.org/docs/18/continuous-archiving.html
- https://patroni.readthedocs.io/
- https://etcd.io/docs/

**Next:** Chapter 074 — PostgreSQL Cross-Region Replication, DR Cutover and Failback.
