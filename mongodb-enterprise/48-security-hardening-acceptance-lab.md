# 48 — Security Hardening Acceptance Lab

Part 6 — Enterprise Security and Governance

**Baseline:** MongoDB 8.0; retained authenticated TLS/SCRAM standalone from Chapters 41–43 for the baseline lab.  
**Status:** Written; static review complete; live security acceptance pending.  
**Prerequisites:** Chapters 41–47, independent administrator access, owned disposable fixtures and a protected evidence workspace.

## 1. Define the acceptance claim before testing

Security acceptance combines effective configuration, observed positive behavior, observed rejection and recovery. A configuration file, installed Enterprise binary or successful administrator login is insufficient alone.

This chapter creates a new scoped fixture, verifies the retained server's baseline, rotates its application credential, and assembles a reviewable evidence ledger. Optional Enterprise controls must be tested on the deployment being accepted. The result is an evidence-completeness assessment for a stated scope, not a compliance certification or a universal production-readiness declaration.

Never transfer a passed test between targets. Chapter 44's audit standalone, Chapter 45's encrypted standalone and Chapter 46's encrypted-field replica set are separate deployments. Their evidence supports those exercises; it does not prove that `mongodb-ch41` has Enterprise auditing or encrypted storage.

## 2. Select a profile and accountable target

| Profile | Required controls | Intended claim |
|---|---|---|
| `tls-scram` | Inventory, network, TLS, TLS rejection, authentication, authorization, rotation, access review, recovery and cleanup | Retained standalone baseline lab evidence complete |
| `enterprise-security` | All baseline controls plus Enterprise module, audit, encrypted storage and field encryption | Full selected-control evidence on one authorized deployment |

For `enterprise-security`, provision a compatible Enterprise replica-set lab if QE is selected; the Chapter 45 standalone cannot meet QE topology requirements. Repeat baseline controls on that same deployment with reviewed target-specific connection procedures. Do not change the retained Community image or reuse its plaintext data directory to satisfy the profile.

If your deployment's actual policy differs—for example, OIDC, x509-only clients, managed volume encryption instead of the native storage engine, or a shared production service—create a reviewed target-specific acceptance plan. The fixed teaching profiles below do not automatically authorize exemptions or pretend those designs failed simply because they differ.

Record target ID, topology, environment, owner, change reference, exact versions/FCV, selected profile, test window, expected application contract and rollback. Each target gets a separate run ID and ledger.

## 3. Required observations and failure layers

| Control | Positive observation | Negative/recovery observation |
|---|---|---|
| Network | Intended private lab path reaches the server | No published host ports; actual listener/network scope reviewed |
| TLS | Valid CA and name connect | Plaintext, unrelated CA and resolvable wrong name rejected |
| Authentication | Intended user authenticates on its auth database | Wrong password fails; anonymous protected read denied |
| Authorization | Reader sees exact known rows | Reader insert fails with code 13; data remains unchanged |
| Rotation | Fresh new-secret process works | Fresh prior-secret process fails; roles/user ID unchanged |
| Access review | Expanded grants match intended fixture role | Unapproved inherited grants and privileged identities reviewed |
| Recovery | Independent admin works before/after changes | Known-good TLS configuration/custody and restart path reviewed |
| Audit | Selected events actually captured | Coverage gaps, rotation and destination recovery checked |
| Encrypted storage | Effective setting and readable encrypted restart | Wrong-key restore fails; correct-key restore verified |
| Field encryption | Raw protected values are ciphertext; approved query/decrypt works | Wrong-key/KMS identity fails; fresh authorized recovery works |

A DNS error does not prove hostname validation. A TLS error does not prove failed SCRAM authentication. An authorization event does not prove transaction commit. Keep the actual failure layer in each test record.

## 4. Establish a fresh evidence workspace

Create a new workspace beside the retained `mongodb-ch41` directory:

```bash
umask 077
mkdir mongodb-ch48
cd mongodb-ch48
mkdir scripts evidence
export LAB48_ROOT="$PWD"
export TLS48_ROOT='/absolute/path/to/mongodb-ch41'
test -n "${MONGO_IMAGE:?use the exact pinned Chapter 41 image}"
test -f "$TLS48_ROOT/pki/public/ca.crt"
```

Use the retained Docker network `mongodb-ch41_security41`, server name `mongo41` and administrator `ch41_bootstrap` in `admin`. The current public CA must still be valid. Keep the CA private key and server private key out of client/evidence mounts.

**Before Section 5**, copy `scripts/ledger48.py` from Section 13 and execute its initialization commands once. It creates a manifest and a ledger whose controls all start `not_run`. The run must begin before its observations. No result is inferred from earlier chapters or generated configuration.

## 5. Capture the actual process and network baseline

Inspect selected Docker fields, avoiding container environment output that could contain secrets:

```bash
docker inspect --format '{{.Id}} {{.Image}}' mongodb-ch41
docker inspect --format '{{json .NetworkSettings.Ports}}' mongodb-ch41
docker network inspect --format '{{.Name}} internal={{.Internal}}' mongodb-ch41_security41
docker inspect --format '{{json .NetworkSettings.Networks}}' mongodb-ch41
```

Record the process/container identity, image digest, networks, published-port mapping and aliases in protected evidence. A mapping with null published bindings is different from a host-published listener. Verify this against the retained compose configuration and the actual host listener/firewall scope.

The baseline expects the internal network and no published host ports. Container `bindIpAll` can be consistent with that isolated teaching scope; the surrounding network boundary matters. It is not permission to expose a production listener broadly. Review unexpected attached networks or published bindings before continuing.

Identify a known-good TLS configuration backup from Chapter 42 and the independent administrator recovery procedure. Do not use the pre-TLS/plaintext configuration as the normal recovery target.

## 6. Define fresh clients and guarded fixtures

Every wrapper invocation creates a fresh client. Save outputs privately without logging passwords. The mounted evidence directory lets the administrator script save normalized facts.

```bash
export ACTION48='inventory'
admin48() {
  docker run --rm -it --user "$(id -u):$(id -g)" \
    --network mongodb-ch41_security41 \
    -v "$TLS48_ROOT/pki/public:/trust:ro" \
    -v "$LAB48_ROOT/scripts:/scripts:ro" \
    -v "$LAB48_ROOT/evidence:/evidence" \
    --env ACTION48 "$MONGO_IMAGE" \
    mongosh 'mongodb://mongo41:27017/admin' --tls --tlsCAFile /trust/ca.crt \
    --username ch41_bootstrap --authenticationDatabase admin \
    --authenticationMechanism SCRAM-SHA-256 --password "$@"
}
reader48() {
  docker run --rm -it --network mongodb-ch41_security41 \
    -v "$TLS48_ROOT/pki/public:/trust:ro" \
    -v "$LAB48_ROOT/scripts:/scripts:ro" "$MONGO_IMAGE" \
    mongosh 'mongodb://mongo41:27017/mongodb_enterprise_tutorial_ch48' \
    --tls --tlsCAFile /trust/ca.crt --username ch48_reader \
    --authenticationDatabase mongodb_enterprise_tutorial_ch48 \
    --authenticationMechanism SCRAM-SHA-256 --password "$@"
}
```

Save `scripts/admin48.js`:

