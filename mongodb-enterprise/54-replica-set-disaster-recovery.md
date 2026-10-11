# 54 — Replica Set Disaster Recovery

Part 7 — Backup Recovery and Disaster Recovery

**Baseline:** MongoDB 8.0/FCV 8.0, WiredTiger, compatible pinned Database Tools, Linux Docker host.  
**Status:** Written; static review complete; live replica-set disaster recovery pending.  
**Prerequisites:** Chapters 25–32 and 49–53; Python 3, OpenSSL, Docker and capacity for six disposable members.

## 1. Define the disaster-recovery claim

This lab creates a fresh authenticated TLS three-member source replica set, captures a known idle application dataset, acknowledges a later write and stops every source member. It restores the earlier dataset into a different replica set on an isolated network, adds two empty members through initial sync, and validates majority writes and secondary reads.

The recoverable scope is one ordinary application database with its collection metadata. Credentials, internal keyfiles, TLS and replica configuration are provisioned separately on recovery. This is a complete exercise for that stated dataset contract, not a claim that a scoped archive backs up every database, identity or deployment setting.

Both deployments are on one host. Stopping all source members simulates total source-service loss; it does not prove recovery after losing the host or region. Production DR requires independently retained artifacts, keys, infrastructure and access. The retained Chapter 35/41/51 deployments are untouched.

## 2. Distinguish failover, replacement and disaster recovery

| Condition | Appropriate response |
|---|---|
| Healthy majority; primary failed | Normal election and client retry under the application contract |
| One member lost; healthy authoritative set remains | Replace/resync the member; Chapter 30 |
| Majority unavailable but viable current data survives | Assess topology, acknowledged writes and fencing before intervention |
| Entire service/storage unavailable | Restore a verified recovery point into new isolated infrastructure |
| Logical corruption already replicated | Restore a clean point and reconcile valid later writes; Chapters 52–53 |

Do not use forced reconfiguration as a generic DR shortcut. It can alter the acknowledged-write safety assumptions and does not recover unavailable data. Record which surviving history, backup chain and application acknowledgments are authoritative before selecting a recovery path.

## 3. Establish authority, fencing and acceptance

Exactly one deployment may accept authoritative application writes after cutover. Fence the old service through the actual provisioning/network/access controls before allowing recovery traffic. DNS changes alone do not fence clients with old connection pools or direct endpoints.

| Gate | Required evidence |
|---|---|
| Source fenced | Every source member inaccessible for application writes; restart automation controlled |
| Recovery identity correct | Distinct replica-set name, hosts, network and data directories |
| Recovery point validated | Verified backup scope, cutoff, integrity and business reconciliation |
| Redundancy restored | One primary and two healthy caught-up data-bearing secondaries |
| Application contract works | Fresh scoped credentials, majority write and expected reads/rejections |
| Cutover approved | Owners accept recovery-point loss and endpoint transition |

This lab's fence is stopped, non-restarting owned Docker containers on a separate internal network. The inventory helper validates that observation; it cannot certify cloud power fencing, firewalls or another orchestration system. Preserve the original data for investigation. Never start the old set after recovery starts accepting writes merely to “fail back.”

## 4. Prepare a new private workspace

Use an approved exact MongoDB 8.0 image digest containing `mongosh`, `mongodump` and `mongorestore`. If Tools are absent, supply an approved compatible pinned client image through a reviewed adapter. Record exact versions and image digest before proceeding.

```bash
umask 077
mkdir mongodb-ch54
cd mongodb-ch54
export LAB54_ROOT="$PWD"
mkdir scripts evidence artifacts logs pki keys
mkdir s-a s-b s-c r-a r-b r-c
export RUN54="$(python3 -c 'import uuid; print(uuid.uuid4())')"
printf '%s\n' "$RUN54" > evidence/run54.txt
test -n "${MONGO_IMAGE:?set the approved MongoDB 8.0 image digest}"
case "$MONGO_IMAGE" in *@sha256:*) ;; *) exit 1 ;; esac
docker run --rm "$MONGO_IMAGE" mongod --version
docker run --rm "$MONGO_IMAGE" mongodump --version
docker run --rm "$MONGO_IMAGE" mongorestore --version
docker network create --internal --label chapter=54 --label "run=$RUN54" mongodb-ch54_source
docker network create --internal --label chapter=54 --label "run=$RUN54" mongodb-ch54_recovery
```

Fixed container/network names must be absent. A conflict is a stop condition, not permission to remove existing resources. Require disk/RAM headroom for six WiredTiger processes, restore/index work and initial sync. At least 0.25 GiB of WiredTiger cache is configured per member, but total process memory is larger than cache size.

Run each code block separately. Do not paste the chapter as an unattended script; stop on any failed command or unexpected observation. Save the controller/helper scripts before invoking them.

## 5. Provision separate internal keys and valid TLS

Source and recovery have different member-authentication keys. This prevents accidental membership across the two identity domains; network separation is still mandatory.

