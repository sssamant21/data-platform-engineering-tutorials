# 51 — Consistent Snapshots and Restore Validation

Part 7 — Backup Recovery and Disaster Recovery

**Baseline:** MongoDB 8.0, WiredTiger, Linux Docker host and an approved pinned image.  
**Status:** Written; static review complete; live physical backup/restore validation pending.  
**Prerequisites:** Chapters 49–50, Python 3, OpenSSL and sufficient space for three complete data directories.

## 1. Define the physical recovery claim

This lab starts a fresh authenticated TLS standalone, creates a deterministic fixture, cleanly stops it and copies its complete data directory. It restarts the source, adds a post-backup document and restores the earlier files into a separate container. Verification checks the earlier document set, retained collection UUIDs, restored authentication, indexes, validators and storage validation results.

The executable baseline is a **cold physical copy**, not a live block-device snapshot. It demonstrates the consistency and isolated-restore contract without requiring privileged storage provisioning. Section 13 provides the separate live snapshot runbook for an approved storage platform.

Both containers use the same host and Docker network. This proves process/data-directory isolation, not regional or host-loss disaster recovery. The retained Chapter 35 and Chapter 41 deployments are untouched. Do not copy their live volumes or introduce an outage into those labs.

## 2. Choose the capture mechanism

| Method | Consistency boundary | Operational requirements |
|---|---|---|
| Cold complete copy | Successfully stopped database; files remain unmodified throughout copy | Outage and confirmed process exit |
| Supported volume snapshot | Documented atomic capture of the required storage set | Correct journal/data coverage, storage consistency and snapshot health |
| Locked live capture | Reviewed MongoDB flush/write-lock procedure around capture | Lock ownership, bounded write pause and unlock recovery |
| Enterprise hot backup | Supported storage-engine backup mechanism | Compatible Enterprise version, backup procedure and key handling |
| Managed backup | Platform's coordinated snapshot/replay chain | Healthy agents/stores and tested restore workflow |

Ordinary copying of changing WiredTiger files is not an atomic snapshot. A successful `cp` exit does not establish a valid live backup. Physical recovery requires the complete supported file set, compatible runtime and startup options; it does not support arbitrary namespace remapping as in Chapter 50.

## 3. Record the storage and security dependencies

Record data path, journal placement, storage engine, exact binary/image, FCV, topology, capture mechanism and encryption mode. Map each required volume to the snapshot/copy set. Include filesystem/volume identifiers for a storage snapshot and verify provider-specific multi-volume guarantees rather than assuming simultaneous command submission means atomicity.

| Dependency | Recovery handling |
|---|---|
| Complete `dbPath` including journal | Copy as one stopped, stable tree in this lab |
| Server binary and FCV | Use the exact source image digest and validate FCV |
| Authentication metadata | Physical copy includes it; restored admin credential must work |
| TLS configuration/trust/key | Separate protected recovery dependency; not inside this data archive |
| Storage encryption/KMS | Preserve required access/key versions; apply cipher-specific restore rules |
| Replica/shard topology | Use a dedicated topology recovery procedure; not this standalone recipe |

This lab deliberately uses an unencrypted Community-compatible WiredTiger data directory with TLS and authentication. Do not apply its startup command to encrypted Enterprise files. Chapter 45 covers encrypted recovery, including the special rollover procedure required for cold AES256-GCM restores. Plaintext physical artifacts can contain sensitive data and authentication metadata; protect them accordingly.

## 4. Create a fresh owned workspace and network

Run each step separately and stop on unexpected output. Do not paste the entire chapter as an unattended script. Use the approved exact MongoDB 8.0 image digest, not a floating tag.

```bash
umask 077
mkdir mongodb-ch51
cd mongodb-ch51
export LAB51_ROOT="$PWD"
mkdir source logs scripts evidence pki
export RUN51="$(python3 -c 'import uuid; print(uuid.uuid4())')"
printf '%s\n' "$RUN51" > evidence/run51.txt
test -n "${MONGO_IMAGE:?set an approved MongoDB 8.0 image digest}"
case "$MONGO_IMAGE" in
  *@sha256:*) ;;
  *) printf '%s\n' 'A digest-pinned image is required.' >&2; exit 1 ;;
esac
docker run --rm "$MONGO_IMAGE" mongod --version
docker network create --internal --label chapter=51 --label "run=$RUN51" mongodb-ch51_net
```

