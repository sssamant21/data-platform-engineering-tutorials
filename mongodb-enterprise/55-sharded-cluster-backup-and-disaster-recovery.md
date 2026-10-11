# 55 — Sharded Cluster Backup and Disaster Recovery

Part 7 — Backup Recovery and Disaster Recovery

**Baseline:** MongoDB 8.0/FCV 8.0 and compatible pinned Database Tools.  
**Status:** Written; static review complete; live sharded backup/recovery validation pending.  
**Prerequisites:** Chapters 35–40 and 49–54, saved Chapter 35 build files, Docker/Compose, Python 3 and capacity for a two-shard lab.

## 1. Define the cluster-wide recovery contract

This lab creates a new source sharded cluster, distributes deterministic orders across two shards, captures a coordinated logical backup while the cluster is locked, acknowledges a later write and fences every source process. It builds a separate recovery cluster, pre-shards the destination, restores application data through `mongos` and validates both shards plus a cross-shard transaction.

A sharded cluster is not a collection of independent replica-set backups. Recovery must preserve a consistent relationship between application data, sharding metadata, transaction history and the selected cutoff. A healthy router does not establish that every shard or config-server replica set recovered.

The executable baseline reconstructs the destination catalog from the known application contract and restores data logically. Physical/managed catalog restoration is a different workflow in Section 14. Both clusters use one Docker host; this does not demonstrate host/region disaster recovery.

## 2. Identify the complete recovery boundary

| Component | Recovery responsibility |
|---|---|
| Config-server replica set | Catalog, shard registration and placement metadata under the selected workflow |
| Every data-shard replica set | Its data and supported consistent history |
| Routers | Correct config-server seed list, network and client routing |
| Application schema | Collection options, indexes, shard keys, references and transaction effects |
| Security/infrastructure | Credentials, TLS, internal authentication, keys, versions and independent storage |

For logical recovery into a new cluster, preserve the **destination** config database and pre-shard collections using the source's reviewed shard-key definitions. For physical/managed recovery, recover the coordinated config-server/shard set according to its exact procedure. Do not mix these approaches by restoring an old `config` database into an independently initialized logical destination.

No `mongorestore --oplogReplay` recipe applies through `mongos`. Independently selected per-shard oplog cutoffs do not automatically establish a global recovery point.

## 3. Choose the lab's security and consistency profile

The Chapter 35 topology is an explicitly isolated synthetic lab with no authentication/TLS, an internal Docker network and no published ports. This chapter copies only its build configuration/bootstrap scripts into **new** projects. It does not remove security from an existing deployment or claim this profile is production-ready.

Use synthetic data only. Host administrators and other containers attached to the network can access it. Production or a secure managed lab needs authentication, internal member authentication, TLS, least privilege, key custody and independent fault domains. Use Chapter 52's managed adapter and approved authenticated clients for that profile rather than weakening it to fit these commands.

The coordinated logical capture requires a reviewed global write/DDL/transaction pause, stopped balancer and the release-supported cluster lock procedure. Quiescence must include all writer paths and background changes. Elections or topology changes that invalidate capture require a new attempt.

## 4. Copy configuration into two fresh owned projects

Set `CH35_ROOT` to the saved Chapter 35 **configuration** workspace. Copy no data directories or named volumes. Required files are `compose.yaml`, `scripts/lib35.js`, `scripts/bootstrap35.js` and `scripts/register35.js` from that chapter.

```bash
umask 077
mkdir mongodb-ch55
cd mongodb-ch55
export LAB55_ROOT="$PWD"
export CH35_ROOT='/absolute/path/to/mongodb-ch35'
export RUN55="$(python3 -c 'import uuid; print(uuid.uuid4())')"
mkdir source recovery scripts artifacts evidence logs
printf '%s\n' "$RUN55" > evidence/run55.txt
test -n "${MONGO_IMAGE:?use the reviewed pinned Chapter 35 MongoDB 8.0 digest}"
case "$MONGO_IMAGE" in *@sha256:*) ;; *) exit 1 ;; esac
for side55 in source recovery; do
  mkdir "$side55/scripts"
  cp "$CH35_ROOT/compose.yaml" "$side55/compose.yaml"
  cp "$CH35_ROOT/scripts/lib35.js" "$side55/scripts/lib35.js"
  cp "$CH35_ROOT/scripts/bootstrap35.js" "$side55/scripts/bootstrap35.js"
  cp "$CH35_ROOT/scripts/register35.js" "$side55/scripts/register35.js"
done
```

Source/recovery share the **names** `cfg35`, `rs35a`, `rs35b`, `shard35a`, `shard35b` inside different isolated networks. Identical names do not mean identical cluster identity. Record and compare their independent `config.version.clusterId` values. Never attach either deployment to the other network.

