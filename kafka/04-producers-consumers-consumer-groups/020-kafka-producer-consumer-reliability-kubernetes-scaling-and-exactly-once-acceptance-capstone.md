# Chapter 020 — Kafka Producer and Consumer Reliability, Kubernetes Scaling and Exactly-Once Acceptance Capstone

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 04 — Producers, Consumers and Consumer Groups (final capstone)  
**Primary platform:** Kubernetes + Strimzi Operator + KRaft  
**Prerequisites:** Chapters 016–019, [Kubernetes lab foundation](../kubernetes/README.md), Chapters 011–015 for broker/ISR recovery  
**Audience:** Kafka SREs, DBREs, platform engineers, application owners, incident commanders  
**Publication:** Complete · **Live execution:** Pending · **Independent security review:** Pending · **Production acceptance:** Pending

> **Safety boundary:** Run only in a disposable namespace/cluster. Never reduce replication or min ISR, delete broker PVCs, reset a live business consumer group, force unclean leader election, or run a destructive chaos test in production. This capstone separates **published instructions**, **executed evidence**, and **approved operational readiness**.

## 1. Capstone mission

Build and evaluate a Kubernetes-native Kafka producer/consumer workload that continues to meet its business processing contract through controlled application-level failures, rolling updates, consumer scaling, and transactional recovery.

The assessment spans:

- Durable producer acknowledgments, idempotence, batching, retry and timeout semantics.
- Consumer poll/processing/offset-commit correctness and replay.
- Group assignment, rebalancing, Kubernetes scaling and graceful shutdown.
- Kafka transactional producer commit/abort, read-committed visibility and producer fencing.
- External side-effect boundaries, business-event IDs, idempotent sinks and reconciliation.
- Observability, SLOs, incident response, change approval and operational handoff.

**Completion rule:** Writing a manifest or passing a topic metadata check is not sufficient. The capstone requires workload behavior evidence and explicit pass/fail criteria.

## 2. Reference architecture

```text
 GitOps pull request / approved change
               |
       Kubernetes namespace kafka-lab
               |
  +------------+-------------+
  |                          |
Producer Job/Deployment   Consumer Deployment
  |                          |
  | acks=all                 | group.id, manual commits
  | idempotence              | bounded poll loop, SIGTERM drain
  v                          v
  Kafka bootstrap Service (discovery only)
               |
    Strimzi KRaft Kafka brokers
       RF=3 / min ISR=2
        /             \
  input topic      output topic
        \             /
         transaction coordinator
                 |
    read_committed verification consumer
                 |
     business-ID reconciliation evidence
                 |
 Prometheus/OpenTelemetry + K8s events
                 |
     SLO dashboard / incident runbooks
```

The producer and consumer are application workloads. Kafka brokers and KRaft controllers remain operator-managed. Do not scale a broker StatefulSet manually to fix application consumer lag.

## 3. Scope, roles and change-control gates

| Role | Accountability |
|---|---|
| Kafka platform owner | Broker health, topic configuration, ISR and ACLs |
| Application owner | Processing semantics, business IDs, downstream correctness |
| SRE/on-call | SLOs, monitoring, incident coordination and rollback |
| Security reviewer | Identity, TLS/SASL, Secrets, network isolation |
| Change approver | Lab fault scope, deployment scaling and recovery actions |
| Assessor | Independently evaluates evidence and scoring |

**Gate G0 — lab authorization:** record Kubernetes context, namespace, cluster identity, intended topic/group names, approved image digests, time window and rollback owner.

**Gate G1 — baseline health:** Kafka Ready, KRaft quorum healthy, RF=3, full ISR, sufficient CPU/memory/PVC space, producer and consumer client compatibility.

**Gate G2 — fault authorization:** allow only application-Pod-level restart or controlled scaling in the disposable lab. No broker/volume faults required.

**Gate G3 — recovery verification:** reconcile business event IDs and committed offsets, not only Pod readiness.

**Gate G4 — signoff:** require executed evidence, security review and unresolved-risk register.

## 4. Reliability contract and SLO worksheet