The fixed container/network names must be absent before creation. A name conflict is a stop condition, not permission to remove an unknown resource. Require enough free disk space for source, preserved backup and writable restore clone, plus logs and headroom. No host ports are published.

Save the scripts from Sections 7 and 10 before starting the data workflow. Store the image digest and host filesystem/capacity observations in protected evidence. The workspace marker is an ownership aid, not an authorization mechanism against another privileged host user.

## 5. Create a fresh lab CA and server certificate

This CA belongs only to Chapter 51. Its server certificate covers both container DNS names and local bootstrap access. Do not replace system trust or reuse production keys.

```bash
openssl req -x509 -newkey rsa:3072 -sha256 -nodes -days 30 \
  -keyout pki/ca.key -out pki/ca.crt -subj '/CN=Chapter51LabCA' \
  -addext 'basicConstraints=critical,CA:TRUE' \
  -addext 'keyUsage=critical,keyCertSign,cRLSign'
openssl req -new -newkey rsa:3072 -nodes \
  -keyout pki/server.key -out pki/server.csr -subj '/CN=source51'
cat > pki/server.ext <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:source51,DNS:restore51,DNS:localhost,IP:127.0.0.1
EOF
openssl x509 -req -in pki/server.csr -CA pki/ca.crt -CAkey pki/ca.key \
  -CAcreateserial -out pki/server.crt -days 14 -sha256 -extfile pki/server.ext
cat pki/server.crt pki/server.key > pki/server.pem
chmod 600 pki/ca.key pki/server.key pki/server.pem
mkdir pki/public pki/runtime
cp pki/ca.crt pki/public/ca.crt
cp pki/ca.crt pki/runtime/ca.crt
cp pki/server.pem pki/runtime/server.pem
chmod 644 pki/public/ca.crt pki/runtime/ca.crt
chmod 600 pki/runtime/server.pem
openssl verify -CAfile pki/public/ca.crt -verify_hostname source51 pki/server.crt
openssl verify -CAfile pki/public/ca.crt -verify_hostname restore51 pki/server.crt
```

Only `pki/runtime` goes to servers; only `pki/public` goes to ordinary clients. The CA private key stays on the host. Reusing the one server leaf for two disposable lab containers keeps this exercise small; production recovered endpoints need separately reviewed certificate/identity provisioning.

## 6. Start the source and bootstrap authentication

The container directly runs `mongod` as the host user, with no image initialization environment variables and no password in arguments. Files written into the bind-mounted data directory belong to that same user.

```bash
docker run -d --name mongodb-ch51-source --hostname source51 \
  --label chapter=51 --label "run=$RUN51" \
  --network mongodb-ch51_net --network-alias source51 \
  --user "$(id -u):$(id -g)" --entrypoint mongod \
  -v "$LAB51_ROOT/source:/data/db" \
  -v "$LAB51_ROOT/pki/runtime:/tls:ro" \
  -v "$LAB51_ROOT/scripts:/scripts:ro" "$MONGO_IMAGE" \
  --dbpath /data/db --auth --bind_ip_all --port 27017 \
  --wiredTigerCacheSizeGB 0.25 --tlsMode requireTLS \
  --tlsCertificateKeyFile /tls/server.pem --tlsCAFile /tls/ca.crt \
  --tlsAllowConnectionsWithoutCertificates
docker logs mongodb-ch51-source
```

Wait for the listener/startup milestone and investigate any exit/error. Save this as `scripts/bootstrap51.js`:

```javascript
const a = db.getSiblingDB('admin');
print('Create a fresh Chapter 51 administrator password.');
a.createUser({user: 'ch51_admin', pwd: passwordPrompt(),
  roles: [{role: 'root', db: 'admin'}]});
```

Use the localhost exception only for the first user in this brand-new instance:

```bash
docker exec -it mongodb-ch51-source mongosh 'mongodb://localhost:27017/admin' \
  --tls --tlsCAFile /tls/ca.crt --file /scripts/bootstrap51.js
```

Keep the secret in your approved secret store. If bootstrap fails or the username exists, inspect the fresh instance; do not disable authentication. A physical restore should recover this user's identity and credentials without creating another first user.

## 7. Implement deterministic storage validation

Save as `scripts/control51.js`. It owns only `mongodb_enterprise_tutorial_ch51`, checks standalone topology and requires MongoDB 8.0/FCV 8.0 for this exact baseline. Its restored authentication assertion compares the original user ID. Physical restoration should retain collection UUIDs.