```javascript
const fs48 = require('fs');
const lab48 = db.getSiblingDB('mongodb_enterprise_tutorial_ch48');
const database48 = lab48.getName();
const owner48 = 'chapter48-security-acceptance';
const role48 = 'ch48_find_records';
const action48 = process.env.ACTION48;
const canon48 = value => EJSON.stringify(value);
const check48 = (condition, message) => { if (!condition) throw new Error(message); };
const write48 = (name, value) => fs48.writeFileSync('/evidence/' + name,
  EJSON.stringify(value), {flag: 'wx', mode: 0o600});
check48(['inventory', 'setup', 'review', 'rotate', 'cleanup'].includes(action48), 'Unknown action');
const build48 = db.adminCommand({buildInfo: 1});
const options48 = db.adminCommand({getCmdLineOpts: 1});
check48(build48.ok === 1 && /^8\.0\./.test(build48.version), 'Version review required');
check48(options48.ok === 1 && options48.parsed.net?.tls?.mode === 'requireTLS' &&
  options48.parsed.security?.authorization === 'enabled', 'TLS/auth policy required');
if (action48 === 'inventory') {
  write48('server-inventory.json', {serverVersion: build48.version, modules: build48.modules,
    tlsMode: options48.parsed.net.tls.mode, authorization: options48.parsed.security.authorization,
    observedAt: new Date()});
  print('Current process TLS/auth inventory saved; no secret-bearing options exported');
} else if (action48 === 'setup') {
  check48(lab48.getCollectionInfos().length === 0 && lab48.getUsers().users.length === 0 &&
    lab48.getRoles({showBuiltinRoles: false}).roles.length === 0, 'Nonempty fixture refused');
  check48(!fs48.existsSync('/evidence/fixture-state.json'), 'Existing state refused');
  lab48.createCollection('records');
  lab48.records.insertMany([{_id: 's1', owner: owner48, value: 11},
    {_id: 's2', owner: owner48, value: 22}]);
  lab48.createRole({role: role48, roles: [], privileges: [
    {resource: {db: database48, collection: 'records'}, actions: ['find']}
  ]});
  print('Choose a unique initial fixture-reader password:');
  lab48.createUser({user: 'ch48_reader', pwd: passwordPrompt(),
    mechanisms: ['SCRAM-SHA-256'], roles: [{role: role48, db: database48}],
    customData: {owner: owner48, revision: 'initial'}});
  write48('fixture-state.json', {owner: owner48, database: database48,
    userId: lab48.getUser('ch48_reader').userId,
    collectionUUID: lab48.getCollectionInfos({name: 'records'})[0].info.uuid});
  print('Scoped owned reader fixture created');
} else {
  const state48 = EJSON.parse(fs48.readFileSync('/evidence/fixture-state.json', 'utf8'));
  check48(state48.owner === owner48 && state48.database === database48, 'State mismatch');
  const user48 = lab48.getUser('ch48_reader', {showPrivileges: true});
  const collections48 = lab48.getCollectionInfos();
  check48(user48 && user48.customData?.owner === owner48 &&
    canon48(user48.userId) === canon48(state48.userId), 'User ownership mismatch');
  check48(collections48.length === 1 && collections48[0].name === 'records' &&
    canon48(collections48[0].info.uuid) === canon48(state48.collectionUUID), 'Collection ownership mismatch');
  const privileges48 = [{resource: {db: database48, collection: 'records'}, actions: ['find']}];
  const roleInfo48 = lab48.getRole(role48, {showPrivileges: true});
  check48(roleInfo48 && roleInfo48.roles.length === 0 &&
    canon48(roleInfo48.privileges) === canon48(privileges48), 'Role privilege mismatch');
  check48(canon48(user48.roles) === canon48([{role: role48, db: database48}]) &&
    canon48(user48.inheritedPrivileges) === canon48(privileges48), 'Expanded user access mismatch');
  const rows48 = lab48.records.find({}).sort({_id: 1}).toArray();
  check48(rows48.length === 2 && rows48[0]._id === 's1' && rows48[1]._id === 's2' &&
    rows48[0].value === 11 && rows48[1].value === 22 &&
    rows48.every(row => row.owner === owner48), 'Fixture data changed');
  if (action48 === 'review') {
    write48('fixture-access-review.json', {user: user48.user, db: user48.db,
      roles: user48.roles, inheritedPrivileges: user48.inheritedPrivileges,
      mechanisms: user48.mechanisms, fixtureContentVerified: true, observedAt: new Date()});
    print('Exact fixture grants and unchanged data verified');
  } else if (action48 === 'rotate') {
    check48(user48.customData.revision === 'initial', 'Already rotated; inspect actual state');
    print('Choose a different new fixture-reader password:');
    lab48.updateUser('ch48_reader', {pwd: passwordPrompt(),
      customData: {...user48.customData, revision: 'rotated'}});
    const after48 = lab48.getUser('ch48_reader');
    check48(canon48(after48.userId) === canon48(state48.userId) &&
      canon48(after48.roles) === canon48(user48.roles), 'Rotation changed identity/roles');
    write48('rotation-confirmation.json', {userIdPreserved: true, rolesPreserved: true,
      observedAt: new Date(), freshClientAcceptance: 'still required'});
    print('Database password updated; test prior/new credentials through fresh clients');
  } else if (action48 === 'cleanup') {
    check48(user48.customData.revision === 'rotated', 'Complete rotation before normal cleanup');
    check48(lab48.getUsers().users.length === 1 &&
      lab48.getRoles({showBuiltinRoles: false}).roles.length === 1, 'Unexpected identities/roles');
    check48(lab48.dropUser('ch48_reader'), 'Reader removal failed');
    check48(lab48.dropRole(role48), 'Role removal failed');
    check48(lab48.records.drop(), 'Collection removal failed');
    check48(lab48.getUsers().users.length === 0 && lab48.getCollectionInfos().length === 0 &&
      lab48.getRoles({showBuiltinRoles: false}).roles.length === 0, 'Cleanup verification failed');
    write48('cleanup-confirmation.json', {ownedFixtureRemoved: true, observedAt: new Date()});
    fs48.renameSync('/evidence/fixture-state.json', '/evidence/fixture-state.disposed.json');
    print('Owned acceptance fixture removed; independent administrator/TLS retained');
  }
}
```

Stop on a failed guard or partial operation. MongoDB changes and evidence-file writes are not atomic together. Inspect actual state and saved identifiers before recovering; do not remove guard checks or overwrite an existing evidence file to hide a failure.

## 7. Verify positive TLS and protected-data behavior

```bash
export ACTION48='inventory'
admin48 --quiet --file /scripts/admin48.js
export ACTION48='setup'
admin48 --quiet --file /scripts/admin48.js
```

Save `scripts/reader48.js`:

```javascript
const lab48 = db.getSiblingDB('mongodb_enterprise_tutorial_ch48');
const rows48 = lab48.records.find({}).sort({_id: 1}).toArray();
if (rows48.length !== 2 || rows48[0]._id !== 's1' || rows48[1]._id !== 's2' ||
    rows48[0].value !== 11 || rows48[1].value !== 22) throw new Error('Unexpected reader content');
const denial48 = lab48.runCommand({insert: 'records', documents: [
  {_id: 'forbidden48', owner: 'chapter48-security-acceptance', value: 99}
]});
if (denial48.ok !== 0 || denial48.code !== 13) throw new Error('Expected denied insert code 13');
print(EJSON.stringify({fixtureReads: 2, insertDeniedCode: 13, observedAt: new Date()}));
```

