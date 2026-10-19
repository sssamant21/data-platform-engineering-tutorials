# 69 — Metrics Logs FTDC and Dashboard Design

Part 9 — Specialized Data and Observability

**Audience:** DBREs, SREs, Platform Engineers and Developers.  
**Goal:** Collect bounded diagnostic evidence, calculate valid per-member rates, correlate logs and FTDC with a workload, and specify dashboards that reveal missing monitoring data.  
**Baseline:** Retained authenticated TLS MongoDB 8.0 / FCV 8.0 replica set, exact recorded mongosh and a reviewed pinned synchronous PyMongo 4.x release on Python 3.11+. Core exercises are Community-compatible.  
**Status:** Written; syntax and offline rate/log-parser checks complete; live sampling, log correlation and FTDC acceptance pending.  
**Prerequisites:** Chapters 21–24, 25–29, 41–42, 57–63 and 68; accepted deployment, member inventory and evidence ownership.  
**Estimated time:** 60–90 minutes.

## 1. Define the monitoring contract

A dashboard should answer whether users are affected, which member or dependency is constrained, what changed, and whether the evidence is fresh enough to support a decision. A green panel with no recent samples is a monitoring failure.

The lab collects three samples from one pinned member, runs a small owned workload, calculates deltas with restart guards, summarizes structured log evidence, and inventories FTDC without changing its configuration. It does not install an exporter or publish a Grafana dashboard; the dashboard deliverable is an explicit panel/data contract that can be implemented in the accepted monitoring stack.

Keep these evidence planes separate:

| Plane | Source | Question |
|---|---|---|
| User experience | Application requests, traces and client metrics | Are successful responses meeting latency/error objectives? |
| Database process | serverStatus, replication state, collection/query evidence | What work, contention or failures does the process report? |
| Host/container/storage | OS/cloud/Kubernetes monitoring | Are CPU, memory, throttling or storage limits constraining it? |
| Event context | Structured MongoDB/application/operator logs | What happened near the incident boundary? |
| Retained diagnostics | FTDC plus a bounded evidence packet | What historical process measurements survive the incident? |

Server operation latency is not end-to-end application latency. Collection statistics are not host free space. Replication health is not proof of a fresh downstream warehouse. Correlate the planes rather than using one as a substitute for another.

## 2. Identity, time and metric semantics

Every sample needs deployment, member endpoint, replica set, process identity, role, server version, sample time and collector status. A replica-set-aware connection can route to a different primary after an election. Member-local counters must not be subtracted across different members.

For this lab use a direct connection to one recorded writable primary member. This is a diagnostic choice, not application routing guidance. Preserve verified TLS and the member's certificate hostname. If an election occurs, stop the owned workload and record the role change; do not silently keep attributing it to the original primary.

| Metric kind | Examples | Dashboard treatment |
|---|---|---|
| Cumulative counter | opcounters, connection creation, latency operation counts | Rate from valid same-process deltas |
| Gauge | Current connections, queue depth, cache occupancy | Current value plus trend; do not apply a counter rate |
| Cumulative duration | opLatencies latency microseconds | Delta duration / delta operations, with unit conversion |
| Timestamp/state | Member optime, role, collector last success | Lag/state and freshness, not arbitrary subtraction of totals |
| Distribution | Application latency histogram | Quantile from the distribution; do not infer P99 from a mean |

For counter C and elapsed time Δt, rate is `(C2-C1)/Δt`. Suppress the interval on a process restart, changed member identity, decreasing counter, nonpositive elapsed time or missing field. Mark the interval unavailable instead of returning zero. Use measured elapsed time; the collector may take longer than its requested sleep interval.

Averages derived from cumulative operation duration are workload aggregates. They are not query percentiles. Per-process serverStatus fields and units must be checked against the installed server version.[1]

## 3. Permissions and evidence controls

Use an authorized observer with the required serverStatus/replication/getLog permissions. The built-in clusterMonitor role may be suitable after reviewing its grants and the deployment policy. Do not grant write or administrative configuration privileges merely to collect metrics.

Use a distinct workload identity for the owned lab database. A lifecycle identity creates and cleans the fixture. On Kubernetes, use the existing approved host/pod inspection procedure; do not grant broad cluster permissions for an FTDC inventory.

Diagnostic records can reveal namespace, topology and query context. Structured logs can contain sensitive command values. Store full logs and FTDC only in approved restricted evidence storage; share a minimized summary. Avoid logging credentials or dumping unrestricted current operations into a public ticket.

