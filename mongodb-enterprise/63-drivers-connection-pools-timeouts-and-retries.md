# 63 — Drivers Connection Pools Timeouts and Retries

Part 8 — Administration Deployment and Integration

**Baseline:** Healthy three-member Enterprise 8.0/FCV 8.0 TLS/SCRAM replica set retained from Chapter 60 or a fully accepted Chapter 62 native lab. Pin a compatible synchronous PyMongo 4.x release supporting CSOT and the APIs below.  
**Status:** Written; static/helper tests complete; live pool contention, deadline, election and application recovery validation pending.  
**Prerequisites:** Chapter 27 consistency, Chapter 28 elections, Chapter 41 least privilege, Chapter 42 TLS and the accepted deployment/ownership packet.

## 1. Define the client acceptance contract

Create a separate owned application fixture, reuse one client across bounded worker threads, measure pool/command events and operation outcomes, compare a normal pool with a deliberately constrained lab profile, observe distinct timeout boundaries, and reconcile ambiguous writes without inventing new operation identities.

The required lab changes client settings and writes only to `mongodb_enterprise_tutorial_ch63`. It does not resize the retained database, alter its FCV, disable TLS, inject server failpoints or stop nodes. An optional election exercise uses Chapter 28’s separately reviewed maintenance procedure after the cluster is healthy.

A successful request after failover does not establish that every request succeeded. Acceptance includes failed operations, checkout failures, attempted commands, deadlines and reconciliation. A pool-capacity experiment on 50 tiny orders is a demonstration, not a production capacity benchmark.

## 2. Understand discovery, selection and checkout

A replica-set client discovers members from seed addresses and selects a suitable server for each operation. It then obtains a connection from that server’s pool. Seeds are discovery entry points; every advertised address required by the application must be resolvable, reachable and covered by valid TLS names.

| Boundary | Evidence | Typical issue |
|---|---|---|
| Name resolution/TLS/authentication | DNS, certificate and driver diagnostics | Unreachable advertised hosts, wrong SAN or credentials |
| Server selection | Topology and selection timeout | No suitable primary/read target |
| Connection establishment | Connection-created/ready events | TCP/TLS/auth setup delay or connection storms |
| Pool checkout | Checkout duration/failure events | Busy pool or connections still being established |
| Server command | Started/succeeded/failed events | Query, lock, storage or network delay |
| Application request | Queue and total elapsed time | Upstream queueing, serialization and downstream work |

Constructing a client is not a readiness check. Require an explicit authenticated ping and an application operation. A server-side slow query log cannot show time spent waiting in an application queue or waiting to obtain a connection before a command was sent.

## 3. Reuse clients and budget connection fan-out

Use a long-lived client per process and compatible configuration/security identity, shared across supported threads. Close it during orderly process shutdown. Avoid creating/closing a client per request or sharing an inherited client across forked worker processes; create clients in the worker’s supported lifecycle. Sessions/transactions have separate sharing constraints and must not be treated as globally reusable thread-safe request state.

Pools are associated with servers, not one universal application-wide socket limit. Monitoring connections and topology behavior mean a `maxPoolSize` value is not a cap on every socket opened by the process. Read preferences can activate pools on additional members.

For planning, consider the bound:

`application replicas × worker processes × clients per process × contacted servers × maxPoolSize`

This is a capacity envelope for application pools, not the observed connection count. Add monitoring and other clients; compare actual server connections, process/file-descriptor limits, memory and network/NAT limits. For example, 12 pods × 4 workers × 1 client × 3 contacted members × 20 pool slots yields 2,880 possible application pool slots. Primary-only traffic may use far fewer, while secondary reads and reconnects change the distribution.

## 4. Tune pool controls against workload evidence

| Setting | Purpose | Tuning implication |
|---|---|---|
| `maxPoolSize` | Per-server application connection ceiling | Raising it can move contention into the database |
| `minPoolSize` | Maintained minimum per pool | Multiplies idle connections across processes/servers |
| `maxConnecting` | Concurrent connection establishment per pool | Not the total pool size; affects ramp-up and storms |
| `maxIdleTimeMS` | Retire idle connections | Coordinate with idle middlebox policy and churn |
| `waitQueueTimeoutMS` | Checkout wait limit when applicable | Isolate in a non-CSOT experiment; verify driver semantics |

