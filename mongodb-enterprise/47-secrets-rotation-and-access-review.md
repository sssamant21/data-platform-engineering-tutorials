# 47 — Secrets Rotation and Access Review

Part 6 — Enterprise Security and Governance

**Baseline:** MongoDB 8.0, authenticated TLS/SCRAM lab retained from Chapters 41–43.  
**Status:** Written; static review complete; live credential, privilege and cleanup validation pending.  
**Prerequisites:** Chapters 41–46, independent administrator access, approved secret custody and a rollback path.

## 1. Rotation is an application change with security evidence

This chapter rehearses a successor-identity cutover, an in-place password change, a least-privilege review and repair of a deliberate excessive grant. Success means the intended application works through fresh connections, old credentials fail where expected, permissions remain bounded, and evidence does not contain secrets.

Changing a database credential is only one part of rotation. Secret distribution, pool replacement, workload rollout, caches, external providers, ownership and recovery all need explicit checks. An application that still serves requests through an old connection is not proof that its replacement credential works.

The lab creates database `mongodb_enterprise_tutorial_ch47` on the retained Chapter 41 TLS standalone. It does not change retained administrator passwords, Chapter 35 topology, the Chapter 44 audit service, Chapter 45 storage keys or Chapter 46 DEKs. SCRAM/user/role exercises work in Community and Enterprise; provider integrations require their own gates.

## 2. Inventory secrets by dependency and owner

| Secret or credential | Consumers | Rotation dependency |
|---|---|---|
| SCRAM application password | Application instances, workers, scheduled jobs | Database update plus secret distribution and fresh pool creation |
| Replica-set/sharded authentication key | Database members and routers | Supported overlap/rolling membership-auth procedure |
| TLS leaf certificate/private key | Server/client endpoints | Trust, hostname, expiry, reload/restart and renewal checks |
| OIDC/Kerberos/LDAP credentials | Client, identity provider and mapping | Provider lifecycle, token/ticket lifetimes and authorization mapping |
| Storage encryption master key | Database process and matching backups | Chapter 45; storage recovery and historical key retention |
| Field-encryption CMK/DEK | Application, KMS and key vault | Chapter 46; fresh unwrap, ciphertext and historical recovery |
| Backup/cloud workload credential | Agent, storage/KMS endpoint | Backup creation and restore permissions independently verified |

Keep a nonsecret register containing environment, principal plus authentication database, purpose, owner, consumers, approved secret reference/version, rotation schedule/trigger, last verified rotation, expiry and recovery dependencies. A secret reference is not its value; a rotation date is not proof of successful cutover.

Separate emergency rotation after suspected compromise from routine planned rotation. Emergency work may require immediate privilege removal and workload isolation, rather than an overlap that preserves old access.

## 3. Choose successor identities or in-place rotation

| Strategy | Advantage | Tradeoff |
|---|---|---|
| Successor identity A → B | Validate B before retiring A; clear principal-level evidence | Temporary overlap; needs bounded retirement and duplicate-role review |
| Same identity, new password | Stable username | Consumers must converge on the new version; a single user's password is not a two-password overlap policy |
| Provider-managed short-lived identity | Reduced static-secret distribution | Provider/issuer availability, renewal and mapping need acceptance |

This lab first uses separate users `ch47_reader_a` and `ch47_reader_b` with the same custom find-only role. It then changes B's password without changing B's role assignment or user ID.

Do not grant B a broader built-in role merely to speed up migration. Do not restore a revoked identity automatically after a security incident. Rollback is an explicit decision based on the reason for rotation and the last known working state.

## 4. Preserve the retained TLS and administrator baseline

The retained service is `mongodb-ch41`, service hostname `mongo41`, Docker network `mongodb-ch41_security41`. Use the pinned `MONGO_IMAGE` already selected in Chapter 41 and the current Chapter 42 CA, not a plaintext configuration or invalid-certificate bypass.

Create a new host-side workspace next to the retained `mongodb-ch41` directory:

```bash
umask 077
mkdir mongodb-ch47
cd mongodb-ch47
mkdir scripts evidence
export LAB47_ROOT="$PWD"
export TLS47_ROOT='/absolute/path/to/mongodb-ch41'
test -f "$TLS47_ROOT/pki/public/ca.crt"
test -n "${MONGO_IMAGE:?use the exact pinned image from Chapter 41}"
export ACTION47='review'
export REVIEW47='preflight'
```

Replace `TLS47_ROOT`; do not invent a new image/version. The independent administrator remains `ch41_bootstrap` in `admin`. The Chapter 41 identity administrator is scoped to a different database and must not be silently expanded for this fixture.

Define wrappers. Each invocation creates a fresh client container and prompts for its password:

