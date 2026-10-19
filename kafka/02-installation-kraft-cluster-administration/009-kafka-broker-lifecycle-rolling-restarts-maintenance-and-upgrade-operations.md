# Chapter 009 — Kafka Broker Lifecycle, Rolling Restarts, Maintenance and Upgrade Operations

**Track:** Apache Kafka Administration, SRE & Platform Engineering  
**Part 02:** Installation, KRaft and Cluster Administration  
**Audience:** Kafka administrators, SREs, DBREs and platform engineers  
**Prerequisites:** Chapters 001–008; Docker Compose, Bash, Kafka CLI  
**Lab target:** Disposable three-node Kafka 4.1.x KRaft cluster from Chapter 004  
**Status:** Published; live execution and security review pending

> **Safety:** This chapter stops and starts Kafka processes. Run commands only in the isolated Chapter 004 lab. Never restart a production Kafka controller or broker, change software versions, or delete log directories without approved change control, capacity review, backups/recovery plan, and documented rollback constraints.

## 1. Learning objectives

After this chapter you should be able to:

1. Describe broker startup, registration, shutdown, fencing and recovery.
2. Plan one-at-a-time rolling maintenance without exhausting ISR or controller quorum.
3. Explain why combined-role KRaft labs require extra caution.
4. Build preflight, per-node, and postflight acceptance gates.
5. Capture leader, replica, metadata quorum, client, and storage evidence.
6. Distinguish safe process restart from version upgrade and protocol/feature finalization.
7. Diagnose stalled startups, offline partitions, controller instability and failed rollouts.
8. Execute an SRE change runbook with abort and recovery procedures.

## 2. Broker lifecycle and operational architecture

```text
Config + persistent log dirs
           |
       JVM starts
           |
  Load cluster/node identity
           |
  Contact KRaft controller
           |
  Broker registration / fencing state
           |
  Recover logs and metadata
           |
  Become eligible for assignments
           |
  Serve produce / fetch requests
           |
    Maintenance / shutdown
           |
  Client retries + leader movement
           |
  Restart -> catch up -> ISR healthy
```

Kafka's broker lifecycle is not simply “container running.” A process may be alive but not registered, unfenced, reachable from clients, or able to serve partition leadership. After restart, replica catch-up can take time; a broker becoming reachable is **not** proof that replication has recovered.

### 2.1 Broker states and checks

| Phase | Typical evidence | What can still be wrong |
|---|---|---|
| Process starts | systemd/Docker reports running | Incorrect node ID, storage, listeners |
| Metadata contact | controller quorum available | Broker registration/fencing incomplete |
| Client API reachable | `kafka-broker-api-versions.sh` succeeds | Offline partitions, bad advertised listeners |
| Replica catch-up | ISR returns to assigned replicas | Latency/consumer lag may remain high |
| Stable service | Error rate, latency and lag normalize | Business events may still require reconciliation |

### 2.2 KRaft combined roles versus production separation

The Chapter 004 cluster runs **three combined broker/controller nodes**. Stopping one removes both a data replica and a metadata voter. A two-voter majority remains; stopping a second risks metadata quorum loss. Production often separates controllers from brokers to reduce correlated control/data-plane failures. This lab tests **one node at a time only**.

## 3. Rolling restart fundamentals

A rolling restart processes one broker at a time, with full health gates between nodes. It is safer than restarting all brokers simultaneously, but it is not automatically safe: some partitions may already have degraded ISR, replicas may share failure domains, and an in-flight reassignment or controller election can increase risk.

### 3.1 Preflight gate

Do not start maintenance until:

- Cluster and environment are confirmed, change ticket approved, and owners notified.
- Broker and controller health are stable; quorum majority is present.
- No offline partitions; no sustained under-replication or under-min-ISR.
- Required replica placements and available ISR can tolerate one broker loss.
- Producer error rates, consumer lag, and end-to-end event age are within thresholds.
- Storage utilization, disk health, network and CPU capacity are adequate.
- No competing broker upgrades, reassignments, backups with heavy I/O, or incident response.
- Exact versions, binaries, configs, storage mounts and rollback compatibility are recorded.
- Alerting, incident bridge, abort authority and recovery steps are ready.

For RF=3 and `min.insync.replicas=2`, a **healthy three-replica ISR** usually tolerates one broker stop while retaining two ISR replicas. If a partition already has ISR=2, stopping one of those members can cause `acks=all` writes to fail.

### 3.2 Post-node gate

Before advancing to the next broker, require:

1. The restarted broker is reachable and registered.
2. No offline partitions or unexpected controller quorum degradation.
3. All replicas assigned to the broker have caught up and rejoined ISR.
4. Produce/fetch error rates and p95/p99 latency return to approved thresholds.
5. Consumer lag is stable or decreasing; no unexpected rebalance storm.
6. Controller election/leader movement has stabilized.
7. Evidence is saved with timestamps.

A fixed sleep is **not** a substitute for these checks.

## 4. Upgrade strategy and compatibility

Distinguish three operations:

| Operation | Typical change | Rollback considerations |
|---|---|---|
| Restart | Same binary and configuration | Usually operationally reversible if storage intact |
| Config rollout | Static properties or deployment manifest change | Some changes persist dynamically or have irreversible effects |
| Version upgrade | Kafka broker/controller software and potentially metadata feature level | Compatibility and feature finalization can constrain downgrade |

**Recommended process:** pin exact current and target Kafka versions; read the version-matched upgrade guide; validate client compatibility and mixed-version support; back up configurations and recovery evidence; upgrade one supported role/node at a time; monitor each stage; finalize feature/metadata levels **only when supported and intentionally approved**.

Do **not** assume every Kafka version transition supports downgrade after feature finalization or metadata changes. The lab below performs **same-version rolling restarts only**, not a software upgrade.

### 4.1 Controller-specific upgrade caution

Controller and broker rollout ordering is version-dependent, particularly with KRaft and changes to metadata features. Follow the exact release's supported upgrade sequence. Never extrapolate the Chapter 004 combined-role restart order into a production dedicated-controller upgrade procedure.

## 5. Lab prerequisites and baseline

Use the isolated Chapter 004 Compose directory with the three containers:

```bash
cd kafka-ch04-lab
docker compose config --quiet
docker compose up -d
docker compose ps

export KAFKA_C=kafka-ch04-broker1
export KAFKA_BS=broker1:9092
export KAFKA_BIN=/opt/kafka/bin
```

Check Kafka API and quorum:

```bash
docker exec "$KAFKA_C" "$KAFKA_BIN/kafka-broker-api-versions.sh" \
  --bootstrap-server "$KAFKA_BS" >/dev/null

docker exec "$KAFKA_C" "$KAFKA_BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$KAFKA_BS" describe --status
```

The Chapter 004 lab uses Kafka 4.1.x with a fixed KRaft voter set. Official image startup and quorum formatting details are version-specific. If it does not bootstrap in your environment, fix the disposable configuration using the pinned release's documentation; do not format production metadata volumes.

## 6. Lab A — Prepare a replicated test topic

```bash
docker exec "$KAFKA_C" "$KAFKA_BIN/kafka-topics.sh" \
  --bootstrap-server "$KAFKA_BS" --create --if-not-exists \
  --topic sre-maintenance-ch09 \
  --partitions 3 --replication-factor 3 \
  --config min.insync.replicas=2

docker exec "$KAFKA_C" "$KAFKA_BIN/kafka-topics.sh" \
  --bootstrap-server "$KAFKA_BS" --describe \
  --topic sre-maintenance-ch09
```

Verify each partition's `Replicas` and `Isr` contain three broker IDs. `--if-not-exists` does not validate an existing topic's configuration; investigate discrepancies before proceeding.

Produce a baseline:

```bash
printf '%s\n' \
  'order-100:created' 'order-100:paid' 'order-200:created' | \
docker exec -i "$KAFKA_C" "$KAFKA_BIN/kafka-console-producer.sh" \
  --bootstrap-server "$KAFKA_BS" --topic sre-maintenance-ch09 \
  --producer-property acks=all \
  --producer-property enable.idempotence=true \
  --property parse.key=true --property key.separator=:
```

## 7. Lab B — Capture change evidence

```bash
mkdir -p evidence-ch09

docker exec "$KAFKA_C" "$KAFKA_BIN/kafka-topics.sh" \
  --bootstrap-server "$KAFKA_BS" --describe \
  --topic sre-maintenance-ch09 > evidence-ch09/topic-before.txt

docker exec "$KAFKA_C" "$KAFKA_BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$KAFKA_BS" describe --status \
  > evidence-ch09/quorum-before.txt

docker compose ps > evidence-ch09/containers-before.txt
```

Store evidence locally; do not publish real cluster identities, internal hostnames, or secrets from production.

## 8. Lab C — One-broker rolling restart

**Only restart broker2** for this exercise. Broker1 remains available for CLI operations. Verify all three replicas are healthy before the stop.

```bash
docker compose stop broker2
sleep 15

docker exec kafka-ch04-broker1 "$KAFKA_BIN/kafka-topics.sh" \
  --bootstrap-server broker1:9092 --describe \
  --topic sre-maintenance-ch09 \
  > evidence-ch09/topic-degraded.txt

docker exec kafka-ch04-broker1 "$KAFKA_BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server broker1:9092 describe --status \
  > evidence-ch09/quorum-degraded.txt
```