Bound application concurrency and queues separately. A pool limit alone does not impose an adequate admission policy on incoming requests. Long transactions, pinned connections and long polling can occupy connections differently from brief point reads.

A starting estimate is measured operation arrival rate multiplied by connection occupancy time, with headroom validated under representative load. At 500 operations/second and 20 ms average occupancy, average occupancy is roughly ten connections. Tail latency, bursts, read/write distribution and process count still determine whether that estimate works. Do not size from requests per day or CPU count alone.

## 5. Assign distinct timeout boundaries

| Control | Scope | Interpretation |
|---|---|---|
| `serverSelectionTimeoutMS` | Finding a suitable server | Selection failure does not mean a slow query ran |
| `connectTimeoutMS` | Establishing a connection | Not a whole request budget |
| `waitQueueTimeoutMS` | Waiting for pool checkout | Not a database execution timer |
| `socketTimeoutMS` | Socket response wait when applicable | Network timeout can leave write outcome uncertain |
| Query `maxTimeMS` / `max_time_ms` | Server execution limit | Excludes upstream application queueing |
| Write concern `wtimeout` | Waiting for acknowledgement requirements | Does not undo a write that occurred |
| `timeoutMS` / `pymongo.timeout()` | Client operation/deadline scope | Covers driver work, including selection and checkout |
| Service request deadline | Entire service request | Must include application queueing and other dependencies |

Prefer an explicit deadline design. Do not add all option values and call that the request maximum. Their precedence and interaction vary by driver/version; CSOT can change treatment of socket/checkout/write-concern limits. This lab uses **no CSOT** in its checkout experiment and an explicit timeout context in the normal workload. It does not claim that `waitQueueTimeoutMS` is independently enforced under every CSOT configuration.

An outer `pymongo.timeout()` block supplies a shared remaining budget to operations inside it. Starting a fresh timeout around every retry can exceed the original request deadline. Account for business processing/admission time before entering the driver; a client timeout does not by itself bound the whole service.

## 6. Distinguish driver retries from business replay

Eligible retryable reads/writes depend on server topology, driver, operation and error. Single-document updates are different from multi-document writes, transactions or arbitrary application sequences. A successful retryable write acknowledgement is not a transaction across several application operations.

Classic retry behavior and CSOT behavior differ: do not hard-code “exactly one retry” as a universal guarantee. Current retry specifications allow repeated eligible attempts within the remaining CSOT budget. Inspect behavior for the pinned driver and classify nonretryable errors correctly.

An application-level replay is a new call and can be a new logical driver operation. A non-idempotent `$inc`, payment or external side effect can happen twice if replayed after an unknown result. Use a stable business operation ID, uniqueness and atomic state transitions appropriate to the domain. Driver retryability does not make an entire workflow exactly once.

This lab uses `_id = RUN63:scenario:index` and immutable `$setOnInsert` payloads. It rereads at majority concern. If the write or read times out, retain the original ID and reconcile before any business decision. The sample has no unbounded application retry loop.

## 7. Prepare the retained cluster and client environment

Select one accepted cluster. Record its original ownership ID, namespace/CR or host identities, actual set name and healthy replica state. Do not replace that owner ID with `RUN63`; Chapter 63 owns only its separate database fixture. Reject unrelated clusters before writing.

```bash
umask 077
mkdir mongodb-ch63
cd mongodb-ch63
export LAB63_ROOT="$PWD"
mkdir scripts input evidence private
export RUN63="$(python3 -c 'import uuid; print(uuid.uuid4())')"
printf '%s\n' "$RUN63" > evidence/run63.txt
python3 -m venv .venv
. .venv/bin/activate
: "${PYMONGO63_VERSION:?pin the reviewed compatible PyMongo 4.x version}"
python3 -m pip install "pymongo==$PYMONGO63_VERSION"
python3 -m pip freeze > evidence/client-packages63.txt
python3 -c 'import sys, pymongo; print(sys.version); print(pymongo.version)' > evidence/client-runtime63.txt
```