```bash
reader48 --quiet --file /scripts/reader48.js
```

Require exactly the known rows and code `13`. The administrator's review action independently checks unchanged fixture content. Retain normalized outcomes and timestamps, not the prompted password.

## 8. Verify TLS rejection without exposing credentials

For each attempt, record start/end, client exit status and actual failure layer. Do not supply credentials over the deliberately plaintext connection.

**Plaintext control:**

```bash
docker run --rm --network mongodb-ch41_security41 "$MONGO_IMAGE" \
  mongosh 'mongodb://mongo41:27017/admin?serverSelectionTimeoutMS=5000' \
  --quiet --eval 'db.runCommand({ping: 1})'
```

Require nonzero exit caused by the server's TLS requirement; confirm the valid TLS control still works afterward.

**Unrelated-CA control:** generate a fresh public trust anchor solely for this negative test. Keep its private key local and never mount it into the client:

```bash
mkdir negative-ca
openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
  -keyout negative-ca/ca.key -out negative-ca/ca.crt \
  -subj '/CN=Chapter48UnrelatedCA' \
  -addext 'basicConstraints=critical,CA:TRUE'
chmod 600 negative-ca/ca.key
chmod 644 negative-ca/ca.crt
docker run --rm --network mongodb-ch41_security41 \
  -v "$PWD/negative-ca/ca.crt:/trust/unrelated.crt:ro" "$MONGO_IMAGE" \
  mongosh 'mongodb://mongo41:27017/admin?serverSelectionTimeoutMS=5000' \
  --tls --tlsCAFile /trust/unrelated.crt --quiet --eval 'db.runCommand({ping: 1})'
```

Require a certificate trust failure, not inability to read the mounted file.

**Wrong-name control:** Chapter 42 configured the alias `wrongname42`, which is intentionally absent from the server certificate. Confirm the actual retained network has that alias and it resolves to the intended container before testing:

```bash
docker run --rm --network mongodb-ch41_security41 "$MONGO_IMAGE" \
  mongosh --nodb --quiet --eval 'print(await require("dns").promises.lookup("wrongname42"))'
docker run --rm --network mongodb-ch41_security41 \
  -v "$TLS48_ROOT/pki/public:/trust:ro" "$MONGO_IMAGE" \
  mongosh 'mongodb://wrongname42:27017/admin?serverSelectionTimeoutMS=5000' \
  --tls --tlsCAFile /trust/ca.crt --quiet --eval 'db.runCommand({ping: 1})'
```

Require hostname-validation failure. If the alias is absent or resolves incorrectly, this control is blocked; a DNS error does not count. Never add `tlsAllowInvalidHostnames`, `tlsAllowInvalidCertificates` or `tlsInsecure` to turn a failed acceptance control green.

## 9. Verify authentication and exact authorization

Repeat `reader48` with an intentionally wrong password at its prompt. Require fresh database authentication failure and a nonzero exit. Distinguish it from the TLS rejection controls.

For anonymous access, keep valid TLS but omit a username and query the protected collection:

```bash
docker run --rm --network mongodb-ch41_security41 \
  -v "$TLS48_ROOT/pki/public:/trust:ro" "$MONGO_IMAGE" \
  mongosh 'mongodb://mongo41:27017/mongodb_enterprise_tutorial_ch48' \
  --tls --tlsCAFile /trust/ca.crt --quiet --eval \
  'const r=db.runCommand({find:"records",filter:{}}); if(r.ok!==0||r.code!==13) throw new Error("Expected anonymous denial"); print("Anonymous protected read denied with code 13")'
```

This script exits successfully **only when the denial assertion passes**. The wrong-password/TLS commands instead should exit unsuccessfully. Do not apply a universal “nonzero means secure” rule to every test.

After these negative controls, run the valid reader contract again. Then perform administrator review to check exact role inheritance and unchanged data:

```bash
reader48 --quiet --file /scripts/reader48.js
export ACTION48='review'
admin48 --quiet --file /scripts/admin48.js
```

The fixture review is not a deployment-wide access review. Use Chapter 47's full identity/provider/role scope to review retained administrators and other principals, including users defined in other authentication databases.

## 10. Rotate and verify an independent recovery path

```bash
export ACTION48='rotate'
admin48 --quiet --file /scripts/admin48.js
reader48 --quiet --file /scripts/reader48.js
```

For the first reader attempt, enter the prior password. Require fresh authentication rejection. Run it again with the new password and require the same known reads and denied write.

```bash
reader48 --quiet --file /scripts/reader48.js
admin48 --quiet --eval 'db.runCommand({ping: 1})'
```

Record unchanged user ID/direct roles from the rotation artifact, prior-secret failure, new-secret behavior and independent administrator success. Keep new secret custody separate from evidence. The fresh wrappers do not simulate a real fleet rollout; production acceptance also needs pool, worker, scheduled-job and secret-version convergence from Chapter 47.