**Expected:** broker2 leaves ISR after failure detection. If it was a partition leader, leadership moves to an eligible ISR replica. If broker2 was the active controller, the remaining two controllers elect a new metadata leader. The exact assignments depend on the cluster.

While broker2 is stopped, attempt an acknowledged write:

```bash
printf 'order-300:created-during-maintenance\n' | \
docker exec -i kafka-ch04-broker1 \
  "$KAFKA_BIN/kafka-console-producer.sh" \
  --bootstrap-server broker1:9092 \
  --topic sre-maintenance-ch09 \
  --producer-property acks=all \
  --producer-property delivery.timeout.ms=15000 \
  --property parse.key=true --property key.separator=:
```

**Expected:** if two eligible ISR replicas remain, `acks=all` can succeed. A failure is an investigation signal; do not lower `min.insync.replicas`.

Restart broker2:

```bash
docker compose start broker2
```

Poll for convergence instead of relying on a fixed sleep:

```bash
for attempt in $(seq 1 30); do
  description="$(docker exec kafka-ch04-broker1 \
    "$KAFKA_BIN/kafka-topics.sh" --bootstrap-server broker1:9092 \
    --describe --topic sre-maintenance-ch09)"
  printf '%s\n' "$description"
  # Educational parser: matches three numeric IDs in the ISR for each partition.
  count="$(printf '%s\n' "$description" | grep -Ec 'Isr: [0-9]+,[0-9]+,[0-9]+' || true)"
  if [ "$count" -eq 3 ]; then
    echo 'ISR converged on all 3 partitions'
    break
  fi
  sleep 5
done
```

**Operator check:** if ISR has not recovered after the loop, **stop the maintenance**, investigate logs and replica lag, and do not restart another broker. The parser assumes the CLI's normal comma-separated ISR formatting and should be adjusted for a different release.

## 9. Lab D — Post-maintenance data validation

```bash
docker exec kafka-ch04-broker1 "$KAFKA_BIN/kafka-topics.sh" \
  --bootstrap-server broker1:9092 --describe \
  --topic sre-maintenance-ch09 \
  > evidence-ch09/topic-after.txt

docker exec kafka-ch04-broker1 "$KAFKA_BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server broker1:9092 describe --status \
  > evidence-ch09/quorum-after.txt

timeout 30s docker exec kafka-ch04-broker1 \
  "$KAFKA_BIN/kafka-console-consumer.sh" \
  --bootstrap-server broker1:9092 \
  --topic sre-maintenance-ch09 --from-beginning \
  --max-messages 4 --property print.key=true
```

**Expected:** the four test events are readable and broker2 has returned to ISR. Kafka does not guarantee ordering across partitions, so compare records by key and offset rather than relying on global output order.

## 10. Automated preflight and postflight acceptance script

Save as `verify-ch09.sh` in the dedicated Compose directory. This script is **read-only** and does not restart nodes.

```bash
#!/usr/bin/env bash
set -euo pipefail
C=kafka-ch04-broker1
BS=broker1:9092
BIN=/opt/kafka/bin
TOPIC=sre-maintenance-ch09

echo '[1/5] Confirm all three lab containers running'
for service in broker1 broker2 broker3; do
  docker compose ps --status running --services | grep -qx "$service" || \
    { echo "FAIL: $service not running"; exit 1; }
done

echo '[2/5] Broker API readiness'
docker exec "$C" "$BIN/kafka-broker-api-versions.sh" \
  --bootstrap-server "$BS" >/dev/null

echo '[3/5] Metadata quorum status'
docker exec "$C" "$BIN/kafka-metadata-quorum.sh" \
  --bootstrap-server "$BS" describe --status

echo '[4/5] Topic replica and ISR readiness'
desc="$(docker exec "$C" "$BIN/kafka-topics.sh" \
  --bootstrap-server "$BS" --describe --topic "$TOPIC")"
printf '%s\n' "$desc"
partitions="$(printf '%s\n' "$desc" | grep -c 'Partition:' || true)"
healthy="$(printf '%s\n' "$desc" | grep -Ec 'Isr: [0-9]+,[0-9]+,[0-9]+' || true)"
test "$partitions" -eq 3 && test "$healthy" -eq 3 || \
  { echo "FAIL: partitions=$partitions healthy_ISR=$healthy"; exit 1; }

echo '[5/5] Validate metadata read path'
docker exec "$C" "$BIN/kafka-topics.sh" \
  --bootstrap-server "$BS" --list >/dev/null

echo 'PASS: broker process, quorum CLI, topic metadata and ISR preflight'
```