```bash
openssl rand -base64 756 > keys/source.key
openssl rand -base64 756 > keys/recovery.key
chmod 400 keys/source.key keys/recovery.key
openssl req -x509 -newkey rsa:3072 -sha256 -nodes -days 30 \
  -keyout pki/ca.key -out pki/ca.crt -subj '/CN=Chapter54LabCA' \
  -addext 'basicConstraints=critical,CA:TRUE' \
  -addext 'keyUsage=critical,keyCertSign,cRLSign'
openssl req -new -newkey rsa:3072 -nodes \
  -keyout pki/server.key -out pki/server.csr -subj '/CN=Chapter54LabMembers'
cat > pki/server.ext <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth,clientAuth
subjectAltName=DNS:s54a,DNS:s54b,DNS:s54c,DNS:r54a,DNS:r54b,DNS:r54c,DNS:localhost,IP:127.0.0.1
EOF
openssl x509 -req -in pki/server.csr -CA pki/ca.crt -CAkey pki/ca.key \
  -CAcreateserial -out pki/server.crt -days 14 -sha256 -extfile pki/server.ext
cat pki/server.crt pki/server.key > pki/server.pem
mkdir pki/public pki/runtime
cp pki/ca.crt pki/public/ca.crt
cp pki/ca.crt pki/runtime/ca.crt
cp pki/server.pem pki/runtime/server.pem
chmod 600 pki/ca.key pki/server.key pki/server.pem pki/runtime/server.pem
chmod 644 pki/public/ca.crt pki/runtime/ca.crt
openssl verify -CAfile pki/public/ca.crt -verify_hostname s54a pki/server.crt
openssl verify -CAfile pki/public/ca.crt -verify_hostname r54a pki/server.crt
```

The shared six-name leaf is a disposable teaching simplification. Production members need reviewed per-host certificates and recovery issuance/custody. Clients mount only the public CA. Servers mount only runtime TLS and their own internal key; the CA private key is never mounted.

## 6. Start source members and initialize authentication

The fixed function maps each member to its owned data directory and isolated network. It directly runs `mongod` as the host user, with no initialization password environment variables or published host ports.

```bash
start54() {
  case "$1" in
    s-a) host54=s54a; network54=mongodb-ch54_source; set54=rs54source; key54=source ;;
    s-b) host54=s54b; network54=mongodb-ch54_source; set54=rs54source; key54=source ;;
    s-c) host54=s54c; network54=mongodb-ch54_source; set54=rs54source; key54=source ;;
    r-a) host54=r54a; network54=mongodb-ch54_recovery; set54=rs54recovery; key54=recovery ;;
    r-b) host54=r54b; network54=mongodb-ch54_recovery; set54=rs54recovery; key54=recovery ;;
    r-c) host54=r54c; network54=mongodb-ch54_recovery; set54=rs54recovery; key54=recovery ;;
    *) return 1 ;;
  esac
  docker run -d --name "mongodb-ch54-$1" --hostname "$host54" \
    --label chapter=54 --label "run=$RUN54" --restart=no \
    --network "$network54" --network-alias "$host54" \
    --user "$(id -u):$(id -g)" --entrypoint mongod \
    -v "$LAB54_ROOT/$1:/data/db" \
    -v "$LAB54_ROOT/keys/$key54.key:/key/member.key:ro" \
    -v "$LAB54_ROOT/pki/runtime:/tls:ro" \
    -v "$LAB54_ROOT/scripts:/scripts:ro" "$MONGO_IMAGE" \
    --dbpath /data/db --replSet "$set54" --keyFile /key/member.key \
    --auth --bind_ip_all --port 27017 --oplogSize 128 --wiredTigerCacheSizeGB 0.25 \
    --tlsMode requireTLS --tlsCertificateKeyFile /tls/server.pem \
    --tlsCAFile /tls/ca.crt --tlsAllowConnectionsWithoutCertificates
}
start54 s-a
start54 s-b
start54 s-c
```

Check each startup log and listener milestone. Save `scripts/init-source54.js`:

```javascript
const result = rs.initiate({_id: 'rs54source', members: [
  {_id: 0, host: 's54a:27017', priority: 2},
  {_id: 1, host: 's54b:27017'}, {_id: 2, host: 's54c:27017'}]});
if (result.ok !== 1) throw new Error('source initiation failed');
```

Save `scripts/bootstrap-source54.js`:

```javascript
const a = db.getSiblingDB('admin');
if (!a.runCommand({hello: 1}).isWritablePrimary) throw new Error('wait for s54a primary');
print('Create the source-only administrator secret.');
a.createUser({user: 'ch54_sourceAdmin', pwd: passwordPrompt(),
  roles: [{role: 'root', db: 'admin'}]});
```

```bash
docker exec -it mongodb-ch54-s-a mongosh 'mongodb://localhost:27017/admin?directConnection=true' \
  --tls --tlsCAFile /tls/ca.crt --file /scripts/init-source54.js
docker logs mongodb-ch54-s-a
docker exec -it mongodb-ch54-s-a mongosh 'mongodb://localhost:27017/admin?directConnection=true' \
  --tls --tlsCAFile /tls/ca.crt --file /scripts/bootstrap-source54.js
```