```bash
admin47() {
  docker run --rm -it --user "$(id -u):$(id -g)" \
    --network mongodb-ch41_security41 \
    -v "$TLS47_ROOT/pki/public:/trust:ro" \
    -v "$LAB47_ROOT/scripts:/scripts:ro" \
    -v "$LAB47_ROOT/evidence:/evidence" \
    --env ACTION47 --env REVIEW47 "$MONGO_IMAGE" \
    mongosh 'mongodb://mongo41:27017/admin' --tls --tlsCAFile /trust/ca.crt \
    --username ch41_bootstrap --authenticationDatabase admin \
    --authenticationMechanism SCRAM-SHA-256 --password "$@"
}
reader47() {
  local principal47="$1"
  shift
  case "$principal47" in ch47_reader_a|ch47_reader_b) ;; *) return 2 ;; esac
  docker run --rm -it --user "$(id -u):$(id -g)" \
    --network mongodb-ch41_security41 \
    -v "$TLS47_ROOT/pki/public:/trust:ro" \
    -v "$LAB47_ROOT/scripts:/scripts:ro" "$MONGO_IMAGE" \
    mongosh 'mongodb://mongo41:27017/mongodb_enterprise_tutorial_ch47' \
    --tls --tlsCAFile /trust/ca.crt --username "$principal47" \
    --authenticationDatabase mongodb_enterprise_tutorial_ch47 \
    --authenticationMechanism SCRAM-SHA-256 --password "$@"
}
admin47 --quiet --eval 'db.runCommand({ping: 1})'
```

The mounted public CA and scripts must be readable by the host UID used for the client. Evidence is written with that UID. Investigate permissions if the client fails; do not make private material world-readable. An expired certificate, wrong hostname or unavailable container blocks the rotation lab before it reaches authentication.

## 5. Write guarded fixture administration

Save `scripts/admin47.js`. The action is a nonsecret selector. Passwords are prompted inside mongosh. The state file contains ownership identifiers and phase metadata only.

