# Chapter 083 — Kafka Performance Benchmarking, Load Testing and Capacity Validation Engineering

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 17 — Capacity Planning, Performance and FinOps (3/5)  
**Primary platform:** Kubernetes + Strimzi Kafka in KRaft mode, EKS client generators; AWS MSK comparison  
**Prerequisites:** Chapters 001–082, Kafka metrics, Kubernetes quotas and workload isolation  
**Publication:** Published · **Live lab execution:** Pending · **Independent technical/security review:** Pending

> **Safety:** Benchmarking is resource-intensive. Never direct stress traffic at production, customer topics, shared clusters or real patient data. Use isolated non-PHI test topics, rate limits, quotas, cost ceilings, explicit stop conditions and independent approval. Benchmark success requires acknowledged event correctness, not just MB/s.

## 1. Mission and learning outcomes

Design reproducible Kafka benchmarks that measure throughput, latency, durability and recovery under realistic producer/consumer demand. Establish a **capacity envelope** across broker CPU, disk IOPS/throughput, network/AZ traffic, KRaft metadata, partition skew and consumer freshness. Translate results into Strimzi/MSK scaling decisions and SRE acceptance gates.

Readers will learn to distinguish offered load from successfully acknowledged throughput, isolate load-generator bottlenecks, measure P95/P99 and tail latency, preserve ISR/minISR and compare cost per useful GB processed.

## 2. Benchmark architecture

```text
Git-pinned workload + synthetic non-PHI payload corpus
                    |
        EKS producer load generators
                    |
     Kafka leaders / follower replication
       |         |           |
      CPU     PVC/IOPS    network/AZ
       |         |           |
     KRaft metadata / ISR / controller quorum
                    |
         EKS consumer processors
                    |
         event-ID reconciliation ledger
                    |
  Prometheus/Grafana + CI evidence + cost model
                    |
        abort gate + independent review
```

Use dedicated EKS node resources for load generators so client CPU throttling is not mistaken for broker saturation. Protect the cluster with network, storage and Kubernetes quotas.

## 3. Benchmark experiment design

| Variable | Record | Why |
|---|---|---|
| Payload | distribution, schema, non-PHI fixture | realism |
| Keys | cardinality and hot-key skew | partition imbalance |
| Producer | acks, idempotence, batch, linger, compression | durability and latency |
| Topic | partitions, RF, minISR, retention | replication/metadata |
| Consumer | groups, concurrency, processing cost | freshness |
| Environment | AZ, broker count, PVC IOPS/MBps, Kafka version | reproducibility |
| Load profile | warm-up, steady, burst, cooldown | valid comparison |
| Success | unique acknowledged IDs and consumed IDs | correctness |
| Abort | ISR/quorum, P99, lag, disk/network, cost | safety |

Avoid tuning `acks=0` to claim higher throughput when the production contract requires `acks=all`. Compare only equivalent durability configurations.

## 4. Measurement semantics and SLOs

- **Offered throughput:** bytes/events the generator attempted to send.
- **Acknowledged throughput:** unique events successfully acknowledged by Kafka.
- **Processed throughput:** unique events consumed and accepted by the application.
- **Producer P99:** latency from send to acknowledged completion; distinguish retries.
- **End-to-end freshness:** event creation to downstream processing.
- **Backlog drain time:** time to return to steady lag after burst.
- **Data correctness:** count missing and duplicate event IDs separately.

A benchmark with a high send rate but lost acknowledged events is **failed**, not a capacity pass.

## 5. Isolated workload phases

1. **Preflight:** approvals, dedicated topic, namespace, quotas, metrics and baseline.
2. **Warm-up:** stabilize connections, JVM, cache and producer batching; exclude warm-up from steady-state score.
3. **Steady:** bounded workload for enough duration to observe stable P99 and disk/network metrics.
4. **Burst:** apply approved short peak; measure lag and resource reserve.
5. **Recovery:** return to baseline, measure consumer drain and ISR recovery.
6. **Cooldown:** confirm no lingering jobs, quotas, degraded ISR or excessive disk use.
7. **Review:** compare with baseline, repeatability, confidence and correctness.

