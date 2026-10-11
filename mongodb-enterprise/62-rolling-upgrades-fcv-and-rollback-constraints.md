# 62 — Rolling Upgrades FCV and Rollback Constraints

Part 8 — Administration Deployment and Integration

**Baseline:** Self-managed MongoDB Enterprise; a separate three-member 7.0/FCV 7.0 replica set for the 7.0 → 8.0 major-upgrade exercise. Pin exact supported patches and platform/management versions before running.  
**Status:** Written; static checks complete; live binary rollout, election, FCV transition and recovery validation pending.  
**Prerequisites:** Replica-set administration, Chapter 28 maintenance, Chapter 56 restore acceptance, Chapter 59 service operations and Chapters 60–61 for managed Kubernetes deployments.

## 1. Define the operational outcome

Upgrade an isolated three-data-bearing-member replica set while preserving its dataset and identity. Observe each member return healthy before changing another. Exercise application majority writes through the election, measure client errors and recovery, burn in on the target binaries with the source FCV, and make a separate decision to activate the target FCV.

This chapter does not downgrade the retained Chapter 60–61 deployment to construct its starting point. That deployment already runs 8.0/FCV 8.0. Build a **separate** 7.0 lab using the earlier replica-set/TLS/service procedures, or perform only the planning exercise and mark runtime work pending. A same-series 8.0 patch rollout is useful maintenance practice but does not demonstrate a 7.0 → 8.0 FCV transition.

Success means a verified upgrade and a usable recovery decision, not a claim of zero downtime. A planned election can interrupt operations. Recovery from an older backup can lose later writes unless the accepted recovery plan supplies and validates them.

## 2. Separate binary, FCV and management versions

| Version or setting | What to verify | What it does not establish |
|---|---|---|
| Server binary | Direct `buildInfo.version` on every member | FCV convergence or application compatibility |
| FCV | Direct `getParameter` result on every member | Exact patch, driver compatibility or downgrade permission |
| Driver/client | Actual application dependency and tested behavior | Compatibility of every service using the cluster |
| Agent/Ops Manager/controller | Supported matrix and desired/actual status | Running server version merely from a selected image |
| OS/crypto/platform | Package dependencies, CPU, TLS and runtime support | Database schema/query compatibility |

FCV governs compatibility-sensitive server features and persisted formats; it does not make a newer server behave exactly like the older server. Test query semantics, authorization, monitoring and driver behavior on the actual target binary.

For this lab, record exact `SOURCE62_VERSION` in the 7.0 series and `TARGET62_VERSION` in the 8.0 series. Choose patches from release notes and the management compatibility matrix at execution time. Do not copy a historical patch number or assume the highest available package is supported by the installed controller.

## 3. Pin the version-specific upgrade and downgrade rules

Use the versioned 8.0 replica-set upgrade procedure for this 7.0 → 8.0 exercise. It requires a 7.0 source with FCV 7.0; older sources need intervening upgrade stages. Validate each hop separately. Mixed binaries are a controlled transition, not the desired long-term deployment.

The 8.0 documentation states that binary downgrade requires MongoDB Support assistance. Lower source FCV during burn-in reduces exposure to incompatible persisted features, but does **not** grant permission to run old binaries on the upgraded data directory. FCV reversal, package reversal and restore are different actions with different constraints.

Do not transplant downgrade instructions from another release family. In particular, later server releases can document different downgrade capabilities. Record the exact release-specific support decision, incompatibility removals and management workflow before any proposed reversal. This lab executes no binary downgrade.

## 4. Establish one owner and one change at a time

| Deployment owner | Supported change path | Avoid |
|---|---|---|
| Native services maintained by this lab | Reviewed per-host service/package or pinned-binary change | Updating all hosts simultaneously |
| Ops Manager Automation | Reviewed automation plan and supported version/FCV workflow | Manual binary replacement underneath Automation |
| Kubernetes controller | Supported MongoDB CR version and FCV fields | Patching generated StatefulSets/images directly |
| Atlas | Managed-service upgrade procedure | Applying native host commands |