Set `URI63` to a credential-free `mongodb://` seed-list URI with **only** the reviewed `replicaSet` query option. Set `APP63_USER`, `APP63_AUTHDB`, and `CA63_FILE`. Create the application user through the retained owner’s supported workflow with read/write access only to `mongodb_enterprise_tutorial_ch63`. Use a separate diagnostic/maintenance identity for cluster administration.

The runner prompts for the password; do not place it in arguments or evidence. It requires certificate verification. For x509, external authentication, SRV or async drivers, adapt the authenticated client factory and test it separately; this executable lab is synchronous SCRAM with a standard seed-list URI. Local laptop connectivity to one seed is insufficient if discovered member addresses are inaccessible.

## 8. Save settings and the event recorder

Save `scripts/core63.py`. It validates bounded lab settings and stores only event metadata. Listener callbacks run synchronously; keep them short. The in-memory event cap makes truncation visible. These are lab artifacts, not production telemetry exporters.

```python
import collections
import hashlib
import json
import re
import threading
import time

def require(ok, message):
    if not ok:
        raise ValueError(message)

def settings(raw):
    keys = {'pool', 'workers', 'operations', 'waitMS', 'deadlineMS', 'retry', 'pauseMS'}
    require(set(raw) == keys, 'exact settings keys required')
    for name, low, high in [('pool', 1, 16), ('workers', 1, 16), ('operations', 1, 200),
                            ('waitMS', 1, 5000), ('pauseMS', 0, 1000)]:
        require(type(raw[name]) is int and low <= raw[name] <= high, 'invalid ' + name)
    require(type(raw['retry']) is bool, 'retry must be boolean')
    require(raw['deadlineMS'] is None or
            (type(raw['deadlineMS']) is int and 1 <= raw['deadlineMS'] <= 10000), 'invalid deadline')
    return dict(raw)

def operation_id(run, scenario, index):
    require(isinstance(run, str) and re.fullmatch(r'[a-zA-Z0-9-]{1,80}', run), 'invalid run')
    require(isinstance(scenario, str) and re.fullmatch(r'[a-zA-Z0-9-]{1,40}', scenario), 'invalid scenario')
    require(type(index) is int and index >= 0, 'invalid operation index')
    return f'{run}:{scenario}:{index}'

def fixture_digest(rows):
    expected = [{'_id': i, 'code': f'order-{i}', 'amountCents': i * 10} for i in range(1, 51)]
    require(rows == expected, 'exact order fixture differs')
    return hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()

class Recorder:
    def __init__(self):
        self.lock = threading.Lock()
        self.events = []
        self.dropped = 0
    def add(self, kind, **fields):
        row = {'kind': kind, 'monotonic': time.monotonic(), **fields}
        with self.lock:
            if len(self.events) < 10000:
                self.events.append(row)
            else:
                self.dropped += 1
    def snapshot(self):
        with self.lock:
            events = list(self.events)
            return {'events': events, 'counts': dict(collections.Counter(r['kind'] for r in events)),
                    'droppedEvents': self.dropped}

def summary(rows, run, scenario, total):
    require(len(rows) == total and len({r['index'] for r in rows}) == total and
            {r['index'] for r in rows} == set(range(total)), 'incomplete/duplicate operation ledger')
    for row in rows:
        require(row['operationId'] == operation_id(run, scenario, row['index']), 'wrong operation identity')
        require(row['status'] in ('verified', 'unknown') and type(row['timeout']) is bool and
                type(row['elapsedMS']) in (int, float) and row['elapsedMS'] >= 0, 'invalid outcome')
        require(row['status'] != 'verified' or
                (row['exceptionType'] is None and not row['timeout']), 'contradictory success')
    return {'verified': sum(r['status'] == 'verified' for r in rows),
            'unknown': sum(r['status'] == 'unknown' for r in rows),
            'timeoutExceptions': sum(r['timeout'] for r in rows)}
```

Create three profiles. Values are deliberately small lab choices, not defaults or production recommendations:

```json
{"pool":4,"workers":4,"operations":80,"waitMS":1000,"deadlineMS":5000,"retry":true,"pauseMS":0}
```

Save as `input/baseline63.json`. Save the next profile as `input/contention63.json`:

```json
{"pool":1,"workers":8,"operations":160,"waitMS":10,"deadlineMS":null,"retry":false,"pauseMS":0}
```