Wait for `s54a` to become primary before bootstrap. The localhost exception applies only before the first user exists. A not-yet-primary failure is not permission to disable authentication or create a user on a secondary. Keep the secret in your approved secret store.

## 7. Implement fixture, topology and recovery validation

Save as `scripts/control54.js`. The source/recovery selector fixes expected replica-set identity and host lists. Source capture requires all three members healthy. Recovery starts with one member, then acceptance requires all three.

```javascript
const fs = require('fs');
const crypto = require('crypto');
const a = db.getSiblingDB('admin');
const d = db.getSiblingDB('mongodb_enterprise_tutorial_ch54');
const target = process.env.TARGET54, action = process.env.ACTION54;
const stateFile = '/evidence/state54.json';
const sourceHosts = ['s54a:27017', 's54b:27017', 's54c:27017'];
const recoveryHosts = ['r54a:27017', 'r54b:27017', 'r54c:27017'];
const base = Array.from({length: 100}, (_, n) => ({
  _id: n + 1, code: `order-${n + 1}`, amountCents: (n + 1) * 10}));
const later = {_id: 101, code: 'order-101', amountCents: 1010};
const validator = {$jsonSchema: {bsonType: 'object', required: ['_id', 'code', 'amountCents'],
  properties: {code: {bsonType: 'string'}, amountCents: {bsonType: 'number', minimum: 0}}}};
function check(value, message) { if (!value) throw new Error(message); }
function json(value) { return JSON.parse(EJSON.stringify(value, {relaxed: true})); }
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.fromEntries(
    Object.keys(value).sort().map(key => [key, canonical(value[key])]));
  return value;
}
function hash(value) { return crypto.createHash('sha256')
  .update(JSON.stringify(canonical(json(value)))).digest('hex'); }
function save(name, value) { fs.writeFileSync(`/evidence/${name}`,
  EJSON.stringify(value, {relaxed: false}), {flag: 'wx', mode: 0o600}); }
function uuid(name) { return EJSON.stringify(d.getCollectionInfos({name})[0].info.uuid,
  {relaxed: false}); }
function topology(hosts) {
  const status = a.runCommand({replSetGetStatus: 1});
  check(status.ok === 1 && hash(status.members.map(m => m.name).sort()) === hash([...hosts].sort()),
    'unexpected member inventory');
  check(status.members.every(m => m.health === 1) &&
    status.members.filter(m => m.state === 1).length === 1 &&
    status.members.filter(m => m.state === 2).length === hosts.length - 1,
    'wait for healthy primary/secondaries');
  const conf = a.runCommand({replSetGetConfig: 1});
  check(conf.ok === 1 && conf.config.members.every(m => m.votes === 1 && !m.arbiterOnly && !m.newlyAdded),
    'all members must be voting data-bearing members');
  return status;
}
function verify(state, post = false) {
  check(hash(d.getCollectionInfos().map(i => i.name).sort()) === hash(['markers', 'orders']),
    'unexpected collections');
  const owner = d.markers.findOne({_id: 'owner'});
  check(owner && owner.runId === state.runId && owner.chapter === 54, 'owner mismatch');
  const expected = post ? [...base, later] : base;
  const actual = d.orders.find().sort({_id: 1}).toArray();
  check(hash(actual) === hash(expected), 'exact order mismatch');
  const indexes = d.orders.getIndexes();
  check(indexes.length === 2 && indexes.some(i => i.name === 'code_unique54' && i.unique === true
    && hash(i.key) === hash({code: 1})), 'index mismatch');
  const options = d.getCollectionInfos({name: 'orders'})[0].options;
  check(hash(options.validator) === hash(validator) && options.validationLevel === 'strict'
    && options.validationAction === 'error', 'validator mismatch');
  if (target === 'source') {
    check(uuid('orders') === state.ordersUUID && uuid('markers') === state.markersUUID,
      'source identity changed');
    check(d.markers.countDocuments({}) === 1, 'unexpected source marker');
  }
  return {count: actual.length, amountCents: actual.reduce((n, row) => n + row.amountCents, 0),
    digest: hash(actual), ordersUUID: uuid('orders'), markersUUID: uuid('markers')};
}
const hello = a.runCommand({hello: 1});
check(hello.ok === 1 && hello.isWritablePrimary === true &&
  hello.setName === (target === 'source' ? 'rs54source' :
  target === 'recovery' ? 'rs54recovery' : ''), 'wrong primary/replica set');
const build = a.runCommand({buildInfo: 1});
const fcv = a.runCommand({getParameter: 1, featureCompatibilityVersion: 1});
check(build.ok === 1 && build.version.startsWith('8.0.') && fcv.ok === 1 &&
  fcv.featureCompatibilityVersion.version === '8.0', '8.0 stable baseline required');
if (action === 'setup') {
  check(target === 'source' && !fs.existsSync(stateFile), 'fresh source/state required');
  topology(sourceHosts);
  check(d.getCollectionInfos().length === 0, 'existing fixture');
  const state = {runId: fs.readFileSync('/evidence/run54.txt', 'utf8').trim(), serverVersion: build.version};
  d.createCollection('orders', {validator, validationLevel: 'strict', validationAction: 'error'});
  d.createCollection('markers');
  d.orders.createIndex({code: 1}, {unique: true, name: 'code_unique54'});
  d.orders.insertMany(base, {writeConcern: {w: 'majority', j: true}});
  d.markers.insertOne({_id: 'owner', runId: state.runId, chapter: 54},
    {writeConcern: {w: 'majority', j: true}});
  state.ordersUUID = uuid('orders'); state.markersUUID = uuid('markers');
  save('state54.json', state);
  save('baseline54.json', {runId: state.runId, observedAt: new Date(), result: verify(state)});
} else {
  const state = EJSON.parse(fs.readFileSync(stateFile, 'utf8'));
  check(build.version === state.serverVersion, 'exact server version differs');
  if (action === 'verify-source') {
    check(target === 'source', 'source required'); topology(sourceHosts); printjson(verify(state));
  } else if (action === 'later-write') {
    check(target === 'source', 'source required'); topology(sourceHosts); verify(state);
    d.orders.insertOne(later, {writeConcern: {w: 'majority', j: true}});
    save('later-ack54.json', {runId: state.runId, acknowledgedAt: new Date(),
      writeConcern: {w: 'majority', j: true}, acknowledgedIdsOutsideBackup: [101],
      result: verify(state, true)});
  } else if (action === 'preflight-restore') {
    check(target === 'recovery', 'recovery required'); topology(['r54a:27017']);
    check(d.getCollectionInfos().length === 0 && d.getUsers().users.length === 0 &&
      d.getRoles({showBuiltinRoles: false}).roles.length === 0, 'nonempty recovery database');
  } else if (action === 'verify-seed') {
    check(target === 'recovery', 'recovery required'); topology(['r54a:27017']);
    check(d.markers.countDocuments({}) === 1, 'unexpected seed markers');
    save('seed54.json', {runId: state.runId, observedAt: new Date(), result: verify(state)});
  } else if (action === 'add-b' || action === 'add-c') {
    check(target === 'recovery', 'recovery required'); verify(state);
    topology(action === 'add-b' ? ['r54a:27017'] : ['r54a:27017', 'r54b:27017']);
    const added = rs.add(action === 'add-b' ? 'r54b:27017' : 'r54c:27017');
    check(added.ok === 1, 'member add failed');
  } else if (action === 'check-two') {
    check(target === 'recovery', 'recovery required'); printjson(topology(['r54a:27017', 'r54b:27017']));
  } else if (action === 'accept-primary') {
    check(target === 'recovery', 'recovery required'); const status = topology(recoveryHosts);
    const result = verify(state);
    check(d.markers.countDocuments({}) === 1, 'acceptance already run or unexpected markers');
    for (const [doc, code] of [
      [{_id: 'duplicate54', code: 'order-1', amountCents: 1}, 11000],
      [{_id: 'invalid54', code: 'invalid54', amountCents: -1}, 121]
    ]) {
      let denied = false;
      try { d.orders.insertOne(doc); }
      catch (error) { if (error.code !== code) throw error; denied = true; }
      check(denied, 'constraint unexpectedly accepted document; investigate');
    }
    verify(state);
    d.markers.insertOne({_id: 'majority54', runId: state.runId, chapter: 54},
      {writeConcern: {w: 'majority', j: true, wtimeout: 30000}});
    const validation = d.runCommand({validate: 'orders', full: true});
    check(validation.ok === 1 && validation.valid === true &&
      (!validation.errors || !validation.errors.length) &&
      (!validation.warnings || !validation.warnings.length), 'review storage validation');
    save('primary-accepted54.json', {runId: state.runId, observedAt: new Date(), result,
      status, validation, unrecoveredAcknowledgedIds: [101], unrecoveredAmountCents: 1010});
  } else if (action === 'create-app') {
    check(target === 'recovery', 'recovery required'); topology(recoveryHosts); verify(state);
    check(!a.getUser('ch54_app'), 'application username exists');
    print('Create a fresh recovery application password.');
    a.createUser({user: 'ch54_app', pwd: passwordPrompt(),
      roles: [{role: 'readWrite', db: d.getName()}]});
  } else throw new Error('unknown ACTION54');
}
```