Record exact server/FCV, driver, shell, observer identity scope, deployment/member endpoint, source of clock synchronization and UTC incident bounds. Keep monitoring credentials under normal secret rotation and verify collector authorization after rotation.

## 4. Prepare the owned workload

Connect through Chapter 42's mongosh TLS procedure to the retained primary. Run once:

```javascript
var labName = "mongodb_enterprise_ch69_observability";
var lab = db.getSiblingDB(labName);
if (lab.getCollectionInfos().length !== 0) throw new Error("Namespace already exists");
if (!db.hello().isWritablePrimary) throw new Error("Expected writable primary");
lab.ownership.insertOne({ _id: "mongodb-enterprise-tutorial-ch69", createdAt: new Date() });
lab.items.createIndex({ seq: 1 }, { unique: true, name: "seq_unique" });
print("Owned workload namespace ready");
```

Set these nonsecret worker parameters through the approved environment mechanism:

| Variable | Value |
|---|---|
| `CH69_MEMBER_URI` | Credential-free direct URI for one recorded member, e.g. mongodb://db1:27017/?directConnection=true |
| `CH69_CA_FILE` | Verified MongoDB CA path |
| `CH69_OBSERVER_USER` | Authorized monitoring identity |
| `CH69_WORKLOAD_USER` | Scoped identity for the owned workload database |
| `CH69_EVIDENCE_DIR` | Fresh absolute local evidence directory |

Install an exact reviewed PyMongo version in an isolated virtual environment. The scripts prompt for passwords and do not print them. The directory must be newly owned; do not overwrite a prior incident packet.

## 5. Lab A — bounded member sampler and workload

Save the following as `ch69_sample.py`. Sampling and workload calls are sequential so each collection interval has an observable boundary. The small fixture cannot reproduce production saturation or establish a load-test threshold.

```python
import getpass
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pymongo
from pymongo import MongoClient
from pymongo.write_concern import WriteConcern

ROOT = Path(os.environ["CH69_EVIDENCE_DIR"])
ROOT.mkdir(parents=True, exist_ok=False)


def connect(username):
    return MongoClient(
        os.environ["CH69_MEMBER_URI"], username=username,
        password=getpass.getpass("MongoDB password for " + username + ": "),
        authSource="admin", tls=True, tlsCAFile=os.environ["CH69_CA_FILE"],
        serverSelectionTimeoutMS=10000, socketTimeoutMS=10000, maxPoolSize=2,
    )


def field(document, *path):
    for key in path:
        if not isinstance(document, dict) or key not in document:
            return None
        document = document[key]
    return document


observer = connect(os.environ["CH69_OBSERVER_USER"])
writer = connect(os.environ["CH69_WORKLOAD_USER"])
lab = writer.get_database("mongodb_enterprise_ch69_observability",
                          write_concern=WriteConcern(w="majority", wtimeout=10000))
if lab.ownership.find_one({"_id": "mongodb-enterprise-tutorial-ch69"}) is None:
    raise RuntimeError("Workload ownership missing")
if lab.items.count_documents({}) != 0:
    raise RuntimeError("Expected a fresh empty workload fixture")


def sample(label):
    started = time.monotonic()
    status = observer.admin.command("serverStatus")
    hello = observer.admin.command("hello")
    row = {
        "label": label, "utc": datetime.now(timezone.utc).isoformat(),
        "monotonic": time.monotonic(), "collection_seconds": time.monotonic()-started,
        "host": status.get("host"), "pid": status.get("pid"),
        "process": status.get("process"), "version": status.get("version"),
        "uptime": status.get("uptime"), "is_primary": hello.get("isWritablePrimary"),
        "set_name": hello.get("setName"),
        "connections_current": field(status, "connections", "current"),
        "connections_created": field(status, "connections", "totalCreated"),
        "insert_ops": field(status, "opcounters", "insert"),
        "query_ops": field(status, "opcounters", "query"),
        "read_latency_us": field(status, "opLatencies", "reads", "latency"),
        "read_latency_ops": field(status, "opLatencies", "reads", "ops"),
        "cache_used_bytes": field(status, "wiredTiger", "cache", "bytes currently in the cache"),
        "cache_max_bytes": field(status, "wiredTiger", "cache", "maximum bytes configured"),
        "dirty_bytes": field(status, "wiredTiger", "cache", "tracked dirty bytes in the cache"),
    }
    with (ROOT / "samples.jsonl").open("a", encoding="utf-8") as output:
        output.write(json.dumps(row) + "\n")
    print({"label": label, "host": row["host"], "uptime": row["uptime"],
           "collection_seconds": row["collection_seconds"]})
    return row


try:
    first = sample("baseline")
    if not first["is_primary"] or not first["set_name"]:
        raise RuntimeError("Expected recorded replica-set primary")
    time.sleep(5)
    lab.items.insert_many([{"_id": i, "seq": i, "value": i * 2} for i in range(100)])
    for i in range(20):
        row = lab.items.find_one({"seq": i}, comment="ch69-bounded-workload")
        if row is None or row["value"] != i * 2:
            raise RuntimeError("Workload correctness failed")
    if lab.items.count_documents({}) != 100:
        raise RuntimeError("Expected 100 owned rows")
    second = sample("after_workload")
    if second["host"] != first["host"] or not second["is_primary"]:
        raise RuntimeError("Member/role changed; record interval and stop")
    time.sleep(5)
    sample("idle_followup")
    (ROOT / "inventory.json").write_text(json.dumps({
        "driver": pymongo.version, "namespace": lab.name + ".items",
        "rows": 100, "successful_point_reads": 20,
        "member": first["host"], "set_name": first["set_name"]
    }, indent=2), encoding="utf-8")
finally:
    observer.close()
    writer.close()
print("PASS: bounded workload and three member samples captured")
```

