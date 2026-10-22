# Chapter 104 — Azure Event Hubs Kafka Compatibility, Limits and Client Migration

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 21 — Microsoft Azure Kafka Engineering & SRE (4/10)  
**Primary execution platform:** Azure AKS/Kubernetes clients  
**Source:** Apache Kafka on AKS + Strimzi KRaft · **Candidate target:** Azure Event Hubs Kafka-compatible endpoint  
**Prerequisites:** Chapters 001–070 and 101–103; Kafka clients, partitions, authentication, Azure networking  
**Publication:** Published · **Live execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** Event Hubs is a managed event streaming service with a Kafka-compatible endpoint, **not** an interchangeable Kafka broker. Never promise support for Kafka Admin APIs, log compaction, transactions, exactly-once semantics, Connect or Streams internals without testing the exact client/API/tier combination. All cloud mutations require an isolated paid lab, change approval and cost cap. Never expose SAS keys, tokens or connection strings.

## 1. Mission and outcomes

Decide whether an existing Kafka workload can safely move from Strimzi-managed Kafka on AKS to Azure Event Hubs' Kafka endpoint. Build a feature and operational compatibility matrix, quantify quota/cost differences, test AKS client connectivity, preserve event correctness, and design reversible migration and cutover.

**Deliverables:** source inventory, target capability assessment, client configuration, negative/positive tests, event-ID reconciliation, rollback criteria, monitoring and independent acceptance.

## 2. Architecture: same client protocol does not mean same service

```text
                  Azure AKS application
                    producer / consumer
                           |
                Kafka client protocol
                           |
         +-----------------+-----------------+
         |                                   |
 Source: Strimzi Kafka on AKS        Target: Azure Event Hubs
 KRaft brokers / KafkaUser           Kafka-compatible endpoint
 Kafka ACL / broker Admin API         namespace / event hub entity
 Kafka partitions / retention         Azure resource management
 Kafka Connect / Streams              Azure RBAC/SAS + service quotas
         |                                   |
 Kafka-native telemetry               Azure Monitor metrics
         +---------------+-------------------+
                         |
           event-ID/hash reconciliation
                         |
             cutover and rollback gate
```

**Control-plane split:** In Kafka, broker APIs and topic administration are Kafka-native. In Event Hubs, namespace/event hub provisioning, scaling, access policy and lifecycle use supported Azure management interfaces. Kafka wire-protocol compatibility does not grant Kafka broker administration capability.

## 3. Workload classification

| Workload | Initial assessment | Required verification |
|---|---|---|
| Basic produce/consume with supported Kafka client | Candidate | Supported protocol/version, headers, keys, acks, auth |
| Consumer groups and offsets | Candidate | Rebalance behavior, checkpoints, retention, restart |
| Kafka topic administration | Conditional | Provision Event Hubs via supported Azure management |
| Compacted topics / KTable changelog | High risk | Do not assume compaction semantics |
| Kafka transactions / exactly-once | High risk | Verify API support; redesign if unavailable |
| Kafka Streams with state stores | High risk | Repartition/changelog/transaction compatibility |
| Kafka Connect worker | Conditional/high risk | Connector, worker internal topics, Admin API compatibility |
| Broker configuration and ACL tooling | Not portable as-is | Azure management/RBAC/SAS equivalent |
| Cluster replication / ISR controls | Not portable | Azure-managed service durability and DR |
| Long retention and replay | Tier-dependent | Actual retention limits, storage/cost and RPO |

**Rule:** Unknown means **not migration-approved**, not presumed compatible.

## 4. Source inventory and feature matrix

For every source topic capture: owner, event schema, partition count, keys, retention, cleanup.policy, compression, max record size, ordering, consumer groups, lag, peak ingress/egress, schema registry, Connect/Streams dependencies, IAM/ACL principal and RPO/RTO.

Read-only Strimzi/AKS inventory:

```bash
kubectl config current-context
kubectl -n kafka get kafka -o name
kubectl -n kafka get kafkatopic -o wide
kubectl -n kafka get kafkauser -o name
kubectl -n kafka-apps get pods -o wide
```

For detailed topic configuration, use a **preapproved Kafka client Pod** with `kafka-configs.sh --describe` and a mounted client authentication config; do not print credentials or use a superuser.

## 5. Azure Event Hubs target discovery

Read-only commands (requires Azure CLI and permitted account):