Save the optional election profile as `input/election63.json`:

```json
{"pool":4,"workers":4,"operations":160,"waitMS":1000,"deadlineMS":5000,"retry":true,"pauseMS":1000}
```

With no driver CSOT, the contention profile relies on phase-specific selection/connect/socket/write-concern bounds. It is not a whole-request deadline demonstration. The runner has only as many submitted jobs as workers; it does not enqueue an unbounded stream of operations.

## 9. Save the shared-client runner

Save `scripts/client63.py` alongside `core63.py`. Modes are `init`, `workload`, `reconcile`, and `deadline`. The same run/scenario identifies the same immutable operations; always use a new output path. Initial setup creates only the new Chapter 63 database; subsequent modes require its existing owner marker and exact fixture.

```python
import concurrent.futures as futures
import contextlib
import datetime as dt
import getpass
import hashlib
import json
import os
import pathlib
import sys
import time
import urllib.parse
import pymongo
from pymongo import monitoring
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from core63 import Recorder, fixture_digest, operation_id, require, settings, summary

class PoolEvents(monitoring.ConnectionPoolListener):
    def __init__(self, recorder): self.r = recorder
    def record(self, kind, event):
        self.r.add(kind, address=list(event.address),
                   reason=str(getattr(event, 'reason', '')),
                   durationSeconds=getattr(event, 'duration', None))
    def pool_created(self, e): self.record('pool_created', e)
    def pool_ready(self, e): self.record('pool_ready', e)
    def pool_cleared(self, e): self.record('pool_cleared', e)
    def pool_closed(self, e): self.record('pool_closed', e)
    def connection_created(self, e): self.record('connection_created', e)
    def connection_ready(self, e): self.record('connection_ready', e)
    def connection_closed(self, e): self.record('connection_closed', e)
    def connection_check_out_started(self, e): self.record('checkout_started', e)
    def connection_check_out_failed(self, e): self.record('checkout_failed', e)
    def connection_checked_out(self, e): self.record('checked_out', e)
    def connection_checked_in(self, e): self.record('checked_in', e)

class CommandEvents(monitoring.CommandListener):
    def __init__(self, recorder): self.r = recorder
    def started(self, e):
        self.r.add('command_started', command=e.command_name, requestId=e.request_id,
                   address=list(e.connection_id))
    def succeeded(self, e):
        self.r.add('command_succeeded', command=e.command_name, requestId=e.request_id,
                   address=list(e.connection_id), durationMicros=e.duration_micros)
    def failed(self, e):
        self.r.add('command_failed', command=e.command_name, requestId=e.request_id,
                   address=list(e.connection_id), durationMicros=e.duration_micros)

def error_fields(error):
    return {'exceptionType': type(error).__name__, 'timeout': bool(getattr(error, 'timeout', False)),
            'errorLabels': [label for label in ('RetryableWriteError', 'NoWritesPerformed',
                             'TransientTransactionError', 'UnknownTransactionCommitResult')
                            if callable(getattr(error, 'has_error_label', None)) and error.has_error_label(label)]}

def run(mode, profile_path, scenario, output):
    require(mode in ('init', 'workload', 'reconcile', 'deadline'), 'invalid mode')
    require(not pathlib.Path(output).exists(), 'new output path required')
    blob = pathlib.Path(profile_path).read_bytes()
    cfg = settings(json.loads(blob))
    run_id = os.environ['RUN63']
    operation_id(run_id, scenario, 0)
    uri = os.environ['URI63']
    parsed = urllib.parse.urlsplit(uri)
    options = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    require(parsed.scheme == 'mongodb' and parsed.netloc and parsed.username is None and
            parsed.password is None and parsed.path in ('', '/') and not parsed.fragment and
            set(options) == {'replicaSet'} and len(options['replicaSet']) == 1 and
            options['replicaSet'][0], 'credential-free reviewed replicaSet-only URI required')
    recorder = Recorder()
    password = getpass.getpass('Chapter 63 application password: ')
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    with pymongo.MongoClient(uri, username=os.environ['APP63_USER'], password=password,
            authSource=os.environ['APP63_AUTHDB'], tls=True, tlsCAFile=os.environ['CA63_FILE'],
            appname='mongodb-tutorial-ch63', maxPoolSize=cfg['pool'], minPoolSize=0, maxConnecting=2,
            waitQueueTimeoutMS=cfg['waitMS'], connectTimeoutMS=1000,
            serverSelectionTimeoutMS=3000, socketTimeoutMS=10000,
            retryReads=cfg['retry'], retryWrites=cfg['retry'],
            event_listeners=[PoolEvents(recorder), CommandEvents(recorder)]) as client:
        client.admin.command('ping')
        hello = client.admin.command('hello')
        require(hello.get('setName') == options['replicaSet'][0] and hello.get('isWritablePrimary') is True,
                'reviewed writable replica set required')
        database = client.get_database('mongodb_enterprise_tutorial_ch63',
            read_concern=ReadConcern('majority'), write_concern=WriteConcern(w='majority', j=True, wtimeout=3000))
        if mode == 'init':
            require(not database.list_collection_names(), 'new Chapter 63 database required')
            database.markers.insert_one({'_id': 'owner', 'runId': run_id, 'chapter': 63})
            database.orders.insert_many([{'_id': i, 'code': f'order-{i}', 'amountCents': i * 10}
                                         for i in range(1, 51)])
            database.orders.create_index('code', unique=True, name='code_unique63')
        owner = database.markers.find_one({'_id': 'owner'})
        require(owner and owner.get('runId') == run_id and owner.get('chapter') == 63, 'ownership differs')
        digest = fixture_digest(list(database.orders.find().sort('_id', 1)))
        require(any(i.get('name') == 'code_unique63' and i.get('unique') is True and
                    i.get('key') == {'code': 1} for i in database.orders.list_indexes()), 'index differs')
        workload_start = time.monotonic()
        rows = []
        deadline_result = None
        def operation(index):
            identifier = operation_id(run_id, scenario, index)
            payload = {'_id': identifier, 'runId': run_id, 'kind': 'driver-probe'}
            begin = time.monotonic()
            row = {'index': index, 'operationId': identifier, 'status': 'unknown',
                   'exceptionType': None, 'timeout': False, 'errorLabels': []}
            try:
                scope = pymongo.timeout(cfg['deadlineMS'] / 1000) if cfg['deadlineMS'] is not None else contextlib.nullcontext()
                with scope:
                    if mode == 'workload':
                        database.markers.update_one({'_id': identifier}, {'$setOnInsert': payload},
                                                    upsert=True, comment=identifier)
                    observed = database.markers.find_one({'_id': identifier}, comment=identifier)
                    if mode == 'reconcile':
                        row['reconciliation'] = 'present' if observed == payload else 'missing' if observed is None else 'mismatch'
                    require(observed == payload, 'marker missing or differs')
                    row['status'] = 'verified'
            except Exception as error:
                row.update(error_fields(error))
            row['elapsedMS'] = (time.monotonic() - begin) * 1000
            return row
        if mode in ('workload', 'reconcile'):
            def worker(worker_id):
                result = []
                for index in range(worker_id, cfg['operations'], cfg['workers']):
                    result.append(operation(index))
                    if cfg['pauseMS']: time.sleep(cfg['pauseMS'] / 1000)
                return result
            with futures.ThreadPoolExecutor(max_workers=cfg['workers']) as executor:
                jobs = [executor.submit(worker, i) for i in range(cfg['workers'])]
                for job in jobs: rows.extend(job.result())
            rows.sort(key=lambda r: r['index'])
        elif mode == 'deadline':
            # Consume the context's budget before issuing a read; no server slowdown is injected.
            begin = time.monotonic()
            try:
                with pymongo.timeout(0.001):
                    time.sleep(0.020)
                    database.orders.find_one({'_id': 1})
                deadline_result = {'observedTimeout': False, 'exceptionType': None}
            except pymongo.errors.PyMongoError as error:
                deadline_result = {'observedTimeout': bool(error.timeout), **error_fields(error)}
            deadline_result['elapsedMS'] = (time.monotonic() - begin) * 1000
        final_digest = fixture_digest(list(database.orders.find().sort('_id', 1)))
        require(digest == final_digest, 'fixture changed')
        result = {'runId': run_id, 'scenario': scenario, 'mode': mode, 'settings': cfg,
                  'driverVersion': pymongo.version, 'setName': hello['setName'],
                  'startedAt': started, 'finishedAt': dt.datetime.now(dt.timezone.utc).isoformat(),
                  'settingsSha256': hashlib.sha256(blob).hexdigest(), 'fixtureDigest': digest,
                  'workloadStartedMonotonic': workload_start, 'operations': rows,
                  'summary': summary(rows, run_id, scenario, cfg['operations']) if rows else None,
                  'deadlineObservation': deadline_result}
    result['telemetry'] = recorder.snapshot()
    with open(output, 'x', encoding='utf-8') as file:
        json.dump(result, file, indent=2)
        file.write('\n')
    return 0 if (not rows or all(r['status'] == 'verified' for r in rows)) and \
                (mode != 'deadline' or deadline_result['observedTimeout']) else 2

if __name__ == '__main__':
    try:
        require(len(sys.argv) == 5, 'usage: client63.py MODE SETTINGS_JSON SCENARIO NEW_REPORT')
        sys.exit(run(*sys.argv[1:]))
    except Exception as error:
        # Keep credential/topology-bearing exception messages out of ordinary output.
        print('REJECTED: ' + type(error).__name__, file=sys.stderr)
        sys.exit(1)
```