Expected: 100 correct documents, 20 checked point reads and three samples with collection durations. Global operation counters include other workloads and the collector itself. Do not assert that insert/query counter deltas equal the number of Python calls; command semantics and concurrent operations affect these counters.

Run `python ch69_sample.py`. On authorization or network failure, preserve the partial evidence and stop. A production collector should emit a failed-scrape signal and last-success age; it must not manufacture a successful zero-valued database sample.

## 6. Lab B — calculate rates and restart-safe means

Save as `ch69_rates.py`. The two helper functions deliberately return a reason when an interval is invalid.

```python
import json
import os
from pathlib import Path


def counter_rate(before, after, key):
    identity = ("host", "pid", "process", "version", "set_name")
    if any(before.get(k) is None or after.get(k) is None for k in identity):
        return None, "missing_identity"
    if any(before[k] != after[k] for k in identity):
        return None, "identity_changed"
    if before.get("uptime") is None or after.get("uptime") is None:
        return None, "missing_uptime"
    elapsed = after["monotonic"] - before["monotonic"]
    uptime_delta = after["uptime"] - before["uptime"]
    if elapsed <= 0:
        return None, "invalid_elapsed"
    # Uptime roughly follows elapsed time within this single collector run.
    # This also catches a restart whose new uptime happens to exceed the old sample.
    if uptime_delta < 0 or abs(uptime_delta - elapsed) > 2:
        return None, "restart_or_timing_discontinuity"
    if before.get(key) is None or after.get(key) is None:
        return None, "missing_counter"
    delta = after[key] - before[key]
    if delta < 0:
        return None, "counter_reset"
    return delta / elapsed, "valid"


def read_mean_ms(before, after):
    duration_rate, why = counter_rate(before, after, "read_latency_us")
    if why != "valid":
        return None, why
    operation_rate, why = counter_rate(before, after, "read_latency_ops")
    if why != "valid":
        return None, why
    if operation_rate == 0:
        return None, "no_operations"
    return duration_rate / operation_rate / 1000, "valid_mean_not_percentile"


root = Path(os.environ["CH69_EVIDENCE_DIR"])
rows = [json.loads(line) for line in (root / "samples.jsonl").read_text().splitlines()]
if len(rows) != 3:
    raise RuntimeError("Expected three samples; investigate collection completeness")
results = []
for before, after in zip(rows, rows[1:]):
    rates = {key: counter_rate(before, after, key)
             for key in ("insert_ops", "query_ops", "connections_created")}
    result = {"from": before["label"], "to": after["label"],
              "rates_per_second_with_status": rates,
              "read_mean_ms_with_status": read_mean_ms(before, after),
              "connections_current_gauge": after.get("connections_current")}
    results.append(result)
    print(result)
(root / "rates.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
```

Run `python ch69_rates.py`. Inspect invalid/missing reasons rather than requiring nonzero rates. A valid idle interval can have zero operation rate; its read latency mean is unavailable when there are no reads.