```bash
az account show --query '{subscription:id,tenant:tenantId}' -o json
az eventhubs namespace list -g RESOURCE_GROUP -o table
az eventhubs namespace show -g RESOURCE_GROUP -n NAMESPACE -o json
az eventhubs eventhub list -g RESOURCE_GROUP --namespace-name NAMESPACE -o table
az eventhubs eventhub show -g RESOURCE_GROUP --namespace-name NAMESPACE -n EVENT_HUB -o json
```

Capture SKU/tier, namespace capacity, entity partitions, retention, availability zone/DR settings, networking, authorization and region. Check CLI command support and API version; some properties depend on SKU.

## 6. AKS networking and endpoint validation

Kafka clients typically use `NAMESPACE.servicebus.windows.net:9093` for Event Hubs Kafka. Prefer approved private networking where supported. From an authorized AKS debug Pod:

```bash
kubectl -n kafka-apps exec DEBUG_POD -- getent hosts NAMESPACE.servicebus.windows.net
kubectl -n kafka-apps exec DEBUG_POD -- openssl s_client -connect NAMESPACE.servicebus.windows.net:9093 -servername NAMESPACE.servicebus.windows.net -verify_return_error
```

Check Private Link eligibility, private DNS zone links, AKS Pod routing, NSG/firewall, VNet and TLS hostname validation. A successful TLS handshake is **not** proof of Kafka SASL authorization or publish rights.

## 7. SASL authentication and credential boundaries

Event Hubs commonly supports Kafka client `SASL_SSL` with `PLAIN` and SAS connection-string authentication. Azure Entra/OAuth options are client and service-version dependent; consult Microsoft documentation before implementation.

```properties
bootstrap.servers=NAMESPACE.servicebus.windows.net:9093
security.protocol=SASL_SSL
sasl.mechanism=PLAIN
# Inject JAAS username/password from an approved secret provider.
# Do not commit or echo the Event Hubs connection string.
```

Strimzi `KafkaUser` and Kafka ACLs do not configure Event Hubs authorization. Use least-privilege Event Hubs access policy or Azure data-plane role as supported, separate producers and consumers, and rotate credentials through Key Vault/AKS Workload Identity integration where appropriate.

## 8. Kafka API and semantic differences

- **Topic lifecycle:** Map source Kafka topics to Event Hubs entities; do not rely on Kafka auto-topic creation or full AdminClient API parity.
- **Partitions:** Match required key ordering and consumer parallelism; partition-count changes may affect key-to-partition mapping.
- **Retention:** Event Hubs retention limits and replay behavior depend on tier; no assumed Kafka `retention.bytes` parity.
- **Compaction:** Do not treat Event Hubs as a replacement for compacted Kafka state/changelog topics.
- **Transactions and idempotence:** Check exact broker API support; if unavailable, design at-least-once with idempotent consumers and a transactional outbox.
- **Connect/Streams:** Audit Kafka internal topics, Admin APIs, transactional producers and stateful processing requirements; use an alternative service or retain Kafka if unsupported.
- **Schema:** Validate headers, timestamps, serialization, schema IDs and consumer compatibility.
- **Offsets:** Consumer offsets in different systems are **not** automatically portable. Define replay boundaries by timestamp/event ID and deduplicate.

## 9. Capacity, quotas and FinOps

Build a peak model using incoming/outgoing bytes, event count, size distribution, partitions, connections, consumer fanout, request rate and replay. Compare Event Hubs tier capacity and quotas to source Kafka broker CPU/network/disk and storage retention. Include Azure Monitor/log ingestion, private networking, cross-region DR and dual-write migration overlap in cost.

A capacity plan must account for throttling, retries/backoff with jitter and backpressure; adding Kafka partitions is not a universal remedy for namespace throughput limits.

## 10. Safe migration strategy

**Phase A — inventory:** classify every topic/application and identify unsupported API dependencies.

**Phase B — isolated target:** provision approved nonproduction Event Hubs resources through Azure management/IaC; configure private networking and secrets.

**Phase C — synthetic dual write:** emit deterministic event IDs and payload hashes to source and target with separate producer acknowledgment logs. Never assume dual-write is atomic.

**Phase D — shadow consume:** consume from both systems, compare IDs, ordering within key, duplicates, missing events, lag, error rates and latency.

**Phase E — cutover:** gate on compatibility, retention/replay budget, RPO/RTO, cost, owner approval and successful synthetic validation. Shift consumers/producers with an explicit rollback window.

**Phase F — decommission:** only after source retention/rollback requirements and independent signoff are satisfied.

