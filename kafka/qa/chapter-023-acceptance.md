# Chapter 023 compaction and keyed-state acceptance

`python kafka/qa/run_chapter_023.py` creates an isolated compacted three-partition,
RF3/minISR2 topic on the persistent Kafka 4.0.0/KRaft/Strimzi 0.47.0 kind fixture.
The existing storage inventory, bounded Job lifecycle and diagnostics are reused.

## Executed acceptance mapping

- Labs A/B/L: full ISR/valid leaders and effective compact/delete-retention/cleaner
  eligibility/segment settings are checked through Kafka Admin and supported CLI.
- Labs C/D: a compiled/source-launched Java Job acknowledges 108 deterministic
  keyed records, including explicit fixed key routing, size-bounded historical
  churn, a genuine null-value tombstone and a separate literal string "null".
- Lab E: consumers initialize an empty map and read all partitions to captured
  end-offset snapshots. Actual offsets must advance but need not be contiguous.
  The exact final state keeps customer-1=diamond, customer-3=premium and the literal
  null string key, while customer-2 is absent. Tombstone nullability is verified.
- Labs F/K: a bounded observation records whether visible physical record count
  falls below the 108 acknowledged records without a change to captured log ends.
  This demonstrates cleaner progress when observed. No fixed record count or
  cleaning deadline is assumed. The JSON explicitly records unobserved progress.
- Labs G/H: after the first client Job exits, a distinct new Job rebuilds from an
  empty in-memory store and reconciles the same exact state. This is a real fresh
  bootstrap, not a production Deployment/state-PVC crash or checkpoint test.
- Storage/quorum: all nine replica logs remain healthy, broker data PVC/PV identities
  stay fixed, headroom snapshots are read-only, and a valid KRaft leader is checked.

Size-based rolling uses about 6 MiB of logical historical payload; no broker files,
PVCs, partitions or broker settings are modified. Only uniquely owned test topic,
Jobs and ConfigMaps are cleaned up. Null keys are never emitted. The illustrative
50-million-key footprint calculation is labeled a lower bound, not measured capacity.

## Evidence and limitations

`chapter-023-runtime.json` includes both Jobs' immutable provenance, assertions,
state/offset snapshots, exact nullability evidence, cleaner observations, storage
metadata and pending assessments. Phase logs and Kubernetes diagnostics accompany
it in the seven-day Actions artifact.

A passing supported runtime does not prove full compaction completion, tombstone
expiration, legal erasure, cleaner SLOs, production monitoring, atomic state/checkpoint
crash recovery, CSI/node/zone resilience or enterprise certification. These remain
NOT_VALIDATED/PENDING, and certification stays NOT_CERTIFIED. When no record removal
is observed within the bounded window, cleaner progress is explicitly not claimed.

The selector registers 023 on the persistent fixture and scopes its new Java client
to 023. Changes to storage inventory select all importing chapters; other existing
chapter mappings/concurrency are preserved. No Chapter 024 implementation begins
until Chapter 023's supported runtime passes.