Choose one track. The hands-on host steps below assume unautomated native services on three isolated hosts. For managed resources, retain the database gates and application observations but replace host mutations with the supported owner's workflow. Do not run both controllers and manual package commands against the same processes.

Keep controller upgrades, node maintenance, certificate rotation, storage expansion, replica scaling and binary rollout as separate changes. An observed extra restart invalidates a narrowly scoped single-member stage until investigated.

## 5. Build the fresh lab and record ownership

Provision three data-bearing members using the earlier replica-set and TLS procedures, with distinct persistent storage and reachable TLS-valid hostnames. Start all three with the reviewed source 7.0 patch and FCV 7.0. Use set name `rs62lab`, database `mongodb_enterprise_tutorial_ch62`, and separate admin/diagnostic/application identities. The application identity receives read/write access only to this database; diagnostic permissions include replica status/configuration, FCV and build information plus dataset metadata reads.

Each host must have its own reviewed service configuration, database directory, logs, TLS material and service account. Use supported Enterprise binaries and preserve verification of their origin/checksum. Do not reuse a Chapter 60 data directory or PVC.

```bash
umask 077
mkdir mongodb-ch62
cd mongodb-ch62
export LAB62_ROOT="$PWD"
mkdir scripts evidence private input
export RUN62="$(python3 -c 'import uuid; print(uuid.uuid4())')"
printf '%s\n' "$RUN62" > evidence/run62.txt
# Set these to exact reviewed versions, not wildcard package selectors.
: "${SOURCE62_VERSION:?pin a supported 7.0 patch}"
: "${TARGET62_VERSION:?pin a supported 8.0 patch}"
: "${CA62_FILE:?set the client trust bundle}"
: "${URI62:?set the TLS replica-set URI without a password}"
```

Record the three member FQDNs/ports, service units, configuration hashes, data paths and ownership. Map each database address to its host explicitly. Store secrets outside evidence and avoid credential-bearing URIs in command history.

Create the fixture once, through the application TLS connection to the primary. Save as `scripts/seed62.js`; refuse to overwrite an existing lab:

```javascript
const d62 = db.getSiblingDB('mongodb_enterprise_tutorial_ch62');
if (!process.env.RUN62 || d62.getCollectionNames().length !== 0)
  throw new Error('new owned database required');
function ok62(r) {
  if (r.ok !== 1 || r.writeErrors || r.writeConcernError) throw new Error(EJSON.stringify(r));
}
ok62(d62.runCommand({insert: 'markers', documents: [{_id: 'owner', chapter: 62,
  runId: process.env.RUN62}], writeConcern: {w: 'majority', j: true, wtimeout: 30000}}));
ok62(d62.runCommand({insert: 'orders', documents: Array.from({length: 50}, (_, n) =>
  ({_id: n + 1, code: `order-${n + 1}`, amountCents: (n + 1) * 10})),
  writeConcern: {w: 'majority', j: true, wtimeout: 30000}}));
ok62(d62.runCommand({createIndexes: 'orders', indexes: [{key: {code: 1},
  name: 'code_unique62', unique: true}], writeConcern: {w: 'majority', wtimeout: 30000}}));
```

Run with `mongosh "$URI62" --tls --tlsCAFile "$CA62_FILE" --username "$APP62_USER" --authenticationDatabase "$APP62_AUTHDB" --password --file scripts/seed62.js`. Set the named username/auth database variables first; the password is prompted. If seeding partially succeeds, inspect and retire only that owned disposable lab or complete an explicitly reviewed repair; do not blindly rerun inserts and call duplicate errors success.

## 6. Create the compatibility and recovery packet

Before disruption, complete this decision record with real evidence:

| Gate | Required record |
|---|---|
| Server path | Source/target exact versions and versioned upgrade procedure |
| Platform | OS/CPU/crypto/dependencies and available disk/memory capacity |
| Clients | Driver versions, TLS/authentication and representative request tests |
| Features | Indexes, time-series/encryption features, parameters and release incompatibilities |
| Management | Ownership and supported Agent/Ops Manager/controller matrix |
| Backup | Recovery-point identifier, capture time and successful isolated restore |
| Recovery | RPO/RTO, write reconciliation and current-version/support or restore route |
| Availability | Deadline, replication threshold, acceptable client errors and latency |

A backup job marked complete is insufficient. Restore into an isolated compatible deployment and verify data/indexes/roles, TLS and client access using Chapter 56. Keep restored resources fenced from production clients. Determine whether the selected backup tool supports both release families and how backup capture continues during and after the change.

Review 8.0 compatibility changes against the actual workload. Examples worth testing include null/undefined query behavior, encrypted collection algorithms and replaced monitoring metrics. Do not drop a production collection to satisfy an upgrade prerequisite without a separate migration/recovery plan. Keep feature-specific decisions in the packet; this simple orders fixture does not cover every Enterprise integration.

## 7. Capture direct member evidence

Save `scripts/member62.js`. Execute separately against each member using `directConnection=true`, its TLS-valid hostname and the diagnostic identity. Set `MEMBER62_ADDRESS` to that exact configured replica address and `EVIDENCE62_PATH` to a **new** local output path. The script accepts only healthy primary/secondary observations and checks the fixture; it does not perform any mutation.

```javascript
const fs62 = require('fs');
const crypto62 = require('crypto');
const admin62 = db.getSiblingDB('admin');
const data62 = db.getSiblingDB('mongodb_enterprise_tutorial_ch62');
const must62 = (ok, message) => { if (!ok) throw new Error(message); };
const hello62 = admin62.runCommand({hello: 1});
const build62 = admin62.runCommand({buildInfo: 1});
const fcv62 = admin62.runCommand({getParameter: 1, featureCompatibilityVersion: 1});
const status62 = admin62.runCommand({replSetGetStatus: 1});
const config62 = admin62.runCommand({replSetGetConfig: 1});
must62([hello62, build62, fcv62, status62, config62].every(r => r.ok === 1), 'diagnostic command failed');
must62(process.env.RUN62 && process.env.MEMBER62_ADDRESS && process.env.EVIDENCE62_PATH,
  'run/address/new output required');
must62(hello62.setName === 'rs62lab' && hello62.me === process.env.MEMBER62_ADDRESS &&
  (hello62.isWritablePrimary === true || hello62.secondary === true), 'wrong set/member/role');
must62(build62.modules.includes('enterprise'), 'Enterprise binary required');
must62(config62.config.members.length === 3 && config62.config.members.every(m =>
  m.votes === 1 && !m.arbiterOnly && !m.newlyAdded), 'three established data-bearing voters required');
must62(status62.members.length === 3 && status62.members.every(m => m.health === 1) &&
  status62.members.filter(m => m.state === 1).length === 1 &&
  status62.members.filter(m => m.state === 2).length === 2, 'set not fully healthy');
const owner62 = data62.markers.findOne({_id: 'owner'});
must62(owner62 && owner62.chapter === 62 && owner62.runId === process.env.RUN62, 'owner differs');
const read62 = data62.runCommand({find: 'orders', filter: {}, sort: {_id: 1},
  batchSize: 100, readConcern: {level: 'majority'}});
must62(read62.ok === 1 && String(read62.cursor.id) === '0', 'fixture must fit one completed cursor');
const rows62 = read62.cursor.firstBatch;
must62(rows62.length === 50, 'wrong count');
rows62.forEach((r, i) => must62(r._id === i + 1 && r.code === `order-${i + 1}` &&
  r.amountCents === (i + 1) * 10 && Object.keys(r).length === 3, 'document differs'));
must62(data62.orders.getIndexes().some(i => i.name === 'code_unique62' && i.unique === true &&
  i.key.code === 1 && Object.keys(i.key).length === 1), 'unique index differs');
const canonical62 = rows62.map(r => ({_id: Number(r._id), code: r.code, amountCents: Number(r.amountCents)}));
const ts62 = t => JSON.parse(EJSON.stringify(t, {relaxed: false})).$timestamp.t;
const primary62 = status62.members.find(m => m.state === 1);
const lag62 = Math.max(...status62.members.map(m => Math.max(0,
  ts62(primary62.optime.ts) - ts62(m.optime.ts))));
const report62 = {runId: process.env.RUN62, setName: hello62.setName, address: hello62.me,
  observedAt: new Date().toISOString(), version: build62.version, enterprise: true,
  fcv: fcv62.featureCompatibilityVersion, role: hello62.isWritablePrimary ? 'PRIMARY' : 'SECONDARY',
  members: config62.config.members.map(m => m.host).sort(), healthyMembers: 3, lagSeconds: lag62,
  count: 50, amountCents: 12750,
  ordersUUID: EJSON.stringify(data62.getCollectionInfos({name: 'orders'})[0].info.uuid, {relaxed: false}),
  ordersDigest: crypto62.createHash('sha256').update(JSON.stringify(canonical62)).digest('hex')};
fs62.writeFileSync(process.env.EVIDENCE62_PATH, JSON.stringify(report62, null, 2), {flag: 'wx', mode: 0o600});
```