| Reliability dimension | Measurement | Acceptance requirement |
|---|---|---|
| Producer durability | Ack errors, ISR, event ID reconciliation | No unexplained missing acknowledged lab events |
| Producer correctness | Unique business event IDs | No unexplained duplicates after deduplication |
| Consumer progress | Per-partition committed offset and event age | Recovers after planned Pod restart |
| Rebalance behavior | Membership and assignment changes | Stabilizes after scale/rollout |
| Transaction isolation | Committed vs aborted output | Aborted record absent from read_committed |
| Offset integrity | Input offset + output transaction | No premature offset advance |
| Recovery | Time to restored processing | Measured and compared to approved RTO |
| Security | TLS/SASL, Kafka ACLs, Secrets, RBAC | Reviewed production design; lab plaintext isolated |
| Observability | Metrics, logs, events, evidence | Sufficient to explain each incident |

Numeric latency and recovery SLOs must come from the application owner. **Do not fabricate measurements or declare a production SLO passed from the reference configuration.**

## 5. Prerequisites and version compatibility

Assume namespace `kafka-lab`, Strimzi cluster `sre-kafka`, Kafka CLI Pod `kafka-cli`, and lab bootstrap `sre-kafka-kafka-bootstrap:9092`.

```bash
kubectl config current-context
kubectl -n kafka-lab get kafka,kafkanodepool,pods,pvc -o wide
kubectl -n kafka-lab wait kafka/sre-kafka --for=condition=Ready --timeout=900s
kubectl -n kafka-lab get pod kafka-cli
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-metadata-quorum.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 describe --status
kubectl get crd kafkatopics.kafka.strimzi.io -o jsonpath='{.spec.versions[*].name}{"\n"}'
mkdir -p evidence-ch20
```

The examples use `kafka.strimzi.io/v1` only when installed CRDs support it. Use the installed served version otherwise. Confirm Kafka Java client version and the supported classic/new consumer group protocol before attempting protocol-specific tuning. Production must use approved encrypted listeners and authentication; plaintext is lab-only.

## 6. Lab A — Create capstone input/output topics

Save `topics-ch20.yaml`:

```yaml
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-capstone-input-ch20
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  partitions: 3
  replicas: 3
  config:
    min.insync.replicas: 2
    retention.ms: 86400000
---
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: sre-capstone-output-ch20
  namespace: kafka-lab
  labels:
    strimzi.io/cluster: sre-kafka
spec:
  partitions: 3
  replicas: 3
  config:
    min.insync.replicas: 2
    retention.ms: 86400000
```

```bash
kubectl apply --dry-run=server -f topics-ch20.yaml
kubectl apply -f topics-ch20.yaml
kubectl -n kafka-lab get kafkatopic sre-capstone-input-ch20 sre-capstone-output-ch20
for topic in sre-capstone-input-ch20 sre-capstone-output-ch20; do
  kubectl -n kafka-lab exec kafka-cli -- \
    /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
    --describe --topic "$topic" \
    | tee "evidence-ch20/${topic}-describe.txt"
done
```

**Acceptance:** each topic has three partitions, RF=3, full ISR=3, no offline leaders, and min ISR=2. Check Kafka metadata in addition to CR status.

## 7. Lab B — Deterministic durable producer baseline

```bash
printf '%s\n' \
  'acct-A:event-2001' 'acct-A:event-2002' \
  'acct-B:event-2003' 'acct-B:event-2004' \
  'acct-C:event-2005' 'acct-C:event-2006' | \
kubectl -n kafka-lab exec -i kafka-cli -- \
  /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-capstone-input-ch20 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --producer-property max.in.flight.requests.per.connection=5 \
  --property parse.key=true --property key.separator=:
```

Capture output topic metadata, producer exit status and event-ID inventory. Producer success means the client reported delivery under the selected acknowledgment policy; it does **not** prove exactly-once external processing.

## 8. Lab C — Baseline consumer, offsets and replay contract

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-capstone-input-ch20 \
  --group sre-capstone-ch20-baseline \
  --from-beginning --max-messages 6 \
  --property print.key=true \
  --property print.partition=true \
  --property print.offset=true \
  | tee evidence-ch20/baseline-consumed.txt

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --group sre-capstone-ch20-baseline \
  | tee evidence-ch20/baseline-group.txt
