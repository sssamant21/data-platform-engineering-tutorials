# 44 — Enterprise Audit Configuration and Analysis

Part 6 — Enterprise Security and Governance

**Baseline:** MongoDB Enterprise 8.0; record the exact patch, platform, mongosh and Database Tools versions.  
**Status:** Written; static review complete; runtime Enterprise lab validation pending.  
**Prerequisites:** Chapters 41–43, an authorized Enterprise deployment, TLS, a working independent administrator and a protected audit destination.

## 1. What this chapter proves

Build an audit policy, produce known authentication, authorization and administrative events, rotate the log, and reconcile those events with application results. The acceptance target is evidence of the configured coverage, including negative tests and operational limits.

Auditing is separate from authentication, authorization, the diagnostic server log, the profiler and the oplog. None of those replaces an audit retention policy. An audit event also does not replace application acknowledgement or a data-state check.

This lab uses a **dedicated disposable Enterprise standalone**, database `mongodb_enterprise_tutorial_ch44`, and collection `events`. It does not upgrade the retained `mongodb-ch41` Community container or change the Chapter 35 sharded cluster. If Enterprise is unavailable, run the offline analyzer tests and mark the server exercises blocked.

## 2. Audit destinations and deployment coverage

| Choice | Useful for | Operational consideration |
|---|---|---|
| JSON file | This lab, readable events, line-oriented ingestion | More overhead than BSON; restrict access to raw content |
| BSON file | Efficient native output | Convert with a compatible `bsondump`; preserve originals |
| Console | Controlled diagnostics | Container logging and downstream retention become part of the evidence chain |
| Syslog | Existing centralized logging | Truncation and rate limiting can lose evidence without audit-system detection |

Self-managed Enterprise auditing is available in `mongod` and `mongos`. A sharded deployment needs auditing on routers, shard members and config-server members; enabling only routers is incomplete. Track configuration and collection health per process. Since MongoDB 5.0, secondaries do not emit DDL audit events for replicated changes, with documented exceptions for local operations. Do not require identical event counts on every member.

This chapter uses the native `mongo` schema, explicitly selected below. MongoDB 8.0 also supports OCSF. A filter and parser written for native fields must not be reused unchanged for OCSF.

## 3. Interpret audit evidence correctly

| Field/event | Meaning | Limit |
|---|---|---|
| `authenticate`, result `0` | Authentication succeeded | Does not grant every privilege |
| `authenticate`, result `18` | Authentication failed | Other authentication failure codes exist |
| `authCheck`, result `0` | Authorization check succeeded | Does not prove command completion or transaction commit |
| `authCheck`, result `13` | Operation was unauthorized | Validate the application received code 13 too |
| `users` | Authenticated identities and authentication databases | May be empty during failed authentication |
| `param.user`, `param.db` | Target identity for events such as authentication/user management | Target is different from the actor in `users` |
| `uuid` | Client connection identifier | Not a globally unique operation or document identifier |
| `ts` | Event time | Clock synchronization and process identity matter across hosts |

The native `authCheck` payload contains a command and may contain namespace and command arguments. Treat those arguments as sensitive; do not assume every event has a namespace or that every command comment is preserved. Use the controlled username, namespace, connection and time window to correlate this lab.

Operations in an aborted transaction can produce audit events without an audit event announcing the abort. Preserve application transaction outcomes separately.

## 4. Establish the Enterprise and recovery gates

Use an **existing dedicated Enterprise lab service** provisioned under your organization's approved installation procedure. It must already enforce TLS and access control, expose no public listener, and have a working administrator. This chapter changes auditing on that service; it does not provide a generic image substitution or installation procedure.

Record these nonsecret values in your lab notes:

| Item | Required evidence |
|---|---|
| Deployment | Dedicated host/container, standalone topology, owner and disposal scope |
| Binary | Exact version, `buildInfo.modules` containing `enterprise` |
| Entitlement | Approved source and authorization to use Enterprise |
| Recovery | Config backup, restart procedure, independent admin login |
| Storage | Audit mount, available space, process UID/GID, retention and collector ownership |
| Transport | CA path, validated hostname, certificate expiry |

