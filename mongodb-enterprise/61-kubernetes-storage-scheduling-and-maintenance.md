# 61 — Kubernetes Storage Scheduling and Maintenance

Part 8 — Administration Deployment and Integration

**Baseline:** Retained Chapter 60 Enterprise 8.0/FCV 8.0 TLS/SCRAM replica set, reviewed controller/Kubernetes/CSI versions, three data-bearing members.  
**Status:** Written; static review complete; live Kubernetes maintenance and storage continuity pending.  
**Prerequisites:** Chapter 60 acceptance and saved helpers, authorized lab cluster, working diagnostic/application identities, Python 3, kubectl and mongosh.

## 1. Define the maintenance claim

Assess storage and member placement, validate a disruption budget, evict exactly one healthy secondary through the Kubernetes Eviction API, and verify its replacement uses the retained storage and unchanged application dataset. All three members must return healthy before any further maintenance.

The required lab reuses `mongodb-ch60/rs60lab` and Chapter 60's 50 orders worth 12,750 cents. It creates a separate maintenance run ID while preserving the original Chapter 60 ownership ID. It does not delete PVCs, move data between zones, resize volumes, drain a whole node or simulate sudden node/storage loss.

A replacement may return to the same node. That proves a controlled pod replacement, not node evacuation or regional recovery. Optional node maintenance and volume expansion have additional prerequisites described later. Production application availability requires an actual client workload and failure contract beyond this small fixture.

## 2. Separate process, pod, node and storage failure

| Event | What can remain available | What must be checked |
|---|---|---|
| One database process restarts | Other replica members and its retained volume | Shutdown/recovery, role and replication catch-up |
| Pod replaced | Stateful identity, PVC and remaining members | New pod UID, same claim/storage, healthy database |
| Node drained | Other nodes and eligible attachable storage | Capacity, topology, PDB, all workloads and attach behavior |
| Zone unavailable | Members and storage outside that zone | Surviving majority and actual volume accessibility |
| PVC/PV lost or corrupted | Other authoritative members or independent backups | Member replacement or recovery procedure |

StatefulSet ordinal names provide stable naming, not a backup. A pod UID should change after replacement; a retained claim and volume identity should not. A `Retain` reclaim policy does not make a zonal disk available in another zone or preserve data after physical storage loss.

Readiness describes a Kubernetes probe result. MongoDB voting configuration, role, replication state and majority-write success describe database availability. Both are required for maintenance acceptance.

## 3. Review storage topology and lifecycle

Record StorageClass provisioner, reclaim policy, binding mode, expansion support, encryption, access mode, PV node affinity, volume identifiers and actual filesystem capacity. For topology-constrained dynamic provisioning, `WaitForFirstConsumer` lets scheduling and provisioning consider placement together. Existing bound volumes already have their topology; changing a class does not migrate them.

| Storage property | Operational consequence |
|---|---|
| Zonal PV node affinity | Replacement must land on an eligible node in the permitted zone |
| ReadWriteOnce | Usually constrains read/write mounting to one node; not necessarily one pod |
| ReadWriteOncePod | Single-pod access semantics where supported by the CSI/platform combination |
| Retain reclaim policy | Released backing storage requires deliberate retention/reuse/disposal handling |
| Delete reclaim policy | Claim/PV deletion can lead to deletion of backing storage |
| Local PV | Scheduling depends on the node holding the data; not an attachable network volume |
| Expansion support | Requires StorageClass, driver and filesystem support plus supported controller workflow |

Inspect actual PV reclaim policy as well as StorageClass defaults. Avoid changing shared storage classes, editing PV capacity to fake a resize, or deleting claims to force provisioning. Volume snapshots and copied files need MongoDB-consistent capture and restore validation; storage objects alone do not establish a database recovery point.

## 4. Assess scheduling, requests and failure domains

Require the three members on three different Ready nodes for this chapter's node-separation claim. For zone separation, record a separate objective and inspect real `topology.kubernetes.io/zone` labels. This required lab does not claim three-zone availability.