Do not change multiple independent variables at once; repeat runs and record environmental noise.

## 6. Kafka producer and consumer tooling

Kafka includes `kafka-producer-perf-test.sh` and `kafka-consumer-perf-test.sh` in many distributions. Options differ by Kafka version; confirm `--help` before execution.

**Illustrative isolated-only producer invocation** (not executed):

```bash
kafka-producer-perf-test.sh \
  --topic capacity-lab-only \
  --num-records 10000 \
  --record-size 1024 \
  --throughput 1000 \
  --producer-props bootstrap.servers="$BOOTSTRAP" \
    acks=all enable.idempotence=true \
    security.protocol=SASL_SSL \
    sasl.mechanism=SCRAM-SHA-512
```

Actual authentication often requires `sasl.jaas.config`, TLS trust and secret-mounted client configuration; never print credentials. For stronger reproducibility use `--producer.config` if supported by the installed tool or a custom producer with authenticated properties. **This example is incomplete until the site's authentication configuration is supplied.**

## 7. Broker and EKS metrics

Collect broker BytesIn/OutPerSec, Produce/Fetch request latency, RequestHandlerAvgIdlePercent, NetworkProcessorAvgIdlePercent, UnderReplicatedPartitions, OfflinePartitionsCount, replica fetch lag, disk utilization/latency, KRaft controller health, JVM GC and CPU. For EKS clients collect throttling, OOM, retries, P99, lag and synthetic event-ID outcomes.

Metric names and availability vary by exporter, Kafka and Strimzi version; inspect installed JMX mappings rather than assuming all series exist.

## 8. Throughput/latency capacity envelope

Define a valid capacity point only when **all** hold:

- acknowledged throughput meets target and producer errors/retries are acceptable;
- P95/P99 producer and consumer freshness meet approved SLO;
- no unexplained missing acknowledged event IDs;
- KRaft quorum stable and ISR/minISR healthy;
- disk/network/CPU headroom supports the modeled failure case;
- no concurrent untracked reassignments or maintenance;
- workload generator not saturated.

Report a table of load rate, acknowledged MB/s, processed MB/s, P99, lag, CPU, disk MB/s/IOPS, ISR and abort status. Identify the first constraint reached, not merely the maximum send rate.

## 9. Disk, partition and KRaft bottlenecks

Partition increases can improve parallelism but also increase controller metadata, leader movement, file descriptors and small-segment overhead. Reassignment, recovery, compaction and replication may consume more disk/network than steady client traffic.

Benchmark normal operation and **model** N-1/AZ failure; fault injection requires a separate approved isolated exercise.

## 10. Strimzi versus MSK validation

**Strimzi:** Pin KafkaNodePool role/size, Kubernetes requests/limits, PVC class/IOPS, rack placement and Strimzi version. Compare broker scale-out and disk upgrade options against measured bottlenecks.

**MSK:** Pin cluster type, instance, broker count, storage throughput, networking and quotas. Managed-service performance and pricing differ from Strimzi; never transfer an EKS benchmark result to MSK without revalidation.

## 11. Twenty Kubernetes-first performance labs

### Lab 01 — Approve benchmark charter

**Procedure:** Specify isolation, workload owner, traffic caps, duration, cost limit, SLO and abort criteria.

**Expected evidence:** UTC start/end, approved isolated environment, immutable Git SHA, Kafka/Strimzi/client versions, workload seed, input distribution, exact commands, baseline/peak, acknowledged and processed unique IDs, P99, lag, KRaft quorum, ISR, PVC/network/CPU metrics, abort/rollback, cost and independent reviewer. **Status: Pending** until executed. Failure-zone tests are **Tabletop** unless separately approved.

### Lab 02 — Record immutable baseline

**Procedure:** Capture Git SHA, Kafka/Strimzi/EKS versions, topic configs, PVC class and client images.

