# Chapter 056 — Kafka Connect Architecture, Distributed Workers and Connector Lifecycle

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 12 — Kafka Connect, CDC and Schema Management (1/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–055, especially 026–030, 036–055  
**Status:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending

> **Safety:** Use disposable Kafka/Connect clusters, synthetic topics and approved test plugins. Kafka Connect REST can create, update, pause and delete connector workloads; this chapter uses read-only REST inspection and design/tabletop for mutation. Do not expose unauthenticated Connect REST publicly, load untrusted plugins, reset production offsets, delete internal topics, bypass TLS/SASL/ACLs or assume Connect provides exactly-once end-to-end delivery for every connector.

## 1. Mission

Build a production-minded understanding of Kafka Connect as a distributed integration runtime. Operate Strimzi-managed KafkaConnect workers in Kubernetes, distinguish connector and task lifecycles, design internal state topics, isolate plugins, secure the REST API and recover from worker/task failures without losing track of data integrity.

## 2. Learning objectives

- Explain **workers**, **connectors**, **tasks**, **converters**, **transforms**, **source/sink connectors** and **distributed coordination**.
- Map Connect worker internal config, offset and status topics and their durability requirements.
- Distinguish connector status from task status, Kubernetes Pod readiness and application freshness.
- Design Strimzi KafkaConnect CRs, immutable plugin images, scoped identities and secure REST access.
- Review connector lifecycle operations: validate, create, update, pause, resume, restart and delete.
- Investigate at-least-once replay, idempotent sinks, DLQ, retries and offset integrity.
- Define capacity, observability, SLO and operational acceptance gates.

## 3. Kafka Connect architecture

```text
 Source system --> Source connector --> Tasks --> Kafka topics
                         |                         |
                    Connect workers           Sink connector
                  (distributed group)               |
                         |                        Tasks --> Sink system
               config / offsets / status
                  Kafka internal topics
                         |
               Strimzi KafkaConnect CR
                         |
              Kubernetes Pods / Services
                         |
             GitOps / metrics / logs / alerts
```

Workers form a distributed Connect cluster using a shared `group.id` and Kafka-backed internal state. A connector is a logical integration configuration; **tasks** perform data movement and can be reassigned after worker loss. More `tasks.max` does not guarantee more actual tasks or throughput: connector capabilities, source partitioning and external system limits constrain parallelism.

## 4. Source versus sink and delivery semantics

| Property | Source connector | Sink connector |
|---|---|---|
| Reads from | external source or API | Kafka topic partitions |
| Writes to | Kafka topics | external sink |
| Offset state | source-specific offset tracking | Kafka consumer offsets |
| Common failure | source API unavailable, duplicate fetch | sink timeout, duplicate write |
| Correctness gate | source record ID vs Kafka accepted ID | Kafka accepted ID vs durable sink ID |
| Typical contract | at-least-once unless connector-specific guarantees proven | at-least-once unless connector-specific guarantees proven |

Kafka Connect framework and connector-specific exactly-once capabilities vary. **Do not promise exactly-once external effects** without checking the connector, transaction boundaries, sink idempotency and version-specific documentation.

## 5. Distributed worker internal topics

| Internal topic | Purpose | Operational concern |
|---|---|---|
| `config.storage.topic` | connector and task configurations | compacted; durable and shared |
| `offset.storage.topic` | source connector offsets | compacted; preserve during recovery |
| `status.storage.topic` | connector and task status | compacted; avoid accidental deletion |

Select RF appropriate to broker count and availability zones; in multi-broker production clusters typically design durable replicated internal topics, while a single-broker disposable lab cannot use RF=3. The config topic has stricter partition requirements than general data topics; verify release-specific guidance. Internal topics need correct ACLs and must not be confused with user CDC topics.

## 6. Kubernetes and Strimzi deployment boundaries

KafkaConnect CRD availability, `apiVersion`, worker configuration fields, plugin build/image behavior, annotation-based connector management and connector CRDs vary by Strimzi release. Check `kubectl explain kafkaconnect.spec` and installed CRDs first.

**Operator ownership:** Use reviewed KafkaConnect/KafkaConnector CRs or an explicitly chosen REST management model; avoid conflicting GitOps CR reconciliation and manual REST mutations. Do not patch operator-owned Deployments directly. KafkaConnector CR use may require a release-specific opt-in annotation; verify installed documentation.

**Security:** Connect REST is an administrative API. Restrict its Service and NetworkPolicy, use an authenticated authorization-aware gateway if remote administration is necessary, and prevent sensitive connector configs or REST output from being committed to evidence. Kafka ACLs for workers, internal topics and connectors should be scoped to actual operations.

## 7. Read-only lab inventory

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,svc,networkpolicy -o wide
kubectl api-resources | grep -Ei 'kafkaconnect|kafkaconnector'
kubectl explain kafkaconnect.spec
kubectl -n kafka-lab get kafkaconnect -o wide
kubectl -n kafka-lab get kafkaconnector -o wide
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp

# REST read-only examples: use only a secured local test port-forward
# in an approved disposable environment; verify Service name and policy.
# curl -fsS http://127.0.0.1:8083/
# curl -fsS http://127.0.0.1:8083/connectors
# curl -fsS http://127.0.0.1:8083/connectors/sre-synthetic-source/status
# curl -fsS http://127.0.0.1:8083/connector-plugins
```

REST `GET /connectors/{name}/config` may reveal secrets; avoid dumping configs. Kafka Connect REST on port 8083 is frequently unauthenticated by default; **localhost port-forward is not a production authentication control**. Apply namespace RBAC and gateway security according to organizational policy.

## 8. Version-qualified KafkaConnect design sketch

This is **review-only YAML**, not a guaranteed deployable Strimzi manifest. Confirm the served CRD and plugin packaging for the installed version.

```yaml
# Policy artifact only — NOT a Kubernetes CustomResource
connectCluster: sre-connect
kafkaCluster: sre-kafka
replicas: 3
workerGroupId: sre-connect-workers
internalTopics:
  config: sre-connect-configs
  offsets: sre-connect-offsets
  status: sre-connect-status
  replicationFactor: 3
  cleanupPolicy: compact
pluginSupplyChain:
  immutableImageDigest: required
  signedImage: required
  sbom: required
  versionCompatibility: reviewed
security:
  kafkaTlsSasl: required
  leastPrivilegeAcl: required
  restApiRestricted: required
  secretRedaction: required
operations:
  gitopsReconciliation: required
  taskStatusAlerts: required
  dlqMonitoring: required
  uniqueEventLedger: required
```

## 9. Twenty Kubernetes-first Connect labs

### Lab 01 — Establish isolated Connect lab scope

**Objective and procedure:** Confirm approved Kubernetes context, namespace, Strimzi/Kafka versions, CRDs, RBAC, TLS, Kafka ACLs and rollback owner.

**Expected evidence:** Approved Kubernetes context, Kafka/Strimzi/Connect versions, UTC command/query, expected/observed result, security boundary, task/offset integrity, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Worker loss, offset mutation and connector lifecycle changes remain **Tabletop** without an approved isolated change plan.

### Lab 02 — Inspect Kafka Connect architecture

**Objective and procedure:** Diagram worker group, REST API, connectors, tasks, Kafka internal topics, plugin isolation and data flow.

**Expected evidence:** Approved Kubernetes context, Kafka/Strimzi/Connect versions, UTC command/query, expected/observed result, security boundary, task/offset integrity, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Worker loss, offset mutation and connector lifecycle changes remain **Tabletop** without an approved isolated change plan.

### Lab 03 — Discover Strimzi KafkaConnect CRD

**Objective and procedure:** Check installed API schema and supported fields; do not assume a release-independent manifest.

**Expected evidence:** Approved Kubernetes context, Kafka/Strimzi/Connect versions, UTC command/query, expected/observed result, security boundary, task/offset integrity, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Worker loss, offset mutation and connector lifecycle changes remain **Tabletop** without an approved isolated change plan.

### Lab 04 — Inventory Kafka brokers and listeners

**Objective and procedure:** Verify Kafka KRaft quorum, broker Pods, secure bootstrap, listener certificates and KafkaUser identities.

**Expected evidence:** Approved Kubernetes context, Kafka/Strimzi/Connect versions, UTC command/query, expected/observed result, security boundary, task/offset integrity, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Worker loss, offset mutation and connector lifecycle changes remain **Tabletop** without an approved isolated change plan.

### Lab 05 — Design distributed worker group

**Objective and procedure:** Select replicas, worker group.id, bootstrap connectivity, connector/task capacity and resource requests.

**Expected evidence:** Approved Kubernetes context, Kafka/Strimzi/Connect versions, UTC command/query, expected/observed result, security boundary, task/offset integrity, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Worker loss, offset mutation and connector lifecycle changes remain **Tabletop** without an approved isolated change plan.

### Lab 06 — Review internal topic durability

**Objective and procedure:** Plan config, offset and status internal topics with appropriate RF, minISR, compaction and ACLs.

**Expected evidence:** Approved Kubernetes context, Kafka/Strimzi/Connect versions, UTC command/query, expected/observed result, security boundary, task/offset integrity, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Worker loss, offset mutation and connector lifecycle changes remain **Tabletop** without an approved isolated change plan.

### Lab 07 — Review secure Connect worker identity

**Objective and procedure:** Validate TLS/SASL credentials, scoped Kafka ACLs, Secret references, RBAC and namespace boundaries.

**Expected evidence:** Approved Kubernetes context, Kafka/Strimzi/Connect versions, UTC command/query, expected/observed result, security boundary, task/offset integrity, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Worker loss, offset mutation and connector lifecycle changes remain **Tabletop** without an approved isolated change plan.

### Lab 08 — Review connector plugin delivery

**Objective and procedure:** Plan immutable OCI image, compatible plugin version, SBOM, signatures, CVE checks and restart impact.

**Expected evidence:** Approved Kubernetes context, Kafka/Strimzi/Connect versions, UTC command/query, expected/observed result, security boundary, task/offset integrity, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Worker loss, offset mutation and connector lifecycle changes remain **Tabletop** without an approved isolated change plan.

### Lab 09 — Review KafkaConnect resource schema

**Objective and procedure:** Inspect version-specific image, config, replicas, logging, metrics, template and build options.

**Expected evidence:** Approved Kubernetes context, Kafka/Strimzi/Connect versions, UTC command/query, expected/observed result, security boundary, task/offset integrity, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Worker loss, offset mutation and connector lifecycle changes remain **Tabletop** without an approved isolated change plan.

### Lab 10 — Inspect Connect REST reachability

**Objective and procedure:** Check ClusterIP Service, NetworkPolicy, HTTP status and authenticated REST gateway if deployed.

**Expected evidence:** Approved Kubernetes context, Kafka/Strimzi/Connect versions, UTC command/query, expected/observed result, security boundary, task/offset integrity, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Worker loss, offset mutation and connector lifecycle changes remain **Tabletop** without an approved isolated change plan.

### Lab 11 — Inspect worker membership

**Objective and procedure:** Use REST and Pod logs to map workers, distributed coordination and connector task assignments.

**Expected evidence:** Approved Kubernetes context, Kafka/Strimzi/Connect versions, UTC command/query, expected/observed result, security boundary, task/offset integrity, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Worker loss, offset mutation and connector lifecycle changes remain **Tabletop** without an approved isolated change plan.

### Lab 12 — Create synthetic source connector plan

**Objective and procedure:** Design an isolated test source plugin and topic with explicit allowlist, no production external system.

**Expected evidence:** Approved Kubernetes context, Kafka/Strimzi/Connect versions, UTC command/query, expected/observed result, security boundary, task/offset integrity, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Worker loss, offset mutation and connector lifecycle changes remain **Tabletop** without an approved isolated change plan.

### Lab 13 — Create synthetic sink connector plan

**Objective and procedure:** Design an isolated sink with idempotent writes and DLQ, respecting plugin and storage dependencies.

**Expected evidence:** Approved Kubernetes context, Kafka/Strimzi/Connect versions, UTC command/query, expected/observed result, security boundary, task/offset integrity, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Worker loss, offset mutation and connector lifecycle changes remain **Tabletop** without an approved isolated change plan.

### Lab 14 — Validate connector lifecycle semantics

**Objective and procedure:** Rehearse create, validate, pause, resume, restart and delete decisions in GitOps tabletop.

**Expected evidence:** Approved Kubernetes context, Kafka/Strimzi/Connect versions, UTC command/query, expected/observed result, security boundary, task/offset integrity, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Worker loss, offset mutation and connector lifecycle changes remain **Tabletop** without an approved isolated change plan.

### Lab 15 — Validate task configuration and scaling

**Objective and procedure:** Compare tasks.max, actual task count, connector parallelism, partitions and resource headroom.

**Expected evidence:** Approved Kubernetes context, Kafka/Strimzi/Connect versions, UTC command/query, expected/observed result, security boundary, task/offset integrity, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Worker loss, offset mutation and connector lifecycle changes remain **Tabletop** without an approved isolated change plan.

### Lab 16 — Inspect offset and state management

**Objective and procedure:** Map source connector offsets, consumer group offsets, status/config topics and checkpoint/restore policy.

**Expected evidence:** Approved Kubernetes context, Kafka/Strimzi/Connect versions, UTC command/query, expected/observed result, security boundary, task/offset integrity, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Worker loss, offset mutation and connector lifecycle changes remain **Tabletop** without an approved isolated change plan.

### Lab 17 — Validate connector failure observability

**Objective and procedure:** Define connector/task FAILED, rebalance, lag, retry, DLQ, error rate and No Data alerts.

**Expected evidence:** Approved Kubernetes context, Kafka/Strimzi/Connect versions, UTC command/query, expected/observed result, security boundary, task/offset integrity, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Worker loss, offset mutation and connector lifecycle changes remain **Tabletop** without an approved isolated change plan.

### Lab 18 — Model worker Pod loss tabletop

**Objective and procedure:** Analyze worker group rebalance, task restart, at-least-once duplicates and downstream idempotency.

**Expected evidence:** Approved Kubernetes context, Kafka/Strimzi/Connect versions, UTC command/query, expected/observed result, security boundary, task/offset integrity, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Worker loss, offset mutation and connector lifecycle changes remain **Tabletop** without an approved isolated change plan.

### Lab 19 — Model plugin upgrade and rollback tabletop

**Objective and procedure:** Review compatibility, image digest, change ticket, rollout, task validation and safe rollback.

**Expected evidence:** Approved Kubernetes context, Kafka/Strimzi/Connect versions, UTC command/query, expected/observed result, security boundary, task/offset integrity, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Worker loss, offset mutation and connector lifecycle changes remain **Tabletop** without an approved isolated change plan.

### Lab 20 — Complete operational readiness review

**Objective and procedure:** Run read-only preflight, evidence checklist, 100-point rubric, security review and independent signoff.

**Expected evidence:** Approved Kubernetes context, Kafka/Strimzi/Connect versions, UTC command/query, expected/observed result, security boundary, task/offset integrity, rollback/abort, owner and independent assessor. Mark **Pending** until live execution. Worker loss, offset mutation and connector lifecycle changes remain **Tabletop** without an approved isolated change plan.

## 10. Read-only verification script

Save as `verify-ch56.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
echo '[1/10] Context'; kubectl config current-context
echo '[2/10] Kafka cluster'; kubectl -n "$NS" get kafka,kafkanodepool -o wide
echo '[3/10] Connect CRD'; kubectl api-resources | grep -i kafkaconnect
echo '[4/10] Connect resources'; kubectl -n "$NS" get kafkaconnect -o wide
echo '[5/10] Connector resources (if CRD present)'
if kubectl api-resources -o name | grep -q '^kafkaconnectors.kafka.strimzi.io$'; then
  kubectl -n "$NS" get kafkaconnector -o wide
else
  echo 'UNKNOWN/NOT CONFIGURED: KafkaConnector CRD not discovered'
fi
echo '[6/10] Pods'; kubectl -n "$NS" get pods -o wide
echo '[7/10] Services'; kubectl -n "$NS" get svc,endpointslices
echo '[8/10] NetworkPolicies'; kubectl -n "$NS" get networkpolicy
echo '[9/10] Events'; kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[10/10] Connect CRD schema'; kubectl explain kafkaconnect.spec
echo 'PASS: read-only Connect inventory.'
echo 'NOT PROVEN: connector/task health, internal topic durability, REST security, replay or independent review.'
```

Run `chmod +x verify-ch56.sh && ./verify-ch56.sh | tee evidence-ch56/preflight.txt`. Inventory failures are investigation signals, not permission to modify a cluster. If KafkaConnect CRD is absent, report prerequisite missing and do not claim a lab pass.

## 11. Twelve Connect failure scenarios

### Scenario 1 — Connect CR Ready but task FAILED

**Diagnosis:** Check REST task status, worker logs, plugin errors and external dependency. Correlate Connect REST task status, Strimzi CR conditions, Pod logs, Kafka internal topics, ACLs, input/output freshness and unique-event ledger. **Decision:** Freeze unsafe connector changes, protect offsets, restore approved configuration and verify durable sink results. **Acceptance:** UTC evidence, redacted errors, rollback and independent review.

### Scenario 2 — Plugin class not found

**Diagnosis:** Check image contents, plugin.path, classloader isolation and image rollout. Correlate Connect REST task status, Strimzi CR conditions, Pod logs, Kafka internal topics, ACLs, input/output freshness and unique-event ledger. **Decision:** Freeze unsafe connector changes, protect offsets, restore approved configuration and verify durable sink results. **Acceptance:** UTC evidence, redacted errors, rollback and independent review.

### Scenario 3 — Worker group constantly rebalances

**Diagnosis:** Check group.id, worker churn, internal topics, network and resource pressure. Correlate Connect REST task status, Strimzi CR conditions, Pod logs, Kafka internal topics, ACLs, input/output freshness and unique-event ledger. **Decision:** Freeze unsafe connector changes, protect offsets, restore approved configuration and verify durable sink results. **Acceptance:** UTC evidence, redacted errors, rollback and independent review.

### Scenario 4 — Internal offset topic RF invalid for broker count

**Diagnosis:** Check topic existence, RF, ISR, ACL and Connect startup logs. Correlate Connect REST task status, Strimzi CR conditions, Pod logs, Kafka internal topics, ACLs, input/output freshness and unique-event ledger. **Decision:** Freeze unsafe connector changes, protect offsets, restore approved configuration and verify durable sink results. **Acceptance:** UTC evidence, redacted errors, rollback and independent review.

### Scenario 5 — REST Service inaccessible

**Diagnosis:** Check Pod readiness, Service/EndpointSlice, NetworkPolicy and authentication. Correlate Connect REST task status, Strimzi CR conditions, Pod logs, Kafka internal topics, ACLs, input/output freshness and unique-event ledger. **Decision:** Freeze unsafe connector changes, protect offsets, restore approved configuration and verify durable sink results. **Acceptance:** UTC evidence, redacted errors, rollback and independent review.

### Scenario 6 — Connector tasks.max raised without throughput gain

**Diagnosis:** Review source partitioning, connector implementation and bottleneck. Correlate Connect REST task status, Strimzi CR conditions, Pod logs, Kafka internal topics, ACLs, input/output freshness and unique-event ledger. **Decision:** Freeze unsafe connector changes, protect offsets, restore approved configuration and verify durable sink results. **Acceptance:** UTC evidence, redacted errors, rollback and independent review.

### Scenario 7 — Sink duplicates after worker restart

**Diagnosis:** Review at-least-once semantics, idempotent sink, transaction boundaries and offset commits. Correlate Connect REST task status, Strimzi CR conditions, Pod logs, Kafka internal topics, ACLs, input/output freshness and unique-event ledger. **Decision:** Freeze unsafe connector changes, protect offsets, restore approved configuration and verify durable sink results. **Acceptance:** UTC evidence, redacted errors, rollback and independent review.

### Scenario 8 — Source connector silently stops producing

**Diagnosis:** Check task health, source offsets, input heartbeat and event freshness. Correlate Connect REST task status, Strimzi CR conditions, Pod logs, Kafka internal topics, ACLs, input/output freshness and unique-event ledger. **Decision:** Freeze unsafe connector changes, protect offsets, restore approved configuration and verify durable sink results. **Acceptance:** UTC evidence, redacted errors, rollback and independent review.

### Scenario 9 — Connector auth fails after credential rotation

**Diagnosis:** Inspect TLS/SASL, Secret rollout, ACLs and CA trust. Correlate Connect REST task status, Strimzi CR conditions, Pod logs, Kafka internal topics, ACLs, input/output freshness and unique-event ledger. **Decision:** Freeze unsafe connector changes, protect offsets, restore approved configuration and verify durable sink results. **Acceptance:** UTC evidence, redacted errors, rollback and independent review.

### Scenario 10 — DLQ grows but task remains RUNNING

**Diagnosis:** Monitor error counters, DLQ age, record loss policy and application SLO. Correlate Connect REST task status, Strimzi CR conditions, Pod logs, Kafka internal topics, ACLs, input/output freshness and unique-event ledger. **Decision:** Freeze unsafe connector changes, protect offsets, restore approved configuration and verify durable sink results. **Acceptance:** UTC evidence, redacted errors, rollback and independent review.

### Scenario 11 — Connect worker OOM during burst

**Diagnosis:** Review JVM heap, memory limit, batch sizes, plugin leaks and capacity. Correlate Connect REST task status, Strimzi CR conditions, Pod logs, Kafka internal topics, ACLs, input/output freshness and unique-event ledger. **Decision:** Freeze unsafe connector changes, protect offsets, restore approved configuration and verify durable sink results. **Acceptance:** UTC evidence, redacted errors, rollback and independent review.

### Scenario 12 — Upgrade breaks connector serialization

**Diagnosis:** Inspect converter/schema compatibility, rollback and replay evidence. Correlate Connect REST task status, Strimzi CR conditions, Pod logs, Kafka internal topics, ACLs, input/output freshness and unique-event ledger. **Decision:** Freeze unsafe connector changes, protect offsets, restore approved configuration and verify durable sink results. **Acceptance:** UTC evidence, redacted errors, rollback and independent review.

## 12. Eight production Connect runbooks

### Runbook A — Connect platform preflight

**Trigger and first response:** Validate Kafka quorum, worker group, internal topics, ACL, image digest, Pod/PVC and change approval. **Safety gates:** No production offset reset, internal topic deletion, unauthorized REST mutation, plaintext secret exposure, unreviewed plugin image or weakened Kafka durability. **Exit:** Healthy workers/tasks, secure Kafka/REST access, reconciled unique-event ledger, SLO recovery and corrective-action owner.

### Runbook B — Connector or task FAILED

**Trigger and first response:** Inspect REST status, worker logs, errors, plugin and upstream/downstream health. **Safety gates:** No production offset reset, internal topic deletion, unauthorized REST mutation, plaintext secret exposure, unreviewed plugin image or weakened Kafka durability. **Exit:** Healthy workers/tasks, secure Kafka/REST access, reconciled unique-event ledger, SLO recovery and corrective-action owner.

### Runbook C — Worker membership and rebalance storm

**Trigger and first response:** Correlate Pod restarts, group assignment, internal topics, network and task movement. **Safety gates:** No production offset reset, internal topic deletion, unauthorized REST mutation, plaintext secret exposure, unreviewed plugin image or weakened Kafka durability. **Exit:** Healthy workers/tasks, secure Kafka/REST access, reconciled unique-event ledger, SLO recovery and corrective-action owner.

### Runbook D — Offset integrity and replay

**Trigger and first response:** Distinguish source offsets, sink consumer offsets, commits, replay and deduplication. **Safety gates:** No production offset reset, internal topic deletion, unauthorized REST mutation, plaintext secret exposure, unreviewed plugin image or weakened Kafka durability. **Exit:** Healthy workers/tasks, secure Kafka/REST access, reconciled unique-event ledger, SLO recovery and corrective-action owner.

### Runbook E — Plugin delivery and rollback

**Trigger and first response:** Review immutable image, plugin versions, SBOM, staging smoke tests and GitOps revert. **Safety gates:** No production offset reset, internal topic deletion, unauthorized REST mutation, plaintext secret exposure, unreviewed plugin image or weakened Kafka durability. **Exit:** Healthy workers/tasks, secure Kafka/REST access, reconciled unique-event ledger, SLO recovery and corrective-action owner.

### Runbook F — Connect security and REST exposure

**Trigger and first response:** Verify TLS/SASL, ACL, Service/NetworkPolicy, secrets and REST authorization gateway. **Safety gates:** No production offset reset, internal topic deletion, unauthorized REST mutation, plaintext secret exposure, unreviewed plugin image or weakened Kafka durability. **Exit:** Healthy workers/tasks, secure Kafka/REST access, reconciled unique-event ledger, SLO recovery and corrective-action owner.

### Runbook G — DLQ, retries and poison-pill handling

**Trigger and first response:** Assess error tolerance, DLQ ACL, payload sensitivity, replay and downstream correctness. **Safety gates:** No production offset reset, internal topic deletion, unauthorized REST mutation, plaintext secret exposure, unreviewed plugin image or weakened Kafka durability. **Exit:** Healthy workers/tasks, secure Kafka/REST access, reconciled unique-event ledger, SLO recovery and corrective-action owner.

### Runbook H — SLO recovery and incident closure

**Trigger and first response:** Reconcile unique IDs, task health, end-to-end lag, event freshness, RCA and reviewer. **Safety gates:** No production offset reset, internal topic deletion, unauthorized REST mutation, plaintext secret exposure, unreviewed plugin image or weakened Kafka durability. **Exit:** Healthy workers/tasks, secure Kafka/REST access, reconciled unique-event ledger, SLO recovery and corrective-action owner.

## 13. Evidence package

```text
evidence-ch56/
  approved-connect-charter.md
  context-version-matrix.md
  preflight.txt
  connect-architecture-diagram.md
  kafkaconnect-crd-schema.md
  kafka-quorum-listeners.md
  distributed-worker-design.md
  internal-topic-rf-minisr-acl.md
  worker-tls-sasl-acl.md
  plugin-image-sbom-compatibility.md
  kafkaconnect-gitops-review.md
  rest-service-exposure.md
  worker-membership-task-assignment.md
  synthetic-source-connector.md
  synthetic-sink-connector.md
  lifecycle-gitops-tabletop.md
  tasks-max-capacity.md
  source-sink-offset-map.md
  connect-alerts-dlq.md
  worker-failure-tabletop.md
  plugin-upgrade-rollback-tabletop.md
  accepted-processed-event-ledger.csv
  independent-technical-security-review.md
  readiness-scorecard.md
```

Each artifact must record exact version/source, UTC timestamp, expected/observed result, redaction, owner, abort/rollback and reviewer. Do not treat a GitHub document or design tabletop as evidence of a functioning Connect deployment.

## 14. 100-point Connect operations assessment

| Domain | Points | Critical |
|---|---:|---|
| Architecture, scope and lifecycle ownership | 10 | Yes |
| Strimzi KafkaConnect and worker group design | 15 | Yes |
| Internal topic durability and offset integrity | 15 | Yes |
| Secure Kafka/REST access and plugin supply chain | 15 | Yes |
| Connector/task lifecycle and scaling | 15 | Yes |
| Source/sink replay, DLQ and data reconciliation | 10 | Yes |
| Observability, SLO and troubleshooting | 10 | Yes |
| Runbooks, rollback and incident readiness | 5 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 and every critical gate evidenced. **Automatic Fail:** fabricated connector execution, exposed Connect REST, secret leakage, unreviewed plugin supply chain, offset/internal-topic deletion, unsupported exactly-once claims, missing sink reconciliation or absent independent review.

## 15. Cleanup, references and next chapter

Remove only chapter-owned synthetic connectors, test topics and alerts through approved GitOps after evidence retention. Preserve internal state until offsets and sink reconciliation are complete. Never delete production Connect internal topics, consumer offsets, PVCs or Secrets.

**References:** [Apache Kafka Connect Documentation](https://kafka.apache.org/documentation/#connect), [Strimzi Documentation](https://strimzi.io/documentation/), [Kubernetes NetworkPolicies](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

**Next:** Chapter 057 — Kafka Connect Source and Sink Connectors, Data Movement and Production Reliability.

---

**Verification boundary:** Publication establishes document availability only. Live connector deployment, REST/task tests, data integrity and independent technical/security acceptance remain Pending.