```javascript
const fs = require('fs');
const crypto = require('crypto');
const a = db.getSiblingDB('admin');
const d = db.getSiblingDB('mongodb_enterprise_tutorial_ch51');
const action = process.env.ACTION51;
const target = process.env.TARGET51;
const stateFile = '/evidence/state51.json';
const base = Array.from({length: 100}, (_, i) => ({
  _id: i + 1, code: `order-${i + 1}`, amountCents: (i + 1) * 25}));
const later = {_id: 101, code: 'order-101', amountCents: 2525};
const validator = {$jsonSchema: {bsonType: 'object',
  required: ['_id', 'code', 'amountCents'], properties: {
    code: {bsonType: 'string'}, amountCents: {bsonType: 'number', minimum: 0}}}};
function check(value, message) { if (!value) throw new Error(message); }
function eq(x, y) { return EJSON.stringify(x, {relaxed: true}) ===
  EJSON.stringify(y, {relaxed: true}); }
function save(path, value) { fs.writeFileSync(path,
  EJSON.stringify(value, {relaxed: false}), {flag: 'wx', mode: 0o600}); }
function uuids() { return Object.fromEntries(d.getCollectionInfos().map(i =>
  [i.name, EJSON.stringify(i.info.uuid, {relaxed: false})])); }
function verify(state, post) {
  const info = d.getCollectionInfos();
  check(eq(info.map(i => i.name).sort(), ['marker', 'orders']), 'collection set changed');
  const marker = d.marker.findOne({_id: 'owner'});
  check(marker && marker.runId === state.runId && marker.chapter === 51 &&
    d.marker.countDocuments({}) === 1, 'ownership mismatch');
  const actualUUIDs = uuids();
  for (const n of ['marker', 'orders'])
    check(actualUUIDs[n] === state.uuids[n], 'physical UUID mismatch');
  const expected = post ? [...base, later] : base;
  const actual = d.orders.find().sort({_id: 1}).toArray();
  check(eq(actual, expected), 'document mismatch');
  const sum = actual.reduce((n, x) => n + x.amountCents, 0);
  check(sum === (post ? 128775 : 126250), 'business total mismatch');
  const indexes = d.orders.getIndexes();
  check(indexes.length === 2 && indexes.some(i => i.name === 'code_unique51'
    && i.unique === true && eq(i.key, {code: 1})), 'index mismatch');
  const options = info.find(i => i.name === 'orders').options;
  check(eq(options.validator, validator) && options.validationLevel === 'strict'
    && options.validationAction === 'error', 'validator mismatch');
  check(eq(a.getUser('ch51_admin').userId, state.adminUserId), 'admin identity mismatch');
  const validation = d.runCommand({validate: 'orders', full: true});
  check(validation.ok === 1 && validation.valid === true, 'storage validation failed');
  check(!validation.errors || validation.errors.length === 0, 'storage errors present');
  check(!validation.warnings || validation.warnings.length === 0,
    'review storage validation warnings before accepting');
  return {count: actual.length, amountCents: sum, uuids: actualUUIDs,
    storageValidation: validation, documentDigest: crypto.createHash('sha256')
      .update(EJSON.stringify(actual, {relaxed: false})).digest('hex')};
}
const hello = a.runCommand({hello: 1});
const build = a.runCommand({buildInfo: 1});
const fcv = a.runCommand({getParameter: 1, featureCompatibilityVersion: 1});
check(hello.ok === 1 && !hello.setName && hello.msg !== 'isdbgrid', 'standalone required');
check(build.ok === 1 && build.version.startsWith('8.0.') && fcv.ok === 1
  && fcv.featureCompatibilityVersion.version === '8.0', '8.0 stable baseline required');
check(target === 'source51' || target === 'restore51', 'unknown target');
if (action === 'setup') {
  check(target === 'source51' && !fs.existsSync(stateFile), 'fresh source/state required');
  check(d.getCollectionInfos().length === 0 && d.getUsers().users.length === 0
    && d.getRoles({showBuiltinRoles: false}).roles.length === 0, 'existing fixture objects');
  const runId = fs.readFileSync('/evidence/run51.txt', 'utf8').trim();
  check(/^[0-9a-f-]{36}$/.test(runId), 'run ID required');
  d.createCollection('orders', {validator, validationLevel: 'strict',
    validationAction: 'error'});
  d.createCollection('marker');
  d.orders.createIndex({code: 1}, {unique: true, name: 'code_unique51'});
  d.orders.insertMany(base, {writeConcern: {w: 1, j: true}});
  d.marker.insertOne({_id: 'owner', runId, chapter: 51},
    {writeConcern: {w: 1, j: true}});
  const state = {runId, uuids: uuids(), adminUserId: a.getUser('ch51_admin').userId,
    serverVersion: build.version, fcv: '8.0'};
  save(stateFile, state);
  save('/evidence/baseline51.json', {runId, observedAt: new Date(), result: verify(state, false)});
  print('Baseline: 100 orders, 126250 cents; storage valid.');
} else {
  const state = EJSON.parse(fs.readFileSync(stateFile, 'utf8'));
  check(build.version === state.serverVersion, 'exact server version changed');
  if (action === 'verify-base') {
    check(target === 'source51', 'source action required');
    printjson(verify(state, false));
  } else if (action === 'post-backup') {
    check(target === 'source51', 'source action required');
    verify(state, false);
    d.orders.insertOne(later, {writeConcern: {w: 1, j: true}});
    save('/evidence/source-later51.json', {runId: state.runId,
      observedAt: new Date(), result: verify(state, true)});
    print('Source now has 101 orders, 128775 cents.');
  } else if (action === 'verify-restore') {
    check(target === 'restore51', 'restore action required');
    const result = verify(state, false);
    for (const [doc, code] of [
      [{_id: 'negative-duplicate51', code: 'order-1', amountCents: 1}, 11000],
      [{_id: 'negative-validator51', code: 'negative-51', amountCents: -1}, 121]
    ]) {
      let denied = false;
      try { d.orders.insertOne(doc); }
      catch (error) { if (error.code !== code) throw error; denied = true; }
      check(denied, `expected rejection ${code}; inspect unexpected insert`);
    }
    verify(state, false);
    save('/evidence/restored51.json', {runId: state.runId, observedAt: new Date(),
      target, duplicateRejected: true, validatorRejected: true, result});
    print('Restored baseline, retained UUID/user identity and constraints verified.');
  } else throw new Error('unknown ACTION51');
}
```