**Expected evidence:** UTC start/end, approved isolated environment, immutable Git SHA, Kafka/Strimzi/client versions, workload seed, input distribution, exact commands, baseline/peak, acknowledged and processed unique IDs, P99, lag, KRaft quorum, ISR, PVC/network/CPU metrics, abort/rollback, cost and independent reviewer. **Status: Pending** until executed. Failure-zone tests are **Tabletop** unless separately approved.

### Lab 03 — Instrument Kafka brokers

**Procedure:** Collect bytes-in/out, request latency, ISR, URP, offline partitions, CPU, disk and network.

**Expected evidence:** UTC start/end, approved isolated environment, immutable Git SHA, Kafka/Strimzi/client versions, workload seed, input distribution, exact commands, baseline/peak, acknowledged and processed unique IDs, P99, lag, KRaft quorum, ISR, PVC/network/CPU metrics, abort/rollback, cost and independent reviewer. **Status: Pending** until executed. Failure-zone tests are **Tabletop** unless separately approved.

### Lab 04 — Instrument producer clients

**Procedure:** Measure ack success, P50/P95/P99 latency, retries, throttling and errors.

**Expected evidence:** UTC start/end, approved isolated environment, immutable Git SHA, Kafka/Strimzi/client versions, workload seed, input distribution, exact commands, baseline/peak, acknowledged and processed unique IDs, P99, lag, KRaft quorum, ISR, PVC/network/CPU metrics, abort/rollback, cost and independent reviewer. **Status: Pending** until executed. Failure-zone tests are **Tabletop** unless separately approved.

### Lab 05 — Instrument consumer clients

**Procedure:** Measure fetch throughput, lag, freshness, rebalance, commits and processing errors.

**Expected evidence:** UTC start/end, approved isolated environment, immutable Git SHA, Kafka/Strimzi/client versions, workload seed, input distribution, exact commands, baseline/peak, acknowledged and processed unique IDs, P99, lag, KRaft quorum, ISR, PVC/network/CPU metrics, abort/rollback, cost and independent reviewer. **Status: Pending** until executed. Failure-zone tests are **Tabletop** unless separately approved.

### Lab 06 — Define synthetic payload corpus

**Procedure:** Choose approved non-PHI payload sizes, key cardinality, compression and schema.

**Expected evidence:** UTC start/end, approved isolated environment, immutable Git SHA, Kafka/Strimzi/client versions, workload seed, input distribution, exact commands, baseline/peak, acknowledged and processed unique IDs, P99, lag, KRaft quorum, ISR, PVC/network/CPU metrics, abort/rollback, cost and independent reviewer. **Status: Pending** until executed. Failure-zone tests are **Tabletop** unless separately approved.

### Lab 07 — Build baseline throughput test

**Procedure:** Run bounded isolated producer/consumer workload and record stable-state samples.

**Expected evidence:** UTC start/end, approved isolated environment, immutable Git SHA, Kafka/Strimzi/client versions, workload seed, input distribution, exact commands, baseline/peak, acknowledged and processed unique IDs, P99, lag, KRaft quorum, ISR, PVC/network/CPU metrics, abort/rollback, cost and independent reviewer. **Status: Pending** until executed. Failure-zone tests are **Tabletop** unless separately approved.

### Lab 08 — Evaluate batching and linger

**Procedure:** Compare producer batch.size and linger.ms without weakening delivery guarantees.

**Expected evidence:** UTC start/end, approved isolated environment, immutable Git SHA, Kafka/Strimzi/client versions, workload seed, input distribution, exact commands, baseline/peak, acknowledged and processed unique IDs, P99, lag, KRaft quorum, ISR, PVC/network/CPU metrics, abort/rollback, cost and independent reviewer. **Status: Pending** until executed. Failure-zone tests are **Tabletop** unless separately approved.

### Lab 09 — Evaluate compression codecs

**Procedure:** Measure throughput, CPU and compressed bytes under representative payloads.

