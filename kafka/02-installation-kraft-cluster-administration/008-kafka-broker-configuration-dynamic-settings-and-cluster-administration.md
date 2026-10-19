# Chapter 008 — Kafka Broker Configuration, Dynamic Settings and Cluster Administration

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 02 — Installation, KRaft and Cluster Administration  
**Audience:** Kafka administrators, SREs, DBREs and platform engineers  
**Prerequisites:** Chapters 001–007, Kafka CLI, Bash, Docker Compose  
**Target:** Apache Kafka 4.1.x, KRaft mode  
**Publication:** Complete | **Live execution:** Pending | **Security review:** Pending

> **Safety:** Changing broker configurations can impact throughput, availability, retention, and security. All mutation commands below target a disposable Kafka lab. Production changes require change review, baseline capture, canary validation, and rollback. Do not apply unverified settings to controller or broker processes.

## 1. Learning objectives

After this chapter, you can:

1. Explain static broker properties, dynamic cluster defaults, and per-broker overrides.
2. Describe configuration precedence and identify effective settings.
3. Use `kafka-configs.sh` to inspect and safely modify supported dynamic configurations.
4. Separate broker-scoped settings from topic-level settings and client settings.
5. Distinguish rolling-restart changes from dynamically reconfigurable properties.
6. Validate an administrative change with automated assertions and rollback.
7. Investigate configuration drift, invalid values, performance regressions, and operational incidents.
8. Create a production-ready broker configuration change runbook.

## 2. Kafka configuration layers

Kafka configuration is distributed across multiple control surfaces:

```text
                    Git / IaC desired state
                             |
                  static broker.properties
                  or container environment
                             |
                     Broker startup
                             |
              Dynamic cluster-wide defaults
                             |
                 Dynamic broker overrides
                             |
                    Effective broker config
                             |
         Topic-level settings (retention, min ISR, etc.)
                             |
       Client producer/consumer settings (acks, retries, ...)
```

Kafka supports a subset of broker properties as dynamic configurations. Some properties are read-only after startup and require a rolling restart; some dynamic changes apply cluster-wide, while others can be overridden for a specific broker. Kafka's dynamic broker configuration mechanism and precedence are documented in the version-specific operations/configuration guide. **Do not assume every property can be changed dynamically.**

### 2.1 Configuration categories

| Category | Example | How changed | Risk |
|---|---|---|---|
| Static broker | `node.id`, `process.roles`, listener topology | Edit deployment configuration; restart according to approved procedure | Identity/quorum/connectivity outage |
| Dynamic broker | `num.network.threads` (where supported) | `kafka-configs.sh --entity-type brokers` | Throughput and resource contention |
| Dynamic cluster default | Supported broker property at default broker entity | `kafka-configs.sh --entity-default` | Broad blast radius |
| Topic | `retention.ms`, `min.insync.replicas` | Topic config API | Data retention/durability |
| Producer | `acks`, `linger.ms` | Client deployment | Write durability and latency |
| Consumer | `max.poll.interval.ms`, `enable.auto.commit` | Client deployment | Lag, rebalances, processing guarantees |
| Quotas | Producer/consumer throughput limits | Config API for relevant quota entities | Client throttling |

### 2.2 Precedence and persistence

For dynamically reconfigurable broker settings, an explicit per-broker override takes precedence over a dynamic cluster default, which takes precedence over a static configuration value, which in turn takes precedence over the Kafka built-in default. Verify the **effective** configuration and its source rather than relying only on the file on disk.

Dynamic changes are stored in Kafka cluster metadata and survive broker restarts when the same cluster state is retained. This is useful operationally but creates a drift hazard: changing a deployment manifest may not override an existing dynamic broker override. Maintain an authoritative inventory of static and dynamic settings.

### 2.3 KRaft considerations

KRaft controllers manage configuration metadata, but changing broker configs is not the same as editing the controller quorum. Broker configuration APIs require the appropriate administrative permissions in secured deployments. Some controller properties and quorum settings have separate restrictions. Always consult the Kafka version's configuration reference for update modes and valid ranges.

## 3. Enterprise configuration baseline

A production baseline should document:

- Kafka version, broker IDs, controller topology, and cluster ID.
- Listener and advertised-listener endpoints, inter-broker authentication, and TLS.
- Data and metadata storage locations, JVM heap, page cache, disk IOPS, and network capacity.
- Default partition count and replication factor for *new* topics.
- Log retention and cleanup policy, with per-topic exceptions.
- Replica fetcher threads, network and I/O thread counts, request queue sizing.
- Group coordinator settings and internal topic replication factors.
- Broker and client quotas, connection limits, and request-size controls.
- Monitoring/JMX, audit logs, deployment revision, and change ownership.