Monotonic timestamps are valid only within this collector process. Do not concatenate files from restarted collectors and subtract their monotonic times. A production time-series backend supplies its own sample timestamps and counter-reset handling, plus process identity labels. The two-second uptime tolerance is a conservative teaching guard; slow/discontinuous samples may be suppressed and need investigation.

## 7. Failure exercise — false spikes and absent metrics

Before trusting live results, run this standalone offline test against the rate helpers from Section 6. Save the helpers in a reusable module or copy their definitions above this block; this block intentionally does not open a MongoDB connection.

```python
base = {"host": "db1", "pid": 10, "process": "mongod", "version": "8.0.lab",
        "set_name": "rs0", "uptime": 100, "monotonic": 10,
        "query_ops": 100, "read_latency_us": 1000, "read_latency_ops": 10}
after = dict(base, uptime=110, monotonic=20, query_ops=150,
             read_latency_us=21000, read_latency_ops=20)
assert counter_rate(base, after, "query_ops") == (5.0, "valid")
assert read_mean_ms(base, after) == (2.0, "valid_mean_not_percentile")
assert counter_rate(base, dict(after, pid=11), "query_ops")[1] == "identity_changed"
assert counter_rate(base, dict(after, uptime=2), "query_ops")[0] is None
assert counter_rate(base, dict(after, query_ops=5), "query_ops")[1] == "counter_reset"
assert counter_rate(base, dict(after, query_ops=None), "query_ops")[1] == "missing_counter"
assert read_mean_ms(base, dict(after, read_latency_ops=10))[1] == "no_operations"
print("PASS: rates, unit conversion, restart/reset/missing and idle guards")
```

Diagnosis: naïve deltas can generate negative rates or false continuity across restarts. Replacing missing fields with zero creates false health signals. Corrective action is to retain missing/reset labels, segment process histories and verify valid intervals after collection resumes.

## 8. Lab C — structured logs and workload correlation

Collect a bounded UTC window from the member's approved logging destination. For a native service this may be an authorized journal export or rotated log file; for Kubernetes use the recorded pod/container and restart identity. Keep original source attribution and clock/rotation bounds.

An authorized observer can inspect the recent in-memory global log buffer:

```javascript
var result = db.getSiblingDB("admin").runCommand({ getLog: "global" });
if (result.ok !== 1) throw new Error("getLog failed");
printjson({ count: result.log.length, totalLinesWritten: result.totalLinesWritten });
```

The buffer is not a durable incident archive. Retrieve full log content only through the approved restricted evidence path. MongoDB logs are structured JSON with timestamp, severity, component, message ID, context and optional attributes; individual entries can be truncated.[2]

A comment on a fast operation does not guarantee a corresponding slow-query log entry. This lab does not lower global slow thresholds or enable broad profiling to force visibility. Correlate the 20 successful point reads with actual emitted evidence if present; otherwise record that no matching entry was captured. Chapter 22 covers controlled profiling separately.

Save a sanitized closed log window as `mongo-window.jsonl`. Use this parser as `ch69_logs.py`; it emits only timestamp/severity/component/message ID/context and malformed-line count, not command payloads.

```python
import json
import os
from collections import Counter
from pathlib import Path

root = Path(os.environ["CH69_EVIDENCE_DIR"])
counts = Counter()
malformed = 0
selected = []
with (root / "mongo-window.jsonl").open(encoding="utf-8") as source:
    for line in source:
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if not isinstance(entry, dict):
                raise ValueError("Expected JSON object")
        except (ValueError, TypeError):
            malformed += 1
            continue
        severity = entry.get("s", "unknown")
        component = entry.get("c", "unknown")
        counts[(severity, component)] += 1
        if severity in {"W", "E", "F"}:
            selected.append({"time": entry.get("t"), "severity": severity,
                             "component": component, "id": entry.get("id"),
                             "context": entry.get("ctx")})
summary = {"severity_component_counts": [
    {"severity": s, "component": c, "count": n} for (s, c), n in sorted(counts.items())
], "malformed_lines": malformed, "warning_error_events": selected}
(root / "log-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(summary)
```

Run `python ch69_logs.py`. Expected output depends on the actual retained window; zero warnings is a valid result, not proof that the incident had no failures. Nonzero malformed lines can indicate wrappers, multiline export, truncated transfer or mixed formats; inspect and correct the evidence export. Message IDs identify log statements, not unique request/event instances.

For reproducible parser acceptance, use a separate synthetic file with one warning, one informational entry and one malformed line. Label it synthetic; do not substitute it for live incident evidence.