**Rollback caution:** If writes have occurred only on the target after cutover, returning to source requires a tested reverse-replay or reconciliation plan; a simple bootstrap-server revert may lose events.

## 11. Twenty Kubernetes-first labs

### Lab 01 — Discover source Kafka contracts

**Goal and procedure:** Inventory topics, partitions, replication, retention, compaction, producer idempotence, transactions, ACLs, Connect, Streams and client versions. Use an approved isolated AKS namespace and Azure nonproduction subscription. For active tests, use version-pinned Kafka clients, redacted secret injection and bounded synthetic events. Do not provision or mutate paid Azure resources without explicit approval.

**Expected evidence:** record source Kafka and target Event Hubs versions/tier, client library, UTC time, resource scope, input event IDs, expected/observed results, negative cases, cost, cleanup, rollback, owner and reviewer. **Execution:** Pending until run; migration simulations may be Tabletop.

### Lab 02 — Discover Event Hubs target

**Goal and procedure:** Inventory namespace tier, hubs, partitions, retention, throughput/capacity units, networking and supported Kafka protocol. Use an approved isolated AKS namespace and Azure nonproduction subscription. For active tests, use version-pinned Kafka clients, redacted secret injection and bounded synthetic events. Do not provision or mutate paid Azure resources without explicit approval.

**Expected evidence:** record source Kafka and target Event Hubs versions/tier, client library, UTC time, resource scope, input event IDs, expected/observed results, negative cases, cost, cleanup, rollback, owner and reviewer. **Execution:** Pending until run; migration simulations may be Tabletop.

### Lab 03 — Create compatibility matrix

**Goal and procedure:** Classify each source API and application behavior as supported, conditional, unsupported or unknown with Microsoft doc evidence. Use an approved isolated AKS namespace and Azure nonproduction subscription. For active tests, use version-pinned Kafka clients, redacted secret injection and bounded synthetic events. Do not provision or mutate paid Azure resources without explicit approval.

**Expected evidence:** record source Kafka and target Event Hubs versions/tier, client library, UTC time, resource scope, input event IDs, expected/observed results, negative cases, cost, cleanup, rollback, owner and reviewer. **Execution:** Pending until run; migration simulations may be Tabletop.

### Lab 04 — Model Event Hub entity mapping

**Goal and procedure:** Map Kafka topic to Event Hub entity, consumer group naming and provisioning ownership. Use an approved isolated AKS namespace and Azure nonproduction subscription. For active tests, use version-pinned Kafka clients, redacted secret injection and bounded synthetic events. Do not provision or mutate paid Azure resources without explicit approval.

**Expected evidence:** record source Kafka and target Event Hubs versions/tier, client library, UTC time, resource scope, input event IDs, expected/observed results, negative cases, cost, cleanup, rollback, owner and reviewer. **Execution:** Pending until run; migration simulations may be Tabletop.

### Lab 05 — Review authentication

**Goal and procedure:** Compare Strimzi SCRAM/mTLS Kafka ACL with Event Hubs supported SASL_SSL and Azure RBAC/SAS. Use an approved isolated AKS namespace and Azure nonproduction subscription. For active tests, use version-pinned Kafka clients, redacted secret injection and bounded synthetic events. Do not provision or mutate paid Azure resources without explicit approval.

**Expected evidence:** record source Kafka and target Event Hubs versions/tier, client library, UTC time, resource scope, input event IDs, expected/observed results, negative cases, cost, cleanup, rollback, owner and reviewer. **Execution:** Pending until run; migration simulations may be Tabletop.

### Lab 06 — Validate namespace DNS and TLS

**Goal and procedure:** Check private endpoint/VNet DNS and Kafka endpoint 9093 from approved AKS debug Pod. Use an approved isolated AKS namespace and Azure nonproduction subscription. For active tests, use version-pinned Kafka clients, redacted secret injection and bounded synthetic events. Do not provision or mutate paid Azure resources without explicit approval.

**Expected evidence:** record source Kafka and target Event Hubs versions/tier, client library, UTC time, resource scope, input event IDs, expected/observed results, negative cases, cost, cleanup, rollback, owner and reviewer. **Execution:** Pending until run; migration simulations may be Tabletop.

### Lab 07 — Review quota and throttling

**Goal and procedure:** Estimate ingress/egress, partitions, connections, request limits, throughput units and tier restrictions. Use an approved isolated AKS namespace and Azure nonproduction subscription. For active tests, use version-pinned Kafka clients, redacted secret injection and bounded synthetic events. Do not provision or mutate paid Azure resources without explicit approval.