**Important:** Kafka built-in defaults are not necessarily production best practices. For example, a default replication factor of 1 is unsuitable for critical data even if a single-broker lab requires it. Define topic-specific durability contracts.

## 4. Lab prerequisites

Reuse the disposable Chapter 006 Kafka container, not a production broker:

```bash
cd kafka-ch06-lab
docker compose up -d
docker compose ps
docker exec kafka-ch06 /opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server kafka:9092 >/dev/null
```

Set convenient shell variables:

```bash
export KAFKA_C=kafka-ch06
export KAFKA_BS=kafka:9092
export KAFKA_BIN=/opt/kafka/bin
```

If the Chapter 006 Kafka 4.1.x container cannot start due to image-specific KRaft bootstrap behavior, fix that isolated environment using the official image instructions before proceeding. Do not reformat production storage or change its cluster ID.

## 5. Lab A — Inspect broker configuration

Read dynamic overrides for broker node 1:

```bash
docker exec "$KAFKA_C" "$KAFKA_BIN/kafka-configs.sh" \
  --bootstrap-server "$KAFKA_BS" \
  --entity-type brokers --entity-name 1 --describe
```

Read dynamic cluster-wide broker defaults:

```bash
docker exec "$KAFKA_C" "$KAFKA_BIN/kafka-configs.sh" \
  --bootstrap-server "$KAFKA_BS" \
  --entity-type brokers --entity-default --describe
```

Inspect all broker configs and sources, if supported by the pinned version:

```bash
docker exec "$KAFKA_C" "$KAFKA_BIN/kafka-configs.sh" \
  --bootstrap-server "$KAFKA_BS" \
  --entity-type brokers --entity-name 1 \
  --describe --all
```

**Expected:** dynamic-only descriptions may be empty when no overrides exist. With `--all`, the output includes effective/default values and may include synonyms/source information. Exact output formatting varies by Kafka release.

**SRE interpretation:** an empty dynamic override list does not mean the broker has no configuration; it means no matching dynamic override was returned.

## 6. Lab B — Safe dynamic change with rollback

For this disposable exercise, change the broker's `num.network.threads` to a conservative value. **First inspect its current effective value and supported update mode** in the Kafka 4.1.x broker configuration reference. This property is dynamically configurable in supported Kafka versions; validate the exact image before use.

Capture the baseline:

```bash
mkdir -p evidence-ch08

docker exec "$KAFKA_C" "$KAFKA_BIN/kafka-configs.sh" \
  --bootstrap-server "$KAFKA_BS" \
  --entity-type brokers --entity-name 1 --describe --all \
  > evidence-ch08/broker-before.txt

docker exec "$KAFKA_C" "$KAFKA_BIN/kafka-configs.sh" \
  --bootstrap-server "$KAFKA_BS" \
  --entity-type brokers --entity-name 1 --describe \
  > evidence-ch08/dynamic-before.txt
```

**Do not run the next command if a prior override already exists** unless you have recorded its value and prepared to restore that exact value. This lab assumes no existing override for `num.network.threads`.

```bash
docker exec "$KAFKA_C" "$KAFKA_BIN/kafka-configs.sh" \
  --bootstrap-server "$KAFKA_BS" \
  --entity-type brokers --entity-name 1 \
  --alter --add-config num.network.threads=4
```

Validate:

```bash
docker exec "$KAFKA_C" "$KAFKA_BIN/kafka-configs.sh" \
  --bootstrap-server "$KAFKA_BS" \
  --entity-type brokers --entity-name 1 --describe
```

Expected: a dynamic override for `num.network.threads=4` appears. Changing thread counts may not improve performance; the goal is to learn safe administrative control, not to tune production.

### 6.1 Rollback

If there was no prior dynamic override, remove only the override introduced by the lab:

```bash
docker exec "$KAFKA_C" "$KAFKA_BIN/kafka-configs.sh" \
  --bootstrap-server "$KAFKA_BS" \
  --entity-type brokers --entity-name 1 \
  --alter --delete-config num.network.threads
```

If a prior override existed, restore that **recorded value** instead of deleting it. Deleting an override causes Kafka to fall back to the next-precedence source, which may differ from the original effective configuration.

