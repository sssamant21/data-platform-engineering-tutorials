# Elasticsearch runbook validation matrix (fill with actual cluster evidence)

**Execution environment:** Begin with staging or a safely isolated test index. Production testing of a mutating procedure must be a separately approved maintenance change, never an exploratory test. The runbooks below are **unverified until evidence is supplied**.

| # | Runbook | Safe read-only exercise | Controlled staging scenario | Required production-grade evidence |
|---|---|---|---|---|
| 01 | Cluster health | Cluster health, nodes, shards, pending tasks, node stats | Simulated service degradation in isolated test deployment | Correct incident classification, no accidental state mutation, SLO recovery and escalation |
| 02 | Disk pressure/capacity | Allocation, index sizes, effective watermarks | Disk-growth forecast or provider-approved staging expansion; do **not** fill production disk | Worst-node and aggregate GB, alert thresholds, verified capacity action and recovery |
| 03 | Oversized shard remediation | Shard sizes, merge/search stats and mappings | Approved isolated index reindex to candidate shard sizing | Reindex task completion, key parity, routing/catch-up, shard distribution, latency, rollback |
| 04 | Index creation/mappings | Templates, settings, mappings, aliases | Create `sandbox-` index from reviewed payload | Mapping contract, strict field tests, alias and ingestion/search checks |
| 05 | Reindex + alias cutover | Current aliases, writers, source/dest stats | Two `sandbox-` indices with simulated writes and atomic alias flip | No dropped/duplicate updates, write replay proof, read/write alias correctness, tested rollback |
| 06 | Retention/ILM | ILM status/explain, policy, index settings | Nonproduction lifecycle progression using a reviewed short-duration lab policy | Data+Business approval, no held data affected, all managed indices mapped correctly |
| 07 | Cleanup automation | Indices, aliases, age, tasks, disk baseline | Dry-run then controlled deletion of a **disposable lab index only** | Manifest/approval integrity, skip logic, audit, before/after capacity, failure injection |
| 08 | Query/index performance | Nodes stats, thread pools, shards, workload metrics | Controlled load test/query profile away from production peak | Comparable p95/p99, correctness, rejections, GC, queue deltas and regression test |
| 09 | Snapshot/restore | Snapshot listings, repo status, recovery | Restore renamed nonprod index into isolated target | Snapshot compatibility, verified keys, restore time, RPO/RTO, safe collision handling |
| 10 | Cluster right-sizing | Node inventory, stats, allocation | Provider-supported staging resize with rollback | Failure-domain and workload validation, before/after SLO, capacity and cost |
| 11 | Rolling upgrades | Versions, plugins, health, snapshot inventory | Version-exact staged upgrade of representative topology | Vendor-supported path, client compatibility, snapshot, observed traffic and recovery |
| 12 | Shard allocation | Shards, recovery, allocation explain | Recover eligible lab replica after controlled node event | Deciders, recovery duration, correct replica count, no unsafe primary allocation |
| 13 | JVM/cache | JVM, breakers, caches, thread-pool stats | Bounded synthetic aggregation/search stress in staging | Correct interpretation, no cache-clear shortcut, stable heap/GC and SLO |
| 14 | Growth forecasting | Daily indices, shards, allocation stats | Compute forecasts from repeated sampled snapshots | Owner attribution, peak-node headroom, 30/60/90-day error and cost assumptions |
| 15 | FinOps cost | Indexed bytes, disk utilization, node roles | Compare against deidentified cloud-billing exports | Reconciled billing, cost allocation method, approved optimization, realized savings |

## Completion markers (one per runbook)
- [ ] Exact Elasticsearch patch version, platform/provider, curl version and permissions recorded
- [ ] Read-only command returned expected shape and no unexpected errors
- [ ] All mutating operations scoped to authorized nonprod sandbox or separately approved change
- [ ] Prechange risk, approval and recovery prerequisites recorded
- [ ] Negative case, failure and stop/rollback behavior validated
- [ ] Data/alias/client functional tests and capacity metrics recorded where applicable
- [ ] No patient data, real credentials or sensitive query payloads in committed evidence
- [ ] Independent reviewer signed, change ticket linked, document version marked tested

**Status inventory:** 01–15 = **Needs actual-cluster validation**. Do not assert pass without evidence.