`validate` is read-intensive and can affect availability; here it runs only on a tiny owned lab. A valid storage report does not replace business reconciliation. Any warning is a review stop, not permission to run repair. Failed setup can leave partial objects; inspect them rather than adopting an existing database.

## 8. Establish the baseline over a fresh TLS client

```bash
client51() {
  case "$TARGET51" in source51|restore51) ;; *) return 1 ;; esac
  docker run --rm -it --user "$(id -u):$(id -g)" \
    --network mongodb-ch51_net \
    -v "$LAB51_ROOT/pki/public:/trust:ro" \
    -v "$LAB51_ROOT/scripts:/scripts:ro" \
    -v "$LAB51_ROOT/evidence:/evidence" \
    --env ACTION51 --env TARGET51 "$MONGO_IMAGE" \
    mongosh "mongodb://$TARGET51:27017/admin" --tls --tlsCAFile /trust/ca.crt \
    --username ch51_admin --authenticationDatabase admin \
    --authenticationMechanism SCRAM-SHA-256 --password --file /scripts/control51.js
}
export TARGET51=source51
export ACTION51=setup
client51
export ACTION51=verify-base
client51
```

Save the exact image digest and selected Docker mount/network fields. Avoid dumping environments that might contain secrets. Confirm source data and journal are in the owned `source` tree and no second process mounts it for writing. Stop all chapter writers before capture.

## 9. Cleanly stop and confirm the source

```bash
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/stop-start51.txt
docker stop --time 120 mongodb-ch51-source
docker inspect --format '{{.State.Running}} {{.State.ExitCode}} {{.State.OOMKilled}}' mongodb-ch51-source
docker logs mongodb-ch51-source > logs/source-stopped51.log 2>&1
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/stop-end51.txt
```

Require `Running=false`, `ExitCode=0`, `OOMKilled=false` and a reviewed normal shutdown log. `docker stop` succeeding is insufficient if its timeout forced a kill. If clean exit cannot be established, do not label the copy a clean cold backup; investigate and repeat from a verified source. Keep the container stopped for the entire file-copy/sealing interval.