```bash
chmod +x verify-ch09.sh
./verify-ch09.sh
```

**Scope:** This validates basic cluster health and the lab topic's ISR. It does not check production SLOs, security, rack placement, controller voter health at every node, or binary upgrade compatibility. Record the exit code and output as evidence.

## 11. Rolling maintenance pseudocode for production

This is a **workflow**, not an unattended restart script:

```text
for each approved broker in reviewed maintenance order:
    require current change approval and no active incident
    capture controller quorum and partition ISR
    require healthy partitions and enough ISR after planned loss
    require acceptable producer errors, latency and consumer lag
    apply supported broker shutdown/drain procedure
    restart or upgrade this broker only
    wait for registration, replica catch-up and ISR restoration
    require controller health and stable client metrics
    if any gate fails:
        stop rollout; preserve evidence; execute rollback/escalation
    else:
        record results; proceed to next approved broker
```

Avoid “blind rolling restarts” that proceed after a fixed sleep regardless of cluster health. Automate **gates**, not just restart commands.

## 12. Production incident scenarios

### Scenario 1 — Broker fails to rejoin after restart

**Symptoms:** process running but node missing from cluster, assigned replicas out of ISR.

**Hypotheses:** wrong `node.id`, changed cluster ID, listener/DNS error, storage permission failure, startup incompatibility.

**Investigate:** broker logs, storage mounts, `meta.properties`, effective configs, controller registration, network connectivity.

**Mitigate:** stop further restarts, restore the original configuration/storage identity, recover the affected node using supported procedures.

### Scenario 2 — Under-min-ISR during maintenance

**Symptoms:** `NotEnoughReplicas` producer failures with `acks=all`.

**Hypotheses:** maintenance started with ISR already degraded, follower fell behind, two correlated failures.

**Investigate:** before/during ISR snapshots, broker health, replication lag, `min.insync.replicas`.

**Mitigate:** restore replicas; do not lower min ISR without explicit business-risk approval.

### Scenario 3 — Controller election instability

**Symptoms:** metadata requests time out, leader epochs change repeatedly.

**Hypotheses:** controller role colocated with restarted brokers, network instability, quorum placement, storage latency.

**Investigate:** quorum status and replication, controller logs, election rate, voter connectivity.

**Mitigate:** pause maintenance and restore stable majority; avoid simultaneous controller restarts.

### Scenario 4 — Consumer lag surge after broker restart

**Symptoms:** fetch retries, lag spike, group rebalances, elevated processing age.

**Hypotheses:** leader movement, network timeouts, client retry settings, consumer processing bottleneck.

**Investigate:** partition lag distribution, fetch latency, rebalance logs, leader history, downstream dependencies.

**Mitigate:** allow recovery within approved thresholds, address client instability, and verify business processing completeness.

### Scenario 5 — Version upgrade causes incompatible behavior

**Symptoms:** startup failure or protocol errors after introducing a new binary.

**Hypotheses:** unsupported version jump, incompatible metadata feature level, plugin/client incompatibility, invalid configuration.

**Investigate:** exact binary versions, official upgrade compatibility matrix, feature level, logs, config diff.

**Mitigate:** stop rollout; use only documented rollback procedures. Downgrade may be unsupported after metadata feature finalization.

### Scenario 6 — Disk fills during replica catch-up

**Symptoms:** broker cannot complete recovery, disk usage rises, replica fetch errors.

**Hypotheses:** insufficient headroom, retention/segment growth, compaction backlog, filesystem problem.

**Investigate:** disk utilization, log directory errors, replica lag, retention policy, storage metrics.

**Mitigate:** restore capacity safely; do not delete arbitrary partition log files to make space.

## 13. Troubleshooting matrix

| Signal | First safe check | Abort condition |
|---|---|---|
| Broker unreachable after restart | Process logs, node ID, listeners | Registration not restored |
| ISR remains below RF | Replica fetch lag, storage/network | No convergence within window |
| Offline partitions | Leader/ISR assignments | Any sustained offline partition |
| Metadata quorum unhealthy | Voter status, controller logs | Majority at risk |
| Produce error rate rises | ISR, request latency, client logs | SLO/error-budget breach |
| Consumer lag increases | Per-partition lag, fetch/rebalance | Sustained backlog outside threshold |
| Disk pressure | Volume utilization and log errors | Headroom below approved floor |
| Binary rollback requested | Version/feature compatibility | Downgrade not explicitly supported |

## 14. Production SRE maintenance runbook