On the client workstation, create a fresh directory; do not reuse an old evidence directory:

```bash
umask 077
mkdir mongodb-ch44
cd mongodb-ch44
mkdir scripts evidence
export AUDIT_URI44='mongodb://YOUR-ENTERPRISE-LAB-HOST:27017/admin'
export AUDIT_CA44='/absolute/path/to/lab-ca.crt'
export AUDIT_ADMIN44='YOUR-INDEPENDENT-LAB-ADMIN'

audit_admin44() {
  mongosh "$AUDIT_URI44" --tls --tlsCAFile "$AUDIT_CA44" \
    --username "$AUDIT_ADMIN44" --authenticationDatabase admin \
    --authenticationMechanism SCRAM-SHA-256 --password "$@"
}
audit_reader44() {
  mongosh "$AUDIT_URI44" --tls --tlsCAFile "$AUDIT_CA44" \
    --username ch44_reader --authenticationDatabase mongodb_enterprise_tutorial_ch44 \
    --authenticationMechanism SCRAM-SHA-256 --password "$@"
}
```

Replace the three values before running. These wrappers prompt for passwords; never put passwords in the URI, shell history or evidence. Keep hostnames resolvable and matching the certificate. No invalid-certificate bypass belongs in this lab.

Save `scripts/gate44.js`:

```javascript
const info44 = db.adminCommand({buildInfo: 1});
if (info44.ok !== 1 || !info44.modules?.includes('enterprise')) {
  throw new Error('BLOCKED: authorized Enterprise binary required');
}
if (!/^8\.0\./.test(info44.version)) {
  throw new Error('BLOCKED: review this procedure against the installed server version');
}
const hello44 = db.adminCommand({hello: 1});
if (hello44.setName || hello44.msg === 'isdbgrid') {
  throw new Error('BLOCKED: this fixture requires the dedicated standalone');
}
print(EJSON.stringify({version: info44.version, modules: info44.modules,
  topology: 'standalone', observedAt: new Date()}, null, 2));
```

```bash
audit_admin44 --quiet --file scripts/gate44.js
mongosh --version
```

Inspect the output and record it. A version string or image name alone is not Enterprise evidence. Stop on a failed gate. Do not weaken the retained Chapter 42 TLS baseline to make the test connect.

## 5. Design a bounded audit policy

Successful authorization checks are disabled by default. A filter selecting successful `authCheck` events cannot make them appear unless `auditAuthorizationSuccess` is enabled. Conversely, enabling successes without a bounded filter can create high volume.

The policy below captures all authentication attempts and authorization failures, selected identity changes and collection lifecycle events, plus successful authorization checks on exactly the fixture namespace. It is a **lab policy**, not a complete production compliance policy.

| Branch | Purpose | Deliberate scope |
|---|---|---|
| Authentication | Known success and wrong-password attempt | All identities on this dedicated service |
| Failed authorization | Detect forbidden operations | All namespaces on this dedicated service |
| Identity changes | Creation, removal, updates and grants/revocations | Listed event types, not all possible administrative events |
| Collection lifecycle | Fixture create/drop | Only the fixture namespace |
| Successful access | Observe reader `find` and administrator insert | Only the fixture namespace |

Do not scope every branch to `param.ns`: authentication and role/user management have different payloads. Do not require the authenticated `users` array to identify a failed login.

## 6. Configure native JSON auditing

On the **dedicated Enterprise server**, back up the actual service configuration using its normal configuration-management workflow. Confirm the service user can create files in an owned audit directory such as `/var/log/mongodb/ch44-audit`, with restrictive permissions and adequate space. Keep the data directory and audit directory separate. If the service is containerized, persist that directory outside the writable container layer.

Merge the following keys into the existing YAML; do not paste duplicate `systemLog`, `setParameter`, `security` or `net` sections. Preserve the existing storage path, listener limits, TLS and `authorization: enabled`. The file paths must match the service's permitted mounts and security policy.