For this teaching recovery control, verify the independent administrator before and after rotation and review the known-good TLS restore/restart procedure. Do not alter the retained server configuration solely to create an outage. If restart/recovery is required by the deployment change, perform a separately scoped drill and include its actual outcomes, not an inferred pass from the existence of a backup file.

## 11. Accept Enterprise audit and encryption on their actual target

The `enterprise-security` profile is incomplete until all selected controls pass on its own declared target. Do not mark a control `passed` because an Enterprise option appears in a template or because another lab had a successful run.

| Control | Reuse the procedure | Target-specific evidence |
|---|---|---|
| Enterprise module | Chapters 43–45 inventory gates | Running binary modules/version, source and entitlement |
| Audit | Chapter 44 | Effective filter/schema, authentication/authorization/user events, closed rotated logs and coverage analysis |
| Storage encryption | Chapter 45 | Fresh/migrated encrypted target, original-key restart, wrong-key and correct-key restore, key-custody references |
| Field encryption | Chapter 46 | Supported topology/client/library, raw ciphertext, intended queries, wrong-key/KMS denial and fresh authorized recovery |

Server storage encryption does not encrypt audit logs or logical exports automatically. Field encryption does not remove the need for TLS, authorization, KMS policy or application redaction. Key retention must account for historical backups after rotation.

The baseline Community target can complete `tls-scram` while the Enterprise profile remains blocked on missing capability. That is a narrower accepted scope, not Enterprise security acceptance. If all these controls are required by your actual production policy, a missing gate blocks that policy's acceptance.

## 12. Review host, provider and operational boundaries

The compact executable controls are necessary but not a complete host/cloud/application security assessment. Record additional deployment requirements and review them explicitly:

| Boundary | Required review |
|---|---|
| Host/container | Process identity, private-file modes, image provenance, mount access, core/swap and patch policy |
| Network | Approved source paths, listener/published-port scope, firewall/security-group/network-policy enforcement |
| Identity provider | Issuer/trust, groups/claims, token/ticket renewal, stale mapping and leaver revocation |
| Secrets/KMS | Scoped workloads, source/version custody, denied identities and key retrieval after cold restart |
| Evidence/telemetry | Protected storage, redaction, collector lag, retention and access audit |
| Backup | Restore plus key dependencies, consistency point, tested RPO/RTO and retention obligations |
| Change handling | Owner, test window, rollback boundary, exceptions, monitoring and incident response |

Do not introduce blanket log redaction or disable diagnostics without measuring its operational impact. Preserve enough safe metadata to investigate authentication, latency, audit-path and KMS failures.

## 13. Build a ledger that does not manufacture passes

Save `scripts/ledger48.py`. It initializes a manifest/ledger, validates required controls, binds referenced artifacts by SHA-256, rejects wrong target/run, stale/future timestamps, missing/failed controls, unsafe evidence paths and altered artifacts. It checks evidence structure and declared assertions; humans must still verify the source observations and approval.