**Expected evidence:** record source Kafka and target Event Hubs versions/tier, client library, UTC time, resource scope, input event IDs, expected/observed results, negative cases, cost, cleanup, rollback, owner and reviewer. **Execution:** Pending until run; migration simulations may be Tabletop.

### Lab 08 — Review retention and replay

**Goal and procedure:** Compare source Kafka retention.ms/bytes and compaction with Event Hubs tier retention and capture strategy. Use an approved isolated AKS namespace and Azure nonproduction subscription. For active tests, use version-pinned Kafka clients, redacted secret injection and bounded synthetic events. Do not provision or mutate paid Azure resources without explicit approval.

**Expected evidence:** record source Kafka and target Event Hubs versions/tier, client library, UTC time, resource scope, input event IDs, expected/observed results, negative cases, cost, cleanup, rollback, owner and reviewer. **Execution:** Pending until run; migration simulations may be Tabletop.

### Lab 09 — Review ordering and partition keys

**Goal and procedure:** Map producer key routing, partition count and per-partition order guarantees. Use an approved isolated AKS namespace and Azure nonproduction subscription. For active tests, use version-pinned Kafka clients, redacted secret injection and bounded synthetic events. Do not provision or mutate paid Azure resources without explicit approval.

**Expected evidence:** record source Kafka and target Event Hubs versions/tier, client library, UTC time, resource scope, input event IDs, expected/observed results, negative cases, cost, cleanup, rollback, owner and reviewer. **Execution:** Pending until run; migration simulations may be Tabletop.

### Lab 10 — Review producer delivery

**Goal and procedure:** Audit acks, retries, idempotence and transactional APIs against supported target behavior. Use an approved isolated AKS namespace and Azure nonproduction subscription. For active tests, use version-pinned Kafka clients, redacted secret injection and bounded synthetic events. Do not provision or mutate paid Azure resources without explicit approval.

**Expected evidence:** record source Kafka and target Event Hubs versions/tier, client library, UTC time, resource scope, input event IDs, expected/observed results, negative cases, cost, cleanup, rollback, owner and reviewer. **Execution:** Pending until run; migration simulations may be Tabletop.

### Lab 11 — Review consumer groups

**Goal and procedure:** Map offset checkpoints, group IDs, rebalances, lag and migration starting offsets. Use an approved isolated AKS namespace and Azure nonproduction subscription. For active tests, use version-pinned Kafka clients, redacted secret injection and bounded synthetic events. Do not provision or mutate paid Azure resources without explicit approval.

**Expected evidence:** record source Kafka and target Event Hubs versions/tier, client library, UTC time, resource scope, input event IDs, expected/observed results, negative cases, cost, cleanup, rollback, owner and reviewer. **Execution:** Pending until run; migration simulations may be Tabletop.

### Lab 12 — Review schema contracts

**Goal and procedure:** Validate serialization, headers, timestamps, key/value and schema registry integration. Use an approved isolated AKS namespace and Azure nonproduction subscription. For active tests, use version-pinned Kafka clients, redacted secret injection and bounded synthetic events. Do not provision or mutate paid Azure resources without explicit approval.

**Expected evidence:** record source Kafka and target Event Hubs versions/tier, client library, UTC time, resource scope, input event IDs, expected/observed results, negative cases, cost, cleanup, rollback, owner and reviewer. **Execution:** Pending until run; migration simulations may be Tabletop.

### Lab 13 — Review Kafka Connect dependencies

**Goal and procedure:** Inventory source/sink connectors, Admin API requirements, worker internal topics and unsupported assumptions. Use an approved isolated AKS namespace and Azure nonproduction subscription. For active tests, use version-pinned Kafka clients, redacted secret injection and bounded synthetic events. Do not provision or mutate paid Azure resources without explicit approval.

**Expected evidence:** record source Kafka and target Event Hubs versions/tier, client library, UTC time, resource scope, input event IDs, expected/observed results, negative cases, cost, cleanup, rollback, owner and reviewer. **Execution:** Pending until run; migration simulations may be Tabletop.

### Lab 14 — Review Kafka Streams dependencies

**Goal and procedure:** Check state stores, changelog/repartition topics, transactions, exactly-once and broker API compatibility. Use an approved isolated AKS namespace and Azure nonproduction subscription. For active tests, use version-pinned Kafka clients, redacted secret injection and bounded synthetic events. Do not provision or mutate paid Azure resources without explicit approval.