## 9. Lab D — FTDC inventory and preservation

FTDC is a retained diagnostic capture mechanism distinct from application logs and a central monitoring backend. Its enabled state, collection path and available history must be verified on each recorded process.[3]

Through the authorized observer:

```javascript
printjson(db.getSiblingDB("admin").runCommand({
  getParameter: 1, diagnosticDataCollectionEnabled: 1
}));
```

Review the existing service/operator configuration for dbPath and diagnostic-directory settings. For mongod, the usual default is `diagnostic.data` beneath dbPath; deployment and process configuration can change the path.[3] Do not assume a mongos or managed service uses the same location/access method.

On the recorded host, set the resolved directory explicitly and perform a read-only inventory:

```bash
export CH69_FTDC_DIR='/recorded/dbpath/diagnostic.data'
python - <<'PY'
import os
from pathlib import Path
root = Path(os.environ['CH69_FTDC_DIR'])
if not root.is_dir():
    raise RuntimeError('Recorded FTDC directory unavailable; verify process/configuration')
files = sorted(p for p in root.iterdir() if p.is_file())
print({'directory': str(root), 'files': len(files),
       'bytes': sum(p.stat().st_size for p in files)})
for path in files:
    stat = path.stat()
    print({'file': path.name, 'bytes': stat.st_size, 'mtime_epoch': stat.st_mtime})
PY
```

Capture inventory twice at a recorded interval and check whether files or timestamps progress while the process is running. The number of files and rotation pattern are version/configuration dependent; do not assert an exact file count.

Preserve incident FTDC using the deployment's supported collection procedure and record member/process, capture time, file manifest and checksum. A file copied while actively changing may not be an immutable consistent artifact. Prefer supported capture tooling or reviewed closed-file handling; record incomplete/active files rather than declaring the packet complete.

FTDC uses a diagnostic format; do not parse its files as ordinary JSON or promise that arbitrary `bsondump` produces correct decoded metrics. Use an approved version-compatible diagnostic analyzer or support workflow. Verify that the retained packet covers the incident UTC window and the affected member.

Do not delete `diagnostic.data` to fix disk pressure, disable FTDC to improve a benchmark, or change capture settings in this chapter. Diagnose filesystem growth and rotation separately. Capture missing/disabled FTDC as an evidence gap and assign its remediation owner.

## 10. Replica-set and resource correlation

Use `replSetGetStatus` through each authorized member observer when diagnosing member state and optimes.[4] Capture primary identity and member health in the same UTC window as the process samples. Replication lag needs source/secondary optime comparison with role and timestamp semantics; a healthy heartbeat alone does not prove catch-up.

Map the process to its host/pod, PVC/volume and cloud disk. Correlate cache pressure with OS memory and disk read latency; connection churn with driver pool/timeout behavior; replication lag with write demand and storage/network constraints; and election events with application failures.

Never sum primary and secondary counters and label the result unique business transactions. Router and shard process metrics can represent overlapping work. Use separate process roles and aggregation semantics for sharded dashboards. Keep host CPU/IO and database counters aligned to the same deployment/member identifiers.

## 11. Dashboard design contract

Implement the following panels in the accepted Grafana/Prometheus, Ops Manager or other monitoring stack. Exact exporter metric names vary by product/version; map them from the installed collector's actual output before writing queries.

| Row | Panels | Required semantics and drilldown |
|---|---|---|
| User impact | Request rate, error ratio, P50/P95/P99, dependency timeout rate | Application histograms; workload/route scope; traces |
| Data freshness | Replica role/state, replication lag, CDC materialization lag | Member identity and source/sink boundary; election annotations |
| Demand | Read/write/command rates and connections | Counter rates, process reset guards, current connections as gauge |
| Latency/work | Server interval mean, slow operations, examined/returned work | Mean clearly labeled; bounded query/profiler evidence |
| Memory/cache | Cache used/max, dirty bytes, eviction activity, OS memory | Units and missing-field handling; container limit/throttling context |
| Storage | Free bytes, growth, IOPS/throughput, latency and queues | Volume/cloud identity; capacity and device limits |
| Resilience | Member health, restarts, rollback/initial-sync events | UTC event annotations; bounded log links |
| Monitoring health | Scrape success, last-success age, missing expected members | Missing data distinct from zero; collector errors and coverage |

Every panel definition should name its source field/metric, unit, gauge/counter/distribution type, labels, aggregation, update cadence, freshness budget and owner. Provide links to the member inventory, log window, query evidence and runbook.