```javascript
const fs47 = require('fs');
const lab47 = db.getSiblingDB('mongodb_enterprise_tutorial_ch47');
const name47 = lab47.getName();
const owner47 = 'chapter47-rotation-lab';
const role47 = 'ch47_find_records';
const statePath47 = '/evidence/state47.json';
const action47 = process.env.ACTION47;
const canon47 = value => EJSON.stringify(value);
const assert47 = (condition, message) => { if (!condition) throw new Error(message); };
const expectedFind47 = [{resource: {db: name47, collection: 'records'}, actions: ['find']}];
const expectedWrite47 = [{resource: {db: name47, collection: 'records'}, actions: ['insert']}];
function save47(state) {
  const temp = statePath47 + '.tmp';
  fs47.writeFileSync(temp, EJSON.stringify(state), {flag: 'wx', mode: 0o600});
  fs47.renameSync(temp, statePath47);
}
function requireUser47(user, id) {
  const value = lab47.getUser(user);
  assert47(value && value.customData?.owner === owner47, 'Identity ownership mismatch');
  assert47(canon47(value.userId) === canon47(id), 'User ID mismatch');
  return value;
}
function requireRole47(name, privileges) {
  const value = lab47.getRole(name, {showPrivileges: true});
  assert47(value && value.roles.length === 0, 'Role inheritance mismatch');
  assert47(canon47(value.privileges) === canon47(privileges), 'Role privilege mismatch');
}
const allowed47 = ['setup', 'add-successor', 'retire-a', 'rotate-b', 'escalate', 'repair', 'review', 'cleanup'];
assert47(allowed47.includes(action47), 'Unknown ACTION47');
const build47 = db.adminCommand({buildInfo: 1});
assert47(build47.ok === 1 && /^8\.0\./.test(build47.version), 'Review the installed server version');
const options47 = db.adminCommand({getCmdLineOpts: 1});
assert47(options47.ok === 1 && options47.parsed.net?.tls?.mode === 'requireTLS' &&
  options47.parsed.security?.authorization === 'enabled', 'TLS/auth baseline required');
if (action47 === 'setup') {
  assert47(!fs47.existsSync(statePath47), 'Existing state refused');
  assert47(lab47.getCollectionInfos().length === 0 && lab47.getUsers().users.length === 0 &&
    lab47.getRoles({showBuiltinRoles: false}).roles.length === 0, 'Nonempty fixture refused');
  lab47.createCollection('records');
  lab47.records.insertMany([{_id: 'r1', owner: owner47, value: 10},
    {_id: 'r2', owner: owner47, value: 20}]);
  lab47.createRole({role: role47, roles: [], privileges: expectedFind47});
  print('Choose a unique password for predecessor A:');
  lab47.createUser({user: 'ch47_reader_a', pwd: passwordPrompt(),
    mechanisms: ['SCRAM-SHA-256'], roles: [{role: role47, db: name47}],
    customData: {owner: owner47, revision: 'a-initial'}});
  const state = {owner: owner47, database: name47, phase: 'a-only',
    aUserId: lab47.getUser('ch47_reader_a').userId,
    collectionUUID: lab47.getCollectionInfos({name: 'records'})[0].info.uuid,
    serverVersion: build47.version, createdAt: new Date()};
  fs47.writeFileSync(statePath47, EJSON.stringify(state), {flag: 'wx', mode: 0o600});
  print('Owned predecessor fixture created');
} else {
  const state = EJSON.parse(fs47.readFileSync(statePath47, 'utf8'));
  assert47(state.owner === owner47 && state.database === name47, 'State ownership mismatch');
  const collections = lab47.getCollectionInfos();
  assert47(collections.length === 1 && collections[0].name === 'records' &&
    canon47(collections[0].info.uuid) === canon47(state.collectionUUID), 'Collection ownership mismatch');
  requireRole47(role47, expectedFind47);
  if (action47 === 'add-successor') {
    assert47(state.phase === 'a-only', 'Require A-only phase');
    requireUser47('ch47_reader_a', state.aUserId);
    assert47(!lab47.getUser('ch47_reader_b'), 'Existing successor refused');
    print('Choose a different unique password for successor B:');
    lab47.createUser({user: 'ch47_reader_b', pwd: passwordPrompt(),
      mechanisms: ['SCRAM-SHA-256'], roles: [{role: role47, db: name47}],
      customData: {owner: owner47, revision: 'b-initial'}});
    state.bUserId = lab47.getUser('ch47_reader_b').userId;
    state.phase = 'overlap'; save47(state);
    print('Scoped successor created; predecessor remains active');
  } else if (action47 === 'retire-a') {
    assert47(state.phase === 'overlap', 'Require reviewed overlap phase');
    requireUser47('ch47_reader_a', state.aUserId);
    requireUser47('ch47_reader_b', state.bUserId);
    assert47(lab47.dropUser('ch47_reader_a'), 'Predecessor removal failed');
    state.phase = 'b-only'; save47(state);
    print('Owned predecessor retired; verify fresh login rejection');
  } else if (action47 === 'rotate-b') {
    assert47(state.phase === 'b-only', 'Require B-only phase');
    const before = requireUser47('ch47_reader_b', state.bUserId);
    assert47(before.customData.revision === 'b-initial', 'Password fixture already changed');
    print('Choose a new B password; keep the prior version only through the negative test:');
    lab47.updateUser('ch47_reader_b', {pwd: passwordPrompt(),
      customData: {...before.customData, revision: 'b-rotated'}});
    const after = requireUser47('ch47_reader_b', state.bUserId);
    assert47(canon47(before.roles) === canon47(after.roles), 'Roles changed during password rotation');
    state.passwordRevision = 'b-rotated'; state.rotatedAt = new Date(); save47(state);
    print('Password changed; user ID and direct roles preserved');
  } else if (action47 === 'escalate') {
    assert47(state.phase === 'b-only' && !state.driftFixture, 'Require B-only clean phase');
    requireUser47('ch47_reader_b', state.bUserId);
    assert47(!lab47.getRole('ch47_fixture_write'), 'Existing drift role refused');
    lab47.createRole({role: 'ch47_fixture_write', roles: [], privileges: expectedWrite47});
    lab47.grantRolesToUser('ch47_reader_b', [{role: 'ch47_fixture_write', db: name47}]);
    state.driftFixture = true; save47(state);
    print('Deliberate fixture-only excessive grant added; run access review, not the read-only smoke test');
  } else if (action47 === 'repair') {
    assert47(state.driftFixture === true, 'No owned drift fixture');
    requireUser47('ch47_reader_b', state.bUserId);
    requireRole47('ch47_fixture_write', expectedWrite47);
    lab47.revokeRolesFromUser('ch47_reader_b', [{role: 'ch47_fixture_write', db: name47}]);
    assert47(lab47.dropRole('ch47_fixture_write'), 'Drift role removal failed');
    state.driftFixture = false; save47(state);
    print('Owned excessive grant removed; rerun review and denied-write test');
  } else if (action47 === 'review') {
    const label = process.env.REVIEW47;
    assert47(typeof label === 'string' && /^[a-z0-9-]+$/.test(label), 'Safe unique REVIEW47 label required');
    const listed = lab47.runCommand({usersInfo: 1, showCredentials: false});
    assert47(listed.ok === 1, 'Cannot list identities');
    const users = listed.users.map(identity => {
      const detail = lab47.runCommand({usersInfo: {user: identity.user, db: identity.db},
        showCredentials: false, showPrivileges: true, showAuthenticationRestrictions: true});
      assert47(detail.ok === 1 && detail.users.length === 1, 'Cannot expand identity privileges');
      const user = detail.users[0];
      return {user: user.user, db: user.db, userId: user.userId, roles: user.roles,
        inheritedRoles: user.inheritedRoles, inheritedPrivileges: user.inheritedPrivileges,
        mechanisms: user.mechanisms, authenticationRestrictions: user.authenticationRestrictions || [],
        inheritedAuthenticationRestrictions: user.inheritedAuthenticationRestrictions || [],
        owner: user.customData?.owner || null};
    });
    const report = {scope: name47, phase: state.phase, observedAt: new Date(),
      serverVersion: build47.version, users};
    fs47.writeFileSync('/evidence/review-' + label + '.json', JSON.stringify(report, null, 2),
      {flag: 'wx', mode: 0o600});
    print('Nonsecret fixture access snapshot written; evaluate before acceptance');
  } else if (action47 === 'cleanup') {
    assert47(state.phase === 'b-only' && !state.driftFixture, 'Require retired predecessor and repaired drift');
    const users = lab47.getUsers().users;
    const roles = lab47.getRoles({showBuiltinRoles: false}).roles;
    assert47(users.length === 1 && roles.length === 1, 'Unexpected users or roles refused');
    requireUser47('ch47_reader_b', state.bUserId);
    const rows = lab47.records.find({}).sort({_id: 1}).toArray();
    assert47(rows.length === 2 && rows[0]._id === 'r1' && rows[1]._id === 'r2' &&
      rows[0].owner === owner47 && rows[1].owner === owner47 &&
      rows[0].value === 10 && rows[1].value === 20, 'Unexpected fixture content refused');
    assert47(lab47.dropUser('ch47_reader_b'), 'Successor removal failed');
    assert47(lab47.dropRole(role47), 'Reader role removal failed');
    assert47(lab47.records.drop(), 'Fixture collection removal failed');
    fs47.renameSync(statePath47, '/evidence/state47.disposed.json');
    print('Owned chapter47 identities, roles and records removed; TLS/admin retained');
  }
}
```