Output exit 0 means the mode’s recorded operations verified, exit 2 means an observation report includes unknown operations or the deadline observation was not achieved, and exit 1 means setup/finalization failed. No report after a finalization failure is evidence of incomplete collection; it must not be relabeled as success. Preserve raw private diagnostics separately if required by the incident owner.

The ledger catches per-operation exceptions so failures remain visible; a programming/payload error is not automatically a retryable database error. Callbacks avoid documents, replies and exception text. Stored addresses are still infrastructure metadata; retain reports privately. Command success events describe command responses, not full business success or majority-write acceptance by themselves.

## 10. Establish normal client behavior

Run fixture initialization once, followed by the normal workload:

```bash
python3 scripts/client63.py init input/baseline63.json baseline evidence/initialized63.json
python3 scripts/client63.py workload input/baseline63.json baseline evidence/baseline63.json
```

Require the reviewed set and run marker, exact 50 orders/12,750 cents, unique index, verified operations and no unexplained checkout failures. Correlate event times after `workloadStartedMonotonic`; the event log also contains setup and final verification. Ignore neither warm-up cost nor failures merely because a later operation succeeded.

Summarize operation p50/p95/p99 from **all** elapsed outcomes and report failure counts separately. A small sample cannot support stable production tail estimates. Compare per-command duration with full operation elapsed time; the latter includes a write and read plus driver work. The difference is not a precise checkout measure—use CMAP durations/events for that.

