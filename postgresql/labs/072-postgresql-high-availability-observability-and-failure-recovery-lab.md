# Chapter 072 — HA Observability and Failure Recovery Lab

**PostgreSQL 18 · Disposable HA topology · Runtime pending**

## 1. Environment and safety

Use an isolated PostgreSQL 18 HA cluster with a supported orchestrator, quorum-backed DCS, tested fencing and a lab-only proxy/application endpoint. Ensure all nodes and DCS voters are disposable. Do not stop production instances, remove production DCS voters, partition production networks or change live routing.

## 2. Baseline telemetry

On every PostgreSQL node run:

```bash
psql -X -v ON_ERROR_STOP=1 -U postgres -d postgres -f postgresql/labs/sql/072-ha-observability-inspect.sql
```

Label outputs with node, UTC time and role. Capture Patroni leader state, DCS quorum/member health, fencing status, proxy writer backend, application probe, backup freshness, WAL archive status and active alerts.

## 3. Synthetic application transaction

Create a disposable test table on the elected leader and issue unique, idempotent test writes through the **lab-only** writer endpoint. Measure success rate, latency and read-after-write verification. Never use a production application table.

## 4. Replica degradation

In the lab, stop one standby using the orchestrator-supported procedure. Observe sender/receiver state, WAL LSN lag, slot retained WAL, application behavior and alert routing. Restore standby, confirm replay catch-up and record time to recovery.

## 5. Control-plane degradation

Stop one of three etcd voters. Confirm quorum remains and no unexpected leader change occurs. Restore the voter. In a separate fencing-verified lab, simulate quorum loss and confirm the safe outcome is no competing writable leader. If fencing cannot be independently demonstrated, mark the partition/quorum test NOT VERIFIED.

## 6. Application routing fault

Configure a lab-only proxy backend mismatch or block access to the elected leader. Confirm the synthetic application probe fails, the alert fires and routing can be safely restored. Verify stale connections are drained.

## 7. Primary failure and service recovery

Use the HA manager's supported failure injection, not an ad-hoc pg_promote. Collect the incident timeline: detection, fencing, leader election, promotion, routing, application recovery and redundancy restoration. Verify exactly one writable primary, reconcile ambiguous commit IDs and restore the former primary as a standby.

## 8. Backup continuity and closure

After failover, verify backup jobs, archive command health, replication slots, timeline changes and the latest restorable point. Complete [072 scorecard](../labs/acceptance/072-ha-observability-scorecard.csv), attach logs and alert evidence, and leave the lab at its baseline.

**Runtime:** pending. A failed application probe or missing fencing evidence means no acceptance PASS.