```

**Acceptance:** six unique event IDs; within-key ordering follows partition offsets. The console consumer is a diagnostic tool and does not demonstrate durable business side effects or manual commit correctness. Short-lived console consumer offset commits may not be visible immediately; record the actual outcome.

## 9. Lab D — Rebalance and parallelism demonstration

Use three separate interactive sessions of the Kafka console consumer with the **same disposable group** `sre-capstone-ch20-members`. For each membership level 1, 2, 3, and optionally 4:

```bash
kubectl -n kafka-lab exec -it kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-capstone-input-ch20 \
  --group sre-capstone-ch20-members \
  --consumer-property auto.offset.reset=earliest
```

From another terminal:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --group sre-capstone-ch20-members --members --verbose \
  | tee evidence-ch20/membership-snapshot.txt
```

**Acceptance:** total partition ownership is three; when four members are stable, at least one has zero partitions. Record rebalance time and any interruption. Do not equate four Pods with four useful partition workers.

## 10. Lab E — Kubernetes consumer Deployment review

The following manifest is a **deployable template only after the container entrypoint is verified**. It must implement an actual Kafka consumer using the supplied environment variables, handle SIGTERM, track completed offsets, and expose suitable health probes. A Kafka CLI image is not a substitute for a production application.

Save `consumer-deployment-ch20.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: consumer-ch20
  namespace: kafka-lab
spec:
  replicas: 1
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  selector:
    matchLabels:
      app: consumer-ch20
  template:
    metadata:
      labels:
        app: consumer-ch20
    spec:
      terminationGracePeriodSeconds: 90
      containers:
        - name: consumer
          image: <VERIFIED_CONSUMER_IMAGE_DIGEST>
          env:
            - name: KAFKA_BOOTSTRAP_SERVERS
              value: sre-kafka-kafka-bootstrap:9092
            - name: KAFKA_TOPIC
              value: sre-capstone-input-ch20
            - name: KAFKA_GROUP_ID
              value: sre-capstone-ch20-app
            - name: ENABLE_AUTO_COMMIT
              value: "false"
          resources:
            requests:
              cpu: 200m
              memory: 256Mi
            limits:
              cpu: "1"
              memory: 1Gi
```

**Approval gate:** validate the image digest, runtime entrypoint, signal handling, TLS/SASL config, Kafka ACLs, liveness/readiness semantics, resource profile and application offset commit implementation. The environment variable `ENABLE_AUTO_COMMIT` is illustrative; it has no effect unless the application explicitly consumes it.

After approval:

```bash
kubectl apply --dry-run=server -f consumer-deployment-ch20.yaml
kubectl apply -f consumer-deployment-ch20.yaml
kubectl -n kafka-lab rollout status deployment/consumer-ch20 --timeout=180s
kubectl -n kafka-lab get deployment,pods -l app=consumer-ch20 -o wide
```

**Acceptance:** actual group membership and processing progress, not just Kubernetes readiness. If no reviewed image is available, mark this lab Pending and do not claim a live application test.

## 11. Lab F — Controlled consumer scale-out and scale-in

Only if Lab E passed and the cluster has capacity:

```bash
kubectl -n kafka-lab scale deployment/consumer-ch20 --replicas=2
kubectl -n kafka-lab rollout status deployment/consumer-ch20 --timeout=180s
kubectl -n kafka-lab scale deployment/consumer-ch20 --replicas=3
kubectl -n kafka-lab rollout status deployment/consumer-ch20 --timeout=180s
```

Inspect group members and partition assignments after each change. Measure event age and rebalance duration. Return to one replica **only after** verifying safe drain, no uncommitted in-flight side effects and the application owner's approval:

```bash
kubectl -n kafka-lab scale deployment/consumer-ch20 --replicas=1
kubectl -n kafka-lab rollout status deployment/consumer-ch20 --timeout=180s
```

**Acceptance:** group stabilizes, assigned partitions sum to three, committed progress resumes, and no unexplained business event IDs are missing. Scaling can cause at-least-once replay; deduplication must be verified separately.

## 12. Lab G — Application-Pod recovery exercise

**Fault boundary:** consumer application Pod only; never Kafka broker, controller or PVC.