**Expected evidence:** record source Kafka and target Event Hubs versions/tier, client library, UTC time, resource scope, input event IDs, expected/observed results, negative cases, cost, cleanup, rollback, owner and reviewer. **Execution:** Pending until run; migration simulations may be Tabletop.

### Lab 15 — Prepare dual-write experiment

**Goal and procedure:** Define nonproduction mirrored events with IDs, retry handling, cost cap and independent reconciliation. Use an approved isolated AKS namespace and Azure nonproduction subscription. For active tests, use version-pinned Kafka clients, redacted secret injection and bounded synthetic events. Do not provision or mutate paid Azure resources without explicit approval.

**Expected evidence:** record source Kafka and target Event Hubs versions/tier, client library, UTC time, resource scope, input event IDs, expected/observed results, negative cases, cost, cleanup, rollback, owner and reviewer. **Execution:** Pending until run; migration simulations may be Tabletop.

### Lab 16 — Validate synthetic produce

**Goal and procedure:** Write test event IDs with approved SASL_SSL client and verify acks/errors/latency. Use an approved isolated AKS namespace and Azure nonproduction subscription. For active tests, use version-pinned Kafka clients, redacted secret injection and bounded synthetic events. Do not provision or mutate paid Azure resources without explicit approval.

**Expected evidence:** record source Kafka and target Event Hubs versions/tier, client library, UTC time, resource scope, input event IDs, expected/observed results, negative cases, cost, cleanup, rollback, owner and reviewer. **Execution:** Pending until run; migration simulations may be Tabletop.

### Lab 17 — Validate synthetic consume

**Goal and procedure:** Read from approved group, compare payload hashes and offsets, report duplicates/missing. Use an approved isolated AKS namespace and Azure nonproduction subscription. For active tests, use version-pinned Kafka clients, redacted secret injection and bounded synthetic events. Do not provision or mutate paid Azure resources without explicit approval.

**Expected evidence:** record source Kafka and target Event Hubs versions/tier, client library, UTC time, resource scope, input event IDs, expected/observed results, negative cases, cost, cleanup, rollback, owner and reviewer. **Execution:** Pending until run; migration simulations may be Tabletop.

### Lab 18 — Exercise negative authentication

**Goal and procedure:** Test denied access with isolated identity, verify no secret leakage and restore. Use an approved isolated AKS namespace and Azure nonproduction subscription. For active tests, use version-pinned Kafka clients, redacted secret injection and bounded synthetic events. Do not provision or mutate paid Azure resources without explicit approval.

**Expected evidence:** record source Kafka and target Event Hubs versions/tier, client library, UTC time, resource scope, input event IDs, expected/observed results, negative cases, cost, cleanup, rollback, owner and reviewer. **Execution:** Pending until run; migration simulations may be Tabletop.

### Lab 19 — Design rollback and cutover

**Goal and procedure:** Define freeze window, offset strategy, lag threshold, rollback boundary and source retention buffer. Use an approved isolated AKS namespace and Azure nonproduction subscription. For active tests, use version-pinned Kafka clients, redacted secret injection and bounded synthetic events. Do not provision or mutate paid Azure resources without explicit approval.

**Expected evidence:** record source Kafka and target Event Hubs versions/tier, client library, UTC time, resource scope, input event IDs, expected/observed results, negative cases, cost, cleanup, rollback, owner and reviewer. **Execution:** Pending until run; migration simulations may be Tabletop.

### Lab 20 — Conduct migration acceptance

**Goal and procedure:** Score compatibility, correctness, cost, security, DR, SLO and independent approval. Use an approved isolated AKS namespace and Azure nonproduction subscription. For active tests, use version-pinned Kafka clients, redacted secret injection and bounded synthetic events. Do not provision or mutate paid Azure resources without explicit approval.

**Expected evidence:** record source Kafka and target Event Hubs versions/tier, client library, UTC time, resource scope, input event IDs, expected/observed results, negative cases, cost, cleanup, rollback, owner and reviewer. **Execution:** Pending until run; migration simulations may be Tabletop.

## 12. Read-only discovery validation script