User/role changes and state-file updates are not one atomic transaction. If a command or file write fails halfway, stop, compare actual user IDs, privileges and collection UUID with the saved state, and resolve the partial operation before rerun. Do not delete guards to force success. A leftover `.tmp` file is a recovery clue, not permission to overwrite state blindly.

## 6. Create A and establish the application contract

```bash
export ACTION47='setup'
admin47 --quiet --file /scripts/admin47.js
```

Choose A's password at its prompt. Keep it in your approved lab secret custody; do not write it into custom data or evidence.

Save `scripts/reader47.js`:

```javascript
const lab47 = db.getSiblingDB('mongodb_enterprise_tutorial_ch47');
const rows47 = lab47.records.find({}).sort({_id: 1}).toArray();
if (rows47.length !== 2 || rows47[0]._id !== 'r1' || rows47[1]._id !== 'r2' ||
    rows47[0].value !== 10 || rows47[1].value !== 20) throw new Error('Read contract mismatch');
const denied47 = lab47.runCommand({insert: 'records', documents: [
  {_id: 'forbidden47', owner: 'chapter47-rotation-lab', value: 99}
]});
if (denied47.ok !== 0 || denied47.code !== 13) throw new Error('Expected Unauthorized insert');
print(EJSON.stringify({reads: 2, deniedWriteCode: 13, verifiedAt: new Date()}));
```

```bash
reader47 ch47_reader_a --quiet --file /scripts/reader47.js
```

Require two expected rows and denied insert code `13`. The same contract will be used for B before and after rotation. `ping` alone is insufficient because it does not prove scoped data access or write denial.

## 7. Capture a baseline access review

```bash
export ACTION47='review'
export REVIEW47='a-baseline'
admin47 --quiet --file /scripts/admin47.js
```

The snapshot first lists users without credentials, then expands each explicitly identified user. `usersInfo` cannot combine an all-user request with `showPrivileges`; this two-step approach avoids silently missing inherited privileges.

The report includes direct roles, inherited roles/privileges, mechanisms, restrictions and ownership. It intentionally omits password hashes and arbitrary custom data. Protect it anyway: usernames and privilege topology are operational information.

This fixture snapshot covers identities defined in the chapter database. It is not a deployment-wide access census: identities defined in `admin` or `$external` can hold privileges elsewhere, including on this database. Section 14 extends the scope for a real review.

## 8. Evaluate exact expected access offline

Save `scripts/review47.py`. It checks this fixture's phase against expected identities, direct role and exact inherited privilege surface. It reports drift; it does not modify MongoDB or certify ownership/business need.

