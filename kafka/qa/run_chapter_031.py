#!/usr/bin/env python3
"""Chapter031 independently executable bounded secure native microbenchmark."""
from performance_lab import PerformanceLab, broker_snapshot, filesystem_headroom, execute_benchmark
from performance_acceptance import trial_plan, aggregate

LIMITS = ['Single-host kind with shared local-path PVC filesystem is a functional microbenchmark, not '
 'representative throughput, saturation, storage IOPS/latency, node placement or production '
 'capacity certification.',
 'Three capped offered rates and three repetitions use 1KiB native deterministic payloads. '
 'Separate-process warmup is unmeasured; each trial includes client connection startup. No '
 'steady-state or sustained disk limit is inferred.',
 'Kafka 4.0 tool per-trial percentiles are retained; no average of p99 values is called a global '
 'p99. Payload MiB is distinct from wire bytes, compression or replication traffic.',
 'Actual Admin leader/full-ISR/quorum polling kills the native process tree on unhealthy '
 'observations. It is periodic polling, not continuous proof or Prometheus-based SLO alerting. '
 'Broker Pod UID/restart drift is checked between trials.',
 'Client cgroup snapshots cover the entire benchmark Pod, including tool startup, health polling '
 'and auditing. Broker CPU/network/storage utilization and provider burst metrics are '
 'NOT_AVAILABLE without a monitoring stack; absence is not low usage.',
 'No acks weakening, message-size/compression/partition/concurrency sweep, matched '
 'plaintext-vs-TLS overhead, noisy-neighbor experiment, production bottleneck conclusion or '
 'independent assessor score is claimed. Full performance assessment and enterprise certification '
 'remain pending.']
ASSESSMENT={'status':'NOT_YET_ACCEPTED','score':None,'production_representativeness':'NOT_ESTABLISHED',
    'critical_gaps':['broker CPU/network/disk resource correlation','production-like sustained load and saturation','independent reviewer signoff'],
    'other_sweeps':'NOT_EXECUTED: message size, acks comparison, compression, partitions, concurrency, matched secure-vs-plaintext overhead'}


def main():
    return execute_benchmark('031',trial_plan(),LIMITS,{},ASSESSMENT,aggregate)


if __name__=='__main__':raise SystemExit(main())