**Expected evidence:** UTC start/end, approved isolated environment, immutable Git SHA, Kafka/Strimzi/client versions, workload seed, input distribution, exact commands, baseline/peak, acknowledged and processed unique IDs, P99, lag, KRaft quorum, ISR, PVC/network/CPU metrics, abort/rollback, cost and independent reviewer. **Status: Pending** until executed. Failure-zone tests are **Tabletop** unless separately approved.

### Lab 10 — Evaluate partition count

**Procedure:** Model or test parallelism, leader skew, KRaft metadata and ordering consequences.

**Expected evidence:** UTC start/end, approved isolated environment, immutable Git SHA, Kafka/Strimzi/client versions, workload seed, input distribution, exact commands, baseline/peak, acknowledged and processed unique IDs, P99, lag, KRaft quorum, ISR, PVC/network/CPU metrics, abort/rollback, cost and independent reviewer. **Status: Pending** until executed. Failure-zone tests are **Tabletop** unless separately approved.

### Lab 11 — Evaluate consumer parallelism

**Procedure:** Compare consumer count to partition count and downstream processing limits.

**Expected evidence:** UTC start/end, approved isolated environment, immutable Git SHA, Kafka/Strimzi/client versions, workload seed, input distribution, exact commands, baseline/peak, acknowledged and processed unique IDs, P99, lag, KRaft quorum, ISR, PVC/network/CPU metrics, abort/rollback, cost and independent reviewer. **Status: Pending** until executed. Failure-zone tests are **Tabletop** unless separately approved.

### Lab 12 — Test peak burst recovery

**Procedure:** Apply approved bounded peak and measure lag accumulation and drain time.

**Expected evidence:** UTC start/end, approved isolated environment, immutable Git SHA, Kafka/Strimzi/client versions, workload seed, input distribution, exact commands, baseline/peak, acknowledged and processed unique IDs, P99, lag, KRaft quorum, ISR, PVC/network/CPU metrics, abort/rollback, cost and independent reviewer. **Status: Pending** until executed. Failure-zone tests are **Tabletop** unless separately approved.

### Lab 13 — Measure disk throughput ceilings

**Procedure:** Correlate PVC/cloud IOPS/MBps/latency with broker requests and cleaner work.

**Expected evidence:** UTC start/end, approved isolated environment, immutable Git SHA, Kafka/Strimzi/client versions, workload seed, input distribution, exact commands, baseline/peak, acknowledged and processed unique IDs, P99, lag, KRaft quorum, ISR, PVC/network/CPU metrics, abort/rollback, cost and independent reviewer. **Status: Pending** until executed. Failure-zone tests are **Tabletop** unless separately approved.

### Lab 14 — Measure network/AZ ceilings

**Procedure:** Correlate replication and client traffic with node NIC and cross-AZ transfer.

**Expected evidence:** UTC start/end, approved isolated environment, immutable Git SHA, Kafka/Strimzi/client versions, workload seed, input distribution, exact commands, baseline/peak, acknowledged and processed unique IDs, P99, lag, KRaft quorum, ISR, PVC/network/CPU metrics, abort/rollback, cost and independent reviewer. **Status: Pending** until executed. Failure-zone tests are **Tabletop** unless separately approved.

### Lab 15 — Test safe ISR headroom

**Procedure:** Tabletop N-1/AZ failure and assess RF/minISR, quorum and recovery reserve.

**Expected evidence:** UTC start/end, approved isolated environment, immutable Git SHA, Kafka/Strimzi/client versions, workload seed, input distribution, exact commands, baseline/peak, acknowledged and processed unique IDs, P99, lag, KRaft quorum, ISR, PVC/network/CPU metrics, abort/rollback, cost and independent reviewer. **Status: Pending** until executed. Failure-zone tests are **Tabletop** unless separately approved.

### Lab 16 — Compare Strimzi node-pool shapes

**Procedure:** Model CPU/memory/storage versus throughput and per-broker bottlenecks.