Review effective pod requests/limits for database and Agent containers, workload overhead, node allocatable resources, taints/tolerations, node affinity and pod anti-affinity/topology-spread rules. Empty or overly restrictive constraints can cause Pending pods even with apparently free capacity.

Modify scheduling only through supported fields in the pinned MongoDB custom resource. For example, review its `spec.podSpec.podTemplate.spec.affinity` and supported pod-template overrides; do not patch the generated StatefulSet independently. Scheduling changes may roll pods: settle and validate that earlier change before beginning this eviction exercise.

Hard node anti-affinity requires enough eligible nodes. If one node is cordoned and only three eligible nodes existed, the replacement can remain Pending. For node evacuation, plan additional compatible capacity in the PV's allowed topology. Avoid weakening anti-affinity during an incident simply to place two voting members in the same failure domain without an explicit availability decision.

## 5. Prepare the retained lab and maintenance packet

Create a new workspace. Load the **original** ownership ID and recorded CR UID/generation from Chapter 60, not a new database marker. If the retained deployment no longer exists or its identity changed, repeat Chapter 60 in a fresh lab before using this procedure.

```bash
umask 077
mkdir mongodb-ch61
cd mongodb-ch61
export LAB61_ROOT="$PWD"
mkdir scripts evidence private input
test -d "${LAB60_ROOT:?set the retained Chapter 60 workspace}"
test -n "${KCTX60:?set its authorized Kubernetes context}"
export NS60=mongodb-ch60
export RUN60="$(cat "$LAB60_ROOT/evidence/run60.txt")"
export RUN61="$(python3 -c 'import uuid; print(uuid.uuid4())')"
printf '%s\n' "$RUN61" > evidence/maintenance-run61.txt
cp "$LAB60_ROOT/scripts/workload60.py" scripts/workload60.py
test -n "${CR60_UID:?set the retained MongoDB CR UID}"
test -n "${CR60_GENERATION:?set its currently reviewed accepted generation}"
kubectl --context "$KCTX60" get namespace "$NS60" -o json > evidence/namespace61.json
kubectl --context "$KCTX60" -n "$NS60" get mongodb rs60lab -o json > evidence/cr-preflight61.json
```

Inspect namespace run label against `RUN60`, CR UID/run/spec, recent controller/Agent status and actual replica membership. Record the current accepted generation after any settled scheduling changes. No controller upgrade, replica scaling, binary/FCV change, volume resize or concurrent rollout is allowed during this exercise.

Agree a maintenance deadline and replication-lag limit before disruption. This tiny idle fixture uses a five-second timestamp-lag ceiling; a production service needs its actual lag/throughput contract. Timestamp lag alone is not proof of application freshness.

## 6. Create or verify the exact disruption budget

Use the pinned controller's supported managed PDB if it supplies one; otherwise create one scoped standalone PDB after reviewing label ownership. Do not add a second overlapping budget. Inspect all PDB selectors in the namespace before changing anything.

For three healthy data-bearing members, this exercise uses integer `minAvailable: 2`. Its selector must match exactly the three owned database pods, excluding controller and client pods. Replace the following selector with actual stable member labels; no guessed operator label is assumed:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: rs60lab-maintenance
  namespace: mongodb-ch60
spec:
  minAvailable: 2
  selector:
    matchLabels:
      REPLACE_WITH_ACTUAL_MEMBER_LABEL_KEY: REPLACE_WITH_ACTUAL_VALUE