For a secondary, supply a direct URI with `readPreference=secondary` so the fixture read runs there. Verify certificate SANs, keep hostname verification enabled, and use password prompting. Capture raw diagnostic outputs/logs privately alongside the compact report. Timestamp lag is an idle-fixture approximation, not committed/durable optime equivalence or proof that every application write has been applied.

## 8. Evaluate each fully recovered stage

Assemble a stage packet from three unmodified reports with fields `runId`, `capturedAt`, and `members` (the three reports). Record `capturedAt` at the end of collection. Sequential samples must represent a stable stage; recollect if an election or state change occurred while gathering them.

Save `scripts/stage62.py`. This offline gate checks evidence shape, exact versions/FCV, bounded freshness, healthy membership and fixture continuity. It does not verify signatures/provenance, start services, assess backup quality or authorize FCV changes.

```python
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys

def require(ok, message):
    if not ok:
        raise ValueError(message)

def stamp(value):
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(parsed.tzinfo is not None, 'timezone required')
    return parsed

def inspect(packet, run, expected, fcv, now, fresh):
    require(isinstance(run, str) and run.strip() and 'REPLACE' not in run and
            packet['runId'] == run, 'wrong run')
    require(isinstance(expected, dict) and len(expected) == 3 and
            all(re.fullmatch(r'(7\.0|8\.0)\.\d+', v) for v in expected.values()), 'pin three exact versions')
    captured = stamp(packet['capturedAt'])
    if fresh:
        require(0 <= (now - captured).total_seconds() <= 120, 'stale/future current stage')
    rows = packet['members']
    require(len(rows) == 3 and len({r['address'] for r in rows}) == 3 and
            {r['address'] for r in rows} == set(expected), 'wrong member addresses')
    require(sorted(r['role'] for r in rows) == ['PRIMARY', 'SECONDARY', 'SECONDARY'], 'wrong roles')
    identities = set()
    for row in rows:
        require(row['runId'] == run and row['setName'] == 'rs62lab' and row['enterprise'] is True and
                row['version'] == expected[row['address']], 'binary/ownership mismatch')
        require(row['fcv'] == {'version': fcv}, 'wrong or transitional FCV')
        require(row['members'] == sorted(expected) and row['healthyMembers'] == 3 and
                type(row['lagSeconds']) in (int, float) and 0 <= row['lagSeconds'] <= 5,
                'unhealthy/mismatched set')
        require(0 <= (captured - stamp(row['observedAt'])).total_seconds() <= 120,
                'stale/future member observation')
        require(row['count'] == 50 and row['amountCents'] == 12750 and
                isinstance(row['ordersUUID'], str) and row['ordersUUID'] and
                isinstance(row['ordersDigest'], str) and
                re.fullmatch(r'[0-9a-f]{64}', row['ordersDigest']), 'invalid fixture identity')
        identities.add((row['ordersUUID'], row['ordersDigest']))
    require(len(identities) == 1, 'member fixture identities disagree')
    return captured, identities

def evaluate(baseline, current, run, source, expected, fcv, now):
    require(re.fullmatch(r'7\.0\.\d+', source) and fcv in ('7.0', '8.0'), 'wrong lab version path')
    addresses = {r['address']: source for r in baseline['members']}
    before_time, before_ids = inspect(baseline, run, addresses, '7.0', now, False)
    after_time, after_ids = inspect(current, run, expected, fcv, now, True)
    require(set(addresses) == set(expected) and after_time >= before_time, 'membership/time changed')
    require(before_ids == after_ids, 'fixture UUID/digest changed')
    if fcv == '8.0':
        require(all(v.startswith('8.0.') for v in expected.values()), 'FCV ahead of binaries')
    return {'claim': 'recorded_healthy_upgrade_stage', 'runId': run,
            'expectedVersions': expected, 'fcv': fcv, 'fixtureContinuity': True,
            'applicationContinuityStillRequiresLiveEvidence': True,
            'binaryDowngradeAuthorized': False}

if __name__ == '__main__':
    try:
        require(len(sys.argv) == 8,
                'usage: stage62.py BASELINE CURRENT RUN SOURCE_VERSION EXPECTED_JSON FCV NEW_REPORT')
        blobs = [pathlib.Path(p).read_bytes() for p in (sys.argv[1], sys.argv[2], sys.argv[5])]
        report = evaluate(json.loads(blobs[0]), json.loads(blobs[1]), sys.argv[3], sys.argv[4],
                          json.loads(blobs[2]), sys.argv[6], dt.datetime.now(dt.timezone.utc))
        report['inputSha256'] = [hashlib.sha256(b).hexdigest() for b in blobs]
        with open(sys.argv[7], 'x', encoding='utf-8') as output:
            json.dump(report, output, indent=2)
            output.write('\n')
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as error:
        print('REJECTED: ' + str(error), file=sys.stderr)
        sys.exit(1)
```

