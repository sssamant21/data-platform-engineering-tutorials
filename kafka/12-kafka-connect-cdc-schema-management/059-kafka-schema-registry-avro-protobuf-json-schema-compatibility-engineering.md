# Chapter 059 — Kafka Schema Registry, Avro, Protobuf, JSON Schema and Compatibility Engineering

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 12 — Kafka Connect, CDC and Schema Management (4/5)  
**Primary platform:** Kubernetes + Strimzi Operator + Kafka KRaft  
**Prerequisites:** Chapters 001–058, especially 026–030 and 056–058  
**Status:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending

> **Safety:** Use a disposable registry and synthetic subjects. Schema registry is an ecosystem service, **not a native Apache Kafka broker feature**. Compatibility APIs, subject naming, wire formats, auth, and schema references differ by implementation. Do not change production compatibility modes, delete subjects, register breaking schemas, leak registry credentials or disable security without approved change management.

## 1. Mission

Design and operate governed event schemas for Kafka producers, consumers, Kafka Connect and Debezium CDC. Compare Avro, Protobuf and JSON Schema; define subject ownership and compatibility; validate schema evolution and wire-format assumptions; and make schema registry a secure, observable and recoverable platform dependency.

## 2. Learning objectives

- Explain why a registry manages schema identities and evolution while Kafka stores opaque record bytes.
- Distinguish Avro writer/reader schema resolution, Protobuf stable field tags and JSON Schema validation rules.
- Compare BACKWARD, FORWARD, FULL and transitive compatibility under a specific registry's implementation.
- Review subject naming strategies and separate key/value schema governance.
- Integrate Kafka Connect converters and CDC envelopes without losing tombstone semantics.
- Design registry TLS/auth/ACL, availability, caching, backup and disaster recovery.
- Build a CI compatibility gate, rollback matrix, evidence package and independent review.

## 3. Architecture

```text
Source DB / Debezium -> Kafka Connect converter --+
                                                  |
Producer -> serializer -> Registry (schema IDs) --+--> Kafka KRaft topic
                                                         |
                                               deserializer / schema lookup
                                                         |
                                                consumer / sink connector

GitOps + schema CI -> compatibility checks -> reviewed subject registration
Kubernetes -> registry Pods/Service/Ingress, TLS, RBAC, metrics, backup
```

Schema IDs and serialization framing are registry/client specific. Do **not** assume an Avro payload is self-describing or that a schema ID from one registry cluster is valid in another.

## 4. Format comparison

| Format | Strength | Evolution hazard | Review gate |
|---|---|---|---|
| Avro | compact schema-driven encoding, writer/reader resolution | missing default for newly required reader field | writer/reader matrix |
| Protobuf | compact tagged wire format, language ecosystem | reusing field numbers or incompatible type changes | reserved tags and compatibility |
| JSON Schema | explicit JSON validation and tooling | new required properties, type narrowing, additionalProperties | consumer validation matrix |

Compatibility rules are more nuanced than a single mode label; check the actual implementation and client serializer/deserializer behavior. Avro defaults, Protobuf field presence and JSON Schema required fields have different semantics.

## 5. Compatibility engineering

| Mode | General intent | Typical validation |
|---|---|---|
| BACKWARD | new readers can read data written with prior schema | new consumer vs prior producer |
| FORWARD | prior readers can read new writer data | prior consumer vs new producer |
| FULL | both backward and forward | bidirectional version matrix |
| BACKWARD_TRANSITIVE | new readers can read all earlier versions | all prior writers |
| FORWARD_TRANSITIVE | all earlier readers can read new data | all prior readers |
| FULL_TRANSITIVE | both directions across history | full release matrix |
| NONE | skip compatibility enforcement | only for exceptional approved cases |

This table is conceptual; the exact meaning and enforcement are registry-specific. In particular, a non-transitive mode may compare only with the immediately previous version. Treat compatibility success as a **schema-level** check, not proof of application semantic compatibility.

## 6. Synthetic schema evolution fixtures

### Avro v1

```json
{"type":"record","name":"Order","namespace":"sre.ch59","fields":[
  {"name":"id","type":"string"},
  {"name":"amount","type":"double"}
]}
```

### Avro v2 (added optional field with default)

```json
{"type":"record","name":"Order","namespace":"sre.ch59","fields":[
  {"name":"id","type":"string"},
  {"name":"amount","type":"double"},
  {"name":"currency","type":["null","string"],"default":null}
]}
```