Logical restore creates new UUIDs on recovery. The source UUID guard prevents accidental substitution of a source collection; do not expect the logical target UUID to equal it. State/evidence files are external to both data paths and created exclusively.

## 8. Capture a consistent idle application archive

```bash
admin54() {
  case "$TARGET54" in
    source) network54=mongodb-ch54_source; user54=ch54_sourceAdmin
      uri54='mongodb://s54a:27017,s54b:27017,s54c:27017/admin?replicaSet=rs54source' ;;
    recovery) network54=mongodb-ch54_recovery; user54=ch54_recoveryAdmin
      uri54='mongodb://r54a:27017/admin?replicaSet=rs54recovery' ;;
    *) return 1 ;;
  esac
  docker run --rm -it --user "$(id -u):$(id -g)" --network "$network54" \
    -v "$LAB54_ROOT/pki/public:/trust:ro" -v "$LAB54_ROOT/scripts:/scripts:ro" \
    -v "$LAB54_ROOT/evidence:/evidence" --env TARGET54 --env ACTION54 "$MONGO_IMAGE" \
    mongosh "$uri54" --tls --tlsCAFile /trust/ca.crt \
    --username "$user54" --authenticationDatabase admin \
    --authenticationMechanism SCRAM-SHA-256 --password --file /scripts/control54.js
}
export TARGET54=source ACTION54=setup
admin54
test ! -e artifacts/application54.archive.gz
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/capture-start54.txt
docker run --rm -it --user "$(id -u):$(id -g)" --network mongodb-ch54_source \
  -v "$LAB54_ROOT/pki/public:/trust:ro" -v "$LAB54_ROOT/artifacts:/artifacts" "$MONGO_IMAGE" \
  mongodump --uri='mongodb://s54a:27017,s54b:27017,s54c:27017/?replicaSet=rs54source' \
  --ssl --sslCAFile=/trust/ca.crt --username=ch54_sourceAdmin --authenticationDatabase=admin \
  --authenticationMechanism=SCRAM-SHA-256 --db=mongodb_enterprise_tutorial_ch54 \
  --archive=/artifacts/application54.archive.gz --gzip
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/capture-end54.txt
export ACTION54=verify-source
admin54
test -s artifacts/application54.archive.gz
sha256sum artifacts/application54.archive.gz > evidence/archive54.sha256
sha256sum -c evidence/archive54.sha256
```