```yaml
systemLog:
  destination: file
  path: /var/log/mongodb/ch44-server.log
  logAppend: true
  logRotate: rename
auditLog:
  destination: file
  format: JSON
  schema: mongo
  path: /var/log/mongodb/ch44-audit/audit.json
  filter: >-
    {"$or":[
      {"atype":"authenticate"},
      {"atype":"authCheck","result":{"$ne":0}},
      {"atype":{"$in":["createUser","dropUser","updateUser","createRole","dropRole","updateRole","grantRolesToUser","revokeRolesFromUser","grantRolesToRole","revokeRolesFromRole","grantPrivilegesToRole","revokePrivilegesFromRole"]}},
      {"atype":{"$in":["createCollection","dropCollection"]},"param.ns":"mongodb_enterprise_tutorial_ch44.events"},
      {"atype":"authCheck","result":0,"param.ns":"mongodb_enterprise_tutorial_ch44.events"}
    ]}
setParameter:
  auditAuthorizationSuccess: true
```

Restart **only this dedicated lab service** using its documented supervisor procedure. Inspect the service status, diagnostic log, audit-file owner/mode and remaining disk space. Re-run `gate44.js` and a TLS administrator login before any fixture operation. Save a hash of the deployed config in the protected evidence bundle; do not export secret-bearing configuration into public tutorial evidence.

If startup fails, restore the backed-up configuration and investigate unsupported options, filter syntax, duplicate YAML keys, SELinux/AppArmor restrictions and path permissions. Do not remove TLS or authorization to recover. A restored service is recovery evidence, not audit acceptance.

## 7. Static versus runtime audit configuration

This lab uses startup configuration. Changing its filter requires a restart. MongoDB also supports runtime audit filter management; enabling `auditLog.runtimeConfiguration: true` requires removing startup `auditLog.filter` and `auditAuthorizationSuccess`. Combining them prevents startup.

For a production runtime design, review `auditConfig`, privileges, participating processes, persistence and distribution behavior against the exact deployment. Keep a versioned policy and a tested rollback. Do not mix the static lab recipe with runtime management or assume a runtime change reached every cluster process.

After startup, inspect effective options locally through an administrator session:

```javascript
const opts44 = db.adminCommand({getCmdLineOpts: 1});
if (opts44.ok !== 1) throw new Error('Cannot inspect effective options');
print(EJSON.stringify({auditLog: opts44.parsed.auditLog,
  auditAuthorizationSuccess: opts44.parsed.setParameter?.auditAuthorizationSuccess}, null, 2));
```

Compare the effective destination, schema, path and filter with the approved policy. Inspect output before sharing it. Effective configuration is necessary evidence; generated events are still required to prove coverage.

## 8. Create owned least-privilege fixtures

Save `scripts/setup44.js` and execute once as administrator. It refuses pre-existing data, roles or users rather than dropping them.

```javascript
const lab44 = db.getSiblingDB('mongodb_enterprise_tutorial_ch44');
if (lab44.getCollectionInfos().length || lab44.getUsers().users.length ||
    lab44.getRoles({showBuiltinRoles: false}).roles.length) {
  throw new Error('Refusing a nonempty fixture database');
}
lab44.createCollection('events');
lab44.events.insertMany([
  {_id: 'ch44-1', source: 'audit-lab', value: 1},
  {_id: 'ch44-2', source: 'audit-lab', value: 2}
]);
lab44.createRole({role: 'ch44_find_events', roles: [], privileges: [
  {resource: {db: lab44.getName(), collection: 'events'}, actions: ['find']}
]});
print('Choose a unique lab-reader password:');
lab44.createUser({user: 'ch44_reader', pwd: passwordPrompt(),
  mechanisms: ['SCRAM-SHA-256'], roles: [
    {role: 'ch44_find_events', db: lab44.getName()}
  ], customData: {owner: 'chapter44-audit-lab'}});
const user44 = lab44.getUser('ch44_reader');
const collection44 = lab44.getCollectionInfos({name: 'events'})[0];
print(EJSON.stringify({database: lab44.getName(), userId: user44.userId,
  collectionUUID: collection44.info.uuid, createdAt: new Date()}, null, 2));
```

```bash
audit_admin44 --quiet --file scripts/setup44.js
```