## 7. Lab C — Topic settings versus broker settings

Create a disposable topic:

```bash
docker exec "$KAFKA_C" "$KAFKA_BIN/kafka-topics.sh" \
  --bootstrap-server "$KAFKA_BS" \
  --create --if-not-exists --topic sre-config-ch08 \
  --partitions 2 --replication-factor 1
```

Inspect topic configuration:

```bash
docker exec "$KAFKA_C" "$KAFKA_BIN/kafka-configs.sh" \
  --bootstrap-server "$KAFKA_BS" \
  --entity-type topics --entity-name sre-config-ch08 --describe
```

Apply a lab-specific retention policy:

```bash
docker exec "$KAFKA_C" "$KAFKA_BIN/kafka-configs.sh" \
  --bootstrap-server "$KAFKA_BS" \
  --entity-type topics --entity-name sre-config-ch08 \
  --alter --add-config retention.ms=3600000
```

Verify:

```bash
docker exec "$KAFKA_C" "$KAFKA_BIN/kafka-configs.sh" \
  --bootstrap-server "$KAFKA_BS" \
  --entity-type topics --entity-name sre-config-ch08 --describe
```

**Risk:** retention changes affect how long records remain eligible for deletion. This is a disposable topic with no business data. Do not use a one-hour retention setting on production topics without retention and compliance approval.

Rollback:

```bash
docker exec "$KAFKA_C" "$KAFKA_BIN/kafka-configs.sh" \
  --bootstrap-server "$KAFKA_BS" \
  --entity-type topics --entity-name sre-config-ch08 \
  --alter --delete-config retention.ms
```

## 8. Lab D — Verify that administration does not break the data path

```bash
printf 'config-change-event-001\nconfig-change-event-002\n' | \
  docker exec -i "$KAFKA_C" "$KAFKA_BIN/kafka-console-producer.sh" \
  --bootstrap-server "$KAFKA_BS" \
  --topic sre-config-ch08 --producer-property acks=all

timeout 30s docker exec "$KAFKA_C" \
  "$KAFKA_BIN/kafka-console-consumer.sh" \
  --bootstrap-server "$KAFKA_BS" \
  --topic sre-config-ch08 --from-beginning --max-messages 2
```

**Expected:** both messages are readable. This smoke test confirms basic functionality only. It does not prove the dynamic change is beneficial or safe under production load.

## 9. Automated verification

Save as `verify-ch08.sh` in the Chapter 006 Compose directory. The script creates and deletes a unique topic and performs **read-only** broker config inspection; it does not change any broker settings.

```bash
#!/usr/bin/env bash
set -euo pipefail
C=kafka-ch06
BS=kafka:9092
BIN=/opt/kafka/bin
TOPIC="sre-ch08-check-$(date +%s)-$$"

run() { docker exec "$C" "$BIN/$1" "${@:2}"; }
cleanup() {
  run kafka-topics.sh --bootstrap-server "$BS" \
    --delete --topic "$TOPIC" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo '[1/5] Broker connectivity'
run kafka-broker-api-versions.sh --bootstrap-server "$BS" >/dev/null

echo '[2/5] Read broker dynamic configuration'
run kafka-configs.sh --bootstrap-server "$BS" \
  --entity-type brokers --entity-name 1 --describe >/dev/null

echo '[3/5] Create isolated test topic'
run kafka-topics.sh --bootstrap-server "$BS" --create \
  --topic "$TOPIC" --partitions 1 --replication-factor 1 >/dev/null

echo '[4/5] Produce event'
printf 'config-health-event\n' | docker exec -i "$C" \
  "$BIN/kafka-console-producer.sh" \
  --bootstrap-server "$BS" --topic "$TOPIC" \
  --producer-property acks=all

echo '[5/5] Consume and assert'
value="$(timeout 30s docker exec "$C" "$BIN/kafka-console-consumer.sh" \
  --bootstrap-server "$BS" --topic "$TOPIC" \
  --from-beginning --max-messages 1)"
test "$value" = 'config-health-event' || \
  { echo "FAIL: unexpected message: $value"; exit 1; }
echo 'PASS: config read, topic lifecycle and produce/consume'
```

```bash
chmod +x verify-ch08.sh
./verify-ch08.sh
```

**Coverage limitation:** the script does not prove dynamic update/rollback, drift detection, or performance impact. Those require separately captured lab evidence and load tests.

## 10. Production configuration change workflow

### 10.1 Before change