Create `input/expected-baseline62.json` mapping the three real addresses to the exact source patch. Later stages use explicit maps reflecting one, two, then three upgraded members. Never change expected versions just to accept an unexpected binary.

```bash
python3 scripts/stage62.py private/baseline62.json private/baseline62.json \
  "$RUN62" "$SOURCE62_VERSION" input/expected-baseline62.json 7.0 evidence/baseline-accepted62.json
```

The original baseline can become old during the change; it remains immutable reference evidence. Every current stage must be newly collected within two minutes, including a new preflight immediately before disruption. The gate accepts only stable full recovery snapshots, not the period when one member is intentionally down.

## 9. Upgrade the first secondary

Choose the current healthy secondary from live status, map it to the reviewed host/unit and record its identity. Ensure all three members are healthy, the other secondary is caught up and electable, no initial sync/rollback is underway, and the maintenance deadline/recovery route remains viable.

On **only that host**, stop its reviewed native unit gracefully, verify its process has exited, install/select the exact target Enterprise binary through the reviewed platform workflow, and start the same unit with the same data/configuration. A reviewed manually installed binary may use a versioned absolute executable path; package-managed services must use their package workflow. Do not casually replace a shared symlink used by other instances.

Example host commands illustrate the service boundary; set `UNIT62` to the exact owned unit before running:

```bash
: "${UNIT62:?set the reviewed secondary service unit on this host}"
sudo systemctl stop "$UNIT62"
sudo systemctl is-active "$UNIT62" || true
# Inspect MainPID and the owned process/data path; inactive alone is not fencing.
sudo systemctl show "$UNIT62" -p MainPID -p ExecStart -p FragmentPath
# Apply the reviewed exact-version installation/configuration here.
# Use daemon-reload only if the owned unit definition changed.
sudo systemctl start "$UNIT62"
sudo systemctl status "$UNIT62" --no-pager
```