1. Confirm all six baseline event IDs are accounted for and snapshot group offsets.
2. Produce an additional, uniquely numbered test batch.
3. Select a consumer Pod belonging to the disposable Deployment.
4. Obtain explicit lab fault approval.
5. Delete **one** selected consumer Pod; allow the Deployment to replace it.
6. Record termination, new Pod readiness, group rebalance and committed offset recovery.
7. Reconcile all new event IDs and downstream effects.

Example after approval:

```bash
kubectl -n kafka-lab get pods -l app=consumer-ch20 -o wide
# Replace <APP_POD_NAME> only after confirming it belongs to consumer-ch20.
kubectl -n kafka-lab delete pod <APP_POD_NAME>
kubectl -n kafka-lab rollout status deployment/consumer-ch20 --timeout=180s
kubectl -n kafka-lab get pods -l app=consumer-ch20 -o wide
```

**Acceptance:** recovered membership, bounded interruption and event-ID reconciliation. A Pod becoming Ready does not by itself satisfy the acceptance criteria.

## 13. Lab H — Transactional commit/abort and isolation

Reuse the reviewed `TxnDemo.java` client implementation and compile workflow from [Chapter 019](019-kafka-delivery-semantics-transactions-exactly-once-processing-and-kubernetes-recovery.md), but change the output topic to `sre-capstone-output-ch20` and use **new** transactional IDs `sre-capstone-ch20-commit` and `sre-capstone-ch20-abort`.

Run one committed transaction containing `event-2007` and one aborted transaction containing `event-2008`. Compare consumers:

```bash
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-capstone-output-ch20 --from-beginning \
  --consumer-property isolation.level=read_committed \
  --timeout-ms 10000 \
  | tee evidence-ch20/read-committed.txt

kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --topic sre-capstone-output-ch20 --from-beginning \
  --consumer-property isolation.level=read_uncommitted \
  --timeout-ms 10000 \
  | tee evidence-ch20/read-uncommitted.txt
```

**Acceptance:** committed `event-2007` is visible to `read_committed`; aborted `event-2008` is not. A bounded console consumer may exit with timeout after printing records; distinguish that from a transactional failure. **Do not mark this lab passed unless the modified Java client was compiled and actually executed.**

## 14. Lab I — Exactly-once consume-transform-produce design review

Review this sequence:

```text
consumer.enable.auto.commit=false
consumer.isolation.level=read_committed (if input is transactional)
producer.transactional.id=<unique logical task ID>
producer.initTransactions()
poll input
beginTransaction()
write transformed output to Kafka
sendOffsetsToTransaction(next fully processed offsets, group metadata)
commitTransaction()
on abort: seek input consumer to committed offsets and retry safely
on fencing: stop old producer instance immediately
```

Evaluate three crash points:

- **Before commit:** output not visible to read-committed consumers; group offsets do not advance.
- **After successful commit but before application acknowledgment:** transaction may have committed; reconcile output and offset state before business resubmission.
- **External database write before Kafka commit:** external effect can persist even if Kafka transaction aborts. Use an outbox/inbox or idempotent sink; Kafka transactions alone do not cover the database.

**Acceptance:** design documents contiguous per-partition offset tracking, ownership/fencing, abort-and-seek behavior, and external side-effect reconciliation. A tabletop review is not proof of an executed exactly-once stream processor.

## 15. Lab J — Producer timeout and ambiguity tabletop

For RF=3/min ISR=2 and `acks=all`, classify:

| Observation | Possible state | Safe response |
|---|---|---|
| Success acknowledgment | Record accepted under durability policy | Track unique business ID |
| Timeout | Record may already be committed | Reconcile before application retry |
| ISR below min ISR | Durable write may be rejected | Restore ISR, do not lower min ISR |
| Authorization exception | Principal cannot write | Correct least-privilege ACLs |
| Producer fenced | Old transactional epoch invalid | Stop old instance |
| Pod restarted after send | Business attempt may repeat | Idempotent business-key handling |

**Acceptance:** a written recovery decision tree with no unbounded retries or durability weakening.

## 16. Lab K — Observability and SLO evidence collection

Capture Kubernetes and Kafka metadata:

```bash
kubectl -n kafka-lab get pods,deployments,jobs -o wide \
  > evidence-ch20/kubernetes-workloads.txt
kubectl -n kafka-lab get events --sort-by=.lastTimestamp \
  > evidence-ch20/kubernetes-events.txt
kubectl -n kafka-lab exec kafka-cli -- \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server sre-kafka-kafka-bootstrap:9092 \
  --describe --group sre-capstone-ch20-app \
  > evidence-ch20/consumer-group.txt || true
```

Collect producer request latency/errors, consumer processing/event age, committed lag, group rebalances, transaction abort/commit rates, Kafka ISR/offline partitions, and Pod restart/OOM/CPU throttling metrics from your actual monitoring stack. **Do not fabricate Prometheus queries or claim dashboards exist without inspecting deployment and metric names.**

## 17. Lab L — Automated read-only reliability preflight

Save as `verify-ch20.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

NS=kafka-lab
BS=sre-kafka-kafka-bootstrap:9092
BIN=/opt/kafka/bin
TOPICS=(sre-capstone-input-ch20 sre-capstone-output-ch20)

echo '[1/5] Kafka Ready'
kubectl -n "$NS" wait kafka/sre-kafka --for=condition=Ready --timeout=120s

echo '[2/5] KRaft quorum'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status

echo '[3/5] Topic CR and metadata'
for topic in "${TOPICS[@]}"; do
  kubectl -n "$NS" get kafkatopic "$topic" >/dev/null
  desc="$(kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-topics.sh" \
    --bootstrap-server "$BS" --describe --topic "$topic")"
  printf '%s\n' "$desc"
  printf '%s\n' "$desc" | awk -v topic="$topic" '
    /Partition:/ && /Replicas:/ && /Isr:/ {
      split($0,a,"Replicas: "); split(a[2],b," "); rf=split(b[1],r,",")
      split($0,c,"Isr: "); split(c[2],d," "); isr=split(d[1],s,",")
      seen++
      if(rf!=3 || isr!=3) bad++
    }
    END {
      if(seen!=3 || bad){print "FAIL "topic": partitions="seen" degraded="bad;exit 1}
      print "PASS "topic": 3 partitions, RF=3, ISR=3"
    }'
done

echo '[4/5] Kafka connectivity'
kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-broker-api-versions.sh" \
  --bootstrap-server "$BS" >/dev/null

echo '[5/5] Effective topic configs'
for topic in "${TOPICS[@]}"; do
  kubectl -n "$NS" exec kafka-cli -- "$BIN/kafka-configs.sh" \
    --bootstrap-server "$BS" --entity-type topics \
    --entity-name "$topic" --describe
done

echo 'PASS: metadata preflight only. Application/transaction/SLO acceptance remains separate.'
```

```bash
chmod +x verify-ch20.sh
./verify-ch20.sh | tee evidence-ch20/metadata-acceptance.txt
```

**Script limitations:** it does not prove min ISR from parsed output, event delivery, transaction commit/abort visibility, group stability, no duplicates, security compliance or SLOs. Those need independent tests and evidence.

## 18. Evidence manifest and validation requirements

Store sanitized evidence with an immutable run identifier:

```text
evidence-ch20/
  context-and-approvals.md
  cluster-and-client-versions.txt
  input-topic-describe.txt
  output-topic-describe.txt
  producer-events.txt
  baseline-consumed.txt
  membership-before-after.txt
  deployment-rollout.txt
  pod-restart-and-recovery.txt
  transaction-commit-abort.txt
  read-committed.txt
  read-uncommitted.txt
  offset-reconciliation.csv
  metric-snapshots.md
  metadata-acceptance.txt
  incident-timeline.md
  security-review.md
  assessor-signoff.md
```

Every test must record **planned action, actual command, timestamp, expected result, observed result, evidence path, reviewer, and pass/fail**. Redact tokens, private keys, credentials and sensitive payloads before sharing.

## 19. Ten production failure scenarios

### Scenario 1 — Producer acknowledgment timeout

**Signal:** retries increase; send times out.

**Diagnosis:** broker ISR, network latency, Pod CPU, request/delivery timeout and actual committed IDs.

**Recovery:** restore health and reconcile ambiguous records; do not blindly resubmit.

### Scenario 2 — ISR below write durability threshold

**Signal:** `NOT_ENOUGH_REPLICAS` for `acks=all`.

**Diagnosis:** broker Pod/PVC and follower fetch health.

