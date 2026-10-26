# Chapter 032 producer tuning, ordering and timeout acceptance

`python kafka/qa/run_chapter_032.py` independently executes on the disposable
persistent Kafka 4.0.0/KRaft/Strimzi 0.47.0 SCRAM fixture. The shared
`performance_lab.py` keeps Chapter 031's accepted lifecycle and default workload
independently executable; CI regresses Chapter 031 when shared code changes.

## Bounded matched experiment

Fifteen measured trials repeat five candidates three times in deterministic rotated
orders. All use six partitions, RF3/minISR2, 1,200 x 1KiB records, offered cap
400 records/s, identical client CPU/memory/image, SASL_SSL with hostname verification,
acks=all, idempotence=true and max.in.flight=5. One separate warmup is excluded.

| Comparison | Linger ms | Batch bytes | Codec | Primary change |
|---|---:|---:|---|---|
| Baseline | 0 | 16384 | none | reference |
| Linger | 5 | 16384 | none | linger versus baseline |
| Batch | 5 | 65536 | none | batch versus linger |
| LZ4 | 5 | 65536 | lz4 | codec versus batch |
| Zstandard | 5 | 65536 | zstd | codec versus batch |

A fixed synthetic dataset contains 1,200 distinct event IDs padded to 1KiB with
compressible content. Native Kafka perf tools select from this payload file using
the pinned deterministic generator. Every trial must report the same dataset SHA256.
The auditor regenerates the expected selected payload multiset and verifies exact
acknowledged counts, consumed bytes/hashes and committed captured partition ends.
No uniform unkeyed partition distribution or representative application entropy is
inferred. Tuned candidates may be slower; observations are retained without a
mandatory speedup or production configuration selection.

Native producer/consumer summaries, error/retry counters, per-trial p50/p95/p99,
batch-size-average and compression-rate-average are captured. Kafka 4.0's actual
buffer-pool metric is `bufferpool-wait-time-ns-total`, in nanoseconds, as defined by
the tagged [BufferPool implementation](https://github.com/apache/kafka/blob/4.0.0/clients/src/main/java/org/apache/kafka/clients/producer/internals/BufferPool.java).
Missing metrics remain unavailable, never zero. Client cgroup CPU/throttling deltas
and memory observations are real Pod measurements, including startup, health polling
and auditing; they are not broker utilization or pure codec CPU measurements.
Per-candidate medians/sample variation and per-trial p99 are retained without an
invented pooled percentile. Public per-trial profiles and hashes preserve controls.

## Correctness and failure boundaries

- Reject max.in.flight=6 with explicit idempotence enabled through the Kafka client
  configuration validator before traffic. Acks and ISR are never lowered.
- In separate owned topics, send 30 uniquely keyed sequence values on partition 0
  for supported in-flight limits 1 and 5. Capture starting offsets, verify every
  acknowledgment and callback, consume the exact ordered sequence and commit/recheck
  the captured end. Record callback and enqueue timing with a stated nearest-rank
  percentile definition. This proves the tested healthy-session partition-local
  behavior, not global order or arbitrary external business exactly-once effects.
- Use a verified-unpublished Service port only in a fresh client's bootstrap config.
  With max.block=2000ms, classify the synchronous metadata TimeoutException as
  NOT_ENQUEUED within a predeclared ten-second harness budget. A returned Future or
  successful send fails this assertion. Fresh secure producers then prove recovery.
  Queued delivery timeout and acknowledgment-loss retry deduplication are explicitly
  NOT_EXECUTED; metadata failure cannot substitute for those tests.

The pinned [Kafka 4.0 producer configuration reference](https://kafka.apache.org/40/configuration/producer-configs/)
defines idempotence constraints and the separate buffering/request/delivery timeout
semantics. No unsupported exactly-once or retry-fault result is inferred.

## Safety, evidence and remaining gates

The common harness checks persistent binding/headroom, node pressure, immutable
client image, restricted credential mounts and ServiceAccount denial. Native workers
have bounded heaps, deadlines and rate/payload budgets. Actual Admin polling kills
native process trees on current-topic leader/ISR/quorum failure. Broker UID/restart
and Kafka Ready checks gate continuation between trials. No broker listener, PVC,
NetworkPolicy, production client or production credentials are mutated.

JSON retains every attempt, failed/unexecuted state, safe commands, raw native
outputs, exact data checks, resource observations and limitations. Sanitization runs
before artifacts upload; only owned test resources are cleaned up before kind
teardown. Replicated measured payload is about 53MiB, plus warmup/Kafka overhead and
60 small ordering records; tests do not seek disk exhaustion or saturation.

Single-host kind cannot establish production capacity, broker CPU/network/storage
correlation, cloud IOPS, noisy-neighbor behavior or multi-zone headroom. Additional
linger/batch sizes, snappy/gzip, message sizes/skew, concurrency, matched plaintext
security overhead, real in-flight retry-fault testing and independent review remain
pending. No production winner, numeric assessment score or enterprise certification
is awarded. Full assessment is NOT_YET_ACCEPTED; certification is NOT_CERTIFIED.