For Avro, a new reader can resolve old records when the new field has an appropriate default; actual compatibility must still be checked by the chosen registry and reader.

### Protobuf v1/v2

```proto
syntax = "proto3";
package sre.ch59;
message Order {
  string id = 1;
  double amount = 2;
  // v2 adds: optional string currency = 3;
}
```

Never reuse field number 3 after removing it; reserve deleted field numbers and names. The `optional` keyword and presence semantics depend on Protobuf language/version/toolchain support.

### JSON Schema v1/v2

```json
{
  "$schema":"https://json-schema.org/draft/2020-12/schema",
  "type":"object",
  "properties":{
    "id":{"type":"string"},
    "amount":{"type":"number"},
    "currency":{"type":["string","null"]}
  },
  "required":["id","amount"],
  "additionalProperties":false
}
```

This JSON Schema is a synthetic v2 example; actual registry support for drafts and compatibility rules must be checked. With `additionalProperties:false`, an old strict consumer schema may reject records containing the new `currency` property even if new consumers accept old data.

## 7. Subject naming and key/value governance

- Topic-name subject strategies often distinguish `topic-key` and `topic-value`.
- Record-name strategies can share record subjects across topics; governance must prevent unintended coupling.
- Topic-record-name strategies can scope by both topic and record.
- Schema references and compatibility rules can be subject- and implementation-specific.

Document subject owner, environment, serialization format, retention, data classification, compatibility policy, rollout and rollback for each critical stream.