Save this as `scripts/labels55.py` and run it to create an exclusive Compose override in each fresh workspace:

```python
import json
import os
import pathlib

run_id = os.environ['RUN55']
labels = {'chapter': '55', 'run': run_id}
services = ['cfg1', 'cfg2', 'cfg3', 'a1', 'a2', 'a3', 'b1', 'b2', 'b3', 'r1', 'r2']
for side in ('source', 'recovery'):
    config = {'services': {name: {'labels': labels, 'restart': 'no'} for name in services},
              'networks': {'cluster': {'labels': labels}},
              'volumes': {name + suffix: {'labels': labels}
                          for name in services[:9] for suffix in ('-data', '-config')}}
    with (pathlib.Path(side) / 'labels55.json').open('x', encoding='utf-8') as output:
        json.dump(config, output, indent=2)
```

```bash
python3 scripts/labels55.py
dc55() {
  case "$1" in source|recovery) side55="$1" ;; *) return 1 ;; esac
  shift
  docker compose -p "mongodb-ch55-$side55" \
    -f "$LAB55_ROOT/$side55/compose.yaml" -f "$LAB55_ROOT/$side55/labels55.json" "$@"
}
dc55 source config
dc55 recovery config
docker ps -a --filter label=com.docker.compose.project=mongodb-ch55-source
docker volume ls --filter label=com.docker.compose.project=mongodb-ch55-source
docker ps -a --filter label=com.docker.compose.project=mongodb-ch55-recovery
docker volume ls --filter label=com.docker.compose.project=mongodb-ch55-recovery
```

Require both projects to have no prior containers/volumes. Review rendered images, internal networks, distinct volumes and absence of host ports. The source is stopped before recovery runs, reducing concurrent process memory; retain enough disk for both clusters, artifact and initial-sync headroom. Chapter 35's capacity estimates remain teaching estimates, not measured DR sizing.

## 5. Build only the fresh source cluster

```bash
dc55 source up -d cfg1 cfg2 cfg3 a1 a2 a3 b1 b2 b3
docker run --rm --user "$(id -u):$(id -g)" --network mongodb-ch55-source_cluster \
  -v "$LAB55_ROOT/source/scripts:/scripts:ro" "$MONGO_IMAGE" \
  mongosh --nodb --quiet --file /scripts/bootstrap35.js
dc55 source up -d r1 r2
docker run --rm --user "$(id -u):$(id -g)" --network mongodb-ch55-source_cluster \
  -v "$LAB55_ROOT/source/scripts:/scripts:ro" "$MONGO_IMAGE" \
  mongosh 'mongodb://r1:27017/admin' --quiet --file /scripts/register35.js
```

The borrowed bootstrap checks the exact three replica sets and their members. The register script permits only the expected two shard registrations. Inspect logs and stop on any readiness/configuration mismatch. Do not run Chapter 35's application fixture scripts in these projects.

Save Sections 6 and 7's scripts. Client operations use only the selected network and `mongos` endpoint:

```bash
client55() {
  case "$TARGET55" in source|recovery) ;; *) return 1 ;; esac
  docker run --rm --user "$(id -u):$(id -g)" --network "mongodb-ch55-$TARGET55"_cluster \
    -v "$LAB55_ROOT/scripts:/scripts:ro" \
    -v "$LAB55_ROOT/evidence:/evidence" \
    --env TARGET55 --env ACTION55 "$MONGO_IMAGE" \
    mongosh 'mongodb://r1:27017/admin' --quiet --file /scripts/control55.js
}
```

## 6. Implement routed data and topology verification

Save as `scripts/lib55.js`. Two range chunks are assigned explicitly before data insertion/restore, giving fifty fixture rows per shard while balancing is stopped. Target UUIDs/catalog identity are newly created, not copied from the source logical dump.