**Expected evidence:** UTC start/end, approved isolated environment, immutable Git SHA, Kafka/Strimzi/client versions, workload seed, input distribution, exact commands, baseline/peak, acknowledged and processed unique IDs, P99, lag, KRaft quorum, ISR, PVC/network/CPU metrics, abort/rollback, cost and independent reviewer. **Status: Pending** until executed. Failure-zone tests are **Tabletop** unless separately approved.

### Lab 17 — Compare MSK broker alternatives

**Procedure:** Evaluate supported instance/storage limits and benchmark parity assumptions.

**Expected evidence:** UTC start/end, approved isolated environment, immutable Git SHA, Kafka/Strimzi/client versions, workload seed, input distribution, exact commands, baseline/peak, acknowledged and processed unique IDs, P99, lag, KRaft quorum, ISR, PVC/network/CPU metrics, abort/rollback, cost and independent reviewer. **Status: Pending** until executed. Failure-zone tests are **Tabletop** unless separately approved.

### Lab 18 — Test telemetry and abort gate

**Procedure:** Exercise isolated alerting when client SLO, ISR or disk threshold is breached.

**Expected evidence:** UTC start/end, approved isolated environment, immutable Git SHA, Kafka/Strimzi/client versions, workload seed, input distribution, exact commands, baseline/peak, acknowledged and processed unique IDs, P99, lag, KRaft quorum, ISR, PVC/network/CPU metrics, abort/rollback, cost and independent reviewer. **Status: Pending** until executed. Failure-zone tests are **Tabletop** unless separately approved.

### Lab 19 — Calculate capacity envelope

**Procedure:** Report sustained throughput, burst throughput, P99, headroom and cost per useful GB.

**Expected evidence:** UTC start/end, approved isolated environment, immutable Git SHA, Kafka/Strimzi/client versions, workload seed, input distribution, exact commands, baseline/peak, acknowledged and processed unique IDs, P99, lag, KRaft quorum, ISR, PVC/network/CPU metrics, abort/rollback, cost and independent reviewer. **Status: Pending** until executed. Failure-zone tests are **Tabletop** unless separately approved.

### Lab 20 — Obtain independent acceptance

**Procedure:** Review raw data, reproducibility, failure gates, event ledger and security approval.

**Expected evidence:** UTC start/end, approved isolated environment, immutable Git SHA, Kafka/Strimzi/client versions, workload seed, input distribution, exact commands, baseline/peak, acknowledged and processed unique IDs, P99, lag, KRaft quorum, ISR, PVC/network/CPU metrics, abort/rollback, cost and independent reviewer. **Status: Pending** until executed. Failure-zone tests are **Tabletop** unless separately approved.

## 12. Offline benchmark evidence validator

Save as `validate_benchmark.py`. This checks a **pre-existing** JSON summary; it does not generate traffic or claim runtime validation.

```python
#!/usr/bin/env python3
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument("summary", help="Path to benchmark JSON summary")
p.add_argument("--max-p99-ms", type=float, required=True)
p.add_argument("--max-lag-seconds", type=float, required=True)
args = p.parse_args()

with open(args.summary, encoding="utf-8") as f:
    d = json.load(f)

required = ["offered_events", "acknowledged_unique_events", "processed_unique_events",
            "missing_acknowledged_ids", "producer_p99_ms", "consumer_lag_seconds",
            "under_replicated_partitions", "offline_partitions", "kraft_quorum_healthy",
            "generator_saturated", "source_evidence_ref"]
missing = [k for k in required if k not in d]
if missing:
    p.error("missing required evidence fields: " + ", ".join(missing))

checks = {
    "event_ids_reconciled": d["missing_acknowledged_ids"] == 0,
    "processed_matches_acknowledged": d["processed_unique_events"] == d["acknowledged_unique_events"],
    "producer_p99": d["producer_p99_ms"] <= args.max_p99_ms,
    "consumer_freshness": d["consumer_lag_seconds"] <= args.max_lag_seconds,
    "replication_healthy": d["under_replicated_partitions"] == 0 and d["offline_partitions"] == 0,
    "kraft_quorum": d["kraft_quorum_healthy"] is True,
    "generator_not_saturated": d["generator_saturated"] is False,
    "evidence_reference": bool(d["source_evidence_ref"]),
}
print(json.dumps({"checks": checks, "pass": all(checks.values())}, indent=2))
raise SystemExit(0 if all(checks.values()) else 1)
```