Record the printed identifiers privately. A partial setup failure needs inspection and recovery before rerun; do not turn the guard into automatic overwrite. The reader has only `find` on `events`, not the built-in broad `read` role.

## 9. Generate successful access and a denied write

Save `scripts/reader44.js`:

```javascript
const lab44 = db.getSiblingDB('mongodb_enterprise_tutorial_ch44');
const start44 = new Date();
const rows44 = lab44.events.find({source: 'audit-lab'}).sort({_id: 1}).toArray();
if (rows44.length !== 2 || rows44[0]._id !== 'ch44-1' || rows44[1]._id !== 'ch44-2') {
  throw new Error('Unexpected fixture data');
}
const denied44 = lab44.runCommand({insert: 'events', documents: [
  {_id: 'ch44-forbidden', source: 'audit-lab', value: 99}
]});
if (denied44.ok !== 0 || denied44.code !== 13) {
  throw new Error('Expected Unauthorized code 13');
}
print(EJSON.stringify({start: start44, end: new Date(), reads: rows44.length,
  deniedInsertCode: denied44.code, applicationAssertions: 'passed'}, null, 2));
```

```bash
audit_reader44 --quiet --file scripts/reader44.js
```

Record the time window and assertions. As administrator, independently verify that `ch44-forbidden` is absent and the fixture still contains exactly two documents:

```javascript
const lab44 = db.getSiblingDB('mongodb_enterprise_tutorial_ch44');
if (lab44.events.countDocuments({}) !== 2 ||
    lab44.events.findOne({_id: 'ch44-forbidden'}) !== null) {
  throw new Error('Denied-write state verification failed');
}
print('Independent data-state verification passed');
```

This supplies three different observations: application denial, audit authorization denial, and unchanged data. Do not label an `authCheck` success as a successful CRUD operation.

## 10. Generate an authentication failure

Run the reader wrapper again, intentionally supplying a wrong password at its prompt:

```bash
audit_reader44 --quiet --eval 'db.runCommand({ping: 1})'
```

Expect authentication failure and a nonzero client exit. Record the exit status immediately (`echo "$?"`) and the UTC time window. Never save either the correct or intentionally wrong password in evidence.

Find a native `authenticate` event for `param.user: ch44_reader`, `param.db: mongodb_enterprise_tutorial_ch44`, with result `18`. Failed attempts can have an empty `users` array. A timeout, TLS failure or DNS error does not prove failed database authentication; those happen before this audit event.

## 11. Rotate and preserve a closed evidence segment

With the file-based diagnostic log and `logRotate: rename` configured, rotate only the audit log as administrator:

```javascript
const rotate44 = db.adminCommand({logRotate: 'audit', comment: 'chapter44-coverage-boundary'});
if (rotate44.ok !== 1) throw new Error('Audit rotation failed');
print(EJSON.stringify({rotation: 'audit', observedAt: new Date()}, null, 2));
```

On the server, identify the newly closed timestamp-suffixed file and verify that a new `audit.json` exists with correct permissions. Do not assume the rotation comment is captured by this filter, or use rotation as a universal flush guarantee. If required events are missing from the closed segment, inspect adjacent segments and retain the gap as an unresolved coverage issue.

Copy the **closed segment** using your approved secure transfer method to `evidence/audit-closed.json`. Preserve the original file, its hash, source process, version, policy hash, timezone, capture window and rotation response. Do not analyze a live file that may end halfway through an event.

```bash
test -s evidence/audit-closed.json
sha256sum evidence/audit-closed.json > evidence/audit-closed.sha256
chmod 600 evidence/audit-closed.json evidence/audit-closed.sha256
```

For BSON output, retain the raw BSON and convert a closed copy with `bsondump` into a separate JSON file. Record the tool version and transformation. A successful conversion is not proof of source completeness.

## 12. Analyze native events without hiding malformed input

Save `scripts/analyze44.py`. It accepts newline-delimited native JSON, validates the fields it uses, reports aggregates without printing raw arguments, and checks five fixture expectations. It intentionally rejects OCSF, malformed/truncated JSON, empty input and incomplete coverage. It is a lab checker, not a production SIEM or cryptographic completeness verifier.

