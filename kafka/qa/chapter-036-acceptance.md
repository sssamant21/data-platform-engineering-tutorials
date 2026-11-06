# Chapter 036 acceptance contract

The manuscript is published separately from test implementation. A successful runtime JSON report certifies only the supported disposable-lab assertions below. It does not complete the manuscript's full production assessment or constitute enterprise certification.

Run `python kafka/qa/run_chapter_036.py` against an isolated `kind-kafka-qa` cluster with the persistent observability fixture and Strimzi 0.47.0. The runner installs ten content-pinned Prometheus Operator CRDs after validating the disposable context and all downloaded hashes. Both the dedicated workflow and changed-chapter orchestrator use this same entry point.

## Supported measurable checks

- Kafka 4.0.0 / Strimzi 0.47.0 / KRaft, three dual-role brokers, RF 3 and minimum ISR 2, persistent bound broker PVCs and filesystem headroom. Existing successful fixtures remain intact.
- A separately created monitoring namespace has Pod Security `restricted` admission, including an actual server-side rejected privileged Pod dry run. Namespace/object UIDs guard adoption, updates, forwards and cleanup.
- Prometheus Operator is restricted to its monitoring namespace. Its Secret watch cannot access Kafka identity Secrets. Prometheus discovery roles read Pods, Services and endpoint metadata only; actual impersonated authorization checks deny Secret reads in both namespaces. Non-API workloads have no API tokens.
- Actual Operator-created Prometheus and Alertmanager StatefulSets, one replica each; Prometheus uses a bound `standard` PVC. Prometheus retention is 1 hour / 100 MB, remote write is absent, and admin mutation APIs are disabled.
- Exactly six healthy, recently scraped targets: three actual broker Pod IPs, Strimzi operator, monitoring operator, and one disposable client target. Missing or nonfinite required metrics fail rather than become zero.
- Twelve deterministic 1 KiB records, explicit partition/offset acknowledgements, exact consumer IDs and values, processing then synchronous commit, independently queried final group offsets of four per partition, full ISR and KRaft Admin proof. Client counters, lag and real timing gauges in Prometheus must match that proof. Unknown client lag is absent before verification.
- Broker ISR and KRaft metrics agree with Kafka Admin; direct exporter type metadata proves request p99 is a gauge. JVM heap and actual GC series cover all brokers. Configured KRaft voter count is not treated as proof of live quorum.
- Actual pinned `promtool check rules` and `promtool test rules` Jobs cover healthy, pending/firing/resolved, absent target, missing broker/metric, UnderMinISR and invalid KRaft signals. Actual recording-rule results retain per-broker identity. Percentiles are neither averaged nor passed to histogram quantile.
- Authenticated Grafana API login, provisioned readonly datasource, real datasource health, provisioned dashboard/units, and actual Prometheus-backed numeric query frames showing three brokers and three p99 values.
- Only the uniquely owned synthetic target Deployment is scaled down and restored. Observe actual Prometheus pending and firing state, Alertmanager active state, authenticated local webhook firing and resolved receipts, and replacement target Pod UID. A separate readonly Kafka Admin probe checks ISR/quorum throughout. Brokers are never stopped; broker UIDs and restart counts remain unchanged.
- Bounded API/download/Job/rollout/forward timeouts, loopback-only forwards, finite cardinality/sample budget, own-resource cleanup, sanitized JSON and diagnostics. No broker PVC or segment file is deleted or edited.

## Pins and source provenance

Operator v0.94.2 is pinned to immutable commit `0db90444c4e6fa5672be5bf7d2b15ca9dd1c5ace`; every CRD must match its Git blob SHA-1 before any CRD mutation, with SHA-256 saved in evidence. Its tagged compatibility documentation recommends the tested Prometheus 3.14.0 and Alertmanager 0.34.0 used here. Grafana is pinned to 13.3.0. Runtime binary/API versions must match; the existence of a release tag alone does not pass validation.

Sources: [Operator compatibility](https://github.com/prometheus-operator/prometheus-operator/blob/v0.94.2/Documentation/getting-started/compatibility.md), [tagged defaults](https://github.com/prometheus-operator/prometheus-operator/blob/v0.94.2/pkg/operator/defaults.go), [Strimzi PodMonitor example](https://github.com/strimzi/strimzi-kafka-operator/blob/0.47.0/examples/metrics/prometheus-install/strimzi-pod-monitor.yaml), [Kafka 4 KRaft metrics](https://github.com/apache/kafka/blob/4.0.0/raft/src/main/java/org/apache/kafka/raft/internals/KafkaRaftMetrics.java), [Grafana release](https://github.com/grafana/grafana/releases/tag/v13.3.0).

## Evidence and limitations

The uploaded `chapter-036-runtime.json` contains check statuses, source reconciliation, target identities/scrape timestamps, rule/Grafana/PVC/security results, authenticated local alert lifecycle, independent Kafka health and explicit limitations. CRD provenance, source hashes, direct exporter samples, promtool logs and Kubernetes diagnostics accompany it. Credentials and encoded authorization headers are redacted before upload.

Single-host kind cannot qualify CSI/provider IOPS or latency, disk/node/AZ loss, multi-replica monitoring availability, storage capacity enforcement, remote monitoring durability, attributed page cache or production node/cAdvisor coverage. Default kind networking does not establish enforced network policy. Local HTTP/Bearer and Grafana basic authentication do not qualify production TLS/SSO, external routing, human paging or on-call response. Synthetic processing does not prove external business durability. No long soak, production capacity or independent acceptance review is claimed. Full assessment remains `NOT_YET_ACCEPTED`, score null; enterprise status `NOT_CERTIFIED` even when supported runtime checks pass.