```

Validate with server-side dry-run and use the supported owner workflow to deploy it. Record its actual name as `PDB61_NAME`. Do not overwrite a controller-managed budget with a different field owner. Wait for its observed generation and require expectedPods/currentHealthy=3, desiredHealthy=2 and disruptionsAllowed at least 1, with no pending disruptions.

A PDB constrains voluntary disruptions through the Eviction API. It does not protect against direct pod deletion, all controller rollouts, abrupt node loss or node-pressure eviction. It does not inspect MongoDB's voting/replication state. Never bypass a blocking budget with `--disable-eviction`, forced deletion or a lower availability threshold to make maintenance proceed.

## 7. Record direct database health and fixture identity

Save `scripts/database61.js`. Run with a diagnostic identity permitted to read this dataset, inspect replica configuration/status and obtain collection metadata. Use verified TLS and the actual connection string from Chapter 60. `RUN60` is the original fixture owner; `SET60_NAME` is the reviewed runtime set name.

```javascript
const fs61 = require('fs');
const crypto61 = require('crypto');
const a61 = db.getSiblingDB('admin');
const d61 = db.getSiblingDB('mongodb_enterprise_tutorial_ch60');
function check61(ok, message) { if (!ok) throw new Error(message); }
const hello61 = a61.runCommand({hello: 1});
check61(process.env.RUN60 && process.env.SET60_NAME &&
  hello61.setName === process.env.SET60_NAME && hello61.isWritablePrimary === true,
  'reviewed primary required');
const owner61 = d61.markers.findOne({_id: 'owner'});
check61(owner61 && owner61.runId === process.env.RUN60 && owner61.chapter === 60, 'owner mismatch');
const rows61 = d61.orders.find().sort({_id: 1}).toArray();
check61(rows61.length === 50, 'wrong order count');
rows61.forEach((row, n) => check61(row._id === n + 1 && row.code === `order-${n + 1}` &&
  row.amountCents === (n + 1) * 10 && Object.keys(row).length === 3, 'document mismatch'));
check61(d61.orders.getIndexes().some(i => i.name === 'code_unique60' && i.unique === true &&
  i.key.code === 1 && Object.keys(i.key).length === 1), 'unique index differs');
const status61 = a61.runCommand({replSetGetStatus: 1});
const config61 = a61.runCommand({replSetGetConfig: 1});
check61(status61.ok === 1 && config61.ok === 1 && status61.members.length === 3 &&
  config61.config.members.length === 3, 'wrong member inventory');
const primary61 = status61.members.find(m => m.state === 1);
check61(primary61, 'no primary');
const ts61 = value => JSON.parse(EJSON.stringify(value, {relaxed: false})).$timestamp.t;
const primarySeconds61 = ts61(primary61.optime.ts);
const members61 = status61.members.map(m => {
  const conf61 = config61.config.members.find(c => c.host === m.name);
  check61(conf61 && conf61.votes === 1 && !conf61.arbiterOnly && !conf61.newlyAdded,
    'expected established voting data-bearing member');
  return {name: m.name, health: m.health, state: m.state,
    lagSeconds: Math.max(0, primarySeconds61 - ts61(m.optime.ts))};
});
check61(members61.every(m => m.health === 1 && m.lagSeconds <= 5) &&
  members61.filter(m => m.state === 1).length === 1 &&
  members61.filter(m => m.state === 2).length === 2, 'wait for healthy caught-up set');
const canonicalRows61 = rows61.map(r => ({_id: Number(r._id), code: r.code,
  amountCents: Number(r.amountCents)}));
const result61 = {runId: process.env.RUN60, setName: hello61.setName,
  observedAt: new Date().toISOString(), members: members61,
  count: 50, amountCents: 12750,
  ordersDigest: crypto61.createHash('sha256').update(JSON.stringify(canonicalRows61)).digest('hex'),
  ordersUUID: EJSON.stringify(d61.getCollectionInfos({name: 'orders'})[0].info.uuid,
    {relaxed: false})};
check61(process.env.EVIDENCE61_PATH, 'new local evidence path required');
fs61.writeFileSync(process.env.EVIDENCE61_PATH, JSON.stringify(result61, null, 2),
  {flag: 'wx', mode: 0o600});