Avoid high-cardinality labels containing document IDs, unrestricted query text, user IDs or request IDs. Use bounded deployment/member/workload labels; keep detailed request context in controlled logs/traces. Avoid mixing microseconds and milliseconds or megabytes and bytes under one axis.

Panel ordering should lead from user impact to possible causes. A cache percentage alone should not decide remediation. Compare relevant workload, eviction/I/O, latency and host pressure. Capacity warnings and incident alerts need their own operational thresholds; Chapter 70 develops SLOs and alert design.

## 12. Dashboard acceptance and failure drills

| Drill | Expected dashboard result | Failure indication |
|---|---|---|
| Idle process | Valid near-zero operation rate; latency mean unavailable when no operations | Missing sample plotted as healthy zero |
| Bounded fixture | Correct workload evidence plus member-local demand trend | Claims exact global counter-to-client-call equality |
| Counter reset/offline synthetic restart | Interval suppressed; restart/reset reason retained | Negative rate or spurious continuity |
| Missing field | Panel unavailable with coverage signal | Silent zero substitution |
| Collector outage in test monitoring environment | Freshness/failed scrape signal | Old green value displayed without age |
| Member role change | Updated role and election annotation | Historical rates reassigned to a different member |
| Log evidence gap | Window/coverage gap recorded | Empty log treated as proof of no incident |
| FTDC unavailable | Evidence gap and collection owner | Fabricated historical metrics |

Run outage/election drills only under the retained deployment's previously accepted maintenance procedure and record their effects. The chapter's scripts execute the bounded workload and offline reset/missing checks; they do not stop the database or collector.

## 13. Troubleshooting

| Symptom | Evidence | Cause to test | Action and verification |
|---|---|---|---|
| Negative/spiking counter rate | Member/process identity, uptime and samples | Restart or mixed histories | Segment the series; verify a new valid interval |
| Connections high with low demand | Current/created deltas and client pool evidence | Churn or excessive pools | Review Chapter 63 client lifecycle; verify application recovery |
| Cache appears full | Cache/eviction/I/O plus OS memory | Working set or ordinary cache use | Diagnose pressure with latency and eviction, not occupancy alone |
| P99 panel uses server mean | Query expression and source fields | Metric semantics wrong | Use application histogram; relabel server interval mean |
| Logs lack workload comment | Thresholds, time window and source identity | Fast query not emitted or window incomplete | Record coverage; use separately authorized scoped profiling if needed |
| FTDC missing on expected host | dbPath, settings, process identity and access | Wrong path, disabled capture or unsupported access | Resolve inventory/permissions; verify progress without changing configuration |
| Disk pressure includes logs | Volume usage, rotation and process open files | Retention/rotation issue | Follow reviewed logging runbook and verify free-space recovery |
| Cluster aggregate double counts | Role/member label joins and queries | Router/shard or replica work combined | Correct aggregation contract; compare per-member panels |
| Dashboards stay green after outage | Last successful sample and scrape signal | Stale values carried forward | Expose freshness and failed collection; rehearse missing-data alert |

## 14. Evidence, cleanup and review

| Check | Required evidence |
|---|---|
| Environment | Exact versions, topology, observed member and identity scopes |
| Fixture | 100 correct rows and 20 checked point reads |
| Samples | Three records, identity/uptime/time fields and collection durations |
| Rate checks | Valid delta/units plus missing/reset/no-operation suppression |
| Log handling | Actual window/coverage, parser summary and malformed count |
| FTDC | Enabled-state result, resolved path, inventory/progress and capture bounds |
| Dashboard contract | Panels mapped to real collector metrics and freshness owners |
| Cleanup | Owned workload drop; retained diagnostics and cluster unchanged |

Mark each item passed, failed or not run. Keep actual evidence separate from synthetic parser/rate inputs. Save nonsecret summaries before cleaning the owned workload through the accepted mongosh TLS session:

```javascript
var labName = "mongodb_enterprise_ch69_observability";
var lab = db.getSiblingDB(labName);
if (lab.ownership.findOne({ _id: "mongodb-enterprise-tutorial-ch69" }) === null) {
  throw new Error("Ownership missing: investigate before cleanup");
}
if (lab.dropDatabase().ok !== 1) throw new Error("Owned workload cleanup failed");
if (db.getSiblingDB(labName).getCollectionInfos().length !== 0) {
  throw new Error("Cleanup left workload collections");
}
print("PASS: chapter-owned workload database removed");
```

