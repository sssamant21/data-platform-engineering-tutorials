#!/usr/bin/env bash
set -Eeuo pipefail

# Disposable kind + Strimzi integration test. NEVER targets a user-supplied cluster.
EVIDENCE="${EVIDENCE_DIR:-kafka/qa/evidence/strimzi-runtime}"
mkdir -p "$EVIDENCE"
START="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
STATUS=FAIL
KAFKA=qa-kafka
NS=kafka-qa
BOOTSTRAP=qa-kafka-kafka-bootstrap:9092
CLIENT=kafka-qa-client
TOPIC="qa-smoke-${GITHUB_RUN_ID:-local}"
MESSAGES=$'kafka-qa-k8s-001\nkafka-qa-k8s-002\nkafka-qa-k8s-003'
record() { printf '%s\n' "$*" | tee -a "$EVIDENCE/checks.txt"; }
diagnostics() {
  kubectl get nodes -o wide > "$EVIDENCE/nodes.txt" 2>&1 || true
  kubectl get pods -A -o wide > "$EVIDENCE/pods.txt" 2>&1 || true
  kubectl get kafka,kafkanodepools -n "$NS" -o yaml > "$EVIDENCE/kafka-resources.yaml" 2>&1 || true
  kubectl get events -n "$NS" --sort-by=.lastTimestamp > "$EVIDENCE/events.txt" 2>&1 || true
  kubectl logs -n "$NS" deploy/strimzi-cluster-operator --tail=200 > "$EVIDENCE/operator.log" 2>&1 || true
  kubectl logs -n "$NS" "$KAFKA-dual-role-0" --tail=200 > "$EVIDENCE/broker.log" 2>&1 || true
}
finish() {
  code=$?
  trap - EXIT
  if [ "$code" -eq 0 ]; then STATUS=PASS; fi
  diagnostics
  printf '{"status":"%s","started_utc":"%s","finished_utc":"%s","namespace":"%s","kafka":"%s","topic":"%s","scope":"One-node ephemeral kind KRaft Strimzi Kafka integration smoke test; not 120-lab certification"}\n' "$STATUS" "$START" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$NS" "$KAFKA" "$TOPIC" > "$EVIDENCE/result.json"
  record "FINAL_STATUS=$STATUS"
  exit "$code"
}
trap finish EXIT

record "Checking isolated kind context"
case "$(kubectl config current-context)" in kind-*) ;; *) record "REFUSING non-kind context"; exit 1;; esac
kubectl create namespace "$NS"
record "Installing pinned Strimzi 0.47.0"
helm repo add strimzi https://strimzi.io/charts/
helm repo update strimzi
helm install strimzi-cluster-operator strimzi/strimzi-kafka-operator --version 0.47.0 --namespace "$NS" --set 'watchAnyNamespace=false' --wait --timeout 5m
record "Deploying one-node KRaft Kafka"
cat <<'YAML' | kubectl apply -n "$NS" -f -
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: dual-role
  labels:
    strimzi.io/cluster: qa-kafka
spec:
  replicas: 1
  roles:
    - controller
    - broker
  storage:
    type: ephemeral
  resources:
    requests:
      memory: 768Mi
      cpu: 200m
    limits:
      memory: 1536Mi
      cpu: "2"
  jvmOptions:
    -Xms: 256m
    -Xmx: 512m
---
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: qa-kafka
  annotations:
    strimzi.io/kraft: enabled
    strimzi.io/node-pools: enabled
spec:
  kafka:
    version: 3.9.1
    metadataVersion: 3.9-IV0
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
    config:
      offsets.topic.replication.factor: 1
      transaction.state.log.replication.factor: 1
      transaction.state.log.min.isr: 1
      default.replication.factor: 1
      min.insync.replicas: 1
  entityOperator:
    topicOperator: {}
    userOperator: {}
YAML
kubectl wait kafka/"$KAFKA" -n "$NS" --for=condition=Ready --timeout=360s
record "PASS kafka-ready"

kubectl run "$CLIENT" -n "$NS" --image=apache/kafka:3.9.1 --restart=Never --command -- sleep 900
kubectl wait pod/"$CLIENT" -n "$NS" --for=condition=Ready --timeout=180s
record "PASS client-ready"

kubectl exec -n "$NS" "$CLIENT" -- /opt/kafka/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP" --create --topic "$TOPIC" --partitions 1 --replication-factor 1
kubectl exec -n "$NS" "$CLIENT" -- /opt/kafka/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP" --describe --topic "$TOPIC" | tee "$EVIDENCE/topic.txt"
record "PASS topic-created"

printf '%s\n' "$MESSAGES" | kubectl exec -i -n "$NS" "$CLIENT" -- /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server "$BOOTSTRAP" --topic "$TOPIC"
record "PASS produce"
kubectl exec -n "$NS" "$CLIENT" -- /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server "$BOOTSTRAP" --topic "$TOPIC" --from-beginning --max-messages 3 --timeout-ms 30000 > "$EVIDENCE/received.txt"
printf '%s\n' "$MESSAGES" > "$EVIDENCE/expected.txt"
diff -u "$EVIDENCE/expected.txt" "$EVIDENCE/received.txt"
record "PASS consume-and-verify"