```

The script runs on the authenticated client, so its output path is local to that client. Collect the file securely into this workspace; never mount server data paths for evidence. The timestamp lag calculation is an intentionally limited idle-fixture check and does not compare exact committed/durable optimes. Perform a real majority marker/read observation as well.

## 8. Capture the stable pre-maintenance inventory

Collect Chapter 60's CR/StatefulSet/pod/PVC/PV files again, plus node and PDB inventories. Use new filenames with a `before61` prefix and record UTC capture times. Re-run `workload60.py` for the unchanged owned layout.

```bash
kubectl --context "$KCTX60" get nodes -o json > private/nodes-before61.json
kubectl --context "$KCTX60" -n "$NS60" get pdb -o json > evidence/pdbs-before61.json
kubectl --context "$KCTX60" -n "$NS60" get pods -o wide > evidence/placement-before61.txt
```

The baseline must show three Ready members on three Ready nodes, three distinct bound retained PVs, an exact PDB selector and a healthy voting set. Map MongoDB member FQDNs to pod names explicitly and record the intended target as a current secondary. Match that pod's UID and owner chain to the accepted baseline.

Assemble `private/before61.json` from the unmodified API/client records using the following field names: `cr`, `statefulsets`, `pods`, `pvcs`, `pvs`, `nodes`, `pdbs`, `database`, `capturedAt`, `maintenanceId`. The first seven are full corresponding JSON responses; `database` is the Section 7 output. `maintenanceId` is `RUN61`. `capturedAt` records the end of collection. Do not invent successful records or copy an old status with a new timestamp.

The evaluator below uses the Chapter 60 gate and adds placement/PDB/continuity checks. Keep unrelated full PV/node inventory private. Sequential snapshots are not atomic; recollect if objects change during baseline capture.

## 9. Evaluate recorded placement and continuity

Save `scripts/maintenance61.py` alongside the copied `workload60.py`. It performs offline checks before issuing an eviction request and after recovery. It does not connect to Kubernetes or authorize unrelated maintenance.

```python
import datetime as dt
import hashlib
import json
import pathlib
import sys
import workload60

def require(ok, message):
    if not ok:
        raise ValueError(message)

def stamp(raw):
    value = dt.datetime.fromisoformat(raw.replace('Z', '+00:00'))
    require(value.tzinfo is not None, 'timezone-aware timestamp required')
    return value

def select_pdb(pdb, pod):
    selector = pdb['spec']['selector']
    require(not selector.get('matchExpressions'), 'use reviewed matchLabels-only lab PDB')
    labels = selector.get('matchLabels', {})
    require(isinstance(labels, dict) and labels, 'nonempty PDB selector required')
    return all(pod['metadata'].get('labels', {}).get(k) == v for k, v in labels.items())