Retain the exact evidence directory according to its incident/lab retention policy. Do not remove native FTDC files, process logs, collector configuration, cluster resources or other chapter data as part of this cleanup.

Review questions:

1. Why is current connections a gauge while totalCreated is a counter?
2. Why can serverStatus read mean not supply application P99?
3. Which identity and time checks must pass before subtracting counters?
4. Why does absence of a slow-query log entry not prove the operation was absent?
5. How do you verify that an FTDC packet covers the affected process and time window?
6. What should a dashboard show during a collector outage?
7. Why can replica/router aggregation double-count business activity?

## 15. DBRE/SRE operational acceptance extension — monitoring that fails visibly

This extension closes the gap between **collecting evidence** and **operating a trustworthy monitoring service**. It does not claim a live dashboard, paging integration or production validation.

### 15.1 Service ownership, detection and escalation contract

Before enabling paging, complete this deployment-specific table. A blank owner or untested signal is an acceptance failure, not an implicit default.

| Failure mode | Primary signal | Independent corroboration | Stop / escalation gate |
|---|---|---|---|
| User-facing latency or error incident | Application request error ratio and latency histogram, scoped by route/service | Driver timeout/error counts, traces, MongoDB workload evidence | Page application and DBRE on-call according to the approved SLO policy; do not equate server mean with application P99 |
| MongoDB collector unavailable | Collector scrape failure **and** last-success age per expected member | Member inventory and independent connectivity/collector logs | Escalate monitoring blind spot; never treat missing series as healthy zero |
| Unexpected primary election | Member role transition and process identity history | Replica-set state, logs and application error rate | Confirm majority and write correctness before considering manual intervention |
| Replication backlog | Per-secondary optime delay and retained oplog window | Storage latency, network evidence and write rate | Escalate when the accepted catch-up/recovery budget is at risk; do not assume a single universal lag threshold |
| Storage pressure | Filesystem/PVC available capacity and growth rate | MongoDB cache/IO behavior and storage provider limits | Use Chapter 75's guarded triage; do not delete FTDC or force database compaction as first response |

Required metadata for each alert: named owner, routing destination, severity, runbook link, metric source and labels, evaluation interval, lookback window, data freshness budget, silence/change policy, and last verified test. Choose numeric thresholds only from the service's approved SLO, capacity budget and observed baseline. Chapter 70 owns burn-rate and alert-threshold selection.

### 15.2 Monitoring backend acceptance test

Run these checks against an **isolated, authorized test monitoring environment** with the real deployed collector/exporter and dashboard definitions. The existing Python scripts do not perform these tests.

1. **Inventory:** Record all expected MongoDB members and collector targets. Compare expected vs observed series, including labels and process identity. Save the exact collector/exporter version and metric-name mapping.
2. **Healthy scrape:** Record successful collection and a last-success timestamp for every expected target. Verify a dashboard displays units, roles, source identity and age correctly.
3. **Missing data:** Disable only the **test collector target** using its approved maintenance procedure, not the database. Wait beyond the configured freshness budget. Assert that the target becomes unavailable, the monitoring-health panel does not remain green, and the approved blind-spot notification reaches the test destination.
4. **Recovery:** Re-enable the test collector; verify a fresh sample, correct identity, resolved monitoring-health alert and no fabricated zero-valued interval.
5. **Counter continuity:** Use a synthetic reset series or an approved test-process restart; verify the rate expression suppresses invalid continuity and that an event annotation identifies the restart.
6. **Coverage audit:** Compare alert/dashboard target labels with the original member inventory, including secondaries and any sharded components in scope. Unmapped targets or duplicated aggregation are failures.

**Evidence required:** timestamped target inventory, redacted collector configuration and version, before/during/after dashboard query results, alert evaluation and notification record, test change ID, rollback outcome and named reviewer. If any test is unavailable, record **NOT RUN**, not PASS.

### 15.3 Safe incident investigation sequence

1. Establish the UTC incident window and affected application SLI; identify whether the user-facing impact is ongoing.
2. Check the monitoring plane's own freshness, scrape success, clock alignment and expected-member coverage.
3. Correlate client error/latency with MongoDB member state and role, replication lag, storage, network and Kubernetes scheduling where applicable.
4. Capture bounded evidence and the process/member identity before considering remediation. Preserve restricted logs and FTDC according to policy.
5. Select a topology-specific runbook. Do not restart a member, change elections, adjust cache or delete diagnostic files merely because a dashboard panel looks abnormal.
6. Verify application recovery, member health, consistency and alert resolution; record what was **not** observable.
7. Document incident owner, timeline, customer impact, contributing causes, monitoring blind spots and prevention follow-up.