The 120-second stop timeout is an upper bound on a shutdown operation, not a sleep instruction. Allow the system enough time for the actual dataset; do not shorten production timeouts to make a drill look faster.

## 10. Copy and seal the complete stopped tree

Save as `scripts/tree51.py`. It rejects links/special files, requires a new destination, includes hidden files, records the exact file/directory set and verifies file hashes. Its copy command does not know whether MongoDB is stopped; Section 9's observations are a mandatory prerequisite.

```python
#!/usr/bin/env python3
import hashlib
import json
import pathlib
import shutil
import stat
import sys

def inventory(root):
    root = pathlib.Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('root must be a non-symlink directory')
    records = []
    for path in sorted(root.rglob('*')):
        info = path.lstat()
        relative = path.relative_to(root).as_posix()
        if stat.S_ISLNK(info.st_mode):
            raise ValueError('links are not accepted: ' + relative)
        if stat.S_ISDIR(info.st_mode):
            records.append({'path': relative, 'kind': 'directory'})
        elif stat.S_ISREG(info.st_mode):
            digest = hashlib.sha256()
            size = 0
            with path.open('rb') as source:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    digest.update(block)
                    size += len(block)
            records.append({'path': relative, 'kind': 'file',
                            'bytes': size, 'sha256': digest.hexdigest()})
        else:
            raise ValueError('special file rejected: ' + relative)
    if not records:
        raise ValueError('empty data tree')
    return {'format': 1, 'entries': records}

def main():
    try:
        if len(sys.argv) != 4 or sys.argv[1] not in ('copy', 'seal', 'verify'):
            raise ValueError('usage: tree51.py copy SRC NEW_DST | seal|verify DATA MANIFEST')
        action, first, second = sys.argv[1:]
        root = pathlib.Path(first)
        other = pathlib.Path(second)
        actual = inventory(root)
        if action == 'copy':
            if other.exists() or other.is_symlink():
                raise ValueError('destination already exists')
            if root.resolve() == other.resolve() or root.resolve() in other.resolve().parents:
                raise ValueError('destination must be outside source tree')
            shutil.copytree(root, other, copy_function=shutil.copy2)
            if inventory(other) != actual:
                raise ValueError('copied tree mismatch')
        elif action == 'seal':
            if root.resolve() in other.resolve().parents:
                raise ValueError('manifest must be outside data tree')
            with other.open('x', encoding='utf-8') as output:
                json.dump(actual, output, indent=2)
        else:
            if other.is_symlink() or not other.is_file():
                raise ValueError('manifest must be a regular non-symlink file')
            expected = json.loads(other.read_text(encoding='utf-8'))
            if expected != actual:
                raise ValueError('tree integrity mismatch')
        print('tree operation passed; MongoDB consistency requires separate evidence')
        return 0
    except (OSError, ValueError, TypeError, shutil.Error) as error:
        print(str(error), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
```

```bash
test "$(docker inspect --format '{{.State.Running}}' mongodb-ch51-source)" = false
test "$(docker inspect --format '{{.State.ExitCode}}' mongodb-ch51-source)" = 0
python3 scripts/tree51.py copy source backup51
python3 scripts/tree51.py seal backup51 evidence/backup51-manifest.json
python3 scripts/tree51.py verify backup51 evidence/backup51-manifest.json
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/backup-complete51.txt
```

The helper copies all regular files; it does not cherry-pick `.wt` files or discard journals/catalog files. It preserves file metadata through `copy2` on this same-user host. Production restore also requires reviewed ownership, permissions, ACLs and filesystem properties.

The hash manifest detects accidental changes to this preserved tree. It is not a signature and cannot defend against rewriting both manifest and backup. Protect the preserved backup from modification and keep a separately protected integrity record. Do not mount `backup51` as a running server's writable data path.

## 11. Restart the source and create a post-backup witness

```bash
docker start mongodb-ch51-source
docker logs mongodb-ch51-source
export TARGET51=source51
export ACTION51=post-backup
client51
```

Wait for normal startup first. The controller verifies the old baseline before inserting order 101. Source now has **101 orders**, totaling **128,775 cents**. The preserved backup should still represent 100 orders/126,250 cents. This witness proves that the later write is outside the captured state; do not overwrite the backup after this step.

## 12. Restore from a writable clone and validate