Require a successful capture and unchanged full fixture before sealing. Keep all fixture writers stopped during capture; no TTL/background writer exists. This scoped dump does not use `--oplog` and is not arbitrary PITR. For a live full-instance recovery contract, use the supported full oplog capture/replay or managed/physical path described in Section 14.

Preserve the archive and checksum outside the failed service, with independently protected retention/key access in production. A local checksum detects accidental changes, not an attacker rewriting both files. Gzip is not encryption.

Now acknowledge a write that the backup does not contain:

```bash
export ACTION54=later-write
admin54
```

Source has 101 orders/51,510 cents. The external acknowledgment evidence explicitly lists ID 101 and its 1,010 cents. Do not take another backup after this step; recovery will deliberately expose that loss.

## 9. Fence every owned source member

Declare the exercise incident and stop all three source members. Do not delete their data directories. Confirm labels against the run marker before stopping anything.

```bash
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/incident54.txt
for member54 in s-a s-b s-c; do
  test "$(docker inspect --format '{{index .Config.Labels "run"}}' "mongodb-ch54-$member54")" = "$RUN54" || exit 1
  test "$(docker inspect --format '{{index .Config.Labels "chapter"}}' "mongodb-ch54-$member54")" = 54 || exit 1
done
docker stop --time 120 mongodb-ch54-s-a mongodb-ch54-s-b mongodb-ch54-s-c
docker inspect --format '{"name":{{json .Name}},"running":{{json .State.Running}},"run":{{json (index .Config.Labels "run")}},"restart":{{json .HostConfig.RestartPolicy.Name}},"networks":{{json .NetworkSettings.Networks}}}' \
  mongodb-ch54-s-a mongodb-ch54-s-b mongodb-ch54-s-c > evidence/fence54.jsonl
```

Save `scripts/fence54.py`:

```python
#!/usr/bin/env python3
import json
import sys

def evaluate(records, run_id):
    expected = {'/mongodb-ch54-s-a', '/mongodb-ch54-s-b', '/mongodb-ch54-s-c'}
    if not isinstance(run_id, str) or not run_id.strip() or len(records) != 3:
        raise ValueError('run ID and exactly three member records required')
    names = []
    for record in records:
        if not isinstance(record, dict) or set(record) != {'name', 'running', 'run', 'restart', 'networks'}:
            raise ValueError('unexpected record fields')
        if not isinstance(record['name'], str):
            raise ValueError('member name must be a string')
        names.append(record['name'])
        if record['run'] != run_id or record['running'] is not False or record['restart'] != 'no':
            raise ValueError('source not stopped or ownership/restart policy differs')
        if not isinstance(record['networks'], dict) or set(record['networks']) != {'mongodb-ch54_source'}:
            raise ValueError('unexpected source network attachment')
    if set(names) != expected or len(set(names)) != 3:
        raise ValueError('missing, duplicate or foreign source member')
    return {'claim': 'declared_docker_source_fence', 'run_id': run_id, 'members_stopped': 3}

def main():
    try:
        if len(sys.argv) != 3:
            raise ValueError('usage: fence54.py RUN_ID inventory.jsonl')
        with open(sys.argv[2], encoding='utf-8') as source:
            records = [json.loads(line) for line in source if line.strip()]
        print(json.dumps(evaluate(records, sys.argv[1]), indent=2))
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
```