def inspect(packet, run, uid, generation, pdb_name):
    report = workload60.evaluate(packet['cr'], packet['statefulsets'], packet['pods'],
                                packet['pvcs'], packet['pvs'], run, uid, generation)
    names = set(report['memberPods'])
    members = [p for p in packet['pods']['items'] if p['metadata']['name'] in names]
    nodes = {n['metadata']['name']: n for n in packet['nodes']['items']}
    placements = [p['spec']['nodeName'] for p in members]
    require(len(set(placements)) == 3, 'members must occupy three distinct nodes')
    for name in placements:
        node = nodes[name]
        require(not node['metadata'].get('deletionTimestamp') and
                any(c.get('type') == 'Ready' and c.get('status') == 'True'
                    for c in node['status']['conditions']), 'member node not Ready')
    pdbs = packet['pdbs']['items']
    chosen = [p for p in pdbs if p['metadata']['name'] == pdb_name and
              p['metadata']['namespace'] == 'mongodb-ch60']
    require(len(chosen) == 1, 'recorded PDB missing or duplicate')
    pdb = chosen[0]
    require(type(pdb['spec']['minAvailable']) is int and pdb['spec']['minAvailable'] == 2 and
            'maxUnavailable' not in pdb['spec'], 'wrong lab disruption budget')
    selected = {p['metadata']['name'] for p in packet['pods']['items'] if select_pdb(pdb, p)}
    require(selected == names, 'PDB must select exactly the three database members')
    for other in pdbs:
        if other is not pdb:
            require(not any(select_pdb(other, p) for p in members), 'overlapping PDB requires review')
    status = pdb['status']
    require(not pdb['metadata'].get('deletionTimestamp') and
            status['observedGeneration'] == pdb['metadata']['generation'] and
            status['expectedPods'] == 3 and status['currentHealthy'] == 3 and
            status['desiredHealthy'] == 2 and status['disruptionsAllowed'] >= 1 and
            not status.get('disruptedPods'), 'PDB not ready for one disruption')
    database = packet['database']
    require(database['runId'] == run and database['count'] == 50 and
            database['amountCents'] == 12750, 'wrong database fixture')
    rows = database['members']
    require(len(rows) == 3 and len({m['name'] for m in rows}) == 3 and
            sorted(m['state'] for m in rows) == [1, 2, 2] and
            all(m['health'] == 1 and type(m['lagSeconds']) in (int, float) and
                0 <= m['lagSeconds'] <= 5 for m in rows), 'database not fully healthy')
    require(isinstance(database['ordersDigest'], str) and len(database['ordersDigest']) == 64 and
            all(c in '0123456789abcdef' for c in database['ordersDigest']) and
            isinstance(database['ordersUUID'], str) and database['ordersUUID'], 'invalid data identity')
    require(abs((stamp(packet['capturedAt']) - stamp(database['observedAt'])).total_seconds()) <= 120,
            'database observation too far from inventory capture')
    return report, {p['metadata']['name']: p for p in members}

def evaluate(before, after, run, uid, generation, pdb_name, target, maintenance_id, now):
    require(maintenance_id and 'REPLACE' not in maintenance_id and
            before['maintenanceId'] == maintenance_id, 'maintenance identity differs')
    base, base_pods = inspect(before, run, uid, generation, pdb_name)
    require(target in base_pods, 'target is not an owned member')
    if after is None:
        require(0 <= (now - stamp(before['capturedAt'])).total_seconds() <= 120, 'stale/future preflight')
        return {'claim': 'recorded_kubernetes_database_preflight', 'maintenanceId': maintenance_id,
                'targetPod': target, 'targetUid': base_pods[target]['metadata']['uid'],
                'databaseRoleMappingStillRequiresLiveReview': True}
    require(after['maintenanceId'] == maintenance_id, 'after maintenance identity differs')
    result, recovered_pods = inspect(after, run, uid, generation, pdb_name)
    require(stamp(after['capturedAt']) > stamp(before['capturedAt']) and
            0 <= (now - stamp(after['capturedAt'])).total_seconds() <= 120, 'invalid/stale final capture')
    require(set(base_pods) == set(recovered_pods), 'member identity names changed')
    for name in base_pods:
        previous, current = base_pods[name]['metadata']['uid'], recovered_pods[name]['metadata']['uid']
        require((previous != current) if name == target else (previous == current),
                'expected only the selected pod UID to change')
    def identities(packet):
        return ({c['metadata']['name']: (c['metadata']['uid'], c['spec']['volumeName'])
                 for c in packet['pvcs']['items'] if c['metadata']['name'] in base['pvcNames']},
                {p['metadata']['name']: p['metadata']['uid'] for p in packet['pvs']['items']
                 if p['metadata']['name'] in base['pvNames']})
    require(identities(before) == identities(after), 'claim/PV identities changed')
    require(base['pvcNames'] == result['pvcNames'] and base['pvNames'] == result['pvNames'],
            'storage inventory changed')
    for key in ('setName', 'ordersDigest', 'ordersUUID'):
        require(before['database'][key] == after['database'][key], 'database identity/data changed')
    require({m['name'] for m in before['database']['members']} ==
            {m['name'] for m in after['database']['members']}, 'MongoDB member addresses changed')
    return {'claim': 'recorded_single_pod_replacement_with_storage_continuity',
            'maintenanceId': maintenance_id, 'targetPod': target,
            'beforeUid': base_pods[target]['metadata']['uid'],
            'afterUid': recovered_pods[target]['metadata']['uid'],
            'pvcNames': result['pvcNames'], 'pvNames': result['pvNames'],
            'majorityApplicationWriteStillRequiresLiveEvidence': True,
            'nodeEvacuationProven': False}