```bash
python3 scripts/tree51.py verify backup51 evidence/backup51-manifest.json
python3 scripts/tree51.py copy backup51 restore51
python3 scripts/tree51.py verify restore51 evidence/backup51-manifest.json
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/restore-start51.txt
docker run -d --name mongodb-ch51-restore --hostname restore51 \
  --label chapter=51 --label "run=$RUN51" \
  --network mongodb-ch51_net --network-alias restore51 \
  --user "$(id -u):$(id -g)" --entrypoint mongod \
  -v "$LAB51_ROOT/restore51:/data/db" \
  -v "$LAB51_ROOT/pki/runtime:/tls:ro" "$MONGO_IMAGE" \
  --dbpath /data/db --auth --bind_ip_all --port 27017 \
  --wiredTigerCacheSizeGB 0.25 --tlsMode requireTLS \
  --tlsCertificateKeyFile /tls/server.pem --tlsCAFile /tls/ca.crt \
  --tlsAllowConnectionsWithoutCertificates
docker logs mongodb-ch51-restore
export TARGET51=restore51
export ACTION51=verify-restore
client51
date -u +'%Y-%m-%dT%H:%M:%SZ' > evidence/restore-accepted51.txt
python3 scripts/tree51.py verify backup51 evidence/backup51-manifest.json
```

Require normal startup, then authenticate using the original administrator password. Inspect `restored51.json`: the exact original 100 documents, 126,250 cents, retained UUIDs and admin user ID, valid storage report and both constraint rejections. Compare its document digest with the baseline. Order 101 must be absent here while present on source.

Startup changes files in the writable restore clone. Consequently, its bytes need not match the original manifest after startup. Recheck the **preserved backup**, not the running clone, to prove restore did not mutate your recovery artifact.

Do not remove lock/journal/catalog files or run `--repair` to force a failed restore to start. Preserve logs, confirm the capture was clean and complete, and repeat with a fresh clone after correcting the cause. This cold baseline avoids the extra stale-lock handling that a live locked snapshot may require under its documented restore procedure.

## 13. Apply the contract to live storage snapshots

This is an operational adapter for a separate approved disposable storage lab. It is not permission to snapshot or lock an existing production server. Use the platform's tested commands and exact volume IDs rather than guessing `/dev` names from examples.

1. Inventory every data/journal volume and the storage engine. Establish the supported atomic-consistency mechanism. Where the procedure requires it, flush and lock the database before capture.
2. Record the lock result/count, target process identity and capture start. Confirm independent access to unlock and monitor the allowed write-pause budget.
3. Invoke the approved storage snapshot operation for the complete volume set. Determine when the provider has established the immutable capture point, as distinct from finishing asynchronous transfer.
4. Release only the lock acquired by this operation, confirm write availability and record capture IDs/times. If the state or capture outcome is uncertain, release the owned lock safely and mark the backup unusable pending investigation.
5. Verify snapshot health and copy/retain it in the required independent fault domain. Restore through a new writable volume and isolated compatible server, then perform the same data/application acceptance checks.

For an owned standalone, the MongoDB lock commands are:

```javascript
// Run only inside the separately reviewed snapshot window.
const a = db.getSiblingDB('admin');
const result = a.fsyncLock();
printjson(result);
// Capture the complete supported storage set using its approved storage tool.
// Release the lock acquired above from independent administrator access:
printjson(a.fsyncUnlock());
```

Do not execute this block as an unattended script: capture must happen between the two commands. Locks are counted; disconnecting a shell is not an unlock procedure. Do not blindly unlock another operator's lock or assume an election preserves your consistency boundary. If topology changes invalidate capture, discard that attempt and restart the reviewed procedure.

For copy-on-write storage snapshots, monitor changed-block capacity until the snapshot is safely archived. Snapshot creation speed is not restore speed, and a snapshot residing only beside its source can share the same failure domain. Follow filesystem-specific mount/recovery instructions; a read-only mount option alone may not prevent all filesystem journal-recovery behavior.

## 14. Extend validation for replica sets, shards and encryption

| Target | Additional recovery contract |
|---|---|
| Replica set member replacement | Exact member identity, supported reseed/rejoin process and catch-up; Chapter 30 |
| Entire replica set recovery | Controlled isolation, restore topology and acknowledged-write reconciliation; Chapter 54 |
| Sharded cluster | Coordinated shard/config-server metadata and consistency; Chapter 55 |
| Encrypted storage | Matching key/KMS access, cipher-specific startup and key-rollover rules; Chapter 45 |
| Field encryption | Key-vault/KMS/application dependencies and supported backup method; Chapter 46 |

