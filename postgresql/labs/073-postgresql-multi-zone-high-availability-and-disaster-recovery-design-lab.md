# Chapter 073 — Multi-Zone High Availability and Disaster Recovery Design Lab

**PostgreSQL 18 · Simulated AZ topology · Runtime pending**

## 1. Safety and topology

Use a disposable three-node PostgreSQL 18 HA cluster, one HA manager per node, three DCS voters and a lab-only writer endpoint. Label nodes Zone A/B/C and document all **shared host/network/storage dependencies**. If all nodes run on one laptop or Docker host, this is only a **logical zone simulation**, not proof of physical zone independence. Never use production cloud networking, DNS, storage or DCS.

## 2. Inventory and baseline

Create a diagram and record node/AZ, DCS voter, WAL source/standby, replication mode, fencing/watchdog, proxy routing, independent backups, capacity and maximum tolerated loss. Run [073 SQL inspection](../labs/sql/073-multi-zone-ha-inspect.sql) on each node. Record UTC timestamp, node identity and LSNs. Capture DCS quorum using the installed HA manager and DCS tools.

## 3. Single standby-zone failure

Stop the Zone C standby using the HA manager's supported lab procedure. Confirm primary stays writable, quorum remains 2/3 and replica redundancy alert fires. Restore the node, measure catch-up time and WAL retained while disconnected.

## 4. Primary-zone failure

First verify the lab's fencing mechanism and quorum policy. Stop/isolate the Zone A primary through the HA manager's supported failure injection. Independently prove the old primary cannot accept writes. Confirm surviving voters elect one eligible standby, new leader timeline changes, proxy routes to the new leader and test transactions succeed. Record RPO/RTO and reconcile ambiguous client outcomes.

**If fencing cannot be proven, stop and mark the test NOT VERIFIED.**

## 5. Quorum loss simulation

In a separate test, stop two of three DCS voters. Confirm there is no unsafe second leader; the safe outcome may be write unavailability. Restore quorum through the documented DCS procedure and verify leader consistency before resuming writes.

## 6. Regional DR tabletop and optional isolated drill

Treat Region B as a separate DR environment. Inventory independent backup/WAL copies, credentials, certificates, networking, DNS, IaC, monitoring and access. If a real isolated Region B is available, run a restore/PITR drill on **copies only**, then validate an application test marker and achieved RPO/RTO. Never promote a DR node while Region A can still accept writes.

## 7. Recovery and cleanup

Restore all three lab nodes, rejoin former primary safely, verify streaming, slots, archive, backups, DCS quorum and writer endpoint. Complete [073 scorecard](../labs/acceptance/073-multi-zone-dr-scorecard.csv).

**Runtime:** pending. Mark physical AZ and regional resilience NOT VERIFIED when only simulated.