**Rollback boundary:** This chapter's live database lab changes only its explicitly owned fixture. Monitoring backend outage tests must be reversible and scoped to a test collector. Never disable production monitoring to prove an alert.

### 15.4 Machine-readable evidence manifest and pass gate

Save the following template as `ch69-acceptance.json` alongside the evidence packet, replacing every placeholder with observed data:

```json
{
  "chapter": 69,
  "environment": "isolated-test",
  "mongodb_version": "NOT_RECORDED",
  "collector_version": "NOT_RECORDED",
  "deployment_id": "NOT_RECORDED",
  "member_inventory": [],
  "observer_permissions_reviewed": false,
  "fixture_and_samples": "NOT_RUN",
  "offline_counter_tests": "NOT_RUN",
  "log_window_coverage": "NOT_RUN",
  "ftdc_inventory": "NOT_RUN",
  "real_metric_mapping": "NOT_RUN",
  "missing_data_alert_delivery": "NOT_RUN",
  "collector_recovery": "NOT_RUN",
  "owned_cleanup": "NOT_RUN",
  "reviewer": "NOT_ASSIGNED",
  "evidence_references": []
}
```

Run this dependency-free gate as `ch69_gate.py` after recording actual outcomes. It deliberately rejects the template and does not silently promote offline tests to live acceptance.

```python
import json
import os
from pathlib import Path

root = Path(os.environ["CH69_EVIDENCE_DIR"])
e = json.loads((root / "ch69-acceptance.json").read_text(encoding="utf-8"))
required = (
    "fixture_and_samples", "offline_counter_tests", "log_window_coverage",
    "ftdc_inventory", "real_metric_mapping", "missing_data_alert_delivery",
    "collector_recovery", "owned_cleanup",
)
failures = [key for key in required if e.get(key) != "PASS"]
for key in ("mongodb_version", "collector_version", "deployment_id", "reviewer"):
    if not e.get(key) or str(e[key]).startswith(("NOT_", "PLACEHOLDER")):
        failures.append(key)
if not e.get("member_inventory"):
    failures.append("member_inventory")
if not e.get("observer_permissions_reviewed"):
    failures.append("observer_permissions_reviewed")
if not e.get("evidence_references"):
    failures.append("evidence_references")
if failures:
    raise SystemExit("NOT ACCEPTED: " + ", ".join(failures))
print("PASS: recorded chapter-69 acceptance fields are complete; reviewer must verify evidence")
```

A passing gate means **the supplied manifest has complete declarations**, not that evidence is authentic. An independent reviewer must inspect the actual artifacts and authorize promotion. If a test cannot safely be run, retain the gap and its risk owner.

---

## 16. Official references and validation status

1. [MongoDB 8.0 — serverStatus](https://www.mongodb.com/docs/v8.0/reference/command/serverStatus/).
2. [MongoDB 8.0 — Log Messages](https://www.mongodb.com/docs/v8.0/reference/log-messages/).
3. [MongoDB 8.0 — Full Time Diagnostic Data Capture](https://www.mongodb.com/docs/v8.0/administration/full-time-diagnostic-data-capture/).
4. [MongoDB 8.0 — replSetGetStatus](https://www.mongodb.com/docs/v8.0/reference/command/replSetGetStatus/).
5. [MongoDB 8.0 — Analyzing Performance](https://www.mongodb.com/docs/v8.0/administration/analyzing-mongodb-performance/).

Documentation reviewed on 2026-10-11. Sample budgets, uptime tolerance, panel contract and failure guards are teaching choices. Python/JavaScript syntax and offline counter/reset/unit/log-parser cases were checked. These checks do not validate live server fields, observer permissions, workload attribution, FTDC decoding, real log coverage or a deployed dashboard. No live MongoDB/FTDC/dashboard acceptance was performed in the authoring environment.

**Chapter completion:** Written and statically reviewed. Runtime validation remains pending until the authorized evidence collection, dashboard mapping and owned cleanup are executed and recorded.

Previous: [Chapter 68 — Import Export Migration and Data Reconciliation](68-import-export-migration-and-data-reconciliation.md).  
Next: Chapter 70 — Alert Thresholds SLOs and Capacity Forecasting.