if __name__ == '__main__':
    try:
        require(len(sys.argv) == 10,
                'usage: maintenance61.py BEFORE AFTER_OR_DASH RUN60 CR_UID GENERATION PDB TARGET RUN61 NEW_REPORT')
        before_blob = pathlib.Path(sys.argv[1]).read_bytes()
        after_blob = None if sys.argv[2] == '-' else pathlib.Path(sys.argv[2]).read_bytes()
        report = evaluate(json.loads(before_blob), None if after_blob is None else json.loads(after_blob),
                          sys.argv[3], sys.argv[4], int(sys.argv[5]), sys.argv[6], sys.argv[7],
                          sys.argv[8], dt.datetime.now(dt.timezone.utc))
        report['inputSha256'] = [hashlib.sha256(b).hexdigest() for b in (before_blob, after_blob) if b]
        # Nine arguments follow the program name; the report is argument 9.
        with open(sys.argv[9], 'x', encoding='utf-8') as out:
            json.dump(report, out, indent=2)
            out.write('\n')
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as error:
        print('REJECTED: ' + str(error), file=sys.stderr)
        sys.exit(1)
```

Use the actual files and names. The CLI expects nine arguments after the script name; a failure writes no accepted report. Role-to-pod mapping and majority application evidence remain explicit live gates, not inferred from PDB readiness.

## 10. Review preflight and prepare a UID-bound eviction

Run the preflight immediately before the action:

```bash
test -n "${PDB61_NAME:?set the reviewed nonoverlapping PDB name}"
test -n "${TARGET61_POD:?set the owned current secondary pod name}"
python3 scripts/maintenance61.py private/before61.json - "$RUN60" "$CR60_UID" \
  "$CR60_GENERATION" "$PDB61_NAME" "$TARGET61_POD" "$RUN61" evidence/preflight61.json
```

Recheck the live diagnostic connection: the mapped target is still a healthy secondary, no other member is unavailable/lagging, and current voting configuration is the reviewed three-member set. Check no concurrent maintenance/rollout or pending PDB disruption. If the target became primary, stop and choose a new reviewed secondary/baseline; this lab does not silently perform stepdown.

Generate an Eviction object from the accepted recorded target UID. No direct pod delete is used:

```bash
python3 - <<'PY'
import json
import pathlib
report = json.loads(pathlib.Path('evidence/preflight61.json').read_text())
obj = {'apiVersion': 'policy/v1', 'kind': 'Eviction',
       'metadata': {'name': report['targetPod'], 'namespace': 'mongodb-ch60'},
       'deleteOptions': {'preconditions': {'uid': report['targetUid']}}}
with open('private/eviction61.json', 'x') as out:
    json.dump(obj, out, indent=2)
PY
```

Inspect this exact object and live pod UID. The UID precondition prevents evicting a newer replacement under the same name. It does not freeze database roles, node state or other workloads. A preflight packet more than two minutes old must be recollected and reviewed, not relabeled with a fresh timestamp.

## 11. Evict once and observe recovery

Submit one API eviction with normal grace behavior:

```bash
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/eviction-start61.txt
kubectl --context "$KCTX60" create --raw \
  "/api/v1/namespaces/$NS60/pods/$TARGET61_POD/eviction" \
  -f private/eviction61.json > evidence/eviction-response61.json