```python
import json
import pathlib
import sys

DB = 'mongodb_enterprise_tutorial_ch47'
ROLE = {'role': 'ch47_find_records', 'db': DB}
EXPECTED = {'a-only': {'ch47_reader_a'},
            'overlap': {'ch47_reader_a', 'ch47_reader_b'},
            'b-only': {'ch47_reader_b'}}

def check(snapshot):
    if not isinstance(snapshot, dict) or snapshot.get('scope') != DB:
        raise ValueError('wrong review scope')
    phase = snapshot.get('phase')
    if phase not in EXPECTED or not isinstance(snapshot.get('users'), list):
        raise ValueError('invalid phase/users')
    findings = []
    seen = set()
    for user in snapshot['users']:
        if not isinstance(user, dict) or not isinstance(user.get('user'), str):
            raise ValueError('invalid identity')
        name = user['user']
        if name in seen:
            raise ValueError('duplicate identity')
        seen.add(name)
        for field in ('roles', 'inheritedRoles', 'inheritedPrivileges', 'mechanisms', 'authenticationRestrictions', 'inheritedAuthenticationRestrictions'):
            if not isinstance(user.get(field), list):
                raise ValueError('missing/invalid ' + field)
        if user.get('db') != DB or user.get('owner') != 'chapter47-rotation-lab':
            findings.append({'user': name, 'issue': 'identity_scope_or_owner'})
        if user['roles'] != [ROLE] or user['inheritedRoles'] != [ROLE]:
            findings.append({'user': name, 'issue': 'unexpected_role_surface'})
        privileges = user['inheritedPrivileges']
        if len(privileges) != 1:
            findings.append({'user': name, 'issue': 'unexpected_privilege_count'})
        else:
            privilege = privileges[0]
            if not isinstance(privilege, dict):
                raise ValueError('invalid privilege')
            if privilege.get('resource') != {'db': DB, 'collection': 'records'} or privilege.get('actions') != ['find']:
                findings.append({'user': name, 'issue': 'unexpected_resource_or_actions'})
        if user['mechanisms'] != ['SCRAM-SHA-256']:
            findings.append({'user': name, 'issue': 'unexpected_mechanism'})
        if user['authenticationRestrictions'] or user['inheritedAuthenticationRestrictions']:
            findings.append({'user': name, 'issue': 'unexpected_restrictions_need_review'})
        if 'credentials' in user or 'password' in user or 'pwd' in user:
            raise ValueError('secret-bearing review rejected')
    if seen != EXPECTED[phase]:
        findings.append({'issue': 'phase_identity_set_mismatch',
                         'missing': sorted(EXPECTED[phase] - seen),
                         'unexpected': sorted(seen - EXPECTED[phase])})
    return {'scope': DB, 'phase': phase, 'users': len(seen), 'findings': findings,
            'fixture_access': 'drift' if findings else 'matches_expected',
            'business_approval': 'requires owner/reviewer evidence'}

if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError('usage: review47.py SNAPSHOT_JSON')
        report = check(json.loads(pathlib.Path(sys.argv[1]).read_text()))
        print(json.dumps(report, indent=2))
        sys.exit(2 if report['findings'] else 0)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
```

```bash
python3 scripts/review47.py evidence/review-a-baseline.json
```

Exit `0` means the fixture snapshot matches; `2` means drift; `1` means unusable input. Verify source, capture time and actual application tests separately. The evaluator does not prove the snapshot is authentic or current.

## 9. Add B and verify a bounded overlap

```bash
export ACTION47='add-successor'
admin47 --quiet --file /scripts/admin47.js
reader47 ch47_reader_b --quiet --file /scripts/reader47.js
reader47 ch47_reader_a --quiet --file /scripts/reader47.js
export ACTION47='review'
export REVIEW47='overlap'
admin47 --quiet --file /scripts/admin47.js
python3 scripts/review47.py evidence/review-overlap.json
```

B gets a unique password and exactly the same find-only role. Require both fresh client contracts and a matching two-identity overlap review. Keep an overlap end time and named owner in the change record.

In a real application, publish a new approved secret version referencing B, roll a canary, create fresh pools, and verify data operations and denied operations. Confirm workers, cron jobs and retry queues consumed the new version. An unchanged pod count or a secret-manager “current” label alone is not convergence evidence.

Before retiring A, rollback can redirect consumers to its still-authorized credential, provided that is allowed by the security reason for rotation. This lab's wrappers are fresh-client acceptance controls; they do not simulate a production fleet rollout or prove zero downtime.

## 10. Retire A and verify fresh authentication rejection

Proceed after B and the overlap review pass:

```bash
export ACTION47='retire-a'
admin47 --quiet --file /scripts/admin47.js
reader47 ch47_reader_a --quiet --file /scripts/reader47.js
```

Supply A's original password. Expect database authentication failure and a nonzero client exit; record the status immediately with `echo "$?"` plus a timestamp. TLS/DNS/connection failure is not an acceptable substitute. Preserve the actual failure layer in the private evidence record.

```bash
reader47 ch47_reader_b --quiet --file /scripts/reader47.js
export ACTION47='review'
export REVIEW47='b-cutover'
admin47 --quiet --file /scripts/admin47.js
python3 scripts/review47.py evidence/review-b-cutover.json
```

Require B's contract and a B-only review. Retire A's secret versions from active distribution according to retention/incident policy; deleting the database user does not automatically remove copied credentials from applications, logs or external secret systems.

After A is deleted, recreating it is a new provisioning action and user identity, not a simple reversal. During incident response, do not recreate the compromised identity merely because an old consumer fails.

## 11. Rotate B's password without widening access

Record the existing B secret's nonsecret version reference. Change its password via the independent administrator:

```bash
export ACTION47='rotate-b'
admin47 --quiet --file /scripts/admin47.js
reader47 ch47_reader_b --quiet --file /scripts/reader47.js
```

First supply B's **prior** password to the reader prompt. Require fresh authentication rejection and record the immediate exit status. Then invoke the same command again with B's **new** password:

```bash
reader47 ch47_reader_b --quiet --file /scripts/reader47.js
export ACTION47='review'
export REVIEW47='b-password-rotated'
admin47 --quiet --file /scripts/admin47.js
python3 scripts/review47.py evidence/review-b-password-rotated.json
```

Require successful reads, denied writes and matching privileges. The admin action checks unchanged user ID and direct roles. Updating only `pwd` and deliberately preserved custom data avoids replacing the entire roles array. Supplying `roles` to `updateUser` would replace direct roles, not append them.

Password material is carried over the verified TLS connection. `passwordPrompt()` hides terminal entry; it does not independently encrypt transport. Keep the new value in the approved secret workflow and coordinate consumer rollout before declaring production acceptance.

If the new secret was lost or distribution failed, the independent administrator can set another fresh secret under the approved recovery procedure. Do not weaken TLS/access control or try to retrieve plaintext from MongoDB password hashes. Reusing the prior password after a compromise is not a safe default rollback.

## 12. Detect and repair a deliberate excessive grant

Create an owned test-only role granting `insert` on the fixture collection, then grant it to B:

```bash
export ACTION47='escalate'
admin47 --quiet --file /scripts/admin47.js
export ACTION47='review'
export REVIEW47='drift'
admin47 --quiet --file /scripts/admin47.js
python3 scripts/review47.py evidence/review-drift.json
```

Expect evaluator exit `2` with an unexpected role/privilege surface. Do **not** run the read-only smoke test during the deliberate excessive grant: its insert could succeed and would create unexpected fixture data.

Repair only the owned grant and role:

```bash
export ACTION47='repair'
admin47 --quiet --file /scripts/admin47.js
reader47 ch47_reader_b --quiet --file /scripts/reader47.js
export ACTION47='review'
export REVIEW47='repaired'
admin47 --quiet --file /scripts/admin47.js
python3 scripts/review47.py evidence/review-repaired.json
```

Require a matching review, expected reads and code `13` for insert. This shows both configuration evidence and behavior after revocation. Do not close a privilege issue solely because a named role disappeared; inherited grants can still permit the action.

## 13. Existing pools, sessions and emergency revocation

The wrappers always make fresh connections. For a real rollout, test a representative long-lived application separately: baseline operation, credential publication, database change, deliberate pool disposal/reconnection, old-credential fresh failure and new-credential fresh success. Record whether already running operations continue and how the application handles failures/retries.

Logical sessions and authenticated connections are different. Killing a session interrupts its in-progress operations/cursors; it does not guarantee that a future operation cannot use that session again. Prepared transaction exceptions also require care. A successful session-kill command is not permanent credential revocation or proof all connections closed.

For an approved **targeted** self-managed exercise, the session command identifies the user plus its authentication database:

```javascript
const result47 = db.getSiblingDB('admin').runCommand({killAllSessions: [
  {user: 'ch47_reader_a', db: 'mongodb_enterprise_tutorial_ch47'}
]});
if (result47.ok !== 1) throw new Error('Targeted session termination failed');
print('Session termination requested; verify workload behavior and fresh authentication separately');
```

Never use an empty array as a shortcut; it targets all users' sessions. Run only within an explicitly scoped lab/change window and with the required privilege. Deployment-specific command support, including Atlas restrictions, must be checked separately.

