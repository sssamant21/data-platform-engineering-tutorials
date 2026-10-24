# Phase 5.4 — Chapter 001 Three-Node Kafka HA Lab

**Status:** Published; runtime result pending. **Target:** GitHub-hosted disposable kind cluster.

This lab exercises a **three-node combined broker/controller** KRaft topology under Strimzi 0.47.0 / Kafka 4.0.0. It is more resilient than the Chapter 001 single-broker fixture, but **does not fulfill the chapter's six dedicated-role Pod HA acceptance requirement**. A one-node kind host also does not establish host/zone fault tolerance.

## Run

Open [Kafka Chapter 001 HA Lab](../../../.github/workflows/kafka-chapter-001-ha.yml) in GitHub Actions, select **Run workflow** on `main`, or push changes to the lab workflow, fixture or script. No laptop installation is needed.

## Acceptance checks

1. Verify the Kubernetes context is `kind-kafka-qa`.
2. Wait for Kafka and KafkaTopic Ready and verify three Kafka Pods.
3. Verify topic replication factor 3 and one partition.
4. Produce a baseline event with `acks=all`.
5. Delete one disposable broker Pod; retry an `acks=all` publish within a bounded window.
6. Verify operator recovery and replacement Pod UID.
7. Consume both events after recovery and record recovery time.
8. Upload JSON evidence and, on failure, operator logs, Pod status and events.

**Limitations:** A passing test demonstrates recovery and record retention for this scenario only. It does not establish uninterrupted availability, zero RPO for arbitrary failures, dedicated controller/broker isolation, production storage durability, or six-Pod architecture compliance. Keep Chapter 001 overall certification pending until those requirements are independently validated.