Save as `verify-ch104.sh`. This verifies inventory visibility only; it does **not** prove Kafka API compatibility or successful migration.

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${AZURE_RG:?Set approved resource group}"
: "${EH_NAMESPACE:?Set Event Hubs namespace}"
: "${KAFKA_NS:?Set source Kafka namespace}"
: "${APP_NS:?Set AKS client namespace}"
echo '[1/8] Azure account'; az account show --query '{subscription:id,tenant:tenantId}' -o json
echo '[2/8] Event Hubs namespace'; az eventhubs namespace show -g "$AZURE_RG" -n "$EH_NAMESPACE" --query '{name:name,sku:sku,location:location}' -o json
echo '[3/8] Event Hubs entities'; az eventhubs eventhub list -g "$AZURE_RG" --namespace-name "$EH_NAMESPACE" -o table
echo '[4/8] AKS context'; kubectl config current-context
echo '[5/8] Source Kafka'; kubectl -n "$KAFKA_NS" get kafka -o name
echo '[6/8] Source topics'; kubectl -n "$KAFKA_NS" get kafkatopic -o name
echo '[7/8] Client Pods'; kubectl -n "$APP_NS" get pods -o wide
echo '[8/8] NetworkPolicy'; kubectl -n "$APP_NS" get networkpolicy
echo 'PASS: read-only inventory only.'
echo 'NOT PROVEN: SASL auth, API compatibility, replay, migration correctness or security review.'
```

## 13. Twelve migration failure scenarios

### Scenario 01 — Kafka AdminClient topic create fails

**Diagnosis:** Event Hubs Kafka API support differs; provision entities via supported Azure management interfaces. Inspect source Kafka client logs, Event Hubs Azure Monitor, supported API matrix, AKS DNS/networking, SASL identity, offsets, synthetic event ledger and lag. **Response:** stop unsafe cutover, preserve sanitized evidence, recover within tested retention/replay window. **Exit:** measured or explicitly tabletop result, incident owner, RCA and independent signoff.

### Scenario 02 — SASL handshake fails

**Diagnosis:** Validate supported SASL_SSL mechanism, username/password/token, namespace FQDN and clock. Inspect source Kafka client logs, Event Hubs Azure Monitor, supported API matrix, AKS DNS/networking, SASL identity, offsets, synthetic event ledger and lag. **Response:** stop unsafe cutover, preserve sanitized evidence, recover within tested retention/replay window. **Exit:** measured or explicitly tabletop result, incident owner, RCA and independent signoff.

### Scenario 03 — TLS works but metadata request fails

**Diagnosis:** Check Kafka protocol compatibility, namespace tier, entity mapping and advertised endpoint. Inspect source Kafka client logs, Event Hubs Azure Monitor, supported API matrix, AKS DNS/networking, SASL identity, offsets, synthetic event ledger and lag. **Response:** stop unsafe cutover, preserve sanitized evidence, recover within tested retention/replay window. **Exit:** measured or explicitly tabletop result, incident owner, RCA and independent signoff.

### Scenario 04 — AKS private endpoint DNS wrong

**Diagnosis:** Trace private DNS zone, VNet links, route/NSG and namespace resolution. Inspect source Kafka client logs, Event Hubs Azure Monitor, supported API matrix, AKS DNS/networking, SASL identity, offsets, synthetic event ledger and lag. **Response:** stop unsafe cutover, preserve sanitized evidence, recover within tested retention/replay window. **Exit:** measured or explicitly tabletop result, incident owner, RCA and independent signoff.

### Scenario 05 — Throttling after migration

**Diagnosis:** Inspect Azure Monitor incoming/outgoing bytes, requests, quota tier and producer retries. Inspect source Kafka client logs, Event Hubs Azure Monitor, supported API matrix, AKS DNS/networking, SASL identity, offsets, synthetic event ledger and lag. **Response:** stop unsafe cutover, preserve sanitized evidence, recover within tested retention/replay window. **Exit:** measured or explicitly tabletop result, incident owner, RCA and independent signoff.

### Scenario 06 — Unexpected consumer replay

**Diagnosis:** Check offset translation, starting policy, consumer group identity and retention window. Inspect source Kafka client logs, Event Hubs Azure Monitor, supported API matrix, AKS DNS/networking, SASL identity, offsets, synthetic event ledger and lag. **Response:** stop unsafe cutover, preserve sanitized evidence, recover within tested retention/replay window. **Exit:** measured or explicitly tabletop result, incident owner, RCA and independent signoff.

### Scenario 07 — Missing events during dual write

**Diagnosis:** Correlate producer event IDs, ack logs, retries and target lag before cutover. Inspect source Kafka client logs, Event Hubs Azure Monitor, supported API matrix, AKS DNS/networking, SASL identity, offsets, synthetic event ledger and lag. **Response:** stop unsafe cutover, preserve sanitized evidence, recover within tested retention/replay window. **Exit:** measured or explicitly tabletop result, incident owner, RCA and independent signoff.

### Scenario 08 — Kafka transactions unsupported

**Diagnosis:** Do not claim exactly-once; redesign for idempotent consumers and transactional outbox. Inspect source Kafka client logs, Event Hubs Azure Monitor, supported API matrix, AKS DNS/networking, SASL identity, offsets, synthetic event ledger and lag. **Response:** stop unsafe cutover, preserve sanitized evidence, recover within tested retention/replay window. **Exit:** measured or explicitly tabletop result, incident owner, RCA and independent signoff.

### Scenario 09 — Kafka Streams application stalls

**Diagnosis:** Inspect internal topics, Admin API and transaction dependencies; retain Kafka or redesign. Inspect source Kafka client logs, Event Hubs Azure Monitor, supported API matrix, AKS DNS/networking, SASL identity, offsets, synthetic event ledger and lag. **Response:** stop unsafe cutover, preserve sanitized evidence, recover within tested retention/replay window. **Exit:** measured or explicitly tabletop result, incident owner, RCA and independent signoff.

### Scenario 10 — Compacted topic semantics missing

**Diagnosis:** Replace with external state store/snapshot design; do not assume log compaction. Inspect source Kafka client logs, Event Hubs Azure Monitor, supported API matrix, AKS DNS/networking, SASL identity, offsets, synthetic event ledger and lag. **Response:** stop unsafe cutover, preserve sanitized evidence, recover within tested retention/replay window. **Exit:** measured or explicitly tabletop result, incident owner, RCA and independent signoff.

### Scenario 11 — Schema/headers changed

**Diagnosis:** Verify serializer, compression, headers and client compatibility against event hashes. Inspect source Kafka client logs, Event Hubs Azure Monitor, supported API matrix, AKS DNS/networking, SASL identity, offsets, synthetic event ledger and lag. **Response:** stop unsafe cutover, preserve sanitized evidence, recover within tested retention/replay window. **Exit:** measured or explicitly tabletop result, incident owner, RCA and independent signoff.

### Scenario 12 — Rollback fails after source retention expiry

**Diagnosis:** Use migration retention buffer, source write continuity and explicit recovery plan. Inspect source Kafka client logs, Event Hubs Azure Monitor, supported API matrix, AKS DNS/networking, SASL identity, offsets, synthetic event ledger and lag. **Response:** stop unsafe cutover, preserve sanitized evidence, recover within tested retention/replay window. **Exit:** measured or explicitly tabletop result, incident owner, RCA and independent signoff.

## 14. Eight SRE runbooks

### Runbook A — Event Hubs Kafka authentication outage

**Trigger/response:** Trace SASL_SSL, SAS/Entra roles, Key Vault, private endpoint and client error codes. **No-go:** unsupported API, unknown quota, expired replay window, missing reconciliation, broad credentials, missing rollback or unapproved paid resource change. **Exit:** authenticated end-to-end event correctness, restored SLO, reconciled IDs, sanitized evidence and approval.

### Runbook B — Throttling and capacity saturation

**Trigger/response:** Inspect tier limits, Azure Monitor, backpressure, retries and approved scale. **No-go:** unsupported API, unknown quota, expired replay window, missing reconciliation, broad credentials, missing rollback or unapproved paid resource change. **Exit:** authenticated end-to-end event correctness, restored SLO, reconciled IDs, sanitized evidence and approval.

### Runbook C — Consumer lag and replay divergence

**Trigger/response:** Compare source/target checkpoints, event IDs, retention and lag SLO. **No-go:** unsupported API, unknown quota, expired replay window, missing reconciliation, broad credentials, missing rollback or unapproved paid resource change. **Exit:** authenticated end-to-end event correctness, restored SLO, reconciled IDs, sanitized evidence and approval.

### Runbook D — Dual-write reconciliation failure

**Trigger/response:** Freeze cutover, preserve logs, reconcile event ledger and isolate duplicates. **No-go:** unsupported API, unknown quota, expired replay window, missing reconciliation, broad credentials, missing rollback or unapproved paid resource change. **Exit:** authenticated end-to-end event correctness, restored SLO, reconciled IDs, sanitized evidence and approval.

### Runbook E — Unsupported Kafka API incident

**Trigger/response:** Identify API dependency, switch to Azure management plane or roll back application. **No-go:** unsupported API, unknown quota, expired replay window, missing reconciliation, broad credentials, missing rollback or unapproved paid resource change. **Exit:** authenticated end-to-end event correctness, restored SLO, reconciled IDs, sanitized evidence and approval.

### Runbook F — Private connectivity outage

**Trigger/response:** Check AKS Pod DNS, VNet, NSG, private DNS, endpoint and TLS. **No-go:** unsupported API, unknown quota, expired replay window, missing reconciliation, broad credentials, missing rollback or unapproved paid resource change. **Exit:** authenticated end-to-end event correctness, restored SLO, reconciled IDs, sanitized evidence and approval.

### Runbook G — Migration cutover and rollback

**Trigger/response:** Apply go/no-go gates, route writes, validate reads, restore source if needed. **No-go:** unsupported API, unknown quota, expired replay window, missing reconciliation, broad credentials, missing rollback or unapproved paid resource change. **Exit:** authenticated end-to-end event correctness, restored SLO, reconciled IDs, sanitized evidence and approval.

### Runbook H — Independent migration acceptance

**Trigger/response:** Audit compatibility matrix, cost, security, event correctness, RPO/RTO and signoff. **No-go:** unsupported API, unknown quota, expired replay window, missing reconciliation, broad credentials, missing rollback or unapproved paid resource change. **Exit:** authenticated end-to-end event correctness, restored SLO, reconciled IDs, sanitized evidence and approval.

## 15. Migration SLOs and evidence

Measure publish success rate, end-to-end event correctness (IDs and payload hashes), p95/p99 latency, consumer lag, throttled requests, replay completion time, credential errors and namespace capacity. Use workload-specific thresholds; a sample acceptance goal is **zero unexplained missing event IDs** in a bounded synthetic dataset and no unauthorized reads.

```text
evidence-ch104/
  source-kafka-inventory.md
  eventhubs-target-inventory.md
  kafka-api-compatibility-matrix.md
  entity-topic-mapping.md
  sasl-identity-review.md
  aks-private-dns-tls.md
  quota-throttling-cost-model.md
  retention-replay-design.md
  partition-key-ordering.md
  producer-delivery-semantics.md
  consumer-group-offsets.md
  schema-contracts.md
  connect-compatibility.md
  streams-compatibility.md
  dual-write-plan.md
  synthetic-produce.md
  synthetic-consume-ledger.md
  negative-auth.md
  cutover-rollback.md
  independent-migration-acceptance.md
  scorecard.md