An emergency sequence may include removing the affected user's grants or identity, isolating affected workloads/endpoints, replacing credentials, terminating scoped operations/sessions and reconnecting approved consumers. Coordinate these actions with the incident owner; they can interrupt work. Preserve transaction/result reconciliation rather than treating every network error as proof nothing committed.

## 14. Perform a deployment-wide access review

For a production review, define the complete identity scope: users in every authentication database, `admin`, `$external`, provider group/claim mappings, custom roles and their inheritance, automation identities and emergency administrators. For self-managed inventory, an authorized reviewer can list all users without credentials, then expand named identities:

```javascript
const listing47 = db.getSiblingDB('admin').runCommand({
  usersInfo: {forAllDBs: true}, showCredentials: false, showCustomData: false
});
if (listing47.ok !== 1) throw new Error('Global identity inventory failed');
print(EJSON.stringify(listing47.users.map(u => ({user: u.user, db: u.db, userId: u.userId, roles: u.roles}))));
```

Treat the output as protected read-only review material. Obtain provider and Atlas inventories through their appropriate management APIs; this self-managed command is not an Atlas account-management procedure. Do not enumerate credential hashes.

| Review dimension | Reviewer question | Required evidence |
|---|---|---|
| Ownership | Who is accountable for this identity? | Current owner and consumer map |
| Business need | Which operations/resources are required? | Approved use case, not just historical role names |
| Effective access | What inherited privileges exist? | Expanded named-user/role snapshots |
| Administrative scope | Can it create users/roles, bypass validation, manage keys or affect cluster state? | Exact action/resource review |
| Lifecycle | Is it stale, temporary, orphaned or duplicated? | Joiner/mover/leaver and expiry/exception record |
| Source controls | Are approved network/authentication restrictions satisfied? | Actual endpoint/provider policy and tests |
| Last use | Is there reliable evidence of consumer use? | Defined audit/telemetry window; absence is not automatic proof of no use |
| Recovery | Can break-glass access work without the rotating secret? | Independently tested, protected recovery path |

Do not infer unused access from an empty log alone: filters, retention gaps, scheduled jobs and provider-side events affect visibility. Record reviewer, date, scope, findings, action owner, due date, exception expiry and before/after evidence. A machine comparison is input to that decision, not owner attestation.

## 15. Secret distribution, audit evidence and troubleshooting

In Kubernetes, distinguish environment variables loaded at process start from mounted files and application reload behavior. A refreshed secret object does not establish that a running process or existing pool is using its new value. Review the actual secret delivery mechanism, rollout controller, mounted-file semantics and application reconnect implementation against its current version.

For external authentication, test renewal and denial from new processes as well as cached token/ticket behavior. For TLS/storage/field-encryption key changes, follow Chapters 42, 45 and 46; keep old trust/key dependencies until the documented recovery obligations end. Generic password rotation is not a substitute for those procedures.

If Enterprise auditing is configured on the target, correlate user-management and authentication/authorization events with the scoped change, using Chapter 44's actual filter/schema. The retained Chapter 41 service does not gain auditing just because the separate Chapter 44 lab enabled it. An audit authorization success still does not prove a write committed or an application rollout completed.

| Symptom | Investigate | Acceptance/recovery evidence |
|---|---|---|
| New credential fails | Auth database, mechanism, secret version, encoding, TLS failure layer | Fresh login and real application operation |
| Some consumers fail | Stale environment/file cache, pool reuse, missed worker/job | Per-consumer convergence and fresh connections |
| Old access still observed | Long-lived connection, inherited grants, external mapping/cache | Fresh old-login rejection plus scoped operation tests |
| Review shows broader access | Built-in/inherited roles, wildcard resource, wrong identity | Approved remediation and changed behavior |
| Admin controller stops | Partial mutation, mismatched UUID/user ID, existing evidence label | Reconciled actual state; guards retained |
| Review reports no users | Wrong scope or malformed snapshot | Complete authenticated source inventory |
| Secret leaked to logs | URI/CLI/APM/error/custom-data capture | Incident-scoped revocation, replacement and exposure assessment |

Evidence should contain identity, authentication database, credential **version reference**, timestamps, observed outcomes, role/resource diffs and approvals. It should not contain passwords, private keys, KMS credentials, SCRAM hashes or raw secret objects. Store detailed operational errors privately and redact sharing copies.

## 16. Offline tests, cleanup and acceptance

Save `scripts/test_review47.py`:

```python
import copy
import unittest
from review47 import check, DB, ROLE

def fixture():
    return {'scope': DB, 'phase': 'b-only', 'users': [{
        'user': 'ch47_reader_b', 'db': DB, 'owner': 'chapter47-rotation-lab',
        'roles': [ROLE], 'inheritedRoles': [ROLE],
        'inheritedPrivileges': [{'resource': {'db': DB, 'collection': 'records'}, 'actions': ['find']}],
        'mechanisms': ['SCRAM-SHA-256'], 'authenticationRestrictions': [],
        'inheritedAuthenticationRestrictions': []}]}

class ReviewTests(unittest.TestCase):
    def test_matching_access(self):
        self.assertEqual(check(fixture())['findings'], [])

    def test_extra_action_and_wrong_resource(self):
        for resource, actions in [({'db': DB, 'collection': 'records'}, ['find', 'insert']),
                                  ({'db': DB, 'collection': ''}, ['find'])]:
            value = fixture()
            value['users'][0]['inheritedPrivileges'][0] = {'resource': resource, 'actions': actions}
            self.assertEqual(check(value)['fixture_access'], 'drift')

    def test_missing_identity_and_role_drift(self):
        value = fixture(); value['users'] = []
        self.assertEqual(check(value)['fixture_access'], 'drift')
        value = fixture(); value['users'][0]['roles'].append({'role': 'readWrite', 'db': DB})
        self.assertEqual(check(value)['fixture_access'], 'drift')

    def test_malformed_duplicate_and_secret(self):
        duplicate = fixture(); duplicate['users'].append(copy.deepcopy(duplicate['users'][0]))
        secret = fixture(); secret['users'][0]['credentials'] = {'synthetic': 'not-real'}
        malformed = fixture(); del malformed['users'][0]['inheritedPrivileges']
        for value in ({}, duplicate, secret, malformed):
            with self.subTest(value=value), self.assertRaises(ValueError): check(value)

if __name__ == '__main__':
    unittest.main()
```

```bash
python3 scripts/test_review47.py
```

Synthetic tests verify comparison/guard behavior only. They are never runtime access-review evidence.

After all positive/negative tests pass and drift is repaired, remove the owned fixtures:

```bash
export ACTION47='cleanup'
admin47 --quiet --file /scripts/admin47.js
admin47 --quiet --eval 'db.runCommand({ping: 1})'
unset ACTION47 REVIEW47
```

Cleanup checks exact collection UUID/content, user ID/owner, expected role surface and absence of the deliberate drift phase. It retains TLS and the independent Chapter 41 administrator. Verify the chapter database has no remaining collections/users/custom roles through an administrator session. Retire the disposable A/B secrets through your secret workflow and retain protected nonsecret evidence.

| Acceptance item | Required observation | Authored chapter status |
|---|---|---|
| Recovery baseline | Independent administrator and valid TLS still work | Runtime pending |
| A-only | Known read results and denied insert | Runtime pending |
| Overlap | A and B fresh contracts; exact matching grants | Runtime pending |
| Cutover | A fresh auth failure; B success; B-only review | Runtime pending |
| Password rotation | Prior B password fails; new B succeeds; user ID/roles unchanged | Runtime pending |
| Access drift | Excessive grant detected, repaired, then denied-write behavior restored | Runtime pending |
| Production consumers | Secret version convergence and representative pool/job rollout | Separate deployment acceptance pending |
| Evidence | No secrets; scope, reviewer, findings and closure recorded | Runtime review pending |
| Cleanup | Owned fixtures removed and retained baseline verified | Runtime pending |
| Offline evaluator | Match, excessive actions/resources, missing users and malformed/secret cases | Offline tests only |

Review questions:

1. Why is a fresh data operation stronger than `ping` for rotation acceptance?
2. Why does the authentication database form part of an identity?
3. What remains unproven when a secret-manager version changes?
4. Why does a role name alone not establish least privilege?
5. How are session termination and credential revocation different?
6. When is restoring the predecessor identity an unacceptable rollback?

## 17. References and next chapter

- [Update users and role replacement semantics](https://www.mongodb.com/docs/v8.0/reference/method/db.updateuser/)
- [Change a user password](https://www.mongodb.com/docs/v8.0/reference/method/db.changeuserpassword/)
- [usersInfo and expanded privileges](https://www.mongodb.com/docs/v8.0/reference/command/usersinfo/)
- [rolesInfo](https://www.mongodb.com/docs/v8.0/reference/command/rolesinfo/)
- [Revoke roles from a user](https://www.mongodb.com/docs/v8.0/reference/method/db.revokerolesfromuser/)
- [Targeted session termination and limitations](https://www.mongodb.com/docs/v8.0/reference/command/killallsessions/)
- [Privilege actions](https://www.mongodb.com/docs/v8.0/reference/privilege-actions/)

Next: [**Chapter 48 — Security Hardening Acceptance Lab**](48-security-hardening-acceptance-lab.md).

Previous: [Chapter 46 — Client Side and Queryable Encryption](46-client-side-and-queryable-encryption.md).