1. Identify the exact cluster, broker IDs, Kafka version, and config entity.
2. Confirm the property is dynamically updateable or requires restart.
3. Record current effective value **and source**, not only the local config file.
4. Check all existing cluster-wide defaults and per-broker overrides.
5. Estimate blast radius and impact on latency, throughput, memory, disk, and durability.
6. Establish baseline SLOs, broker health, partition ISR, and client error rates.
7. Define canary scope, rollback action, owner, approval, and observation window.

### 10.2 During change

1. Apply to one disposable or canary broker when supported and appropriate.
2. Confirm the configuration API accepted the update.
3. Read back the effective value and source.
4. Watch produce/fetch latency, request queue time, CPU, network, GC, ISR, and error budgets.
5. Proceed only if the canary satisfies acceptance criteria.

### 10.3 After change

1. Validate application producer and consumer behavior.
2. Compare metrics with the baseline under comparable load.
3. Record exact commands, operator, timestamp, change ticket, and effective values.
4. Reconcile Git/IaC desired state with dynamic overrides.
5. Restore previous settings if the change violates thresholds.

**Rollback is not always instantaneous.** Some effects (e.g., retention deletion or previously throttled workloads) cannot be reversed merely by restoring the old config value.

## 11. Enterprise incident scenarios

### Incident 1 — Broker performance regression after tuning

**Signal:** produce latency and request queue time increase after a thread-count change.

**Hypotheses:** excessive thread scheduling, CPU contention, changed request mix, unrelated deployment.

**Investigate:** change audit, effective config, CPU saturation, request handler idle percent, network processor idle percent, GC, disk latency.

**Mitigate:** restore recorded previous dynamic value; verify metrics and application behavior recover.

### Incident 2 — Configuration drift between brokers

**Signal:** different brokers behave differently despite identical deployment manifests.

**Hypotheses:** broker-specific dynamic overrides, old static files, stale automation, version skew.

**Investigate:** `kafka-configs.sh --describe --all` for each broker, deployment revision, config source, audit trail.

**Mitigate:** reconcile effective state with approved baseline. Avoid blanket deletion of overrides without understanding their purpose.

### Incident 3 — Unexpected retention loss

**Signal:** consumers cannot replay expected historical records.

**Hypotheses:** reduced `retention.ms`, retention bytes limit, topic-level override, compaction, deleted topic.

**Investigate:** topic config history, broker defaults, log cleanup policy, retention timestamps, consumer offsets.

**Mitigate:** stop further destructive changes, restore policy, recover missing data from upstream source/backups where possible. Increasing retention cannot restore already deleted records.

### Incident 4 — Cluster-wide default causes widespread errors

**Signal:** many brokers degrade simultaneously after a default broker config update.

**Hypotheses:** broad dynamic default applied without canary, incompatibility, capacity assumptions.

**Investigate:** cluster default config, per-broker overrides, timing of errors, metadata/audit history.

**Mitigate:** revert the specific default and validate each broker's effective config; do not overwrite intentional per-broker exceptions.

### Incident 5 — Static setting changed without restart

**Signal:** manifest shows new value but broker continues old behavior.

**Hypotheses:** property requires restart, dynamic override supersedes file, deployment not rolled.

**Investigate:** Kafka property update mode, effective config source, process uptime, rollout status.

**Mitigate:** schedule a reviewed rolling restart where required; avoid simultaneous broker/controller restarts.

### Incident 6 — Unauthorized administrative mutation

**Signal:** unexpected config update, audit entry, or availability impact.

**Hypotheses:** excessive ACLs, leaked admin credential, unreviewed automation.

**Investigate:** audit logs, principal identity, source IP, change history, affected entities.

**Mitigate:** restrict administrative access, rotate compromised credentials where appropriate, restore desired config, preserve evidence and engage security response.

## 12. Troubleshooting matrix

| Symptom | First safe check | Avoid |
|---|---|---|
| `InvalidConfigurationException` | Property validity, supported update mode, value range | Blindly trying unrelated settings |
| `ClusterAuthorizationException` | Admin principal/ACLs | Disabling authentication |
| Dynamic override not visible | Entity type/name and CLI bootstrap target | Assuming update succeeded |
| Static file value ignored | Effective config source and dynamic overrides | Restarting blindly |
| Broker restarts after config change | Startup logs, listener/storage identity | Reformatting volumes |
| ISR degrades after tuning | Broker resource metrics, replication fetch | Lowering min ISR without approval |
| Topic retention unexpectedly short | Topic and broker retention precedence | Resetting consumer offsets |
| Client throttling rises | Quota entity configuration and broker metrics | Removing all quotas globally |