```python
import datetime
import hashlib
import json
import pathlib
import re
import sys
import uuid

BASE = {
    'inventory': ['exactVersionRecorded', 'authorizationEnabled', 'tlsRequired'],
    'network': ['internalNetwork', 'noPublishedPorts', 'listenerScopeReviewed'],
    'tls': ['validCAAndNameConnected'],
    'tls_negative': ['plaintextRejected', 'unrelatedCARejected', 'resolvedWrongNameRejected'],
    'authentication': ['freshUserAuthenticated', 'wrongPasswordRejected', 'anonymousReadDenied'],
    'authorization': ['exactFixtureReads', 'insertDeniedCode13', 'dataUnchanged'],
    'rotation': ['priorSecretFreshLoginRejected', 'newSecretFreshContractPassed', 'identityAndRolesPreserved'],
    'access_review': ['fixtureExpandedGrantsMatch', 'deploymentIdentityReviewCompleted'],
    'recovery': ['independentAdminBeforeAndAfter', 'knownGoodTLSRecoveryReviewed'],
    'cleanup': ['ownedFixtureRemoved', 'independentAdminStillWorks']
}
EXTRA = {
    'enterprise': ['runningEnterpriseModule', 'authorizedDistribution'],
    'audit': ['effectivePolicyVerified', 'requiredEventsObserved', 'closedLogRotationVerified'],
    'storage_encryption': ['effectiveEncryptionVerified', 'originalKeyRestartPassed',
                           'wrongKeyRestoreRejected', 'correctKeyRestorePassed', 'keyCustodyReviewed'],
    'field_encryption': ['rawCiphertextVerified', 'queryAndDecryptContractPassed',
                         'wrongKeyOrKMSIdentityRejected', 'freshAuthorizedRecoveryPassed']
}

def requirements(profile):
    if profile == 'tls-scram':
        return BASE
    if profile == 'enterprise-security':
        return {**BASE, **EXTRA}
    raise ValueError('unknown profile')

def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('timestamp must be ISO string')
    stamp = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('timezone required')
    return stamp.astimezone(datetime.timezone.utc)

def artifact(root, relative, expected):
    if not isinstance(relative, str) or pathlib.PurePosixPath(relative).is_absolute():
        raise ValueError('relative evidence path required')
    parts = pathlib.PurePosixPath(relative).parts
    if not parts or parts[0] != 'evidence' or any(p in {'.', '..'} for p in parts):
        raise ValueError('artifact must remain under evidence')
    if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
        raise ValueError('invalid artifact digest')
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('symlink artifact path rejected')
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError('missing/empty artifact')
    hasher = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    if digest != expected:
        raise ValueError('artifact digest mismatch')

def evaluate(manifest, ledger, root, now=None):
    if not isinstance(manifest, dict) or not isinstance(ledger, dict):
        raise ValueError('objects required')
    if type(manifest.get('formatVersion')) is not int or type(ledger.get('formatVersion')) is not int or manifest.get('formatVersion') != 1 or ledger.get('formatVersion') != 1:
        raise ValueError('format version mismatch')
    for key in ('runId', 'targetId', 'profile'):
        if not isinstance(manifest.get(key), str) or not manifest[key] or ledger.get(key) != manifest[key]:
            raise ValueError('run/target/profile mismatch')
    required = requirements(manifest['profile'])
    limit = manifest.get('maxAgeHours')
    if type(limit) is not int or limit < 1 or limit > 168:
        raise ValueError('review window must be 1..168 hours')
    now = now or datetime.datetime.now(datetime.timezone.utc)
    start = timestamp(manifest.get('startedAt'))
    if start > now:
        raise ValueError('future run start')
    controls = ledger.get('controls')
    if not isinstance(controls, list):
        raise ValueError('controls array required')
    seen = set()
    incomplete = []
    for control in controls:
        if not isinstance(control, dict) or control.get('id') not in required:
            raise ValueError('unknown/invalid control')
        name = control['id']
        if name in seen:
            raise ValueError('duplicate control')
        seen.add(name)
        if control.get('status') not in {'passed', 'failed', 'not_run', 'blocked'}:
            raise ValueError('invalid control status')
        if control['status'] != 'passed':
            incomplete.append({'id': name, 'reason': control['status']})
            continue
        observed = timestamp(control.get('observedAt'))
        if observed < start or observed > now or now - observed > datetime.timedelta(hours=limit):
            raise ValueError('stale/out-of-window observation')
        if control.get('targetId') != manifest['targetId'] or control.get('runId') != manifest['runId']:
            raise ValueError('cross-target/run evidence rejected')
        tests = control.get('tests')
        if not isinstance(tests, dict) or set(tests) != set(required[name]):
            raise ValueError('assertion set mismatch')
        if any(tests[test] is not True for test in required[name]):
            incomplete.append({'id': name, 'reason': 'required assertion not true'})
        artifacts = control.get('artifacts')
        if not isinstance(artifacts, list) or not artifacts:
            raise ValueError('passed control requires bound evidence')
        for item in artifacts:
            if not isinstance(item, dict):
                raise ValueError('invalid artifact reference')
            artifact(root, item.get('path'), item.get('sha256'))
    for missing in sorted(set(required) - seen):
        incomplete.append({'id': missing, 'reason': 'missing'})
    return {'runId': manifest['runId'], 'targetId': manifest['targetId'],
            'profile': manifest['profile'], 'requiredControls': len(required),
            'incomplete': incomplete,
            'assessment': 'incomplete' if incomplete else 'evidence_complete',
            'approval': 'requires source observation review and accountable signoff'}

def initialize(root, profile, target):
    required = requirements(profile)
    if not re.fullmatch('[a-zA-Z0-9_-]+', target):
        raise ValueError('simple nonsecret target ID required')
    manifest = {'formatVersion': 1, 'runId': uuid.uuid4().hex, 'targetId': target,
                'profile': profile, 'startedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'maxAgeHours': 24}
    ledger = {**{k: manifest[k] for k in ('formatVersion', 'runId', 'targetId', 'profile')},
              'controls': [{'id': key, 'status': 'not_run',
                            'tests': {test: False for test in tests}, 'artifacts': []}
                           for key, tests in required.items()]}
    for name, value in [('manifest48.json', manifest), ('ledger48.json', ledger)]:
        with (root / 'evidence' / name).open('x', encoding='utf-8') as handle:
            json.dump(value, handle, indent=2)

if __name__ == '__main__':
    try:
        root = pathlib.Path.cwd().resolve()
        if len(sys.argv) == 4 and sys.argv[1] == 'init':
            initialize(root, sys.argv[2], sys.argv[3])
            print('Manifest created; all controls not_run')
        elif sys.argv[1:] == ['evaluate']:
            manifest = json.loads((root / 'evidence/manifest48.json').read_text())
            ledger = json.loads((root / 'evidence/ledger48.json').read_text())
            report = evaluate(manifest, ledger, root)
            print(json.dumps(report, indent=2))
            sys.exit(2 if report['incomplete'] else 0)
        else:
            raise ValueError('usage: ledger48.py init PROFILE TARGET_ID | evaluate')
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
```