A nonzero `is-active` after stopping is expected; the command above is an observation, not a stop-success gate. Verify stop and target installation before starting. Do not continue past a failed shutdown or uncertain process ownership. Record the exact commands and package/binary checks used by the platform; an empty installation step does not count as an upgrade.

Wait for direct `buildInfo` to show the pinned target patch, FCV to remain stable 7.0, the member to return SECONDARY and all three members to meet the lag threshold. Recollect all three member reports and run the stage gate with the one-target-version map. Verify application majority marker/write/read, secondary reads, logs, authentication and monitoring before proceeding.

## 10. Upgrade the remaining secondary and former primary

Re-evaluate live roles before selecting the next secondary. Upgrade it using the same one-host procedure, then require full recovery and a two-target-version stage report. Never assume a host remains secondary because of its original ordinal or name.

Once both upgraded members are healthy and electable, step down the still-source primary using the reviewed diagnostic/maintenance identity on that primary:

```javascript
// Run only after verifying both upgraded secondaries are healthy and electable.
rs.stepDown(60, 30);
```

Do not add `force: true` to avoid catch-up checks. The client may observe a connection/error around stepdown; reconcile by discovering the current primary and checking replica state rather than automatically repeating the command. Confirm a target-binary member became primary and the former primary is now a healthy secondary before stopping it.

Upgrade the former primary as a secondary, then collect all-member evidence for three target binaries and stable FCV 7.0. If a different primary appears, a member is unhealthy or a controller changes the plan, stop and review the actual topology. Keep the client write/election timeline; a later healthy snapshot cannot prove that no operation failed during the change.

## 11. Exercise majority writes and unknown outcomes

Run an application probe before, during and after each disruption with operation IDs derived from `RUN62`. Save `scripts/probe62.js`; each intended operation uses a fixed `PROBE62_ID`. Reconcile uncertain outcomes by rereading/retrying the same ID and payload, not generating a fresh write identity.

```javascript
const app62 = db.getSiblingDB('mongodb_enterprise_tutorial_ch62');
if (!process.env.RUN62 || !process.env.PROBE62_ID ||
    !process.env.PROBE62_ID.startsWith(process.env.RUN62 + ':')) throw new Error('owned operation ID required');
const operation62 = {_id: process.env.PROBE62_ID, runId: process.env.RUN62, kind: 'upgrade-probe'};
const write62 = app62.runCommand({update: 'markers', updates: [{q: {_id: operation62._id},
  u: {$setOnInsert: operation62}, upsert: true}],
  writeConcern: {w: 'majority', j: true, wtimeout: 30000}});
if (write62.ok !== 1 || write62.writeErrors || write62.writeConcernError)
  throw new Error(EJSON.stringify(write62));
const read62 = app62.runCommand({find: 'markers', filter: {_id: operation62._id},
  limit: 1, singleBatch: true, readConcern: {level: 'majority'}});
const found62 = read62.cursor && read62.cursor.firstBatch[0];
if (read62.ok !== 1 || !found62 || found62.runId !== operation62.runId ||
    found62.kind !== operation62.kind) throw new Error('majority read mismatch');
print(EJSON.stringify({operationId: operation62._id, observedAt: new Date(), majorityReadback: true}));
```

Use the replica-set discovery URI, TLS verification and application credentials. Record start/end times, errors, timeout category and readback evidence externally. This single probe is an idempotent demonstration; representative sustained traffic from the real driver is needed to assess application availability, pool recovery, retries and latency. Do not classify write-concern timeout as proof the write never happened.

## 12. Burn in before activating FCV