```javascript
const fs55 = require('fs');
const crypto55 = require('crypto');
const D55 = 'mongodb_enterprise_tutorial_ch55';
const NS55 = `${D55}.orders`;
const d55 = db.getSiblingDB(D55);
const config55 = db.getSiblingDB('config');
const base55 = Array.from({length: 100}, (_, n) => ({
  _id: n + 1, tenantId: n % 10 + 1, amountCents: (n + 1) * 100}));
const later55 = {_id: 101, tenantId: 1, amountCents: 10100};
const tx55 = base55.map(row => row._id === 1 ? {...row, amountCents: 90} :
  row._id === 10 ? {...row, amountCents: 1010} : row);
const validator55 = {$jsonSchema: {bsonType: 'object',
  required: ['_id', 'tenantId', 'amountCents'], properties: {
    tenantId: {bsonType: 'number', minimum: 1, maximum: 10},
    amountCents: {bsonType: 'number', minimum: 0}}}};
function check55(ok, message) { if (!ok) throw new Error(message); }
function plain55(value) { return JSON.parse(EJSON.stringify(value, {relaxed: true})); }
function canonical55(value) {
  if (Array.isArray(value)) return value.map(canonical55);
  if (value && typeof value === 'object') return Object.fromEntries(
    Object.keys(value).sort().map(key => [key, canonical55(value[key])]));
  return value;
}
function hash55(value) { return crypto55.createHash('sha256')
  .update(JSON.stringify(canonical55(plain55(value)))).digest('hex'); }
function save55(name, value) { fs55.writeFileSync(`/evidence/${name}`,
  EJSON.stringify(value, {relaxed: false}), {flag: 'wx', mode: 0o600}); }
function clusterId55() { return EJSON.stringify(config55.version.findOne({_id: 1}).clusterId,
  {relaxed: false}); }
function router55() {
  check55(db.getSiblingDB('admin').runCommand({hello: 1}).msg === 'isdbgrid', 'mongos required');
  const result = db.getSiblingDB('admin').runCommand({listShards: 1});
  check55(result.ok === 1 && result.shards.length === 2, 'two shards required');
  for (const [id, name] of [['shard35a', 'rs35a'], ['shard35b', 'rs35b']]) {
    const shard = result.shards.find(s => s._id === id);
    check55(shard && shard.host.split('/')[0] === name, 'unexpected shard identity');
  }
  const build = db.getSiblingDB('admin').runCommand({buildInfo: 1});
  check55(build.ok === 1 && build.version.startsWith('8.0.'), 'MongoDB 8.0 required');
  return result;
}
function layout55() {
  const meta = config55.collections.findOne({_id: NS55});
  check55(meta && !meta.dropped && hash55(meta.key) === hash55({tenantId: 1, _id: 1}),
    'shard key/catalog mismatch');
  const chunks = config55.chunks.find({uuid: meta.uuid}).toArray();
  check55(chunks.length === 2 && chunks.some(c => c.shard === 'shard35a') &&
    chunks.some(c => c.shard === 'shard35b'), 'expected two-shard range layout');
  return {key: meta.key, uuid: EJSON.stringify(meta.uuid, {relaxed: false}), chunks};
}
function seed55(runId) {
  check55(d55.getCollectionInfos().length === 0, 'existing application objects');
  sh.stopBalancer();
  check55(sh.getBalancerState() === false, 'balancer not stopped');
  check55(db.getSiblingDB('admin').runCommand({enableSharding: D55, primaryShard: 'shard35a'}).ok === 1,
    'enableSharding failed');
  d55.createCollection('orders', {validator: validator55, validationLevel: 'strict', validationAction: 'error'});
  d55.createCollection('marker');
  d55.orders.createIndex({tenantId: 1, _id: 1}, {unique: true, name: 'tenant_order55'});
  check55(sh.shardCollection(NS55, {tenantId: 1, _id: 1}).ok === 1, 'shardCollection failed');
  check55(sh.splitAt(NS55, {tenantId: 6, _id: MinKey}).ok === 1, 'split failed');
  check55(sh.moveChunk(NS55, {tenantId: 8, _id: 8}, 'shard35b').ok === 1, 'placement failed');
  layout55();
}
function verify55(state, phase) {
  router55(); const layout = layout55();
  check55(hash55(d55.getCollectionInfos().map(i => i.name).sort()) === hash55(['marker', 'orders']),
    'unexpected collections');
  const owner = d55.marker.findOne({_id: 'owner'});
  check55(owner && owner.runId === state.runId && owner.chapter === 55 &&
    d55.marker.countDocuments({}) === 1, 'owner marker mismatch');
  const expected = phase === 'later' ? [...base55, later55] : phase === 'transaction' ? tx55 : base55;
  const actual = d55.orders.find().sort({_id: 1}).toArray();
  check55(hash55(actual) === hash55(expected), 'exact routed document mismatch');
  const options = d55.getCollectionInfos({name: 'orders'})[0].options;
  check55(hash55(options.validator) === hash55(validator55) && options.validationLevel === 'strict' &&
    options.validationAction === 'error', 'validator mismatch');
  const indexes = d55.orders.getIndexes();
  check55(indexes.length === 2 && indexes.some(i => i.name === 'tenant_order55' &&
    i.unique === true && hash55(i.key) === hash55({tenantId: 1, _id: 1})), 'index mismatch');
  const shardRows = {};
  for (const [name, hosts] of [['rs35a', ['a1', 'a2', 'a3']], ['rs35b', ['b1', 'b2', 'b3']]]) {
    const conn = new Mongo(`mongodb://${hosts.map(h => h + ':27017').join(',')}/?replicaSet=${name}`);
    const rows = conn.getDB(D55).orders.find().sort({_id: 1}).toArray();
    const subset = expected.filter(row => name === 'rs35a' ? row.tenantId < 6 : row.tenantId >= 6);
    check55(hash55(rows) === hash55(subset), 'shard-local reconciliation failed');
    shardRows[name] = rows.length;
    const status = conn.getDB('admin').runCommand({replSetGetStatus: 1});
    check55(status.ok === 1 && status.members.length === 3 &&
      status.members.every(m => m.health === 1) && status.members.filter(m => m.state === 1).length === 1 &&
      status.members.filter(m => m.state === 2).length === 2, 'unhealthy shard replica set');
  }
  const cfg = new Mongo('mongodb://cfg1:27017,cfg2:27017,cfg3:27017/?replicaSet=cfg35');
  const status = cfg.getDB('admin').runCommand({replSetGetStatus: 1});
  const fcv = cfg.getDB('admin').runCommand({getParameter: 1, featureCompatibilityVersion: 1});
  check55(fcv.ok === 1 && fcv.featureCompatibilityVersion.version === '8.0', 'stable FCV 8.0 required');
  check55(status.ok === 1 && status.members.length === 3 && status.members.every(m => m.health === 1) &&
    status.members.filter(m => m.state === 1).length === 1 &&
    status.members.filter(m => m.state === 2).length === 2, 'unhealthy config replica set');
  return {count: actual.length, amountCents: actual.reduce((n, row) => n + row.amountCents, 0),
    digest: hash55(actual), shardRows, clusterId: clusterId55(), layout};
}
```

Direct shard reads above are restricted to forensic validation while balancing/writers are stopped. Applications and repair writes always use `mongos`. Do not assume every unsharded document appears on every shard: the marker lives on the database primary shard.

## 7. Implement capture, lock and recovery phases

Save as `scripts/control55.js`. `TARGET55` selects the network externally; persisted cluster IDs prevent adopting the wrong catalog. A locked capture requires independent access to unlock even if the capture command fails.

```javascript
load('/scripts/lib55.js');
const target55 = process.env.TARGET55, action55 = process.env.ACTION55;
check55(['source', 'recovery'].includes(target55), 'unknown target');
router55();
const statePath55 = '/evidence/state55.json';
function writeState55(state) { fs55.writeFileSync(statePath55,
  EJSON.stringify(state, {relaxed: false}), {mode: 0o600}); }
