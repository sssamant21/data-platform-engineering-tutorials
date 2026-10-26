# Chapter 031 bounded secure native performance acceptance

Run `python kafka/qa/run_chapter_031.py` independently on the persistent
Kafka 4.0.0/KRaft/Strimzi 0.47.0 SCRAM fixture. This is actual execution of
Kafka's bundled producer/consumer performance tools, with functional data and
health acceptance. A single-host kind result is not production capacity evidence.

## Experimental contract and checks

- Require ready RF3/minISR2 brokers, actual PVC/PV/StorageClass mappings, no node
  pressure and at least 256MiB free with less than 90% shared-filesystem use.
  Record quotas, node placement, immutable matching image and public config hash.
  local-path filesystem headroom is not an enforced per-PVC storage quota.
- Use a dedicated token-free ServiceAccount, non-root client Jobs, read-only CA
  and password projections, and literal topic/group ACLs. Only the benchmark
  Pod generates credential-bearing configuration files (0600, private temporary
  directory); files are deleted in finally. No passwords enter CLI flags, runner
  files, environment variables or evidence.
- Run one separate 120-record warmup, then nine 1,200-record x 1KiB trials at
  offered caps 200/400/800 records/s. Three balanced orders place each rate in
  every order position once. Total replicated payload is about 32MiB, excluding
  Kafka overhead. Native producer settings remain acks=all, idempotence=true,
  compression=none, linger=0 and batch.size=16384 throughout.
- Use native `--producer.config`, `--print-metrics`, and `--consumer.config`
  flags. Record exact safe commands, exit codes, client version, raw summaries,
  timestamps, per-trial outputs and Pod resource allocation. Help may return 1 only with validated expected flags; benchmark commands
  still require exit 0. Launcher logs use the private writable temporary directory.
  Each native worker
  heap is bounded at 128MiB; the complete client Pod has 1 CPU/768MiB limits.
- Poll real Kafka Admin leader/full-ISR/quorum state while native processes run;
  kill their process tree and fail on unhealthy observations or bounded process
  deadlines (producer 90s, consumer 60s). Check broker Pod UID/readiness/restarts
  between trials. This is actual periodic polling, not Prometheus SLO monitoring.
- Parse conservatively against the tagged Kafka 4.0 tool contracts. A producer
  exit code alone is insufficient: require exact successful count, zero native
  record-error counter, finite ordered latency percentiles and valid rates.
  Preserve retries separately. Consumer count and payload bytes must match.
- Independently regenerate the native tool's SplittableRandom(0) uppercase payload
  multiset, verify every consumed SHA256/count/byte total, and commit/recheck all
  captured partition ends. Kafka's sticky partition distribution is not claimed
  to be balanced or a partition-scaling experiment.
- Retain all nine trials, including slow results; failed/current/unexecuted trial
  states remain in JSON. Report median achieved rate and sample standard deviation
  per offered rate, retaining per-trial p99. No averaged p99 is called a global
  percentile. Zero-millisecond native fetch intervals yield explicit unmeasurable
  rates rather than fabricated finite rates.

The tagged [producer tool](https://github.com/apache/kafka/blob/4.0.0/tools/src/main/java/org/apache/kafka/tools/ProducerPerformance.java),
[consumer tool](https://github.com/apache/kafka/blob/4.0.0/tools/src/main/java/org/apache/kafka/tools/ConsumerPerformance.java)
and [metrics formatter](https://github.com/apache/kafka/blob/4.0.0/tools/src/main/java/org/apache/kafka/tools/ToolsUtils.java)
define these parsers. The producer counts only successful callbacks but can print
callback errors without a failing process status. Its MB/sec label uses 1024^2;
raw units/rounding are retained alongside explicitly labeled payload MiB.

## Limits and assessment

Fresh native processes include connection startup; separate warmup does not make
these steady-state or sustained storage tests. Client cgroup snapshots include
startup, health polling and auditing. Broker CPU/network/IOPS, provider burst
credits and production monitoring are unavailable and explicitly recorded as a
measurement gap. No low-resource-use inference or definitive bottleneck is made.

Message-size, acks, batching/compression, partition/concurrency scaling, matched
plaintext/security overhead and multi-node placement experiments are NOT_EXECUTED.
No production saturation threshold, confidence interval, performance score or
independent assessor approval is invented. The full critical-gate performance
assessment remains NOT_YET_ACCEPTED and enterprise certification NOT_CERTIFIED.

JSON, raw native outputs, safe credential metadata and Kubernetes diagnostics are
sanitized before upload. Only owned synthetic resources are cleaned up before
kind teardown. Existing security runtimes and their successful fixtures remain
independently executable; performance helpers are scoped for future reuse.