The runner prewarms with ping/setup, so this required comparison is principally a warm-client experiment. To study cold starts, use separate new processes and explicit startup timing; changing `maxConnecting` on the warm workload does not demonstrate startup behavior.

## 11. Observe a constrained pool without misclassifying it

Run the bounded contention profile only against the authorized lab:

```bash
python3 scripts/client63.py workload input/contention63.json contention evidence/contention63.json
```

Inspect checkout duration/failure events, reason fields, command attempts, verified/unknown counts and total elapsed times. With one pool slot and eight workers, checkout contention is possible; tiny local operations may still finish without a timeout. If no checkout failure is observed, report **contention timeout not demonstrated**, not a fabricated pass.

You may make one reviewed change to the lab profile, such as a smaller checkout wait or bounded higher concurrency within the validation limits, and record a new scenario/settings hash. Do not inject a sleep into a synchronous listener to pretend it represents database latency, run expensive unindexed queries against shared data, or keep increasing concurrency until production fails.

A checkout failure can also be related to connection setup or pool state. Attribute the failure using its reason, topology and connection events; every `ConnectionFailure` is not pool exhaustion. Restore the baseline profile and run a new recovery scenario:

```bash
python3 scripts/client63.py workload input/baseline63.json recovery evidence/recovery63.json
```

Require restored normal behavior and healthy server observations. Raising `maxPoolSize` is accepted only if it resolves the measured client bottleneck without worsening database latency/resource pressure. This chapter does not infer that a larger pool always improves throughput.