Execute this initialization once as the Section 4 prerequisite, **before** the test window. Do not repeat `init` when returning to this section after running the controls:

```bash
python3 scripts/ledger48.py init tls-scram mongodb-ch41-security
python3 scripts/ledger48.py evaluate
```

The initial evaluation must exit `2` with incomplete controls. A different target/profile requires a new directory/run, not a change to an existing accepted ledger. The default window is 24 hours; an approved window up to seven days must be established before testing. Stale evidence requires a new run, not rewritten observation dates.

## 14. Register actual outcomes and review exceptions

After an actual observation, edit only its matching control entry in `evidence/ledger48.json`. Copy `targetId` and `runId` from the manifest; add the real UTC observation time, outcome and bound artifacts. For a passed control, every listed assertion must be supported by evidence. For a failure/blocker, preserve it as such and create an action record.

An entry has this shape; replace placeholders only with actual values:

```json
{
  "id": "tls",
  "status": "passed",
  "targetId": "ACTUAL_TARGET_ID",
  "runId": "ACTUAL_RUN_ID",
  "observedAt": "ACTUAL_ISO_UTC_TIME",
  "tests": {"validCAAndNameConnected": true},
  "artifacts": [{"path": "evidence/ACTUAL_CAPTURE.json", "sha256": "ACTUAL_64_HEX_DIGEST"}]
}
```

The placeholder entry cannot pass validation. Calculate a digest of the sanitized retained artifact, not a live changing file:

```bash
sha256sum evidence/server-inventory.json
```

Do not mark a TLS rejection or old-password rejection passed merely from any nonzero exit. Bind the observed reason and the adjacent positive control in a protected capture. For manual network/deployment-wide review, record reviewer, target, reviewed source, time, finding and closure. A fabricated note with a valid hash can satisfy structure; source review remains mandatory.

This evaluator checks the manifest's requirements and artifact integrity, not their factual truth, deployment identity authenticity or cryptographic provenance. Hashes bind retained copies but do not establish completeness of upstream logs. Scan/redact captures before retention; the evaluator does not detect every secret or plaintext data leak.

An exception record must name scope, risk, owner, approver, expiry and compensating checks. The fixed profiles do not convert `blocked` into success because an exception was written. Narrow or change the acceptance claim through an explicitly reviewed new policy/run if warranted, and retain the previous incomplete result.

## 15. Test evaluator failure behavior offline

Save `scripts/test_ledger48.py`. These are synthetic structural tests, not real deployment observations:

```python
import copy
import datetime
import hashlib
import pathlib
import tempfile
import unittest
from ledger48 import BASE, evaluate, initialize

NOW = datetime.datetime(2026, 1, 2, tzinfo=datetime.timezone.utc)

def complete(root):
    (root / 'evidence').mkdir()
    artifact = root / 'evidence/synthetic.txt'; artifact.write_text('synthetic only')
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    manifest = {'formatVersion': 1, 'runId': 'synthetic', 'targetId': 'synthetic-target',
                'profile': 'tls-scram', 'startedAt': (NOW - datetime.timedelta(hours=1)).isoformat(),
                'maxAgeHours': 24}
    ledger = {k: manifest[k] for k in ('formatVersion', 'runId', 'targetId', 'profile')}
    ledger['controls'] = [{'id': name, 'status': 'passed', 'targetId': manifest['targetId'],
        'runId': manifest['runId'], 'observedAt': NOW.isoformat(),
        'tests': {test: True for test in tests},
        'artifacts': [{'path': 'evidence/synthetic.txt', 'sha256': digest}]} for name, tests in BASE.items()]
    return manifest, ledger

class LedgerTests(unittest.TestCase):
    def test_complete_structure_and_missing_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp); manifest, ledger = complete(root)
            self.assertEqual(evaluate(manifest, ledger, root, NOW)['assessment'], 'evidence_complete')
            ledger['controls'].pop()
            self.assertEqual(evaluate(manifest, ledger, root, NOW)['assessment'], 'incomplete')

    def test_failed_or_false_assertion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp); manifest, ledger = complete(root)
            ledger['controls'][0]['status'] = 'failed'
            self.assertEqual(evaluate(manifest, ledger, root, NOW)['assessment'], 'incomplete')
            ledger['controls'][0]['status'] = 'passed'
            ledger['controls'][0]['tests']['exactVersionRecorded'] = 1
            self.assertEqual(evaluate(manifest, ledger, root, NOW)['assessment'], 'incomplete')

    def test_scope_stale_duplicates_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp); manifest, ledger = complete(root)
            for mutation in ('scope', 'stale', 'duplicate', 'hash'):
                value = copy.deepcopy(ledger)
                if mutation == 'scope': value['controls'][0]['targetId'] = 'other-target'
                if mutation == 'stale': value['controls'][0]['observedAt'] = (NOW - datetime.timedelta(days=2)).isoformat()
                if mutation == 'duplicate': value['controls'].append(copy.deepcopy(value['controls'][0]))
                if mutation == 'hash': value['controls'][0]['artifacts'][0]['sha256'] = '0' * 64
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    evaluate(manifest, value, root, NOW)

    def test_unsafe_path_and_missing_enterprise_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp); manifest, ledger = complete(root)
            value = copy.deepcopy(ledger); value['controls'][0]['artifacts'][0]['path'] = 'evidence/../outside'
            with self.assertRaises(ValueError): evaluate(manifest, value, root, NOW)
            manifest['profile'] = ledger['profile'] = 'enterprise-security'
            self.assertEqual(evaluate(manifest, ledger, root, NOW)['assessment'], 'incomplete')

    def test_initialization_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp); (root / 'evidence').mkdir()
            initialize(root, 'tls-scram', 'synthetic-target')
            with self.assertRaises(FileExistsError): initialize(root, 'tls-scram', 'synthetic-target')

if __name__ == '__main__':
    unittest.main()
```