## 8. Kubernetes/Strimzi and registry preflight

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,kafkaconnect,pods,svc,networkpolicy -o wide
kubectl -n kafka-lab get events --sort-by=.metadata.creationTimestamp
kubectl -n kafka-lab get endpointslices
kubectl api-resources | grep -Ei 'kafkaconnect|kafkaconnector'
```

Deploy the selected registry using its supported Kubernetes distribution and operator/Helm manifests in a **separate reviewed step**. Strimzi does not automatically deploy a general-purpose schema registry for every Kafka cluster. Avoid assuming a particular vendor REST endpoint is universally supported.

## 9. Registry API example (implementation-specific)

For a registry that implements the commonly used Schema Registry compatibility API, read-only examples might look like:

```bash
# Approved local test endpoint only; replace host and authentication.
REGISTRY_URL=http://127.0.0.1:8081
curl -fsS "$REGISTRY_URL/subjects"
curl -fsS "$REGISTRY_URL/subjects/sre-ch59-orders-value/versions"
curl -fsS "$REGISTRY_URL/config/sre-ch59-orders-value"
```

These URLs are **not portable across all registry products**. Localhost port-forward is not an authentication substitute. Subject responses may reveal schema details; redact appropriately. Schema registration and compatibility test POSTs should run only in an isolated CI/test registry with approved credentials.

## 10. Twenty Kubernetes-first schema labs

### Lab 01 — Approve schema governance charter

**Objective and procedure:** Define event owner, subject strategy, compatibility policy, PII classification, schema registry operator and rollback authority.

**Expected evidence:** Registry implementation/version, Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC command/API response, subject/version, expected/observed compatibility, TLS/ACL review, rollback/abort and independent reviewer. Mark **Pending** until executed. Breaking schema registration, compatibility mode mutation and registry failover remain **Tabletop** without approved isolated infrastructure.

### Lab 02 — Inventory Kubernetes Kafka and Connect

**Objective and procedure:** Inspect Strimzi Kafka/KafkaConnect CRDs, KRaft health, Pods, Services, NetworkPolicies and client identities.

**Expected evidence:** Registry implementation/version, Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC command/API response, subject/version, expected/observed compatibility, TLS/ACL review, rollback/abort and independent reviewer. Mark **Pending** until executed. Breaking schema registration, compatibility mode mutation and registry failover remain **Tabletop** without approved isolated infrastructure.

### Lab 03 — Select schema registry implementation

**Objective and procedure:** Compare registry API/protocol, HA, storage, TLS/auth, schema references and deployment ownership; note registry is not built into Apache Kafka.

**Expected evidence:** Registry implementation/version, Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC command/API response, subject/version, expected/observed compatibility, TLS/ACL review, rollback/abort and independent reviewer. Mark **Pending** until executed. Breaking schema registration, compatibility mode mutation and registry failover remain **Tabletop** without approved isolated infrastructure.

### Lab 04 — Inspect registry network and TLS

**Objective and procedure:** Review Service/Ingress, DNS, cert SAN, trust chain, NetworkPolicy and egress policy.

**Expected evidence:** Registry implementation/version, Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC command/API response, subject/version, expected/observed compatibility, TLS/ACL review, rollback/abort and independent reviewer. Mark **Pending** until executed. Breaking schema registration, compatibility mode mutation and registry failover remain **Tabletop** without approved isolated infrastructure.

### Lab 05 — Inspect registry RBAC and authorization

**Objective and procedure:** Validate subject-level access, API credentials, service identities, secret rotation and audit logs.

**Expected evidence:** Registry implementation/version, Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC command/API response, subject/version, expected/observed compatibility, TLS/ACL review, rollback/abort and independent reviewer. Mark **Pending** until executed. Breaking schema registration, compatibility mode mutation and registry failover remain **Tabletop** without approved isolated infrastructure.

### Lab 06 — Define subject naming strategy

**Objective and procedure:** Review topic-value/topic-key/record-name strategies, schema references and collision risks.

**Expected evidence:** Registry implementation/version, Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC command/API response, subject/version, expected/observed compatibility, TLS/ACL review, rollback/abort and independent reviewer. Mark **Pending** until executed. Breaking schema registration, compatibility mode mutation and registry failover remain **Tabletop** without approved isolated infrastructure.

### Lab 07 — Define Avro evolution fixture

**Objective and procedure:** Create synthetic v1/v2 records with added field and default; validate writer/reader resolution.

**Expected evidence:** Registry implementation/version, Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC command/API response, subject/version, expected/observed compatibility, TLS/ACL review, rollback/abort and independent reviewer. Mark **Pending** until executed. Breaking schema registration, compatibility mode mutation and registry failover remain **Tabletop** without approved isolated infrastructure.

### Lab 08 — Define Protobuf evolution fixture

**Objective and procedure:** Create synthetic v1/v2 with stable field numbers; review reserved field numbers/names.

**Expected evidence:** Registry implementation/version, Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC command/API response, subject/version, expected/observed compatibility, TLS/ACL review, rollback/abort and independent reviewer. Mark **Pending** until executed. Breaking schema registration, compatibility mode mutation and registry failover remain **Tabletop** without approved isolated infrastructure.

### Lab 09 — Define JSON Schema evolution fixture

**Objective and procedure:** Review required fields, additionalProperties, type constraints and compatibility behavior.

**Expected evidence:** Registry implementation/version, Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC command/API response, subject/version, expected/observed compatibility, TLS/ACL review, rollback/abort and independent reviewer. Mark **Pending** until executed. Breaking schema registration, compatibility mode mutation and registry failover remain **Tabletop** without approved isolated infrastructure.

### Lab 10 — Compare compatibility modes

**Objective and procedure:** Test planned BACKWARD/FORWARD/FULL, transitive variants and NONE in a disposable registry.

**Expected evidence:** Registry implementation/version, Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC command/API response, subject/version, expected/observed compatibility, TLS/ACL review, rollback/abort and independent reviewer. Mark **Pending** until executed. Breaking schema registration, compatibility mode mutation and registry failover remain **Tabletop** without approved isolated infrastructure.

### Lab 11 — Validate schema registration policy

**Objective and procedure:** Plan CI schema lint, subject ownership, compatibility API check, review and immutable release artifact.

**Expected evidence:** Registry implementation/version, Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC command/API response, subject/version, expected/observed compatibility, TLS/ACL review, rollback/abort and independent reviewer. Mark **Pending** until executed. Breaking schema registration, compatibility mode mutation and registry failover remain **Tabletop** without approved isolated infrastructure.

### Lab 12 — Validate serializer/deserializer compatibility

**Objective and procedure:** Review registry URL, TLS/SASL, schema ID wire format, cache behavior and client versions.

**Expected evidence:** Registry implementation/version, Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC command/API response, subject/version, expected/observed compatibility, TLS/ACL review, rollback/abort and independent reviewer. Mark **Pending** until executed. Breaking schema registration, compatibility mode mutation and registry failover remain **Tabletop** without approved isolated infrastructure.

### Lab 13 — Review schema ID and disaster recovery

**Objective and procedure:** Assess registry storage backup, subject/config export, cross-region replication and ID preservation.

**Expected evidence:** Registry implementation/version, Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC command/API response, subject/version, expected/observed compatibility, TLS/ACL review, rollback/abort and independent reviewer. Mark **Pending** until executed. Breaking schema registration, compatibility mode mutation and registry failover remain **Tabletop** without approved isolated infrastructure.

### Lab 14 — Review CDC envelope and tombstones

**Objective and procedure:** Check Debezium before/after/source/op, delete/tombstone, nullable fields and sink handling.

**Expected evidence:** Registry implementation/version, Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC command/API response, subject/version, expected/observed compatibility, TLS/ACL review, rollback/abort and independent reviewer. Mark **Pending** until executed. Breaking schema registration, compatibility mode mutation and registry failover remain **Tabletop** without approved isolated infrastructure.

### Lab 15 — Review Kafka Connect converter settings

**Objective and procedure:** Compare AvroConverter, ProtobufConverter, JsonSchemaConverter availability and plugin packaging.

**Expected evidence:** Registry implementation/version, Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC command/API response, subject/version, expected/observed compatibility, TLS/ACL review, rollback/abort and independent reviewer. Mark **Pending** until executed. Breaking schema registration, compatibility mode mutation and registry failover remain **Tabletop** without approved isolated infrastructure.

### Lab 16 — Test consumer rollback matrix

**Objective and procedure:** Use synthetic v1/v2 compatibility worksheet to predict old consumer/new producer behavior.

**Expected evidence:** Registry implementation/version, Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC command/API response, subject/version, expected/observed compatibility, TLS/ACL review, rollback/abort and independent reviewer. Mark **Pending** until executed. Breaking schema registration, compatibility mode mutation and registry failover remain **Tabletop** without approved isolated infrastructure.

### Lab 17 — Model breaking schema change

**Objective and procedure:** Rehearse rejected registration, CI failure, producer rollback and communication without disabling compatibility.

**Expected evidence:** Registry implementation/version, Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC command/API response, subject/version, expected/observed compatibility, TLS/ACL review, rollback/abort and independent reviewer. Mark **Pending** until executed. Breaking schema registration, compatibility mode mutation and registry failover remain **Tabletop** without approved isolated infrastructure.

### Lab 18 — Model registry outage

**Objective and procedure:** Assess producer cached schema IDs, new registration failure, consumer cache, SLO and failover.

**Expected evidence:** Registry implementation/version, Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC command/API response, subject/version, expected/observed compatibility, TLS/ACL review, rollback/abort and independent reviewer. Mark **Pending** until executed. Breaking schema registration, compatibility mode mutation and registry failover remain **Tabletop** without approved isolated infrastructure.

### Lab 19 — Model security incident

**Objective and procedure:** Review leaked registry token, unauthorized subject changes, schema poisoning and audit response.

**Expected evidence:** Registry implementation/version, Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC command/API response, subject/version, expected/observed compatibility, TLS/ACL review, rollback/abort and independent reviewer. Mark **Pending** until executed. Breaking schema registration, compatibility mode mutation and registry failover remain **Tabletop** without approved isolated infrastructure.

### Lab 20 — Complete independent schema acceptance

**Objective and procedure:** Capture evidence, compatibility matrix, rollback, 100-point rubric and independent security review.

**Expected evidence:** Registry implementation/version, Kafka/Strimzi/Connect versions, approved Kubernetes context, UTC command/API response, subject/version, expected/observed compatibility, TLS/ACL review, rollback/abort and independent reviewer. Mark **Pending** until executed. Breaking schema registration, compatibility mode mutation and registry failover remain **Tabletop** without approved isolated infrastructure.

## 11. Read-only registry and Kafka inventory verifier

Save as `verify-ch59.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
NS=kafka-lab
echo '[1/9] Context'; kubectl config current-context
echo '[2/9] Kafka/Connect'; kubectl -n "$NS" get kafka,kafkanodepool,kafkaconnect -o wide
echo '[3/9] Pods'; kubectl -n "$NS" get pods -o wide
echo '[4/9] Services'; kubectl -n "$NS" get svc,endpointslices
echo '[5/9] NetworkPolicies'; kubectl -n "$NS" get networkpolicy
echo '[6/9] Events'; kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo '[7/9] KafkaConnect schema'; kubectl explain kafkaconnect.spec
echo '[8/9] Registry service inventory (best effort)'
kubectl -n "$NS" get svc -o name | grep -Ei 'schema|registry' || echo 'UNKNOWN: no registry service name matched'
echo '[9/9] Registry HTTP API (optional, approved endpoint)'
if [[ -n "${REGISTRY_URL:-}" ]]; then
  curl --fail --silent --show-error --max-time 5 "$REGISTRY_URL/subjects"