**Trigger:** approved broker restart, OS patching, configuration rollout or Kafka software upgrade.

1. **Change initiation:** record ticket, cluster, owners, scope, window, Kafka versions and rollback decision-maker.
2. **Preflight:** confirm quorum, RF/ISR, offline partitions, SLOs, storage capacity, backups and competing changes.
3. **Capture baseline:** topic leader/ISR snapshots, controller status, broker metrics, producer/consumer error rates, lag.
4. **Canary:** choose a reviewed low-risk broker, consider leader distribution and failure-domain placement.
5. **Change one node:** perform approved graceful shutdown and restart/upgrade; never stop another until gates pass.
6. **Validate recovery:** registration, partition leadership, ISR catch-up, metadata stability, client errors, business event age.
7. **Continue or abort:** advance only after all gates pass; otherwise stop, restore previous supported state, escalate.
8. **Postflight:** confirm all nodes, replicas, SLOs, consumer groups and end-to-end data flow.
9. **Close:** publish change evidence, residual risks, deviations, rollback actions, and lessons learned.

### Rollback decision tree

```text
Health gate failed?
   |
   +-- Broker config-only change?
   |      Restore previous approved config; restart if required
   |
   +-- Same-version restart?
   |      Diagnose startup/storage/network; restore node
   |
   +-- Kafka version upgrade?
          Check official downgrade compatibility and metadata feature state
          If supported: follow documented rollback
          Otherwise: halt and escalate recovery, do not force downgrade
```

## 15. Production observability and SLO signals

Track broker availability, active controller stability, offline partitions, under-replicated partitions, under-min-ISR partitions, replica catch-up time, leader elections, producer error rate, produce/fetch latency, disk usage, consumer lag and end-to-end event processing age.

**Example acceptance policy (illustrative):** zero sustained offline partitions; full ISR restoration before proceeding; no sustained increase in client errors; p99 latency and consumer processing age within the application's agreed maintenance thresholds. Establish numerical thresholds from historical baselines and contractual SLOs, not generic values.

## 16. Enterprise readiness checklist

- [ ] Maintenance change reviewed, owned and scheduled.
- [ ] Version-specific Kafka upgrade documentation read.
- [ ] Controller quorum and broker failure domains assessed.
- [ ] RF/min ISR sufficient for one-node maintenance.
- [ ] Storage, network and replica catch-up capacity available.
- [ ] Static/dynamic configuration sources captured.
- [ ] Preflight and postflight scripts tested in staging.
- [ ] Broker-by-broker gates and abort criteria documented.
- [ ] Binary/feature compatibility and rollback limits understood.
- [ ] End-to-end producer/consumer validation included.
- [ ] Incident bridge, communication and escalation ready.
- [ ] Evidence retained for change audit.

## 17. Assessment — 100 points

| Requirement | Points |
|---|---:|
| Explain broker startup, registration and fencing | 10 |
| Differentiate broker and controller lifecycle risks | 10 |
| Establish a complete preflight gate | 10 |
| Capture leader/ISR and quorum evidence | 10 |
| Safely restart one lab broker | 10 |
| Verify acknowledged writes during one-broker loss | 10 |
| Validate ISR catch-up before proceeding | 10 |
| Explain upgrade compatibility and feature finalization | 10 |
| Diagnose a failed rolling restart | 10 |
| Produce an auditable maintenance and rollback runbook | 10 |

**Pass target:** 80/100 with no unsafe action and independently captured evidence. Publication alone does not constitute a completed lab or approved production procedure.

## 18. Cleanup

Keep `evidence-ch09` outside the disposable Kafka data volumes. Delete only this chapter's test topic when no longer needed:

```bash
docker exec kafka-ch04-broker1 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server broker1:9092 --delete \
  --topic sre-maintenance-ch09
```

Retain the three-broker lab for Chapter 010 if desired. To destroy the dedicated lab only, verify the Compose project and run `docker compose down -v` **only after confirming the permanent volume deletion is intended**.

## 19. References and next chapter

- [Apache Kafka documentation](https://kafka.apache.org/documentation/)
- [Kafka operations and upgrade guide](https://kafka.apache.org/documentation/#upgrade)
- [Kafka KRaft operations](https://kafka.apache.org/documentation/#kraft)
- [Kafka configuration reference](https://kafka.apache.org/documentation/#brokerconfigs)

**Next:** Chapter 010 — Kafka Installation, KRaft and Cluster Administration Acceptance Capstone.

---

**Verification boundary:** GitHub publication confirms the written material exists. Docker labs, controlled failures, upgrade procedures, automated tests and security review remain pending until executed and evidenced.