## 12. Observe deadline and selection failures separately

Run the already-expired timeout-context observation:

```bash
python3 scripts/client63.py deadline input/baseline63.json deadline evidence/deadline63.json
```

Require a timeout exception. The context is deliberately consumed before a read, so this demonstrates deadline enforcement, **not** a slow server or precise one-millisecond request scheduling. Check whether a find command started in the relevant event interval; do not assume an expired client budget always means a write could not have been sent in a different scenario.

For a separate local server-selection observation, save `scripts/selection63.py`. It reserves a loopback port without listening, uses no database credentials, and changes no real cluster:

```python
import json
import socket
import time
import pymongo
from pymongo.errors import ServerSelectionTimeoutError

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reserved:
    reserved.bind(('127.0.0.1', 0))
    port = reserved.getsockname()[1]
    begin = time.monotonic()
    with pymongo.MongoClient(f'mongodb://127.0.0.1:{port}/', directConnection=True,
                            serverSelectionTimeoutMS=300, connectTimeoutMS=100) as client:
        try:
            client.admin.command('ping')
        except ServerSelectionTimeoutError:
            print(json.dumps({'claim': 'local_selection_failure_observed',
                              'elapsedMS': (time.monotonic() - begin) * 1000}))
        else:
            raise RuntimeError('expected local selection failure not observed')
```

This script does not test production DNS/TLS/authentication or a server executing a command. Elapsed wall time can exceed the configured value due to discovery cadence, scheduling and cleanup. A live socket-timeout or server `maxTimeMS` demonstration needs a separately reviewed bounded workload/fault test; do not claim those paths were exercised by this local selection example.

## 13. Reconcile unknown writes by stable identity

Reconcile every original scenario after its worker activity has stopped and the cluster is healthy. Use the **same run, scenario and operation count** and a baseline-derived profile with that original count; reconciliation only reads markers at majority concern.

Create the 160-operation reconciliation profile once:

```bash
python3 - <<'PY'
import json
import pathlib
profile = json.loads(pathlib.Path('input/baseline63.json').read_text())
profile['operations'] = 160
with open('input/reconcile-contention63.json', 'x') as output:
    json.dump(profile, output)
PY
```

```bash
# For baseline, the baseline profile already has the original count.
python3 scripts/client63.py reconcile input/baseline63.json baseline evidence/baseline-reconciled63.json
# For contention, prepare a baseline-settings copy with operations=160.
python3 scripts/client63.py reconcile input/reconcile-contention63.json contention evidence/contention-reconciled63.json
```

Inspect `present`, `missing`, `mismatch`, and read errors independently. An operation that originally timed out can later be present; its original error remains part of the availability result. A missing record during an unresolved write/read/network incident is not definitive proof that no write occurred. Quiesce original activity, check the authoritative cluster and preserve uncertainty where needed.

A payload mismatch requires investigation. Do not overwrite the existing marker to make reconciliation pass. If a reviewed replay is appropriate, rerun the same immutable IDs and payloads after the deadline/recovery decision; record it as a new attempt with a new output file. Do not add a new operation ID for the same business action.

This fixture’s marker upsert/read is a deliberately simple idempotent operation. For real order state, balances or external side effects, require unique business keys, conditional transitions, transactions/outbox or another explicit consistency contract; a marker alone does not protect unrelated effects.

## 14. Observe optional election and client recovery

Only after normal and recovery profiles pass, start the bounded election workload in one terminal:

```bash
python3 scripts/client63.py workload input/election63.json election evidence/election63.json
```

In a second terminal, use Chapter 28’s owned replica-set stepdown procedure with the maintenance identity, healthy/electable secondaries and no concurrent changes. Do not use the Chapter 63 application identity to obtain administrative power, stop two members, force election or disable retry budgets.

Record stepdown time, old/new primary, replica health and the actual overlap with workload operations/command events. If the workload finished before the action, the election-overlap claim is not demonstrated. The pool listener records pool changes but not every topology transition; keep separate diagnostic/management evidence.

Compare application errors, latency and attempted commands before/during/after election, then reconcile all 160 election IDs with a baseline-settings profile containing that count. A retry-disabled comparison needs another separately reviewed election and scenario; it is not inferred from contention because that profile also changes pool/deadline settings.