else
  echo 'SKIPPED: REGISTRY_URL unset; do not infer registry health'
fi
echo 'PASS: read-only Kubernetes and optional registry inventory.'
echo 'NOT PROVEN: schema compatibility, TLS/auth security, DR restore, serializer correctness or independent review.'
```

Run `chmod +x verify-ch59.sh && ./verify-ch59.sh | tee evidence-ch59/preflight.txt`. The optional API call assumes an implementation exposing `/subjects` and an approved authenticated path; do not put credentials in the shell command or evidence.

## 12. Twelve schema failure scenarios

### Scenario 1 — Backward compatibility check fails

**Diagnosis:** Inspect added required fields, defaults, unions and writer-reader resolution. Correlate registry subject history, CI compatibility gate, serializer/deserializer version, Kubernetes Pod/Service/TLS, Connect converter status, DLQ and consumer SLO. **Response:** Block breaking deployment, restore reviewed schema/registry config and reconcile affected event IDs. **Evidence:** UTC timeline, sanitized schema diff, rollback and independent review.

### Scenario 2 — Protobuf field number reused

**Diagnosis:** Block change; compare wire semantics and reserved field policy. Correlate registry subject history, CI compatibility gate, serializer/deserializer version, Kubernetes Pod/Service/TLS, Connect converter status, DLQ and consumer SLO. **Response:** Block breaking deployment, restore reviewed schema/registry config and reconcile affected event IDs. **Evidence:** UTC timeline, sanitized schema diff, rollback and independent review.

### Scenario 3 — JSON Schema required property breaks old payloads

**Diagnosis:** Review required, defaults, additionalProperties and producer/consumer contract. Correlate registry subject history, CI compatibility gate, serializer/deserializer version, Kubernetes Pod/Service/TLS, Connect converter status, DLQ and consumer SLO. **Response:** Block breaking deployment, restore reviewed schema/registry config and reconcile affected event IDs. **Evidence:** UTC timeline, sanitized schema diff, rollback and independent review.

### Scenario 4 — Subject naming collision

**Diagnosis:** Review topic-key/value vs record-name strategy and governance ownership. Correlate registry subject history, CI compatibility gate, serializer/deserializer version, Kubernetes Pod/Service/TLS, Connect converter status, DLQ and consumer SLO. **Response:** Block breaking deployment, restore reviewed schema/registry config and reconcile affected event IDs. **Evidence:** UTC timeline, sanitized schema diff, rollback and independent review.

### Scenario 5 — Registry unavailable during deployment

**Diagnosis:** Inspect DNS, TLS, Service, storage, HA, cached schema behavior and SLO. Correlate registry subject history, CI compatibility gate, serializer/deserializer version, Kubernetes Pod/Service/TLS, Connect converter status, DLQ and consumer SLO. **Response:** Block breaking deployment, restore reviewed schema/registry config and reconcile affected event IDs. **Evidence:** UTC timeline, sanitized schema diff, rollback and independent review.

### Scenario 6 — Consumer sees unknown schema ID

**Diagnosis:** Review serializer wire format, registry cluster mismatch, replication and ID mapping. Correlate registry subject history, CI compatibility gate, serializer/deserializer version, Kubernetes Pod/Service/TLS, Connect converter status, DLQ and consumer SLO. **Response:** Block breaking deployment, restore reviewed schema/registry config and reconcile affected event IDs. **Evidence:** UTC timeline, sanitized schema diff, rollback and independent review.

### Scenario 7 — Connect converter class not found

**Diagnosis:** Inspect plugin image, converter dependencies and Connect classloader isolation. Correlate registry subject history, CI compatibility gate, serializer/deserializer version, Kubernetes Pod/Service/TLS, Connect converter status, DLQ and consumer SLO. **Response:** Block breaking deployment, restore reviewed schema/registry config and reconcile affected event IDs. **Evidence:** UTC timeline, sanitized schema diff, rollback and independent review.

### Scenario 8 — CDC tombstone rejected by sink

**Diagnosis:** Review null value handling, compaction, delete semantics and converter config. Correlate registry subject history, CI compatibility gate, serializer/deserializer version, Kubernetes Pod/Service/TLS, Connect converter status, DLQ and consumer SLO. **Response:** Block breaking deployment, restore reviewed schema/registry config and reconcile affected event IDs. **Evidence:** UTC timeline, sanitized schema diff, rollback and independent review.

### Scenario 9 — PII exposed in schema defaults or docs

**Diagnosis:** Audit schema content, metadata, ACLs and redaction. Correlate registry subject history, CI compatibility gate, serializer/deserializer version, Kubernetes Pod/Service/TLS, Connect converter status, DLQ and consumer SLO. **Response:** Block breaking deployment, restore reviewed schema/registry config and reconcile affected event IDs. **Evidence:** UTC timeline, sanitized schema diff, rollback and independent review.

### Scenario 10 — Registry ACL denies producer registration

**Diagnosis:** Check subject-level authorization and dedicated service identity. Correlate registry subject history, CI compatibility gate, serializer/deserializer version, Kubernetes Pod/Service/TLS, Connect converter status, DLQ and consumer SLO. **Response:** Block breaking deployment, restore reviewed schema/registry config and reconcile affected event IDs. **Evidence:** UTC timeline, sanitized schema diff, rollback and independent review.

### Scenario 11 — Breaking schema bypasses CI

**Diagnosis:** Investigate review gates, compatibility mode change and audit logs. Correlate registry subject history, CI compatibility gate, serializer/deserializer version, Kubernetes Pod/Service/TLS, Connect converter status, DLQ and consumer SLO. **Response:** Block breaking deployment, restore reviewed schema/registry config and reconcile affected event IDs. **Evidence:** UTC timeline, sanitized schema diff, rollback and independent review.

### Scenario 12 — Failover registry has different schema IDs

**Diagnosis:** Validate registry replication/restore semantics and producer/consumer compatibility. Correlate registry subject history, CI compatibility gate, serializer/deserializer version, Kubernetes Pod/Service/TLS, Connect converter status, DLQ and consumer SLO. **Response:** Block breaking deployment, restore reviewed schema/registry config and reconcile affected event IDs. **Evidence:** UTC timeline, sanitized schema diff, rollback and independent review.

## 13. Eight production schema runbooks

### Runbook A — Schema compatibility rejection

**Trigger and first response:** Inspect subject, version, mode, breaking fields, rollback and consumer matrix. **Safety:** Never disable compatibility globally to unblock a deployment, delete production subjects, leak schema credentials, bypass TLS/ACL or assume cross-registry schema ID equivalence. **Exit:** Proven producer/consumer compatibility, secure registry service, DLQ and event-ledger reconciliation, restored SLO and corrective-action owner.

### Runbook B — Serializer/deserializer failure

**Trigger and first response:** Check schema ID, wire format, registry URL, TLS, cache, plugin and client version. **Safety:** Never disable compatibility globally to unblock a deployment, delete production subjects, leak schema credentials, bypass TLS/ACL or assume cross-registry schema ID equivalence. **Exit:** Proven producer/consumer compatibility, secure registry service, DLQ and event-ledger reconciliation, restored SLO and corrective-action owner.

### Runbook C — Registry outage

**Trigger and first response:** Check Kubernetes Service/Pods, HA, storage, auth, network, cache behavior and recovery SLO. **Safety:** Never disable compatibility globally to unblock a deployment, delete production subjects, leak schema credentials, bypass TLS/ACL or assume cross-registry schema ID equivalence. **Exit:** Proven producer/consumer compatibility, secure registry service, DLQ and event-ledger reconciliation, restored SLO and corrective-action owner.

### Runbook D — Protobuf field evolution incident

**Trigger and first response:** Audit tag numbers, reserved fields, optional/repeated semantics and backward plan. **Safety:** Never disable compatibility globally to unblock a deployment, delete production subjects, leak schema credentials, bypass TLS/ACL or assume cross-registry schema ID equivalence. **Exit:** Proven producer/consumer compatibility, secure registry service, DLQ and event-ledger reconciliation, restored SLO and corrective-action owner.

### Runbook E — JSON Schema evolution incident

**Trigger and first response:** Review required properties, type unions, additionalProperties and consumer expectations. **Safety:** Never disable compatibility globally to unblock a deployment, delete production subjects, leak schema credentials, bypass TLS/ACL or assume cross-registry schema ID equivalence. **Exit:** Proven producer/consumer compatibility, secure registry service, DLQ and event-ledger reconciliation, restored SLO and corrective-action owner.

### Runbook F — Connect converter and CDC envelope failure

**Trigger and first response:** Inspect converter plugin, Debezium schema, null/tombstone and DLQ integrity. **Safety:** Never disable compatibility globally to unblock a deployment, delete production subjects, leak schema credentials, bypass TLS/ACL or assume cross-registry schema ID equivalence. **Exit:** Proven producer/consumer compatibility, secure registry service, DLQ and event-ledger reconciliation, restored SLO and corrective-action owner.

### Runbook G — Schema governance and unauthorized change

**Trigger and first response:** Audit subject ACL, token, change approval, compatibility settings and incident containment. **Safety:** Never disable compatibility globally to unblock a deployment, delete production subjects, leak schema credentials, bypass TLS/ACL or assume cross-registry schema ID equivalence. **Exit:** Proven producer/consumer compatibility, secure registry service, DLQ and event-ledger reconciliation, restored SLO and corrective-action owner.

### Runbook H — Registry DR and acceptance

**Trigger and first response:** Verify backup/restore, subject/config parity, schema ID handling, client recovery and signoff. **Safety:** Never disable compatibility globally to unblock a deployment, delete production subjects, leak schema credentials, bypass TLS/ACL or assume cross-registry schema ID equivalence. **Exit:** Proven producer/consumer compatibility, secure registry service, DLQ and event-ledger reconciliation, restored SLO and corrective-action owner.

## 14. Evidence package

```text
evidence-ch59/
  approved-schema-governance-charter.md
  context-version-registry-implementation.md
  preflight.txt
  registry-platform-selection.md
  registry-tls-networkpolicy.md
  registry-auth-rbac-audit.md
  subject-naming-governance.md
  avro-v1-v2-fixtures.json
  protobuf-v1-v2-fixtures.proto
  jsonschema-v1-v2-fixtures.json
  compatibility-mode-matrix.csv
  ci-schema-gate.md
  serializer-deserializer-review.md
  registry-backup-restore-id-policy.md
  debezium-envelope-tombstones.md
  connect-converter-plugin-review.md
  consumer-rollback-matrix.md
  breaking-change-tabletop.md
  registry-outage-tabletop.md
  registry-security-tabletop.md
  accepted-processed-event-ledger.csv
  independent-technical-security-review.md
  readiness-scorecard.md