```bash
python3 scripts/test_ledger48.py
```

A synthetic complete ledger proves the validator accepts the intended shape, not that security controls passed. A missing Enterprise control, scope mismatch, altered artifact or stale capture must never be hidden by a successful helper-test result.

## 16. Cleanup, evaluate and obtain accountable signoff

Before normal cleanup, require successful rotation and resolved negative-test issues. Cleanup refuses changed ownership, unexpected privileges or unexpected data; partial runs need reconciliation first.

```bash
export ACTION48='cleanup'
admin48 --quiet --file /scripts/admin48.js
admin48 --quiet --eval 'db.runCommand({ping: 1})'
unset ACTION48
```

The administrator script verifies fixture removal. Record the final independent administrator login and retained TLS baseline. Retire the disposable fixture secrets and unrelated test-CA private key through their approved lifecycle. Keep nonsecret evidence and actual failures according to retention policy. Do not dispose of retained Chapter 41 recovery credentials or key material needed by another lab's backups.

Register the final cleanup observation, then evaluate:

```bash
python3 scripts/ledger48.py evaluate > evidence/assessment48.json
```

Exit `0` means declared evidence is structurally complete and bound to the selected scope; `2` means incomplete controls; `1` means invalid/unusable evidence. Review the actual report and source captures. The redirected report can exist even when evaluation fails; file existence is not acceptance.

The accountable signoff record must include run/target/profile, reviewer, source-observation review, result, unresolved issues/exceptions, recovery owner and decision time. Production approval additionally needs the actual deployment's policy, rollout/operational requirements and organization-approved process.

| Acceptance item | Required observation | Authored chapter status |
|---|---|---|
| Baseline profile | All ten controls observed on retained target | Runtime pending |
| Enterprise profile | Four additional controls on a compatible authorized target | Separate runtime acceptance pending |
| Negative controls | Correct failure layers and adjacent working controls | Runtime pending |
| Evidence integrity | Target/run, timestamps, hashes and safe references validated | Runtime evidence pending |
| Scope review | Deployment identities, network, host/provider/key custody reviewed | Manual review pending |
| Recovery/cleanup | Independent admin retained; owned fixtures removed | Runtime pending |
| Evaluator | Missing/failed/stale/wrong-scope/altered/unsafe input tests | Offline tests only |

Review questions:

1. Why can separate successful audit and encryption labs fail to establish one deployment's acceptance?
2. Which negative scripts should exit nonzero, and which should exit zero after proving denial?
3. Why does a correct artifact hash not prove the observation is true?
4. What extra requirements apply when QE is selected for the Enterprise profile?
5. How should stale evidence or an approved exception affect the stated claim?
6. Why must recovery access remain independent of the credential being rotated?

## 17. References and next chapter

- [Security checklist for self-managed deployments](https://www.mongodb.com/docs/v8.0/administration/security-checklist/)
- [TLS configuration](https://www.mongodb.com/docs/v8.0/tutorial/configure-ssl/)
- [usersInfo and expanded access](https://www.mongodb.com/docs/v8.0/reference/command/usersinfo/)
- [Enterprise audit guarantees](https://www.mongodb.com/docs/v8.0/core/auditing/)
- [Encryption at rest](https://www.mongodb.com/docs/v8.0/core/security-encryption-at-rest/)
- [Queryable Encryption compatibility](https://www.mongodb.com/docs/v8.0/core/queryable-encryption/reference/compatibility/)

Next: **Chapter 49 — Backup Architecture RPO and RTO** (planned).