function lockView55(admin) {
  return admin.aggregate([{$currentOp: {}}, {$facet: {
    locked: [{$match: {fsyncLock: {$exists: true}}}],
    unlocked: [{$match: {fsyncLock: {$exists: false}}}]}},
    {$project: {fsyncLocked: {$gt: [{$size: '$locked'}, 0]},
      fsyncUnlocked: {$gt: [{$size: '$unlocked'}, 0]}}}]).toArray()[0];
}
function observeLocks55(locked) {
  const cfg = new Mongo('mongodb://cfg1:27017,cfg2:27017,cfg3:27017/?replicaSet=cfg35');
  const observations = {router: lockView55(db.getSiblingDB('admin')),
    configPrimary: lockView55(cfg.getDB('admin'))};
  for (const result of Object.values(observations))
    check55(result && result.fsyncLocked === locked && result.fsyncUnlocked === !locked,
      'cluster lock observation differs; inspect every component');
  return observations;
}
if (action55 === 'setup-source') {
  check55(target55 === 'source' && !fs55.existsSync(statePath55), 'fresh source required');
  const state = {runId: fs55.readFileSync('/evidence/run55.txt', 'utf8').trim(),
    sourceClusterId: clusterId55(), sourceBalancerBefore: sh.getBalancerState()};
  seed55(state.runId);
  d55.orders.insertMany(base55, {writeConcern: {w: 'majority', j: true}});
  d55.marker.insertOne({_id: 'owner', runId: state.runId, chapter: 55},
    {writeConcern: {w: 'majority', j: true}});
  save55('state55.json', state);
  save55('baseline55.json', {runId: state.runId, observedAt: new Date(), result: verify55(state, 'base')});
} else {
  const state = EJSON.parse(fs55.readFileSync(statePath55, 'utf8'));
  check55(clusterId55() === (target55 === 'source' ? state.sourceClusterId : state.recoveryClusterId),
    'cluster identity mismatch');
  if (action55 === 'lock-source') {
    check55(target55 === 'source' && !state.lockOwned, 'source lock already owned or wrong target');
    verify55(state, 'base'); check55(sh.getBalancerState() === false, 'balancer must be off');
    save55('lock-intent55.json', {runId: state.runId, observedAt: new Date()});
    const result = db.getSiblingDB('admin').fsyncLock();
    check55(result.ok === 1 && Number(result.lockCount) === 1, 'unexpected lock count; investigate ownership');
    state.lockOwned = true; writeState55(state);
    save55('locked55.json', {runId: state.runId, observedAt: new Date(), result,
      observations: observeLocks55(true)});
  } else if (action55 === 'unlock-source') {
    check55(target55 === 'source' && state.lockOwned, 'owned source lock required');
    const result = db.getSiblingDB('admin').fsyncUnlock();
    check55(result.ok === 1 && Number(result.lockCount) === 0, 'unexpected remaining locks');
    const observations = observeLocks55(false);
    state.lockOwned = false; writeState55(state);
    save55('unlocked55.json', {runId: state.runId, observedAt: new Date(), result, observations});
    verify55(state, 'base');
  } else if (action55 === 'later-source') {
    check55(target55 === 'source' && !state.lockOwned, 'unlocked source required'); verify55(state, 'base');
    d55.orders.insertOne(later55, {writeConcern: {w: 'majority', j: true}});
    save55('later-ack55.json', {runId: state.runId, acknowledgedAt: new Date(),
      writeConcern: {w: 'majority', j: true}, outsideBackupIds: [101], result: verify55(state, 'later')});
  } else if (action55 === 'verify-recovery') {
    check55(target55 === 'recovery', 'recovery target required');
    save55('restored55.json', {runId: state.runId, observedAt: new Date(), result: verify55(state, 'base'),
      unrecoveredAcknowledgedIds: [101], unrecoveredAmountCents: 10100});
  } else if (action55 === 'transaction-probe') {
    check55(target55 === 'recovery', 'recovery required'); verify55(state, 'base');
    const session = db.getMongo().startSession({readPreference: {mode: 'primary'}});
    try {
      session.startTransaction({readConcern: {level: 'snapshot'},
        writeConcern: {w: 'majority', j: true}});
      const orders = session.getDatabase(D55).orders;
      check55(orders.updateOne({tenantId: 1, _id: 1}, {$inc: {amountCents: -10}}).modifiedCount === 1,
        'first transaction update failed');
      check55(orders.updateOne({tenantId: 10, _id: 10}, {$inc: {amountCents: 10}}).modifiedCount === 1,
        'second transaction update failed');
      session.commitTransaction();
    } catch (error) {
      try { session.abortTransaction(); } catch (_) { /* Preserve original error. */ }
      throw error;
    } finally { session.endSession(); }
    save55('transaction-accepted55.json', {runId: state.runId, observedAt: new Date(),
      result: verify55(state, 'transaction')});
  } else throw new Error('unknown ACTION55');
}
```

Preparation of the new catalog is a separate script in Section 11, before `control55.js` is invoked against recovery. Its cluster ID must be recorded first. No generic metadata-edit or drop command is permitted to resolve an unexpected catalog.

## 8. Lock, capture and always resolve the owned lock

```bash
export TARGET55=source ACTION55=setup-source
client55
export ACTION55=lock-source
client55
```

Before locking, confirm all application writes, DDL, migrations, resharding and transactions have ceased and no relevant operation remains in progress. Review the exact MongoDB 8.0 backup-window procedure. The controller verifies the documented router/config-primary lock observations; retain their output and independent unlock access.

Set an approved maximum write-pause budget before acquisition and monitor it during capture. If capture exceeds that budget, stop the attempt, resolve the owned lock through independent access and reject the partial artifact. A disconnected client is not an unlock mechanism.

Capture through `mongos` without `--oplog` or a scoped `--db` restriction:

```bash
test ! -e artifacts/cluster55.archive.gz
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/capture-start55.txt
docker run --rm --user "$(id -u):$(id -g)" --network mongodb-ch55-source_cluster \
  -v "$LAB55_ROOT/artifacts:/artifacts" "$MONGO_IMAGE" \
  mongodump --uri='mongodb://r1:27017/' --archive=/artifacts/cluster55.archive.gz --gzip