**Recovery:** restore replicas; never reduce min ISR just to make the acceptance script pass.

### Scenario 3 — Consumer group rebalance storm

**Signal:** group membership churn, rising event age.

**Diagnosis:** Deployment rollout, HPA changes, poll interval and shutdown.

**Recovery:** stabilize membership and processing; inspect assignment compatibility.

### Scenario 4 — Duplicate effects after consumer Pod restart

**Signal:** same business ID applied twice.

**Diagnosis:** side-effect success before offset commit, missing sink deduplication.

**Recovery:** reconcile and implement idempotent processing.

### Scenario 5 — Premature offset commit skips work

**Signal:** committed offset beyond unfinished record.

**Diagnosis:** auto commit or incorrect asynchronous offset tracking.

**Recovery:** approved replay from retained offsets; validate downstream state.

### Scenario 6 — Consumer scales beyond partition count

**Signal:** extra Pods idle.

**Diagnosis:** partition/member assignment and HPA targets.

**Recovery:** rightsize replicas; redesign partitioning only through reviewed migration.

### Scenario 7 — Transactional producer fenced

**Signal:** `ProducerFencedException`.

**Diagnosis:** overlapping logical task ownership or duplicate transactional ID.

**Recovery:** stop fenced producer; restore one owner per task.

### Scenario 8 — Aborted records visible downstream

**Signal:** aborted test ID consumed by a business processor.

**Diagnosis:** `isolation.level=read_uncommitted`.

**Recovery:** correct isolation and reconcile downstream effects.

### Scenario 9 — Read-committed consumer appears stalled

**Signal:** log end advances but visible data lags.

**Diagnosis:** long-running transaction and last stable offset.

**Recovery:** resolve transaction, distinguish LSO from LEO lag.

### Scenario 10 — External database side effect survives Kafka abort

**Signal:** DB state changed while Kafka output transaction aborted.

**Diagnosis:** cross-system transaction boundary.

**Recovery:** idempotent sink/outbox/inbox, reconciliation or approved compensation.

## 20. Troubleshooting decision matrix

| Signal | Kubernetes evidence | Kafka evidence | Unsafe action |
|---|---|---|---|
| No producer writes | Pod DNS/Secrets/CPU | Listener, ACL, ISR | Disable security |
| Group not processing | Pod logs, rollout | Members, commits, lag | Reset offsets blindly |
| Rebalance storm | HPA, Pod churn | Group protocol and assignment | Infinite scale-out |
| Duplicate events | Restarts, side-effect logs | Event IDs, committed offsets | Assume idempotent producer fixes sink |
| Commit failure | Pod CPU/network | Coordinator/transaction state | Retry fenced producer |
| Missing records | App logs | Log start/retention/offsets | Set auto.offset.reset=latest |
| Read_committed lag | Transaction Pod health | LSO, open transactions | Ignore transaction timeout |
| Unhealthy RF/ISR | Broker Pods/PVCs | Partition metadata | Lower min ISR |

## 21. Six enterprise runbooks

### Runbook A — Producer availability and durability incident

1. Declare impact, affected topics and error budget.
2. Capture producer errors, ISR, leader placement and broker Pod health.
3. Distinguish acknowledged, rejected and ambiguous event IDs.
4. Restore network/ISR or client configuration without weakening durability.
5. Reconcile records and downstream effects.
6. Record timeline, evidence and follow-up controls.

### Runbook B — Consumer lag and group instability

1. Capture group membership, partition assignments, committed lag and event age.
2. Correlate rebalances with Pod restarts, HPA and rollout.
3. Check processing time, poll interval and downstream rate limits.
4. Stabilize membership, safely adjust replicas within partition bounds.
5. Verify processing freshness and commit progress.
6. Preserve before/after metrics and root cause.

### Runbook C — Graceful Kubernetes consumer rollout

1. Validate image digest, Secrets, group ID and client protocol.
2. Confirm termination grace and application SIGTERM handling.
3. Roll out conservatively with observed partition assignments.
4. Drain in-flight work and commit only completed offsets.
5. Verify rebalances, duplicate IDs and SLO recovery.
6. Roll back on sustained regression.

### Runbook D — Transactional producer failure