Restore a fully healthy cluster before any second action. Retry settings can hide some transient failures, but they cannot make loss of majority, persistent network failure or rejected credentials disappear. Retain the exact driver version and observed attempt behavior rather than asserting a fixed retry count.

## 15. Diagnose client incidents with both sides of the connection

| Symptom | First evidence | Corrective direction |
|---|---|---|
| Selection timeout | DNS, advertised hosts, topology, TLS and primary status | Restore a suitable reachable target; do not enlarge pool first |
| Checkout timeouts with busy pool | CMAP wait/occupancy and workload concurrency | Bound admission; reduce occupancy; then assess pool capacity |
| Slow connection-ready events | TLS/auth/TCP and reconnect bursts | Fix setup path and ramp-up before raising `maxConnecting` |
| Long command durations | Query plans, storage/CPU, locks and replication | Address database/query bottleneck |
| Low command time but high request time | Application queue, checkout and other dependencies | Trace the full request budget |
| Unknown write after timeout | Stable ID, error labels and majority readback | Reconcile before replay/business response |
| Many new clients/connections | Process/client lifecycle and scaling | Reuse clients; account for process/pod fan-out |
| Idle connection churn | Idle timeouts, middleboxes and pool clear events | Coordinate idle policy and observe reconnection cost |

Capture driver exception class and timeout flag plus selected error labels. A timeout property says the exception is timeout-related; it does not uniquely identify the phase. Correlate with events and actual server state. Authorization failures, duplicate keys, programming errors and transient transport failures need different handling.

For Kubernetes, include application replica count, worker count, readiness/startup behavior, DNS and egress paths. For async services, use a compatible async client and avoid synchronous database calls blocking the event loop; these threading scripts do not demonstrate event-loop behavior.

## 16. Acceptance, offline checks and cleanup

Offline verification must parse all Bash/Python/JSON blocks, validate profile bounds, test complete and unknown-operation summaries, reject duplicate/missing/wrong operation IDs and altered fixture rows, and exercise recorder concurrency/cap behavior. Listener/mocked-client checks can establish callback/API wiring only; they cannot prove live pool, TLS or retry behavior.

Required live evidence includes reviewed topology and credentials, owned exact fixture, normal workload results, constrained-pool observations with honest demonstrated/inconclusive status, restored client behavior, deadline/selection observations and reconciliation. Optional election acceptance additionally requires actual overlapping traffic, primary transition, full recovery and reconciled operations.

Keep the chapter’s runtime tracker pending until those observations have run against the actual pinned driver and lab. Do not substitute synthetic records for driver events. Document any missing telemetry or failed finalization.

Retain the fixture for later client integration/CDC work. If cleanup is required, verify the Chapter 63 owner marker, stop its workers/clients, preserve evidence, and drop only the explicitly owned `mongodb_enterprise_tutorial_ch63` database under the owner’s approved retirement. Remove only users/roles created exclusively for this lab through the supported management workflow. Do not drop the retained cluster, namespace, PVCs, Chapter 60/62 fixture or shared credentials.

## 17. References and next chapter

Select documentation matching the pinned driver/server releases; APIs/defaults and CSOT interactions can change.

- [PyMongo connection-pool settings](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/connect/connection-options/connection-pools/)
- [PyMongo operation timeout](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/connect/connection-options/csot/)
- [PyMongo monitoring API](https://pymongo.readthedocs.io/en/stable/api/pymongo/monitoring.html)
- [Driver connection monitoring and pooling specification](https://github.com/mongodb/specifications/blob/master/source/connection-monitoring-and-pooling/connection-monitoring-and-pooling.md)
- [Client-side operation timeout specification](https://github.com/mongodb/specifications/blob/master/source/client-side-operations-timeout/client-side-operations-timeout.md)
- [Retryable writes in MongoDB 8.0](https://www.mongodb.com/docs/v8.0/core/retryable-writes/)
- [PyMongo CRUD configuration](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/crud/configure/)
- [Chapter 62 — Rolling Upgrades FCV and Rollback Constraints](62-rolling-upgrades-fcv-and-rollback-constraints.md)

Next: **Chapter 64 — Change Streams Resume Tokens and CDC** (planned).
