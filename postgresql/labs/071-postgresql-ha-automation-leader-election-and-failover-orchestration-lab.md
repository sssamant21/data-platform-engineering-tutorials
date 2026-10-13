# Chapter 071 — HA Automation, Leader Election and Failover Orchestration Lab

**PostgreSQL 18 · Patroni-style isolated lab · Runtime pending**

## 1. Topology and isolation

Provision three disposable PostgreSQL 18 nodes managed by one compatible Patroni version, three etcd voting members across separate failure domains, and a lab-only HAProxy writer endpoint. Provide independent watchdog/fencing and a backup/PITR baseline. Use a dedicated lab network; do not attach production storage, DCS or DNS. Review installed Patroni/etcd documentation for exact CLI/config syntax.

## 2. Preflight

Record cluster ID, PostgreSQL system ID, Patroni version, etcd member health/quorum, leader identity, TTL/loop_wait/retry_timeout, synchronous mode, failover lag policy, fencing/watchdog configuration, backup/WAL archive state and proxy backend mapping.

Run on every PostgreSQL node, labeling outputs:

```bash
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f postgresql/labs/sql/071-ha-automation-inspect.sql
```

Collect DCS status using the installed etcdctl with configured TLS/auth and Patroni status using the installed patronictl or authenticated REST API. Do not publish credentials.

## 3. Application probe

Create a lab-only database/table on the current writer and generate unique transaction IDs via the **proxy writer endpoint**. Verify writes succeed only on the elected primary and replicas are read-only. Record baseline latency, commit outcome and writer identity.

## 4. Controlled leader crash

Use the HA manager's supported lab-only failure injection to stop the leader process/host. Capture leader lease expiry, fencing proof, new leader election, promotion, timeline, endpoint update and client recovery. Do not manually call pg_promote while old primary can accept writes.

## 5. DCS quorum test

Stop **one** etcd voter; confirm two voters retain quorum and the leader remains stable. Restore it. In a separately isolated test, simulate quorum loss and verify no second writable primary appears. **If the fencing/watchdog guarantee is not independently validated, mark the partition test NOT VERIFIED and do not assert split-brain safety.**

## 6. Network partition test

Only with a verified lab fencing mechanism, isolate the old leader from the DCS while leaving a separate observer able to test write acceptance. Prove the old leader stops accepting writes before a new leader starts. Verify there is never more than one writable node. Stop immediately if dual writes are observed.

## 7. Stale routing and transaction outcome

Force a lab-only proxy backend transition. Verify stale client connections fail closed and reconnect to the elected leader. For a client timeout during COMMIT, query transaction ID on the authoritative leader before retrying; document idempotent reconciliation.

## 8. Former leader rejoin

Keep old leader fenced until it is safely rewound or rebuilt as a replica under the HA manager. Verify PostgreSQL system ID/timeline compatibility, replication, slots, WAL archive and backup continuity.

## 9. Acceptance

Complete [071 HA automation scorecard](../labs/acceptance/071-ha-automation-scorecard.csv). Record timestamps, DCS/quorum evidence, fencing logs, primary/replica state, proxy routing, RPO/RTO, client outcomes and rollback evidence.

**Runtime:** pending. Never mark an unexecuted quorum/fencing test PASS.