The validator checks self-reported summary fields only. An independent reviewer must verify that the source evidence is authentic and the event-ID ledger is complete; it cannot establish correctness by itself.

## 13. Twelve performance failure scenarios

### Scenario 01 — High producer throughput but lost acks

**Diagnosis:** Reject result; reconcile acknowledged event IDs and producer error semantics. Compare offered versus unique acknowledged/processed events, producer P99, consumer freshness, partition skew, Kafka ISR/KRaft, disk latency, EKS throttling and network. **Response:** Stop or reduce test load at abort gates, protect data, isolate generator bottlenecks and preserve evidence. **Exit:** Correctness reconciled, Kafka healthy, bottleneck documented, repeatability and reviewer.

### Scenario 02 — P99 latency rises at low CPU

**Diagnosis:** Inspect disk latency, network, ISR wait, throttling and request queues. Compare offered versus unique acknowledged/processed events, producer P99, consumer freshness, partition skew, Kafka ISR/KRaft, disk latency, EKS throttling and network. **Response:** Stop or reduce test load at abort gates, protect data, isolate generator bottlenecks and preserve evidence. **Exit:** Correctness reconciled, Kafka healthy, bottleneck documented, repeatability and reviewer.

### Scenario 03 — Producer retries inflate apparent throughput

**Diagnosis:** Count acknowledged unique IDs, not send attempts. Compare offered versus unique acknowledged/processed events, producer P99, consumer freshness, partition skew, Kafka ISR/KRaft, disk latency, EKS throttling and network. **Response:** Stop or reduce test load at abort gates, protect data, isolate generator bottlenecks and preserve evidence. **Exit:** Correctness reconciled, Kafka healthy, bottleneck documented, repeatability and reviewer.

### Scenario 04 — Consumer lag rises despite more Pods

**Diagnosis:** Check partition limit, processing bottleneck, rebalances and fetch. Compare offered versus unique acknowledged/processed events, producer P99, consumer freshness, partition skew, Kafka ISR/KRaft, disk latency, EKS throttling and network. **Response:** Stop or reduce test load at abort gates, protect data, isolate generator bottlenecks and preserve evidence. **Exit:** Correctness reconciled, Kafka healthy, bottleneck documented, repeatability and reviewer.

### Scenario 05 — Compression improves network but saturates CPU

**Diagnosis:** Compare codec CPU and total SLO tradeoff. Compare offered versus unique acknowledged/processed events, producer P99, consumer freshness, partition skew, Kafka ISR/KRaft, disk latency, EKS throttling and network. **Response:** Stop or reduce test load at abort gates, protect data, isolate generator bottlenecks and preserve evidence. **Exit:** Correctness reconciled, Kafka healthy, bottleneck documented, repeatability and reviewer.

### Scenario 06 — Benchmark uses unrealistic payloads

**Diagnosis:** Rebuild non-PHI corpus with representative sizes and key skew. Compare offered versus unique acknowledged/processed events, producer P99, consumer freshness, partition skew, Kafka ISR/KRaft, disk latency, EKS throttling and network. **Response:** Stop or reduce test load at abort gates, protect data, isolate generator bottlenecks and preserve evidence. **Exit:** Correctness reconciled, Kafka healthy, bottleneck documented, repeatability and reviewer.

### Scenario 07 — KRaft metadata churn under partition load