## 13. SRE runbook — configuration-induced incident

**Trigger:** availability, latency, data retention, or security regression correlated with a Kafka configuration change.

1. **Declare scope:** cluster, broker IDs, topics, impacted applications, customer impact, start time.
2. **Freeze further mutations:** pause automated config reconciliation and unrelated changes as approved.
3. **Preserve evidence:** effective configs, sources, dynamic overrides, deployment manifests, audit trail, metrics and logs.
4. **Correlate:** compare change timestamp with producer errors, fetch latency, ISR, GC, CPU and disk saturation.
5. **Classify:** dynamic broker override, cluster default, static startup property, topic setting, or client setting.
6. **Rollback precisely:** restore the recorded previous value or delete only a newly introduced override if there was none.
7. **Verify recovery:** confirm effective config, healthy partitions, client success, lag, and SLO recovery.
8. **Assess irreversibility:** determine whether retention deletion, duplicate processing, or data loss occurred.
9. **Communicate:** update stakeholders with impact, mitigation, residual risk, and next checkpoint.
10. **Prevent recurrence:** enforce approvals, drift alerts, canary policy, configuration tests, and least privilege.

### 13.1 Suggested SLO and alert signals

- Broker request latency and request handler/network processor idle percentages.
- Produce/fetch error rates and client timeout rates.
- Under-replicated and under-min-ISR partition counts.
- CPU utilization, GC pause time, heap pressure, disk I/O wait.
- Consumer lag and end-to-end processing age.
- Administrative configuration changes outside approved windows.
- Drift between desired static configuration and effective dynamic configuration.

Metric names depend on Kafka version, JMX exporters and client libraries. Validate alert semantics before production rollout.

## 14. Production readiness checklist

- [ ] Version-pinned broker config reference and update modes documented.
- [ ] Effective configuration and source captured for every broker.
- [ ] Static and dynamic config ownership established.
- [ ] Git/IaC reconciliation accounts for dynamic overrides.
- [ ] Administrative access restricted and audited.
- [ ] Canaries and rollback values prepared.
- [ ] Rolling restart plan available for static changes.
- [ ] Durability, retention, quota and security changes require extra review.
- [ ] Dashboards and alerts cover config-induced failures.
- [ ] Configuration recovery drill completed in staging.

## 15. Assessment — 100 points

| Task | Points |
|---|---:|
| Explain static, dynamic, cluster-default and per-broker settings | 10 |
| Describe configuration precedence and sources | 10 |
| Inspect broker configs with Kafka CLI | 10 |
| Safely change a supported dynamic property | 10 |
| Restore prior effective configuration | 10 |
| Change and revert a disposable topic retention setting | 10 |
| Verify produce/consume after administration | 10 |
| Diagnose a configuration drift scenario | 10 |
| Explain retention and security change risks | 10 |
| Produce a complete configuration incident runbook | 10 |

**Pass target:** 80/100, with evidence of safe change and rollback. Publication does not imply any lab or assessment was executed.

## 16. Cleanup

If `sre-config-ch08` was created only for this chapter, delete it after confirming no needed data remains:

```bash
docker exec kafka-ch06 /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:9092 \
  --delete --topic sre-config-ch08
```

Verify the lab's dynamic broker override has been restored or removed as intended:

```bash
docker exec kafka-ch06 /opt/kafka/bin/kafka-configs.sh \
  --bootstrap-server kafka:9092 \
  --entity-type brokers --entity-name 1 --describe
```

Retain the Chapter 006 lab for the next chapter, or destroy **only** the dedicated disposable Compose project after saving evidence. `docker compose down -v` permanently deletes its Kafka data volume.

## 17. References

- [Apache Kafka configuration documentation](https://kafka.apache.org/documentation/)
- [Kafka broker configuration reference](https://kafka.apache.org/documentation/#brokerconfigs)
- [Kafka operations](https://kafka.apache.org/documentation/#operations)
- [Kafka topic configuration reference](https://kafka.apache.org/documentation/#topicconfigs)

**Next:** Chapter 009 — Kafka Broker Lifecycle, Rolling Restarts, Maintenance and Upgrade Operations.

---

**Verification policy:** GitHub publication verifies source presence only. Live lab results, performance conclusions, and security review must be independently recorded.