```

Require successful API response. A UID conflict or PDB rejection is a stopped action, not permission to force-delete. Preserve the response/error. Do not resubmit against a newly discovered UID without a new preflight and decision.

Watch the selected pod terminate gracefully and its replacement acquire a different UID. Observe scheduling, CSI detach/attach/mount events, container startup, MongoDB recovery and replication catch-up. Record actual timings and failure states. Do not lower termination grace or remove finalizers to accelerate recovery.

Through the application TLS connection, exercise an idempotent run-owned marker write during the disruption with `{w:'majority',j:true,wtimeout:30000}` and read it back at majority read concern. Use a marker ID derived from `RUN61`; retries must reuse the same operation identity and reconcile unknown write outcomes. Preserve client errors/timing rather than reporting uninterrupted service from a later successful read alone.

Wait for the full three-member set and PDB allowance to recover. A Running pod is an intermediate milestone. Do not begin a second eviction while the replacement is starting, initial-syncing, lagging or not majority-visible.

## 12. Verify persistent identity and application state

Run Section 7's diagnostic script again into a new output. Repeat Chapter 60's direct secondary majority reads and application credential/administrative-rejection probes. Require 50 exact orders/12,750 cents, unchanged order UUID and digest, unique index, intended set identity and the maintenance marker's majority visibility.

Collect the full `after61` inventory and assemble `private/after61.json` with the same response fields, new real timestamps and `RUN61`. Run the gate:

```bash
python3 scripts/maintenance61.py private/before61.json private/after61.json \
  "$RUN60" "$CR60_UID" "$CR60_GENERATION" "$PDB61_NAME" "$TARGET61_POD" "$RUN61" \
  evidence/replacement-accepted61.json
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/recovery-end61.txt
```

Require only the selected member's pod UID to change, unchanged PVC/PV identities and healthy separated placement. If another pod restarted unexpectedly, reject the single-pod claim even if final data looks correct. Investigate the wider disruption before deciding whether the exercise can be rerun.

The local gate evaluates supplied bytes and selected fields. It does not prove database consistency beyond the live diagnostic script, application write durability, CSI encryption or elapsed outage. Pair its report with actual client evidence, management status and the event timeline.

## 13. Extend to reviewed node maintenance

Node cordon/drain affects more than the selected database pod. Inventory all workloads, DaemonSets, local storage and PDBs on the node, platform upgrade behavior, and a compatible destination with sufficient capacity in the PV's allowed topology. On a shared production node, a namespace-specific tutorial does not authorize the rest of that disruption.

For a separately approved disposable-node exercise, cordon the exact node before evicting the reviewed secondary, then require the new pod to land elsewhere and the database to recover. Retain both placements and volume attach evidence. A whole-node drain requires its own workload inventory and supported platform procedure; do not add `--force`, `--delete-emptydir-data` or `--disable-eviction` without a specific reviewed need.

Record whether the node was already cordoned before the exercise. Uncordon only a node cordoned by this run after the maintenance/health checks succeed; do not undo another operator's cordon or a platform safety action. If drain or replacement stalls, the node stays under the incident decision until the cause is resolved.

A zonal disk does not become cross-zone storage because Kubernetes retries scheduling. For node loss with inaccessible volumes, use an authoritative healthy member/resync or the disaster-recovery plan. Never force-detach/reattach storage from a potentially live writer without actual infrastructure fencing.

## 14. Plan volume expansion without unsafe reversal

Expansion is an optional separate change, not part of the eviction packet. Verify controller-supported persistence update behavior, StorageClass `allowVolumeExpansion`, CSI and filesystem support, quotas and backup/recovery before changing any size.

| Stage | Evidence |
|---|---|
| Desired size accepted | Supported CR/controller workflow and validated new specification |
| Claim/controller progress | PVC request/status and expansion conditions/events |
| Storage backend expanded | CSI/provider observations and PV capacity |
| Filesystem usable | Actual mounted capacity from the database container |
| Database healthy | Logs, normal workload and replication/application acceptance |

Do not shrink the volume to undo an expansion. Do not edit PV capacity manually to make the controller report completion. If a filesystem resize requires a restart, plan one healthy member at a time and preserve majority. Keep size/capacity evidence distinct from IOPS/throughput: a larger disk is not automatically a validated performance fix.

PVC deletion/recreation and storage-class changes are data migrations with retention/attachment implications. Use a supported migration/member-replacement or restore workflow, not a capacity-edit shortcut.

## 15. Troubleshoot blocked maintenance

| Symptom | Check | Decision |
|---|---|---|
| Eviction rejected by PDB | Selector, current healthy count, observed generation and overlapping budgets | Wait/fix health or scope; preserve availability threshold |
| Replacement Pending | Node affinity, PV topology, requests, taints and anti-affinity | Supply eligible capacity; do not discard claim |
| Multi-attach/mount delay | Old pod/node termination and CSI events | Resolve attachment ownership; avoid unfenced force actions |
| Pod Ready but member recovering | MongoDB/Agent status and replication | Wait within budget; inspect storage/network/oplog constraints |
| Replica healthy but client fails | DNS discovery, TLS names, credentials and retry behavior | Correct actual application path |
| PVC unexpectedly replaced | Resource/claim retention and controller changes | Stop acceptance; protect data and investigate identity loss |
| OOM/CPU pressure during restart | Effective limits, node pressure and recovery workload | Reassess allocation; a PDB does not prevent this failure |
| Volume expansion stalls | Driver/filesystem support and controller conditions | Follow supported expansion remediation, not deletion |

Preserve a clear event sequence: API action, pod termination, detach/attach, container start, member state, full majority/application recovery and final allowance. Identify the bottleneck rather than calling the whole interval “Kubernetes slow.”

## 16. Acceptance, static tests and handoff

Test helpers with separate labeled synthetic packets. Require preflight/final success for a healthy three-node layout and one changed target UID. Require rejection for duplicate placement, node not Ready, wrong run/UID/generation, stale/future captures, broad/overlapping PDBs, unavailable allowance, wrong database state/lag, unchanged target UID, another restarted pod, changed claim/PV UID and changed order UUID/digest.

Parse Bash/JS/Python/YAML separately and retain the Chapter 60 helper version/hash. These offline tests establish evaluator behavior only. They do not perform eviction, validate CSI or prove application continuity.

Live acceptance includes exact ownership, healthy voting baseline, reviewed scheduling/storage/PDB, one successful UID-bound eviction, unchanged claims/data identity, full replica recovery, majority marker and secondary reads, application authorization and final management health. Report any failed write/retry latency, extra restarts or policy exception.

Retain the original Chapter 60 ownership marker and accepted deployment for later chapters. Preserve any existing controller-managed PDB and scheduling policies. If this run created a temporary standalone PDB, remove it only after the owner chooses the final disruption policy and verifies no dependency requires it. Do not remove protection just because the exercise ended.

No node, PVC, PV, CRD, namespace or retained database is deleted by this lab. Ongoing resource/cost ownership and backup objectives remain part of handoff. If cleanup is required, use the Chapter 60 guarded retirement and release-specific retention process.

## 17. References and next chapter

Select Kubernetes/controller documentation for the versions retained in Chapter 60; current pages can include newer features.

- [MongoDB custom resource configuration](https://www.mongodb.com/docs/kubernetes/current/tutorial/configure-mdb-cr/)
- [MongoDB controller best practices](https://www.mongodb.com/docs/kubernetes/current/tutorial/plan-k8s-op-considerations/)
- [Kubernetes storage classes](https://kubernetes.io/docs/concepts/storage/storage-classes/)
- [Persistent volumes and expansion](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [Pod disruption budgets](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [Safely drain a node](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/)
- [Kubernetes disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [Chapter 60 — Kubernetes Operator Compatibility and Deployment](60-kubernetes-operator-compatibility-and-deployment.md)

Next: **[Chapter 62 — Rolling Upgrades FCV and Rollback Constraints](62-rolling-upgrades-fcv-and-rollback-constraints.md)**.