Hold all target binaries at FCV 7.0 for a pre-agreed observation interval. Define duration and workload coverage before the change; five idle minutes are not a production burn-in. Compare workload correctness, throughput, latency, CPU/memory, storage, replication, client errors, authentication and backups against the source baseline.

Keep target-FCV-dependent features and unrelated schema changes out of this phase. Validate monitoring queries on the new binaries; missing or renamed metrics can make a dashboard appear healthy because it stopped receiving data.

Required burn-in evidence includes all-member direct version/FCV reports, unchanged fixture identity, representative application results, recovered majority markers, negative privilege checks, updated management health and a target-compatible backup/restore observation. If acceptance fails, preserve the working majority, stop further change and use the reviewed recovery decision. Do not respond with an automatic package downgrade.

## 13. Activate target FCV as a separate boundary

Before this step, require all three binaries at the reviewed target, healthy established voters, no initial sync, accepted burn-in, recoverable backup and the owner’s explicit decision to enable target compatibility features. Record that decision and the support/recovery implications.

For the **unautomated native lab**, run on the current primary in `admin`:

```javascript
db.adminCommand({setFeatureCompatibilityVersion: '8.0', confirm: true});
```

`confirm: true` acknowledges the transition; it does not test that backups or a downgrade route work. Preserve the command result and elapsed time. If it errors or disconnects, inspect current FCV/state and logs before deciding the next action. A same-target retry must follow the documented procedure; never edit `admin.system.version` directly or alternate target values to clear a transitional state.

Capture FCV directly on every member. Require the stable object `{version:'8.0'}` with no transition fields and full replica/application recovery. Run the stage gate with all target versions and FCV 8.0. Establish a fresh post-change backup point and restore acceptance; preserve the pre-change point until retention/reconciliation decisions are complete.

For Kubernetes, use the pinned controller’s supported `spec.featureCompatibilityVersion` workflow instead of racing manual FCV commands with reconciliation. Avoid `AlwaysMatchVersion` for a deliberately separated major-upgrade/burn-in plan. Review the actual CR and runtime FCV; explicit desired FCV and an image change are not acceptance evidence. The controller’s ability to express an older version does not override server downgrade restrictions.

## 14. Choose a recovery route from actual state

| Actual situation | Immediate action | Recovery decision |
|---|---|---|
| Target not yet started; source member stopped | Preserve other members and installation evidence | Restore original configuration only if no new binary/data transition occurred and reviewed procedure allows |
| One target member fails startup | Stop additional upgrades; inspect logs/dependencies | Repair current supported version or obtain support-directed member recovery |
| Mixed binaries; healthy majority | Hold current topology and FCV; freeze new features | Review supported completion/recovery with exact versions and Support |
| All target binaries; source FCV | Preserve evidence and workload state | Burn-in failure does not automatically authorize binary reversal |
| FCV transition incomplete | Preserve logs/current FCV and stop other changes | Resolve or retry the same supported transition after diagnosis |
| Target FCV active | Prevent ad hoc old-binary startup | Support-directed downgrade if applicable, or validated isolated restore/cutover |
| Storage/corruption/lost majority | Fence uncertain writers and protect backups | Authoritative member recovery or disaster-recovery procedure |

A restore fallback requires a compatible destination, credentials/TLS, DNS/client cutover and explicit handling of writes newer than the backup. Validate before admitting clients. Restoring an old snapshot over a live member or attaching its data directory to an older binary is not an accepted rollback procedure.

An application deployment rollback can also fail if it expects older query behavior or schema. Record application/database compatibility in both directions. Track who owns write reconciliation and how duplicate/unknown operations are resolved.

## 15. Adapt the gates to managed and sharded deployments

For Ops Manager or Kubernetes, review the generated/automation plan before applying its supported desired server version. Ensure source FCV stays explicitly pinned through burn-in and establish how the owner rolls/elects members. Observe actual roles, process versions, pod/storage identity and application errors during the plan. A PDB does not control every controller rollout; Chapter 61’s eviction test does not prove controller upgrade behavior.