```bash
python3 scripts/fence54.py "$RUN54" evidence/fence54.jsonl > evidence/fence-accepted54.json
```

Also review source logs/exit status and verify no restart automation or client path bypasses this fence. The stopped containers must remain stopped through recovery acceptance. Recheck inventory immediately before any application cutover; a past observation does not prevent later restart.

## 10. Initialize an isolated single-member recovery set

Start only the empty recovery seed. Do not copy source member data or internal keys into it.

```bash
start54 r-a
docker logs mongodb-ch54-r-a
```

Save `scripts/init-recovery54.js`:

```javascript
const result = rs.initiate({_id: 'rs54recovery', members: [{_id: 0, host: 'r54a:27017', priority: 2}]});
if (result.ok !== 1) throw new Error('recovery initiation failed');
```

Save `scripts/bootstrap-recovery54.js`:

```javascript
const a = db.getSiblingDB('admin');
if (!a.runCommand({hello: 1}).isWritablePrimary) throw new Error('wait for recovery primary');
print('Create a distinct recovery administrator secret.');
a.createUser({user: 'ch54_recoveryAdmin', pwd: passwordPrompt(),
  roles: [{role: 'root', db: 'admin'}]});
```

```bash
docker exec -it mongodb-ch54-r-a mongosh 'mongodb://localhost:27017/admin?directConnection=true' \
  --tls --tlsCAFile /tls/ca.crt --file /scripts/init-recovery54.js
docker logs mongodb-ch54-r-a
docker exec -it mongodb-ch54-r-a mongosh 'mongodb://localhost:27017/admin?directConnection=true' \
  --tls --tlsCAFile /tls/ca.crt --file /scripts/bootstrap-recovery54.js
export TARGET54=recovery ACTION54=preflight-restore
admin54
```

Wait for normal startup/primary election before creating the first user. One member is a temporary isolated restoration stage. A majority of one is not the three-member durability/availability contract and is insufficient for this lab's final acceptance.

## 11. Restore the application seed and verify loss

```bash
sha256sum -c evidence/archive54.sha256
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/restore-start54.txt
docker run --rm -it --user "$(id -u):$(id -g)" --network mongodb-ch54_recovery \
  -v "$LAB54_ROOT/pki/public:/trust:ro" -v "$LAB54_ROOT/artifacts:/artifacts:ro" "$MONGO_IMAGE" \
  mongorestore --uri='mongodb://r54a:27017/?replicaSet=rs54recovery' \
  --ssl --sslCAFile=/trust/ca.crt --username=ch54_recoveryAdmin --authenticationDatabase=admin \
  --authenticationMechanism=SCRAM-SHA-256 --archive=/artifacts/application54.archive.gz \
  --gzip --stopOnError --nsInclude='mongodb_enterprise_tutorial_ch54.*'
export ACTION54=verify-seed
admin54
```

Require successful Tools exit and seed verification: 100 orders/50,500 cents, exact documents, marker, unique index and validator. Order 101 must be absent. A restored listener with fewer/wrong documents is not an accepted seed.

No `admin` credentials or `local` topology metadata were in this scoped archive, so the newly provisioned recovery administrator/replica-set identity remain authoritative. The original source administrator password does not become the target credential through this restore.

A partial restore is not atomic. Stop, inspect and reset only the owned recovery scope under a reviewed retry plan. Do not add `--drop`, bypass validation or alter expected counts to hide a failure.

## 12. Rebuild redundancy through initial sync

Confirm `r-b` and `r-c` remain empty owned directories. Start/add one member at a time, waiting for it to become healthy before the next voting configuration change.

```bash
start54 r-b
export ACTION54=add-b
admin54
export ACTION54=check-two
admin54
```

If `check-two` reports STARTUP/STARTUP2/RECOVERING, wait and inspect member logs, disk, trust, internal key and source oplog coverage. Re-run the read-only check after progress; do not repeatedly issue `rs.add`.

```bash
start54 r-c
export ACTION54=add-c
admin54
export ACTION54=accept-primary
admin54
```

Run acceptance only after all three are healthy. It records their status, validates storage and writes a `majority54` marker with `w: majority`, journaling and a 30-second write timeout. A timeout does not prove no write happened; inspect actual state rather than blindly retrying acceptance.

Do not restore the archive separately into every member. Initial sync populates empty members from the recovered authoritative set. Large datasets require measured sync capacity, sufficient oplog history and recovery-time budgeting; this tiny fixture does not establish production sync throughput.

## 13. Verify both secondaries and a fresh application identity

Save `scripts/secondary54.js`. Run it directly against each recovery secondary using the target administrator and a fresh TLS connection with `readPreference=secondary`.