```

For each artifact: record UTC, client/service tier/version, Live vs Tabletop, expected and observed result, redacted logs, risk, cleanup, owner and reviewer.

## 16. 100-point acceptance assessment

| Domain | Points | Critical |
|---|---:|---|
| Source inventory and API compatibility | 20 | Yes |
| Event Hubs target quotas, networking and authentication | 20 | Yes |
| Ordering, retention, offsets and schema correctness | 15 | Yes |
| Connect/Streams/transaction and unsupported feature analysis | 15 | Yes |
| Synthetic dual-write reconciliation and SLOs | 15 | Yes |
| Cutover, rollback, DR and cost | 10 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 and all critical gates evidenced. **Automatic fail:** untested unsupported Kafka API, lost events without reconciliation, invalid offset migration assumptions, exposed SAS keys, unapproved cost, fabricated live execution or missing independent review.

## 17. References and next chapter

- [Azure Event Hubs for Apache Kafka](https://learn.microsoft.com/en-us/azure/event-hubs/azure-event-hubs-kafka-overview)
- [Event Hubs quotas and limits](https://learn.microsoft.com/en-us/azure/event-hubs/event-hubs-quotas)
- [Event Hubs authentication and authorization](https://learn.microsoft.com/en-us/azure/event-hubs/authorize-access-shared-access-signature)
- [Azure Event Hubs Kafka troubleshooting](https://learn.microsoft.com/en-us/azure/event-hubs/troubleshooting-guide)
- [Strimzi documentation](https://strimzi.io/documentation/)
- [Apache Kafka documentation](https://kafka.apache.org/documentation/)

**Next:** Chapter 105 — Azure Kafka Producers, Consumers, Topics and Data Pipelines.

---

**Verification boundary:** Publication confirms documentation availability only. Live AKS/Event Hubs client tests, API compatibility verification, dual-write reconciliation and independent technical/security review remain Pending.