capture55_status=$?
printf '%s\n' "$capture55_status" > evidence/capture-exit55.txt
export ACTION55=unlock-source
client55
```

Unlock the owned cluster even when the dump fails. Do not allow shell `set -e` to skip the status capture/unlock; perform these steps interactively with independent recovery access. Accept the artifact only after successful capture, confirmed unlock and unchanged baseline verification. If lock acquisition/state recording is uncertain, inspect the actual lock counts and ownership through that independent access rather than rerunning lock or blindly unlocking another operator's lock.

Keep the balancer stopped for deterministic validation until source fencing. Its original setting is retained for policy review; do not restart it in the middle of capture. If topology/election invalidates the lock boundary, mark the artifact unusable and repeat the reviewed procedure.

```bash
test "$(cat evidence/capture-exit55.txt)" = 0
test -s artifacts/cluster55.archive.gz
sha256sum artifacts/cluster55.archive.gz > evidence/cluster55.sha256
sha256sum -c evidence/cluster55.sha256
export ACTION55=later-source
client55
```

The post-backup acknowledged order 101 is worth 10,100 cents. Source now has 101 orders/515,100 cents. Do not overwrite the clean artifact with this later state.

## 9. Fence all routers, shards and config servers

A router-only stop does not fence direct shard writers or another router. Review the run/project labels before stopping all eleven source services. Preserve their volumes and logs.

```bash
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/incident55.txt
dc55 source ps -a
dc55 source stop
source55_ids="$(dc55 source ps -a -q)"
test -n "$source55_ids"
docker inspect --format '{"service":{{json (index .Config.Labels "com.docker.compose.service")}},"project":{{json (index .Config.Labels "com.docker.compose.project")}},"run":{{json (index .Config.Labels "run")}},"running":{{json .State.Running}},"restart":{{json .HostConfig.RestartPolicy.Name}},"networks":{{json .NetworkSettings.Networks}}}' \
  $source55_ids > evidence/fence55.jsonl