**Diagnosis:** Check controller metrics and partition/leader changes. Compare offered versus unique acknowledged/processed events, producer P99, consumer freshness, partition skew, Kafka ISR/KRaft, disk latency, EKS throttling and network. **Response:** Stop or reduce test load at abort gates, protect data, isolate generator bottlenecks and preserve evidence. **Exit:** Correctness reconciled, Kafka healthy, bottleneck documented, repeatability and reviewer.

### Scenario 08 — Disk IOPS caps throughput with free space

**Diagnosis:** Correlate PVC/cloud queue, latency and provisioned limits. Compare offered versus unique acknowledged/processed events, producer P99, consumer freshness, partition skew, Kafka ISR/KRaft, disk latency, EKS throttling and network. **Response:** Stop or reduce test load at abort gates, protect data, isolate generator bottlenecks and preserve evidence. **Exit:** Correctness reconciled, Kafka healthy, bottleneck documented, repeatability and reviewer.

### Scenario 09 — Network/AZ traffic exceeds model

**Diagnosis:** Measure replication, client placement and retries. Compare offered versus unique acknowledged/processed events, producer P99, consumer freshness, partition skew, Kafka ISR/KRaft, disk latency, EKS throttling and network. **Response:** Stop or reduce test load at abort gates, protect data, isolate generator bottlenecks and preserve evidence. **Exit:** Correctness reconciled, Kafka healthy, bottleneck documented, repeatability and reviewer.

### Scenario 10 — Reassignment affects benchmark baseline

**Diagnosis:** Stop or isolate benchmark; record concurrent broker maintenance. Compare offered versus unique acknowledged/processed events, producer P99, consumer freshness, partition skew, Kafka ISR/KRaft, disk latency, EKS throttling and network. **Response:** Stop or reduce test load at abort gates, protect data, isolate generator bottlenecks and preserve evidence. **Exit:** Correctness reconciled, Kafka healthy, bottleneck documented, repeatability and reviewer.

### Scenario 11 — Canary alert misses SLO breach

**Diagnosis:** Inspect metrics, alert rules, scrape delay and on-call routing. Compare offered versus unique acknowledged/processed events, producer P99, consumer freshness, partition skew, Kafka ISR/KRaft, disk latency, EKS throttling and network. **Response:** Stop or reduce test load at abort gates, protect data, isolate generator bottlenecks and preserve evidence. **Exit:** Correctness reconciled, Kafka healthy, bottleneck documented, repeatability and reviewer.

### Scenario 12 — Load generator exhausts EKS node

**Diagnosis:** Separate client-generator resource limits from broker bottlenecks. Compare offered versus unique acknowledged/processed events, producer P99, consumer freshness, partition skew, Kafka ISR/KRaft, disk latency, EKS throttling and network. **Response:** Stop or reduce test load at abort gates, protect data, isolate generator bottlenecks and preserve evidence. **Exit:** Correctness reconciled, Kafka healthy, bottleneck documented, repeatability and reviewer.

## 14. Eight production runbooks

### Runbook A — Benchmark preflight and authorization

**Trigger/actions:** Confirm isolated cluster, approvals, budget, limits and telemetry. **No-go:** stress against production, missing authorization, unhealthy ISR/quorum, unexplained missing event IDs, exceeded cost ceiling or compromised credentials. **Exit:** Kafka client SLO, broker durability, cleaned test resources, evidence and independent signoff.

### Runbook B — Producer P99 regression

**Trigger/actions:** Inspect acks, ISR, request queues, TLS/compression, disk and network. **No-go:** stress against production, missing authorization, unhealthy ISR/quorum, unexplained missing event IDs, exceeded cost ceiling or compromised credentials. **Exit:** Kafka client SLO, broker durability, cleaned test resources, evidence and independent signoff.

### Runbook C — Consumer lag regression

**Trigger/actions:** Measure arrival/service rate, partitions, rebalance and downstream latency. **No-go:** stress against production, missing authorization, unhealthy ISR/quorum, unexplained missing event IDs, exceeded cost ceiling or compromised credentials. **Exit:** Kafka client SLO, broker durability, cleaned test resources, evidence and independent signoff.