1. Identify transactional ID, owner, client version and producer epoch.
2. Distinguish abortable error, timeout and fatal fencing.
3. Stop fenced producer; prevent overlapping ownership.
4. Recover transaction coordinator and ISR if needed.
5. Reconcile committed output and transactional offsets.
6. Resume under one valid task owner.

### Runbook E — Offset replay and business reconciliation

1. Stop active consumers and obtain application-owner approval.
2. Snapshot committed offsets, log start/end and business IDs.
3. Determine replay/skip range and downstream deduplication strategy.
4. Preview any reset; do not execute in this capstone.
5. Reprocess only approved records with reconciliation checks.
6. Document missing/duplicate effects and irreversible retention gaps.

### Runbook F — Capstone incident command and acceptance handoff

1. Confirm change ticket, fault scope and incident commander.
2. Establish baseline, SLO targets and evidence collection.
3. Execute only approved application-level experiments.
4. Stop immediately on broker/ISR degradation or unbounded data effects.
5. Restore baseline and reconcile all event IDs.
6. Obtain independent assessor, application owner and security signoff.

## 22. Acceptance scorecard — 100 points

| Domain | Points | Critical gate |
|---|---:|---|
| Kubernetes/Strimzi/KRaft baseline and safety authorization | 10 | Yes |
| RF=3/min ISR=2 topic provisioning and metadata | 10 | Yes |
| Durable producer config and unique event IDs | 10 | Yes |
| Consumer offsets, lag and processing contract | 10 | Yes |
| Group rebalance and partition-aware scaling | 10 | No |
| Kubernetes Deployment rollout and Pod recovery | 10 | Yes |
| Transaction commit/abort and read_committed proof | 10 | Yes |
| Transactional offset/fencing/external side-effect design | 10 | Yes |
| Monitoring, SLO evidence and automated preflight | 10 | No |
| Incident runbooks, recovery evidence and independent signoff | 10 | Yes |
| **Total** | **100** | |

**Pass threshold:** at least 85/100 **and every critical gate passed with actual evidence**. If an image, runtime, or transaction test was not executed, score that domain Pending, not Passed. Security approval and production deployment approval are separate from the educational score.

## 23. Operational acceptance checklist

- [ ] Context, cluster identity and fault authorization captured.
- [ ] KRaft quorum, Kafka Ready, topic RF/ISR and min ISR verified.
- [ ] Producer acknowledgment, idempotence and business IDs validated.
- [ ] Consumer group, offsets and within-partition ordering verified.
- [ ] Kubernetes Deployment image/entrypoint and graceful shutdown reviewed.
- [ ] Scaling and controlled application Pod recovery executed or marked Pending.
- [ ] Transactional commit/abort visibility demonstrated with a compiled client.
- [ ] Kafka-to-Kafka exactly-once scope and external sink limitations documented.
- [ ] TLS/SASL, ACLs, Secrets and NetworkPolicies independently reviewed.
- [ ] Event-ID reconciliation and SLO evidence retained.
- [ ] Runbooks, rollback, incident timeline and assessor signoff complete.

## 24. Cleanup and recovery

**Only after** preserving evidence, stopping test consumers, and confirming resource ownership:

```bash
kubectl -n kafka-lab delete deployment consumer-ch20 --ignore-not-found
kubectl -n kafka-lab delete kafkatopic \
  sre-capstone-input-ch20 sre-capstone-output-ch20 \
  --ignore-not-found
```

Topic deletion permanently removes test records. Do not delete broker/controller PVCs, KafkaNodePools, the Strimzi cluster or any unrelated application resources.

**References:** [Apache Kafka documentation](https://kafka.apache.org/documentation/), [Strimzi documentation](https://strimzi.io/documentation/), [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/), [Kubernetes Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/), [Kubernetes HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/).

**Part 04 completed:** Chapters 016–020 — Producers, Consumers and Consumer Groups.

**Next:** Chapter 021 — Kafka Log Segments, Storage Internals, Retention and Kubernetes Persistent Volume Reliability, beginning Part 05 — Storage, Retention, Compaction and Tiered Storage.

---

**Verification boundary:** GitHub publication verifies document availability, not that the Kubernetes labs were executed, Java client was compiled, application Pod faults were performed, exactly-once semantics were demonstrated, security controls passed, or production reliability was accepted.