```python
import collections
import datetime
import json
import pathlib
import sys

DB = "mongodb_enterprise_tutorial_ch44"
NS = DB + ".events"
USER = "ch44_reader"

def analyze(path):
    counts = collections.Counter()
    found = set()
    times = []
    with pathlib.Path(path).open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise ValueError("event must be an object")
                atype = event["atype"]
                result = event["result"]
                param = event["param"]
                users = event["users"]
                stamp = event["ts"]["$date"]
                if not isinstance(atype, str) or type(result) is not int:
                    raise ValueError("invalid action/result")
                if not isinstance(param, dict) or not isinstance(users, list):
                    raise ValueError("invalid param/users")
                for user in users:
                    if not isinstance(user, dict) or not isinstance(user.get("user"), str) or not isinstance(user.get("db"), str):
                        raise ValueError("invalid identity")
                if not isinstance(stamp, str):
                    raise ValueError("expected ISO timestamp")
                when = datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                if when.tzinfo is None:
                    raise ValueError("timestamp lacks timezone")
                times.append(when.astimezone(datetime.timezone.utc))
            except (ValueError, KeyError, TypeError) as error:
                raise ValueError(f"line {number}: invalid native event: {error}") from error
            counts[(atype, result)] += 1
            reader = any(u["user"] == USER and u["db"] == DB for u in users)
            target_reader = param.get("user") == USER and param.get("db") == DB
            if atype == "authenticate" and target_reader and result == 0:
                found.add("reader_authentication_success")
            if atype == "authenticate" and target_reader and result == 18:
                found.add("reader_authentication_failure")
            if atype == "authCheck" and reader and param.get("ns") == NS:
                if param.get("command") == "find" and result == 0:
                    found.add("reader_find_authorized")
                if param.get("command") == "insert" and result == 13:
                    found.add("reader_insert_denied")
            if atype == "createUser" and target_reader and result == 0:
                found.add("reader_created")
    if not times:
        raise ValueError("no native events")
    expected = {"reader_authentication_success", "reader_authentication_failure",
                "reader_find_authorized", "reader_insert_denied", "reader_created"}
    missing = sorted(expected - found)
    return {"events": sum(counts.values()), "first": min(times).isoformat(),
            "last": max(times).isoformat(), "counts": [
                {"atype": key[0], "result": key[1], "count": count}
                for key, count in sorted(counts.items())],
            "observed": sorted(found), "missing": missing,
            "fixture_coverage": "incomplete" if missing else "observed",
            "runtime_acceptance": "requires independent application and operational evidence"}

if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise ValueError("usage: analyze44.py CLOSED_NATIVE_JSON_FILE")
        report = analyze(sys.argv[1])
        print(json.dumps(report, indent=2))
        sys.exit(2 if report["missing"] else 0)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
```

```bash
python3 scripts/analyze44.py evidence/audit-closed.json > evidence/analysis.json
```

Exit `0` means the five expected signatures were observed; `2` means coverage is incomplete; `1` means input or parsing failed. All three require interpretation. A syntactically valid log could still omit events, duplicate them, or contain old fixture events. Use a fresh service/evidence window and reconcile timestamps with Sections 8–10. The checker has no claim of tamper detection, provenance verification or full policy coverage.

## 13. Test the analyzer offline and extend analysis

Save `scripts/test_analyze44.py`. Fixtures below are **synthetic** and must never be mixed into runtime evidence.