For Kubernetes, retain namespace/CR ownership and PVC/PV identities, inspect deployment status and Agent errors, and capture the supported desired-version/FCV diff. Do not use `kubectl rollout undo` on the generated StatefulSet as a database downgrade. A partial controller plan needs its documented recovery workflow and server support constraints.

A sharded cluster requires the release-specific config-server, shard and router upgrade sequence, plus cluster-wide FCV and catalog/application acceptance. It is not equivalent to independently applying this standalone replica-set lab to arbitrary shards. Include balancer/chunk activity, router/client compatibility and metadata/backup consistency in its dedicated change packet. This chapter’s required runtime exercise covers one non-sharded replica set only.

## 16. Acceptance, troubleshooting and cleanup

| Symptom | Investigate | Stop condition |
|---|---|---|
| Wrong version after restart | Package selection, executable path, owner reconciliation | Direct build version differs from accepted plan |
| TLS/auth failure | Names, crypto/platform, credentials and permissions | Do not disable certificate verification to continue |
| Recovering/lagging secondary | Logs, storage, network, oplog window and sync source | Do not change another member before recovery |
| Election/client timeout | Electability, catch-up, discovery, pools and retries | Reconcile unknown writes; do not force election casually |
| FCV transitional object | Command outcome, current primary, initial sync and logs | Do not edit system metadata |
| Metrics disappeared | Changed metric names/exporter compatibility | Missing telemetry is not accepted healthy burn-in |
| Extra member/pod restart | Controller/platform actions or process crash | Review expanded scope before continuing |

Offline checks must parse all scripts, test valid source/mixed/target/FCV packets and reject wrong run, exact version, address, FCV, lag, freshness, UUID/digest and target-FCV-before-binaries cases. Test CLI output exclusivity and input hashes. Synthetic evidence tests only the checker.

Live acceptance requires verified source, isolated restored backup, each recovered binary stage, an observed election, representative application/authorization evidence, accepted burn-in, separately accepted FCV activation and post-change restore validation. Keep runtime status pending until those actions have actually run. Record errors and achieved recovery time instead of claiming zero downtime from a green final snapshot.

Retain lab evidence and owned resources for later client-integration work. Keep the separate Chapter 60–61 deployment untouched. If retiring this lab, confirm its owner marker, exact hosts/services/data paths and backup retention before stopping/removing only owned resources. No wildcard data deletion, automatic old-binary startup, system metadata edits or unfenced snapshot overwrite belongs in cleanup.

## 17. References and next chapter

Use documentation selected for the exact deployed server and management versions. Current management pages may describe features unavailable to your pinned controller.

- [Upgrade a replica set from 7.0 to 8.0](https://www.mongodb.com/docs/v8.0/release-notes/8.0-upgrade-replica-set/)
- [MongoDB 8.0 compatibility changes](https://www.mongodb.com/docs/v8.0/release-notes/8.0-compatibility/)
- [FCV command and constraints](https://www.mongodb.com/docs/v8.0/reference/command/setfeaturecompatibilityversion/)
- [MongoDB 8.0 downgrade guidance](https://www.mongodb.com/docs/v8.0/release-notes/8.0-downgrade/)
- [Replica-set stepdown](https://www.mongodb.com/docs/v8.0/reference/method/rs.stepdown/)
- [Controller-managed server upgrade](https://www.mongodb.com/docs/kubernetes/current/tutorial/upgrade-mdb-version/)
- [MongoDB resource specification](https://www.mongodb.com/docs/kubernetes/current/reference/k8s-operator-specification/)
- [Chapter 56 — Restore Drill and Recovery Acceptance Project](56-restore-drill-and-recovery-acceptance-project.md)
- [Chapter 61 — Kubernetes Storage Scheduling and Maintenance](61-kubernetes-storage-scheduling-and-maintenance.md)

Next: **[Chapter 63 — Drivers Connection Pools Timeouts and Retries](63-drivers-connection-pools-timeouts-and-retries.md)**.