### Runbook D — Disk/network saturation

**Trigger/actions:** Stop test safely, inspect throttles and protect Kafka durability. **No-go:** stress against production, missing authorization, unhealthy ISR/quorum, unexplained missing event IDs, exceeded cost ceiling or compromised credentials. **Exit:** Kafka client SLO, broker durability, cleaned test resources, evidence and independent signoff.

### Runbook E — KRaft/ISR abort

**Trigger/actions:** Terminate load, protect quorum/minISR, inspect partitions and client errors. **No-go:** stress against production, missing authorization, unhealthy ISR/quorum, unexplained missing event IDs, exceeded cost ceiling or compromised credentials. **Exit:** Kafka client SLO, broker durability, cleaned test resources, evidence and independent signoff.

### Runbook F — Benchmark reproducibility review

**Trigger/actions:** Pin images, workload seeds, configs, timing and raw evidence. **No-go:** stress against production, missing authorization, unhealthy ISR/quorum, unexplained missing event IDs, exceeded cost ceiling or compromised credentials. **Exit:** Kafka client SLO, broker durability, cleaned test resources, evidence and independent signoff.

### Runbook G — Strimzi/MSK capacity decision

**Trigger/actions:** Compare bottleneck, headroom, scaling risk, AZ costs and SLO. **No-go:** stress against production, missing authorization, unhealthy ISR/quorum, unexplained missing event IDs, exceeded cost ceiling or compromised credentials. **Exit:** Kafka client SLO, broker durability, cleaned test resources, evidence and independent signoff.

### Runbook H — Independent performance acceptance

**Trigger/actions:** Reconcile event IDs, score controls, review exceptions and signoff. **No-go:** stress against production, missing authorization, unhealthy ISR/quorum, unexplained missing event IDs, exceeded cost ceiling or compromised credentials. **Exit:** Kafka client SLO, broker durability, cleaned test resources, evidence and independent signoff.

## 15. Evidence package

```text
evidence-ch083/
  charter-approval.md
  immutable-baseline.md
  broker-metrics.csv
  producer-metrics.csv
  consumer-metrics.csv
  payload-corpus.md
  baseline-run.md
  batch-linger-comparison.md
  compression-comparison.md
  partition-scaling.md
  consumer-scaling.md
  burst-recovery.md
  disk-ceilings.md
  network-az-ceilings.md
  isr-headroom-tabletop.md
  strimzi-sizing.md
  msk-sizing.md
  alert-abort-test.md
  capacity-envelope.csv
  independent-acceptance.md
  benchmark-summary.json
  scorecard.md
```

All artifacts need UTC time, source/version, exact reproducible workload, **Live** versus **Tabletop**, expected/observed metrics, correctness ledger, risk/abort and independent reviewer.

## 16. 100-point benchmarking assessment

| Domain | Points | Critical |
|---|---:|---|
| Workload realism and reproducibility | 20 | Yes |
| Producer/consumer latency and throughput | 20 | Yes |
| Event correctness and Kafka ISR/KRaft safety | 25 | Yes |
| Broker resource bottleneck analysis | 15 | Yes |
| Scaling, cost and failure-headroom decision | 10 | Yes |
| Independent technical/security review | 10 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates independently evidenced. **Automatic Fail:** production stress without approval, fabricated metrics, unaccounted missing acknowledged events, ISR/quorum regression without abort, leaked credentials or absent independent review.

## 17. References and next chapter

**References:** [Apache Kafka](https://kafka.apache.org/documentation/), [Strimzi](https://strimzi.io/documentation/), [Kubernetes](https://kubernetes.io/docs/), [Amazon MSK](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html), [Prometheus](https://prometheus.io/docs/).

**Next:** Chapter 084 — Kafka Cloud Cost Optimization, Storage Lifecycle and Reliability-Aware FinOps.

---

**Verification boundary:** Publication proves document availability only. Live benchmarks, client event reconciliation, failure-zone drills and independent technical/security review remain Pending.