```python
import json
import pathlib
import tempfile
import unittest
from analyze44 import analyze, DB, NS, USER

def event(atype, result, param, reader=False):
    return {"atype": atype, "result": result, "param": param,
            "ts": {"$date": "2026-01-01T00:00:00Z"},
            "users": [{"user": USER, "db": DB}] if reader else []}

class AnalyzerTests(unittest.TestCase):
    def check(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "synthetic.json"
            path.write_text("\n".join(rows) + "\n", encoding="utf-8")
            return analyze(path)

    def fixture(self):
        return [event("authenticate", 0, {"user": USER, "db": DB}),
                event("authenticate", 18, {"user": USER, "db": DB}),
                event("authCheck", 0, {"command": "find", "ns": NS}, True),
                event("authCheck", 13, {"command": "insert", "ns": NS}, True),
                event("createUser", 0, {"user": USER, "db": DB})]

    def test_complete(self):
        report = self.check([json.dumps(e) for e in self.fixture()])
        self.assertEqual(report["missing"], [])
        self.assertEqual(report["events"], 5)

    def test_wrong_identity_or_namespace(self):
        rows = self.fixture()
        rows[2]["users"][0]["user"] = "other"
        rows[3]["param"]["ns"] = DB + ".other"
        report = self.check([json.dumps(e) for e in rows])
        self.assertEqual(report["missing"], ["reader_find_authorized", "reader_insert_denied"])

    def test_invalid_input(self):
        for rows in ([], ['{"atype":'], ['{"class_uid":3002}'],
                     [json.dumps({**self.fixture()[0], "result": True})]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.check(rows)

if __name__ == "__main__":
    unittest.main()
```

```bash
python3 scripts/test_analyze44.py
```

Offline tests prove parser behavior only. For broader production analysis, group failed authentications by target identity and source endpoint, authorization failures by actor and namespace, and user/role changes by actor and target. Apply rate-based thresholds relative to normal workloads. Repeated failure counts alone do not distinguish attacks from a stale application credential.

Keep raw events protected. Share a minimized aggregate when it satisfies the investigation, with a reference to the protected evidence location. Hashes help detect later changes to a retained copy; they do not prove who created it or whether upstream events were omitted.

## 14. Measure volume, latency and failure behavior

Measure the same controlled workload before and after the audit change on this dedicated service. Use equivalent data, concurrency, warm-up and duration; record policy, binary and hardware. Compare p50/p95/p99 latency, throughput, CPU, memory, audit bytes per second and collector lag. Do not present this chapter's small two-document fixture as an overhead benchmark.

For an observed audit rate `R` bytes/second, a collector outage budget `T` seconds and retention duration `D` seconds, estimate separate budgets:

| Budget | Initial estimate | Additional allowance |
|---|---|---|
| Local outage buffer | `R × T` | Burst rate, rotation overlap, filesystem reserve |
| Retained evidence | `R × D` | Compression behavior, indexes, replication and backups |

Use measurements rather than an invented universal multiplier. Rotation alone does not bound disk usage; add approved archival and expiry procedures that never delete an active file or unshipped required evidence.

MongoDB buffers audit events. Events from one connection are ordered. For operations affecting durable database state, MongoDB writes their audit events before the corresponding journal entry. Other events can be lost if the process terminates before audit flush, even after the client receives a response. If the server cannot write to the audit destination, it terminates. Monitor destination capacity and write errors as availability risks.

Do not fill the retained service's disk to test this. If failure injection is required, use a separate disposable instance with a small dedicated audit filesystem, preserve the administrator recovery path, document the expected termination and prove recovery after restoring writable space. No such injection is claimed by this chapter's static checks.

## 15. Troubleshooting, cleanup and recovery

| Symptom | Investigate | Evidence needed before closure |
|---|---|---|
| Server rejects audit options | Community binary, version, YAML merge | Enterprise gate and successful protected restart |
| No successful `find` event | Success parameter, filter namespace, schema | Effective policy and a fresh matching event |
| Failed login absent | TLS/DNS failure, wrong filter branch, delayed flush | Client layer, time window and adjacent closed segments |
| Permission denied on audit path | UID/GID, mount, MAC policy, read-only filesystem | Writable owned path without broad permission changes |
| Analyzer exits 1 | Truncated file, OCSF/BSON input, timestamp format | Correct closed native JSON and verified conversion |
| Analyzer exits 2 | Missing coverage, wrong window, filtered events | Resolve every missing signature; never delete the assertion |
| Service terminates during writes | Space, permissions, audit destination errors | Restored destination and administrator/data checks |

Before cleanup, record the actual `userId` and collection UUID from setup. In a fresh administrator session, inspect them again and compare with your private ownership record. **Only after both match**, remove the owned fixtures:

```javascript
const lab44 = db.getSiblingDB('mongodb_enterprise_tutorial_ch44');
const user44 = lab44.getUser('ch44_reader');
const collection44 = lab44.getCollectionInfos({name: 'events'})[0];
print(EJSON.stringify({userId: user44?.userId, collectionUUID: collection44?.info.uuid}, null, 2));
```

The following block is a separate action after that comparison, not an automatic continuation:

```javascript
const lab44 = db.getSiblingDB('mongodb_enterprise_tutorial_ch44');
if (lab44.getUser('ch44_reader')?.customData?.owner !== 'chapter44-audit-lab') {
  throw new Error('Ownership marker mismatch');
}
if (!lab44.dropUser('ch44_reader')) throw new Error('User removal failed');
if (!lab44.dropRole('ch44_find_events')) throw new Error('Role removal failed');
if (!lab44.events.drop()) throw new Error('Collection removal failed');
if (lab44.getUsers().users.length || lab44.getRoles({showBuiltinRoles: false}).roles.length ||
    lab44.getCollectionInfos().length) throw new Error('Unexpected remaining fixture state');
print('Owned chapter44 fixtures removed');
```

Rotate again and preserve cleanup events before disposing of the dedicated service. The filter includes `dropUser`, `dropRole` and fixture `dropCollection`; inspect those records. Retain protected evidence according to the lab policy. If the service remains in use, restore its approved pre-lab policy through the same reviewed restart workflow and verify TLS, administrator login and writable logging. Do not restore a plaintext configuration or disable audit obligations on a shared service.

The retained Chapter 41–43 TLS service and Chapter 35 sharded cluster remain available for subsequent exercises.

## 16. Acceptance checklist and review questions

| Check | Required observation | Status for this authored chapter |
|---|---|---|
| Edition and topology | Authorized Enterprise 8.0 dedicated standalone | Runtime pending |
| Configuration | Effective native schema, filter, success parameter, TLS/auth retained | Runtime pending |
| Positive control | Reader sees the two expected rows | Runtime pending |
| Negative controls | Wrong-password failure; insert denied with code 13; no inserted document | Runtime pending |
| Audit coverage | Five analyzer signatures plus collection/role and cleanup event inspection | Runtime pending |
| Evidence handling | Closed segments, hashes, provenance and protected storage | Runtime pending |
| Rotation/recovery | Fresh writable file and working independent administrator | Runtime pending |
| Overhead | Equivalent workload measurements and capacity/collector monitoring | Runtime pending |
| Analyzer | Complete, missing, wrong-identity/namespace and malformed synthetic cases | Offline tests only |

Do not mark runtime acceptance from a successful synthetic fixture, a generated configuration, or a Community run. A real deployment acceptance record must include observed outputs and unresolved exceptions.

Review questions:

1. Why can an authorization-success event exist for a write that never commits?
2. Why does filtering failed authentication by the authenticated `users` array miss evidence?
3. Which configuration combination prevents runtime-audit startup?
4. Why does a router-only audit deployment leave coverage gaps?
5. How do rotation, collection lag and audit-path failures affect availability and retention?
6. What can a hash and this analyzer prove, and what remains unproven?

## 17. References and next chapter

Use the documentation matching your exact server release:

- [Auditing and audit guarantees](https://www.mongodb.com/docs/v8.0/core/auditing/)
- [Configure auditing and runtime audit management](https://www.mongodb.com/docs/v8.0/tutorial/configure-auditing/)
- [Configure audit filters](https://www.mongodb.com/docs/v8.0/tutorial/configure-audit-filters/)
- [Native mongo schema audit messages](https://www.mongodb.com/docs/v8.0/reference/audit-message/mongo/)
- [Audit and server log rotation](https://www.mongodb.com/docs/v8.0/reference/command/logrotate/)
- [Configuration options](https://www.mongodb.com/docs/v8.0/reference/configuration-options/)

Next: [**Chapter 45 — Encryption at Rest and Key Management**](45-encryption-at-rest-and-key-management.md).

Previous: [Chapter 43 — Enterprise External Authentication Compatibility](43-enterprise-external-authentication-compatibility.md).