```javascript
const fs = require('fs');
const a = db.getSiblingDB('admin');
const d = db.getSiblingDB('mongodb_enterprise_tutorial_ch54');
const state = EJSON.parse(fs.readFileSync('/evidence/state54.json', 'utf8'));
const hello = a.runCommand({hello: 1});
const status = a.runCommand({replSetGetStatus: 1});
if (hello.setName !== 'rs54recovery' || status.myState !== 2)
  throw new Error('recovery secondary required');
const response = d.runCommand({find: 'orders', sort: {_id: 1}, batchSize: 200,
  readConcern: {level: 'majority'}});
if (response.ok !== 1 || response.cursor.firstBatch.length !== 100)
  throw new Error('wait for secondary majority-visible baseline');
for (let n = 0; n < 100; n++) {
  const row = JSON.parse(EJSON.stringify(response.cursor.firstBatch[n], {relaxed: true}));
  if (row._id !== n + 1 || row.code !== `order-${n + 1}` || row.amountCents !== (n + 1) * 10)
    throw new Error('secondary order mismatch');
}
const marker = d.runCommand({find: 'markers', filter: {_id: 'majority54'},
  readConcern: {level: 'majority'}});
if (marker.ok !== 1 || marker.cursor.firstBatch.length !== 1 ||
  marker.cursor.firstBatch[0].runId !== state.runId) throw new Error('wait for acceptance marker');
const host = hello.me.split(':')[0];
if (!['r54b', 'r54c'].includes(host)) throw new Error('unexpected member');
fs.writeFileSync(`/evidence/${host}-accepted54.json`, JSON.stringify({
  runId: state.runId, host, observedAt: new Date().toISOString(), count: 100,
  majorityMarkerVisible: true}), {flag: 'wx', mode: 0o600});
```

```bash
for host54 in r54b r54c; do
  docker run --rm -it --user "$(id -u):$(id -g)" --network mongodb-ch54_recovery \
    -v "$LAB54_ROOT/pki/public:/trust:ro" -v "$LAB54_ROOT/scripts:/scripts:ro" \
    -v "$LAB54_ROOT/evidence:/evidence" "$MONGO_IMAGE" \
    mongosh "mongodb://$host54:27017/admin?directConnection=true&readPreference=secondary" \
    --tls --tlsCAFile /trust/ca.crt --username ch54_recoveryAdmin --authenticationDatabase admin \
    --authenticationMechanism SCRAM-SHA-256 --password --file /scripts/secondary54.js
done
export ACTION54=create-app
admin54
```

Save `scripts/app54.js`:

```javascript
const fs = require('fs');
const state = EJSON.parse(fs.readFileSync('/evidence/state54.json', 'utf8'));
const d = db.getSiblingDB('mongodb_enterprise_tutorial_ch54');
const hello = db.getSiblingDB('admin').runCommand({hello: 1});
if (hello.setName !== 'rs54recovery') throw new Error('wrong application target');
const owner = d.markers.findOne({_id: 'owner'});
if (!owner || owner.runId !== state.runId) throw new Error('owner mismatch');
if (d.orders.countDocuments({}) !== 100 || d.orders.findOne({_id: 101}))
  throw new Error('unexpected recovery state');
d.markers.insertOne({_id: 'app54', runId: state.runId, chapter: 54},
  {writeConcern: {w: 'majority', j: true, wtimeout: 30000}});
let denied = false;
try { const result = db.getSiblingDB('admin').runCommand({getParameter: 1, featureCompatibilityVersion: 1});
  if (result.code === 13) denied = true; else if (result.ok !== 1) throw new Error('wrong failure'); }
catch (error) { if (error.code !== 13) throw error; denied = true; }
if (!denied) throw new Error('application unexpectedly has administrative access');
fs.writeFileSync('/evidence/app-accepted54.json', JSON.stringify({runId: state.runId,
  observedAt: new Date().toISOString(), majorityWriteSucceeded: true, adminDenied: true}),
  {flag: 'wx', mode: 0o600});
```

```bash
docker run --rm -it --user "$(id -u):$(id -g)" --network mongodb-ch54_recovery \
  -v "$LAB54_ROOT/pki/public:/trust:ro" -v "$LAB54_ROOT/scripts:/scripts:ro" \
  -v "$LAB54_ROOT/evidence:/evidence" "$MONGO_IMAGE" \
  mongosh 'mongodb://r54a:27017,r54b:27017,r54c:27017/admin?replicaSet=rs54recovery' \
  --tls --tlsCAFile /trust/ca.crt --username ch54_app --authenticationDatabase admin \
  --authenticationMechanism SCRAM-SHA-256 --password --file /scripts/app54.js
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/recovery-accepted54.txt
```

Expected authorization failure is code 13; TLS/network errors do not satisfy it. These app writes occur only on recovery while source remains fenced. Production acceptance must also validate the real application queries, relationships, consumers and downstream services.

## 14. Select physical, full-oplog or managed DR alternatives

| Recovery source | Required additional contract |
|---|---|
| Full logical dump with oplog | Full supported capture/replay scope, privileged controlled replay identity; no namespace filters/remapping |
| Physical snapshot/files | Complete consistent data/journal set, matching runtime/options, encrypted-key handling and isolated topology reset |
| Ops Manager PITR | Valid snapshot/replay range, exact clean cutoff and verified delivery; Chapter 52 |
| Viable surviving member | Reviewed authority, acknowledged-history assessment and fencing; not an automatic forced reconfiguration |