Do not start a copied replica-set data directory where it can contact the original cluster by accident. Restored files can retain identity and topology metadata. Do not treat a single shard's snapshot as a full cluster recovery. Copying TLS keys into a backup does not replace a key-management policy.

Test application-visible behavior: namespace/object inventory, document reconciliation, index definitions, validators, reference integrity and selected queries. Storage validation and a healthy listener are necessary observations, but neither alone establishes a usable application recovery.

## 15. Measure recovery and diagnose failures

Use Chapter 49's declared incident/cutoff/acceptance definitions. Cold capture includes an explicit source outage; record shutdown, copy/seal and restart intervals separately. Restore acceptance includes provisioning, clone creation, startup, credential/TLS access, storage checks and application validation. Do not report container startup time alone as RTO.

| Failure | Investigate before retry |
|---|---|
| Source exit nonzero/OOM/forced kill | Shutdown evidence and source health; repeat clean capture |
| Manifest mismatch | Missing, extra or modified files; preserve failed evidence |
| Permission denied on startup | Host UID/GID, mount permissions and approved filesystem policy |
| TLS/authentication failure | Valid trust/name, certificate dates and recovered credential identity |
| WiredTiger recovery/catalog error | Complete consistent capture, version and storage compatibility |
| UUID/documents differ | Wrong backup/target, later writes or incomplete recovery |
| Storage valid but business totals fail | Logical corruption, missing operations or incorrect cutoff |

Keep the original artifact immutable throughout investigation. Never diagnose by starting the backup directory directly. A deliberately truncated file can be used for an integrity negative test on a separate copy, but there is no need to feed known corrupt files to `mongod` to demonstrate checksum rejection.

## 16. Acceptance and owned resource cleanup

Accept this cold-copy lab only after clean shutdown evidence, complete sealed tree, unchanged preserved backup, isolated restored process, original credential/UUIDs, exact baseline documents, valid storage and constraint rejection have all been observed. The live-volume snapshot procedure remains a separate validation item until exercised on the actual storage platform.

Before cleanup, verify labels and mounts for both named containers and the network against `evidence/run51.txt`. A mismatch stops cleanup. Retain the logs and evidence first.

```bash
test "$RUN51" = "$(cat evidence/run51.txt)"
for container51 in mongodb-ch51-source mongodb-ch51-restore; do
  test "$(docker inspect --format '{{index .Config.Labels "chapter"}}' "$container51")" = 51 || exit 1
  test "$(docker inspect --format '{{index .Config.Labels "run"}}' "$container51")" = "$RUN51" || exit 1
  docker inspect --format '{{json .Mounts}}' "$container51"
done
test "$(docker network inspect --format '{{index .Labels "run"}}' mongodb-ch51_net)" = "$RUN51"
docker logs mongodb-ch51-source > logs/source-final51.log 2>&1
docker logs mongodb-ch51-restore > logs/restore-final51.log 2>&1
docker stop --time 120 mongodb-ch51-source mongodb-ch51-restore
docker rm mongodb-ch51-source mongodb-ch51-restore
docker network rm mongodb-ch51_net
```

Execute removal only after the displayed mounts match the owned source/restore paths and no unrelated network attachments exist. Docker removal does not delete the host bind directories. Retain or delete those exact owned directories under the agreed evidence/backup/key retention decision; no recursive wildcard deletion command is supplied.

Never delete retained encryption keys or actual production snapshots as tutorial cleanup. Runtime validation remains pending until the learner completes this procedure; local syntax/helper checks cannot establish MongoDB consistency.

## 17. References and next chapter

- [MongoDB 8.0 filesystem snapshot backup and restore](https://www.mongodb.com/docs/v8.0/tutorial/backup-with-filesystem-snapshots/)
- [MongoDB 8.0 backup methods](https://www.mongodb.com/docs/v8.0/core/backups/)
- [fsyncLock behavior and lock counts](https://www.mongodb.com/docs/v8.0/reference/method/db.fsynclock/)
- [Previous: Chapter 50 — mongodump mongorestore and Logical Recovery](50-mongodump-mongorestore-and-logical-recovery.md)

Next: [**Chapter 52 — Ops Manager Backup and Point in Time Recovery**](52-ops-manager-backup-and-point-in-time-recovery.md).