```

Save `scripts/fence55.py`:

```python
import json
import sys

SERVICES = {'cfg1', 'cfg2', 'cfg3', 'a1', 'a2', 'a3', 'b1', 'b2', 'b3', 'r1', 'r2'}

def evaluate(records, run_id):
    if not isinstance(run_id, str) or not run_id.strip() or len(records) != 11:
        raise ValueError('run ID and exactly eleven records required')
    names = []
    for record in records:
        if not isinstance(record, dict) or set(record) != {
                'service', 'project', 'run', 'running', 'restart', 'networks'}:
            raise ValueError('invalid record fields')
        if not isinstance(record['service'], str):
            raise ValueError('invalid service name')
        names.append(record['service'])
        if record['project'] != 'mongodb-ch55-source' or record['run'] != run_id or \
                record['running'] is not False or record['restart'] != 'no':
            raise ValueError('ownership/fence/restart mismatch')
        if not isinstance(record['networks'], dict) or set(record['networks']) != {'mongodb-ch55-source_cluster'}:
            raise ValueError('unexpected network attachment')
    if set(names) != SERVICES or len(set(names)) != 11:
        raise ValueError('missing, duplicate or foreign service')
    return {'claim': 'declared_docker_cluster_fence', 'run_id': run_id, 'stopped_services': 11}