Physical files can contain the old `local` topology/identity. Use the documented replica-set restore procedure on a writable isolated clone before adding fresh members. Do not start those files where they can contact the original set. Cipher-specific key rollover and startup options remain mandatory for encrypted recovery.

A restored application archive does not replace backup of users, roles, key vaults, encryption keys, configuration and infrastructure when those are in the real contract. Test their reconstruction/restore explicitly. Do not combine physical seeding, old topology metadata and a partial logical replay into an unreviewed recovery recipe.

## 15. Measure loss, cutover and failback correctly

For this drill, ID 101 was majority-acknowledged after capture and is absent on recovery. Record **one unrecovered acknowledged order, 1,010 cents**. Report recovery-point age separately using the verified capture boundary and incident reference; do not equate an acknowledged-operation count with temporal RPO.

RTO includes recovery provisioning, restore/index work, initial sync, key/credential access, secondary checks and application acceptance. A one-member primary or successful restore exit is an intermediate milestone. Use the incident and acceptance timestamps with Chapter 49's definitions; no real production endpoint cutover occurs here.

Before actual cutover, reverify the fence and approved recovered endpoint, stop/reconfigure all writer paths, transition secrets/connection strings, recycle stale pools as needed and observe the real application contract. Select owners and explicit rollback limits before new writes begin.

After recovery accepts writes, the old source is stale. Failback requires a planned migration/resync from the current authoritative deployment and application reconciliation. Reversing DNS to an old set would discard or diverge newer history. Preserve source evidence until the incident owner approves its decommissioning.

## 16. Acceptance, troubleshooting and owned cleanup

Acceptance requires verified capture, declared loss, source fencing, separate recovery identity, exact restored documents/metadata, healthy three-member topology, storage validation, both secondary observations and a scoped fresh application majority write/administrative rejection. Inspect logs and all evidence, not merely the last command's exit status.

| Failure | Investigate |
|---|---|
| Source not fenced | Restart policy, extra network/endpoint or orchestration path |
| Restore wrong/partial | Artifact integrity, scope, version and actual documents |
| Initial sync stalls | Disk space, trust/key, hostname resolution and oplog coverage |
| Majority write times out | Member health/commit progress and whether the write actually exists |
| Secondary marker absent | Replication progress and majority visibility; keep acceptance pending |
| Application admin access succeeds | Actual roles/user identity; repair grants before cutover |

For cleanup, first inspect every named container's chapter/run labels, data mounts and network against the owned workspace. Confirm both networks have no unrelated attachments. Capture logs and retain artifacts/evidence before removal.

```bash
test "$RUN54" = "$(cat evidence/run54.txt)"
for member54 in s-a s-b s-c r-a r-b r-c; do
  test "$(docker inspect --format '{{index .Config.Labels "chapter"}}' "mongodb-ch54-$member54")" = 54 || exit 1
  test "$(docker inspect --format '{{index .Config.Labels "run"}}' "mongodb-ch54-$member54")" = "$RUN54" || exit 1
  case "$member54" in s-*)
    test "$(docker inspect --format '{{.State.Running}}' "mongodb-ch54-$member54")" = false || exit 1 ;;
  esac
  docker inspect --format '{{json .Mounts}}' "mongodb-ch54-$member54"
  docker logs "mongodb-ch54-$member54" > "logs/$member54-final54.log" 2>&1
done
docker stop --time 120 mongodb-ch54-r-a mongodb-ch54-r-b mongodb-ch54-r-c
docker rm mongodb-ch54-s-a mongodb-ch54-s-b mongodb-ch54-s-c mongodb-ch54-r-a mongodb-ch54-r-b mongodb-ch54-r-c
docker network rm mongodb-ch54_source mongodb-ch54_recovery
```

Removal is authorized only for these inspected owned resources. Source containers should still be stopped; an unexpectedly running source stops cleanup and requires fence investigation. Docker removal leaves bind-mounted host data intact. Retain/delete only the explicit owned directories, artifacts and lab keys under the evidence/retention decision; no recursive wildcard deletion is supplied.

## 17. References and next chapter

- [MongoDB 8.0 restore a replica set from backup](https://www.mongodb.com/docs/v8.0/tutorial/restore-replica-set-from-backup/)
- [Replica-set synchronization and initial sync](https://www.mongodb.com/docs/v8.0/core/replica-set-sync/)
- [Replica-set keyfile authentication](https://www.mongodb.com/docs/v8.0/tutorial/deploy-replica-set-with-keyfile-access-control/)
- [Logical backup/restore consistency](https://www.mongodb.com/docs/v8.0/tutorial/backup-and-restore-tools/)
- [Previous: Chapter 53 — Accidental Delete and Drop Recovery](53-accidental-delete-and-drop-recovery.md)

Next: **[Chapter 55 — Sharded Cluster Backup and Disaster Recovery](55-sharded-cluster-backup-and-disaster-recovery.md)**.