```

Every artifact must record exact implementation/version, source, UTC timestamp, expected/observed behavior, subject/version, redaction, owner, abort/rollback and reviewer. No live schema compatibility claim is made without actual test evidence.

## 15. 100-point schema governance assessment

| Domain | Points | Critical |
|---|---:|---|
| Governance, ownership, subject strategy | 10 | Yes |
| Registry HA, TLS, ACL and Kubernetes isolation | 15 | Yes |
| Avro evolution and reader/writer matrix | 10 | Yes |
| Protobuf tag evolution and reserved fields | 10 | Yes |
| JSON Schema evolution and consumer constraints | 10 | Yes |
| Compatibility CI, release/rollback controls | 15 | Yes |
| Kafka Connect/CDC converters and tombstones | 10 | Yes |
| Registry backup/DR and schema ID handling | 10 | Yes |
| Observability, runbooks and incident readiness | 5 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with every critical gate evidenced. **Automatic Fail:** fabricated compatibility testing, unreviewed breaking schema, public unauthenticated registry, leaked credentials, subject deletion, invalid cross-registry schema ID assumptions, unhandled CDC tombstones or absent independent review.

## 16. Cleanup, references and next chapter

Remove only chapter-owned synthetic subjects and test clients using approved registry lifecycle procedures after evidence retention. Never delete production subjects, schema histories, Connect internal topics, offsets, PVCs or Secrets.

**References:** [Apache Avro Specification](https://avro.apache.org/docs/current/specification/), [Protocol Buffers Language Guide](https://protobuf.dev/programming-guides/proto3/), [JSON Schema](https://json-schema.org/), [Apache Kafka Connect](https://kafka.apache.org/documentation/#connect), [Strimzi Documentation](https://strimzi.io/documentation/).

**Next:** Chapter 060 — Kafka Connect, CDC and Schema Management Production Reliability Capstone.

---

**Verification boundary:** Publication establishes document availability only. Live registry deployment, compatibility tests, serializer/converter checks, DR recovery and independent technical/security review remain Pending.