if __name__ == '__main__':
    try:
        if len(sys.argv) != 3:
            raise ValueError('usage: fence55.py RUN_ID inventory.jsonl')
        with open(sys.argv[2], encoding='utf-8') as source:
            records = [json.loads(line) for line in source if line.strip()]
        print(json.dumps(evaluate(records, sys.argv[1]), indent=2))
    except (OSError, ValueError, TypeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
```

```bash
python3 scripts/fence55.py "$RUN55" evidence/fence55.jsonl > evidence/fence-accepted55.json
```

These observations prove only the stated Docker fence. Verify restart automation and external/direct writer paths separately in production. Recheck current observations before cutover; the historical JSON file does not prevent a later restart.

## 10. Build the independent recovery cluster

```bash
dc55 recovery up -d cfg1 cfg2 cfg3 a1 a2 a3 b1 b2 b3
docker run --rm --user "$(id -u):$(id -g)" --network mongodb-ch55-recovery_cluster \
  -v "$LAB55_ROOT/recovery/scripts:/scripts:ro" "$MONGO_IMAGE" \
  mongosh --nodb --quiet --file /scripts/bootstrap35.js
dc55 recovery up -d r1 r2
docker run --rm --user "$(id -u):$(id -g)" --network mongodb-ch55-recovery_cluster \
  -v "$LAB55_ROOT/recovery/scripts:/scripts:ro" "$MONGO_IMAGE" \
  mongosh 'mongodb://r1:27017/admin' --quiet --file /scripts/register35.js
```

Review all three replica sets and both routers. Their volumes/network must be the recovery project's, never the source's. Do not seed independent recovery members with arbitrary copies of source files. This logical workflow starts from newly initialized catalogs and empty shard storage.

## 11. Pre-shard the destination and preserve its config catalog

Save as `scripts/prepare55.js`:

```javascript
load('/scripts/lib55.js');
check55(process.env.TARGET55 === 'recovery', 'recovery target required');
router55();
const path55 = '/evidence/state55.json';
const state55 = EJSON.parse(fs55.readFileSync(path55, 'utf8'));
const id55 = clusterId55();
check55(id55 !== state55.sourceClusterId && !state55.recoveryClusterId,
  'distinct fresh recovery catalog required');
state55.recoveryBalancerBefore = sh.getBalancerState();
seed55(state55.runId);
check55(d55.orders.countDocuments({}) === 0 && d55.marker.countDocuments({}) === 0,
  'destination must be empty');
state55.recoveryClusterId = id55;
fs55.writeFileSync(path55, EJSON.stringify(state55, {relaxed: false}), {mode: 0o600});
save55('recovery-prepared55.json', {runId: state55.runId, clusterId: id55,
  observedAt: new Date(), layout: layout55()});
```

```bash
export TARGET55=recovery
docker run --rm --user "$(id -u):$(id -g)" --network mongodb-ch55-recovery_cluster \
  -v "$LAB55_ROOT/scripts:/scripts:ro" -v "$LAB55_ROOT/evidence:/evidence" \
  --env TARGET55 "$MONGO_IMAGE" mongosh 'mongodb://r1:27017/admin' \
  --quiet --file /scripts/prepare55.js
sha256sum -c evidence/cluster55.sha256
docker run --rm --user "$(id -u):$(id -g)" --network mongodb-ch55-recovery_cluster \
  -v "$LAB55_ROOT/artifacts:/artifacts:ro" "$MONGO_IMAGE" \
  mongorestore --uri='mongodb://r1:27017/' --archive=/artifacts/cluster55.archive.gz \
  --gzip --stopOnError --nsExclude='config.*'
export ACTION55=verify-recovery
client55
```

Do not pass `--drop`: dropping a pre-sharded collection can remove its sharding configuration. Do not restore the source `config` database into this destination. The restore routes documents through the destination catalog; its cluster ID/collection UUIDs and host mappings stay independent.

Existing destination options were explicitly created from this fixture's reviewed contract. Verify them after restore; do not assume restoring into an existing collection changes all its options automatically. Keep application traffic and the balancer stopped until acceptance.

## 12. Verify both routers, both shards and transaction behavior

Expected recovered baseline: 100 orders/505,000 cents, fifty rows on each shard, correct compound shard key, two assigned chunks, restored validator/index and owner marker. Order 101 is absent. `restored55.json` must show a cluster ID different from source.

Run the same routed read contract through router `r2` before the transaction probe. Save as `scripts/router255.js`:

```javascript
load('/scripts/lib55.js');
const state55 = EJSON.parse(fs55.readFileSync('/evidence/state55.json', 'utf8'));
check55(clusterId55() === state55.recoveryClusterId, 'wrong recovery catalog');
save55('router2-accepted55.json', {runId: state55.runId, observedAt: new Date(),
  result: verify55(state55, 'base')});
```

```bash
docker run --rm --user "$(id -u):$(id -g)" --network mongodb-ch55-recovery_cluster \
  -v "$LAB55_ROOT/scripts:/scripts:ro" -v "$LAB55_ROOT/evidence:/evidence" "$MONGO_IMAGE" \
  mongosh 'mongodb://r2:27017/admin' --quiet --file /scripts/router255.js
export ACTION55=transaction-probe
client55
```

The transaction moves ten cents from tenant 1/order 1 on shard A to tenant 10/order 10 on shard B. Both effects must commit; total remains 505,000 cents. The controller verifies exact adjusted documents through `mongos` and directly on each shard. A successful update on only one side is not accepted.

The probe deliberately fails on a transaction error rather than retrying blindly. An unknown commit result requires checking the exact two document values and transaction outcome before a new attempt. Do not infer abort from a network error or apply the increments again without reconciliation.

Validate selected targeted and scatter-gather queries under Chapter 37's explain contract. Check every replica-set member's replication/majority health, storage validation and application-visible indexes/options on both shards. The fixture verifier checks primaries' data and all member states; it does not replace a full production secondary/commit-point assessment.

## 13. Resume balancing only after acceptance

Save as `scripts/resume55.js`:

```javascript
load('/scripts/lib55.js');
const state55 = EJSON.parse(fs55.readFileSync('/evidence/state55.json', 'utf8'));
check55(clusterId55() === state55.recoveryClusterId, 'wrong recovery catalog');
const result55 = verify55(state55, 'transaction');
if (state55.recoveryBalancerBefore === true) sh.startBalancer();
check55(sh.getBalancerState() === state55.recoveryBalancerBefore, 'balancer policy differs');
save55('recovery-accepted55.json', {runId: state55.runId, observedAt: new Date(), result: result55,
  balancerRestored: true, unrecoveredAcknowledgedIds: [101], unrecoveredAmountCents: 10100});
```

```bash
docker run --rm --user "$(id -u):$(id -g)" --network mongodb-ch55-recovery_cluster \
  -v "$LAB55_ROOT/scripts:/scripts:ro" -v "$LAB55_ROOT/evidence:/evidence" "$MONGO_IMAGE" \
  mongosh 'mongodb://r1:27017/admin' --quiet --file /scripts/resume55.js
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/recovery-accepted-time55.txt
```

After balancing resumes, shard-local counts/placement can legitimately change. Preserve the pre-resume placement evidence and continue validating routed business data. Do not keep asserting a fifty/fifty physical distribution as a universal ongoing requirement.

No production endpoint cutover occurs here. Before actual cutover, recheck source fencing, restore scopes, real authentication/TLS, application references, consumers and routing. Recycle stale pools and block direct/old endpoints under the selected authority plan.

## 14. Adapt to managed PITR or physical cluster recovery

| Architecture | Additional required work |
|---|---|
| Ops Manager/Atlas | Coordinated cluster recovery point, all shards/config servers, healthy replay ranges, exact delivery target and per-component verification |
| Physical coordinated snapshots | Consistent complete shard/config set, runtime/options/key compatibility, isolated topology reconstruction and router configuration |
| Logical outage backup | Full reviewed quiet/lock boundary, retained shard-key schema and new-catalog pre-sharding |

Managed backup is preferable when the application cannot accept the coordinated write pause of this logical method. Use Chapter 52's platform/version/credential preparation, then the installed platform's **sharded** restore procedure. Do not restore only one shard and label the whole cluster recovered.

For manual managed/physical recovery, preserve each component's restore metadata, encryption/key access and selected point. Follow the documented config-server and shard restoration order and host/catalog updates. Do not copy arbitrary internal metadata-edit commands from a replica-set-only procedure into this cluster.

Independent shard snapshots are not accepted unless the selected documented procedure establishes consistency for the entire cluster. A config-server-only backup contains metadata, not every shard's application data. Reconstructing routing by guessing chunk ownership risks missing or duplicated results.

## 15. Measure recovery loss and operational readiness

ID 101 was majority-acknowledged after capture and is absent on recovery: **one unrecovered order, 10,100 cents**. Preserve its external acknowledgment record and distinguish operation loss from temporal recovery-point age. Majority replication does not make an older retained backup include a later write.

RTO includes provisioning all components, capture retrieval, pre-sharding, restore/index work, member health, routing, transaction checks and application acceptance. Router startup or one shard's restore duration is insufficient. Use Chapter 49's incident/cutoff/acceptance definitions and identify delays on the critical path.

Once recovery accepts application writes, it becomes authoritative. The stopped source is stale. Failback requires a planned resync/migration and reconciliation, not a DNS reversal or attaching old shards to the recovered config servers.

## 16. Acceptance, failure handling and cleanup

Acceptance requires a supported quiet/locked capture, successful dump, confirmed unlock, artifact integrity, all eleven source services fenced, distinct destination catalog, correct pre-sharding, exact data on both shards/routers and atomic cross-shard transaction behavior. Include actual security/storage/secondary checks for the production profile. Offline validation does not satisfy these live requirements.

| Failure | Safe response |
|---|---|
| Partial lock or uncertain count | Use independent access to resolve the owned pause; reject uncertain capture |
| Backup fails | Unlock safely, preserve logs and produce a fresh artifact after repair |
| Source process restarts | Reestablish authority/fence; stop cutover |
| Destination catalog matches source | Investigate shared volumes/wrong network or wrong restore procedure |
| Correct total but missing/duplicate IDs | Reconcile full documents and shard placement |
| Pre-sharded collection becomes unsharded | Inspect restore flags/catalog; do not accept |
| Transaction probe fails | Inspect shard/config health, write concern and transaction state |

Preserve evidence/logs before cleanup. Inspect every project's run/chapter labels, volume/network ownership and mounts. Source must still be stopped; no owned lock should remain. Remove only the two dedicated projects after those checks:

```bash
dc55 source ps -a
dc55 recovery ps -a
dc55 source logs > logs/source-final55.log 2>&1
dc55 recovery logs > logs/recovery-final55.log 2>&1
dc55 recovery stop
dc55 source down
dc55 recovery down
```

No `--volumes` is supplied: evidence/data retention is a separate decision. Do not remove Chapter 35 volumes, shared backup stores, Agents or production keys. If cleanup ownership or capture state is uncertain, inspect rather than weakening the guards. Retain/delete only the reviewed owned lab artifacts and volumes under their retention decision.

## 17. References and next chapter

- [MongoDB 8.0 coordinated sharded logical backup](https://www.mongodb.com/docs/v8.0/tutorial/backup-sharded-cluster-with-database-dumps/)
- [MongoDB 8.0 logical sharded restore](https://www.mongodb.com/docs/v8.0/tutorial/restore-sharded-cluster-with-database-dumps/)
- [Ops Manager sharded restore](https://www.mongodb.com/docs/ops-manager/current/tutorial/restore-sharded-cluster/)
- [Chapter 35 — Build a Sharded Lab Cluster](35-build-a-sharded-lab-cluster.md)
- [Previous: Chapter 54 — Replica Set Disaster Recovery](54-replica-set-disaster-recovery.md)

Next: **[Chapter 56 — Restore Drill and Recovery Acceptance Project](56-restore-drill-and-recovery-acceptance-project.md)**.
