# 56 — Restore Drill and Recovery Acceptance Project

Part 7 — Backup Recovery and Disaster Recovery

**Baseline:** MongoDB 8.0/FCV 8.0, compatible pinned Database Tools; Linux Docker lab from Chapter 54.  
**Status:** Written; static review complete; live restore drill and recovery acceptance pending.  
**Prerequisites:** Chapters 49–55, Python 3, Docker, OpenSSL, the saved Chapter 54 scripts and an approved isolated lab host.

## 1. Define the project and its acceptance boundary

Run a fresh recovery exercise, collect independent observations, measure the recovery interval, reconcile lost acknowledged writes, and produce a reviewable acceptance packet. The required track is the authenticated TLS replica-set drill from [Chapter 54](54-replica-set-disaster-recovery.md). Chapter 55 supplies an optional, separately assessed sharded track.

This chapter adds an evidence evaluator and an operational acceptance process. It does not create another backup mechanism or replace the restore instructions. Complete the referenced drill commands in their stated order. A successful evaluator means the supplied evidence meets this project's contract; it is not independent verification of the host, operator identity, or production infrastructure.

The mandatory contract covers `mongodb_enterprise_tutorial_ch54`: 100 restored orders, 50,500 cents, exact documents, collection options and indexes, three healthy voting data-bearing recovery members, both secondary reads, fresh scoped application access and explicit acceptance of missing order 101 worth 1,010 cents. Credentials and infrastructure are separately provisioned. No production traffic is cut over.

## 2. Assign roles and freeze success criteria

| Role | Responsibility | Output |
|---|---|---|
| Drill lead | Scope, timestamps, incident coordination and abort decision | Approved exercise contract |
| Restore operator | Build isolated recovery, retrieve artifacts, execute restore | Command logs and recovery observations |
| Application reviewer | Reconcile business state and exercise application credentials | Loss decision and application evidence |
| Infrastructure reviewer | Verify ownership, isolation, source fence and restart controls | Fence review |
| Acceptance owner | Review all gates and authorize the next operational step | Named decision and retention instructions |

One learner can play all roles in the disposable lab but must label that limitation. A production drill should include an operator who did not create the backup: recovering requires usable instructions, credentials and keys, not only the original author's knowledge.

Set maximum recovery time and allowed data loss before the incident simulation. This fixture intentionally loses one acknowledged write; choose a one-write loss budget only if the exercise owner accepts that design. A zero-loss contract must reject this drill result. Do not increase the budget after seeing a slow or incomplete recovery merely to obtain a pass.

## 3. Select a fresh drill and establish isolation

Execute Chapter 54 in a new `mongodb-ch54` directory on a clean approved lab host, with a new run ID, CA, leaf certificates, keyfiles, credentials and source/recovery data paths. Its fixed Docker names require the previous owned exercise to be safely retired first, or a different host. Do not repoint its helpers at an existing service.

Use the exact pinned image and tools recorded for that run. Recover into the different `rs54recovery` set on its own internal network; source is `rs54source`. Keep both endpoint inventories in the packet. Do not copy source users or internal keyfiles as a substitute for the separately provisioned recovery identities.

Prepare the acceptance workspace alongside the drill, outside MongoDB data paths:

```bash
umask 077
mkdir mongodb-ch56
cd mongodb-ch56
export LAB56_ROOT="$PWD"
mkdir scripts input output
test -d "${LAB54_ROOT:?set the absolute fresh Chapter 54 workspace}/evidence"
test -f "$LAB54_ROOT/evidence/run54.txt"
```

At this preparation stage, Chapter 54 need only have reached workspace creation. The acceptance packet is assembled after the live exercise. This chapter never deletes either workspace.

## 4. Record the exercise contract before capture

Save `input/contract56.json` with the real run ID and reviewer names. The following is a template, not an accepted result. The evaluator rejects its placeholder values. Replace the budgets only through a reviewed pre-drill decision.

```json
{
  "schema": 1,
  "runId": "REPLACE_WITH_FRESH_RUN54",
  "track": "replica54",
  "scope": "mongodb_enterprise_tutorial_ch54",
  "maxRecoverySeconds": 1800,
  "maxLostAcknowledgedWrites": 1,
  "maxLostAmountCents": 1010,
  "lead": "REPLACE_WITH_LEAD",
  "acceptanceOwner": "REPLACE_WITH_OWNER",
  "approvedBeforeDrill": "REPLACE_WITH_UTC_TIMESTAMP"
}
```

Keep a separately retained copy or a repository commit of this contract before backup capture begins. The JSON timestamp alone does not prove when approval occurred. Use a ticket or other audit record for production exercises. Time-zone-aware ISO timestamps are required; prefer UTC ending in `Z`.

The recovery time budget here is incident simulation to completion of all Chapter 54 acceptance probes. It excludes any production endpoint migration because this lab does not perform one. Call it **lab recovery readiness time**, not demonstrated production RTO.

## 5. Capture the recovery point and provenance

Follow Chapter 54 through idle dataset capture and archive integrity verification. Record the application pause, absence of competing writers/DDL, server and FCV observations, tool versions, image digest, capture start/end, archive checksum and exact source fixture.

The application dataset is quiet during this scoped logical capture. Its capture interval is not a PITR window. `--oplogReplay` is not added to this archive: replica-set oplog replay requires the appropriate full backup workflow and compatible options. Chapter 52's managed recovery point and Chapter 55's coordinated sharded capture are separate procedures.

Retrieve artifacts through the actual recovery access path. A successful checksum on the original host proves neither off-host retention nor disaster access. For a production exercise, also test access from the intended recovery environment with the backup repository, decryption keys and identity provider available under the incident conditions.

| Evidence | Failure that it helps detect |
|---|---|
| Archive hash plus successful capture exit | Truncation, substitution or failed capture |
| Full fixture digest and collection metadata | Wrong database, missing rows, changed indexes/options |
| Version/FCV/tools inventory | Unsupported restore assumptions |
| Repository and key retrieval observation | Backup exists but cannot be recovered under incident access |
| Stated pause/coordination boundary | Inconsistent application state hidden by count-only checks |

## 6. Inject the incident and declare expected loss

Continue Chapter 54: acknowledge order 101 after capture, save its acknowledgment externally, record the incident timestamp, stop every source member and verify the scoped Docker fence. The source then had 101 orders and 51,510 cents, while the recovery point contains 100 orders and 50,500 cents.

The expected difference is exactly one acknowledged order worth 1,010 cents. A sum difference without ID reconciliation is insufficient: an unrelated missing row and an erroneous extra row could cancel out. Retain the complete baseline digest, acknowledgment and restored digest.

Do not start the old source to “check one more thing” after recovery becomes authoritative. For this lab, the source remains stopped until reviewed cleanup. Production fencing must additionally control actual restart automation, application access and all surviving endpoints; DNS replacement alone does not cover old client pools.

## 7. Restore and validate before application acceptance

Complete Chapter 54's recovery bootstrap, empty target preflight, archive restore, seed verification, sequential member additions and primary acceptance. Keep restore logs and require a successful tool exit. Restore completion is a milestone, not the end of the recovery timer.

Verify exact orders, unique index, strict validator, expected owner marker and separate recovery identity. Logical restore creates new collection UUIDs; the recovery UUID need not equal the source UUID. Source identity checks protect against accidentally replacing the fixture before capture.

Run full collection validation only in this isolated exercise under the planned maintenance conditions. It can block collection operations and add substantial I/O. A valid storage result does not prove correct business meaning, complete backup scope, or authorization. Review warnings/errors rather than treating the presence of a `validate` response as success.

Finish both direct secondary majority-read probes and the fresh application credential probe. Confirm the latter can issue the expected majority write but is denied the administrative operation. Do not substitute an administrator connection for application acceptance.

## 8. Collect a final fence and review statement

After all Chapter 54 probes finish, re-run its `docker inspect` inventory command for all three source members and its `fence54.py` helper. Save the inventory as `evidence/fence-final56.jsonl`. This is a fresh observation close to the acceptance decision; the earlier fence does not establish that nothing restarted later.

Record the observation time immediately after the inventory succeeds:

```bash
date -u +'%Y-%m-%dT%H:%M:%SZ' > "$LAB54_ROOT/evidence/fence-final56.txt"
```

Save `input/review56.json` only after inspecting the logs, contract, identities, restore exit, checksum, fence and access observations. Use actual names and a real timestamp. The booleans are explicit reviewer assertions, not automatic measurements. Unsupported or unperformed checks remain false and fail the gate.

```json
{
  "runId": "REPLACE_WITH_FRESH_RUN54",
  "reviewedAt": "REPLACE_WITH_UTC_TIMESTAMP",
  "reviewer": "REPLACE_WITH_REVIEWER",
  "backupExitSuccessful": false,
  "restoreExitSuccessful": false,
  "archiveChecksumVerified": false,
  "isolationAndRecoveryIdentityReviewed": false,
  "versionsAndFCVReviewed": false,
  "lossAccepted": false,
  "sourceFenceReviewed": false,
  "logsReviewed": false,
  "cutoverDecision": "lab-ready-only"
}
```

For a real cutover, record separate named authorization and infrastructure evidence. This project's `lab-ready-only` decision does not authorize production routing changes.

## 9. Assemble an immutable evidence packet

Copy the exact files from this one run. Do not mix old successful probes with a newer failed restore. Chapter 54's JSON outputs use Extended JSON for some numeric/date values; the evaluator below supports that encoding for the fields it reads.

```bash
cp "$LAB54_ROOT/evidence/run54.txt" input/
for file56 in state54.json baseline54.json later-ack54.json seed54.json \
  primary-accepted54.json r54b-accepted54.json r54c-accepted54.json app-accepted54.json \
  capture-start54.txt capture-end54.txt incident54.txt restore-start54.txt \
  recovery-accepted54.txt fence-final56.jsonl fence-final56.txt; do
  test -f "$LAB54_ROOT/evidence/$file56" || exit 1
  cp "$LAB54_ROOT/evidence/$file56" input/
done
```

Retain the original archive, hash file, command logs, TLS public inventory and provisioning records under the drill's retention policy. Do not put passwords, private keys, keyfiles or tokens into the acceptance report or Git repository. This compact packet references the reviewed checksum outcome; it does not rehash an archive absent from the packet.

Avoid changing input after evaluation. If evidence needs correction, create a new packet/version, explain the correction and re-run the evaluator. Do not overwrite a passed result to hide a failed attempt.

## 10. Implement the fail-closed evaluator

Save as `scripts/accept56.py`. It reads only local files and never connects to MongoDB, changes routes or deletes resources. It rejects missing evidence, cross-run records, wrong fixture/digest, unhealthy redundancy, loss over budget, unordered timestamps, stale final fencing and incomplete review assertions.

```python
import datetime as dt
import hashlib
import json
import pathlib
import sys

REVIEW_FLAGS = (
    'backupExitSuccessful', 'restoreExitSuccessful', 'archiveChecksumVerified',
    'isolationAndRecoveryIdentityReviewed', 'versionsAndFCVReviewed',
    'lossAccepted', 'sourceFenceReviewed', 'logsReviewed')
JSON_FILES = ('state54.json', 'baseline54.json', 'later-ack54.json', 'seed54.json',
              'primary-accepted54.json', 'r54b-accepted54.json',
              'r54c-accepted54.json', 'app-accepted54.json')

def require(ok, message):
    if not ok:
        raise ValueError(message)

def normalize(value):
    if isinstance(value, list):
        return [normalize(x) for x in value]
    if isinstance(value, dict):
        if set(value) in ({'$numberInt'}, {'$numberLong'}):
            return int(next(iter(value.values())))
        if set(value) == {'$numberDouble'}:
            return float(value['$numberDouble'])
        if set(value) == {'$date'}:
            raw = value['$date']
            if isinstance(raw, dict) and set(raw) == {'$numberLong'}:
                return dt.datetime.fromtimestamp(int(raw['$numberLong']) / 1000,
                                                 dt.timezone.utc).isoformat()
            return raw
        return {k: normalize(v) for k, v in value.items()}
    return value

def timestamp(raw):
    require(isinstance(raw, str), 'timestamp must be text')
    value = dt.datetime.fromisoformat(raw.strip().replace('Z', '+00:00'))
    require(value.tzinfo is not None and value.utcoffset() is not None,
            'timezone-aware timestamp required')
    return value.astimezone(dt.timezone.utc)

def named(raw):
    return isinstance(raw, str) and bool(raw.strip()) and 'REPLACE' not in raw

def evaluate(root):
    root = pathlib.Path(root)
    def read(name):
        p = root / name
        require(p.is_file() and not p.is_symlink(), 'missing/linked evidence: ' + name)
        return p.read_text(encoding='utf-8')
    def record(name):
        obj = normalize(json.loads(read(name)))
        require(isinstance(obj, dict), 'object required: ' + name)
        return obj
    contract, review = record('contract56.json'), record('review56.json')
    run = read('run54.txt').strip()
    require(named(run) and contract['runId'] == run and review['runId'] == run,
            'contract/review run mismatch')
    require(type(contract['schema']) is int and contract['schema'] == 1 and
            contract['track'] == 'replica54' and
            contract['scope'] == 'mongodb_enterprise_tutorial_ch54', 'wrong contract')
    for field in ('maxRecoverySeconds', 'maxLostAcknowledgedWrites', 'maxLostAmountCents'):
        require(type(contract[field]) is int and contract[field] >= 0, 'invalid budget')
    require(all(named(contract[k]) for k in ('lead', 'acceptanceOwner')) and
            named(review['reviewer']), 'named reviewers required')
    require(all(review.get(k) is True for k in REVIEW_FLAGS), 'incomplete review')
    require(review['cutoverDecision'] == 'lab-ready-only', 'wrong decision scope')
    data = {name: record(name) for name in JSON_FILES}
    require(all(x.get('runId') == run for x in data.values()), 'mixed evidence runs')
    base = data['baseline54.json']['result']
    digest = base['digest']
    require(isinstance(digest, str) and len(digest) == 64 and
            all(c in '0123456789abcdef' for c in digest), 'invalid baseline digest')
    for name in ('baseline54.json', 'seed54.json', 'primary-accepted54.json'):
        result = data[name]['result']
        require(result['count'] == 100 and result['amountCents'] == 50500 and
                result['digest'] == digest, 'restored business state mismatch: ' + name)
    later = data['later-ack54.json']
    require(later['acknowledgedIdsOutsideBackup'] == [101] and
            later['result']['count'] == 101 and later['result']['amountCents'] == 51510,
            'unexpected acknowledged history')
    primary = data['primary-accepted54.json']
    require(primary['unrecoveredAcknowledgedIds'] == [101] and
            primary['unrecoveredAmountCents'] == 1010, 'loss reconciliation differs')
    require(contract['maxLostAcknowledgedWrites'] >= 1 and
            contract['maxLostAmountCents'] >= 1010, 'loss budget exceeded')
    members = primary['status']['members']
    require(len(members) == 3 and {m['name'] for m in members} ==
            {'r54a:27017', 'r54b:27017', 'r54c:27017'}, 'wrong recovery members')
    require(all(m['health'] == 1 for m in members) and
            sorted(m['state'] for m in members) == [1, 2, 2], 'unhealthy recovery topology')
    valid = primary['validation']
    require(valid['ok'] == 1 and valid['valid'] is True and
            not valid.get('errors') and not valid.get('warnings'), 'storage validation failed')
    for host in ('r54b', 'r54c'):
        secondary = data[host + '-accepted54.json']
        require(secondary['host'] == host and secondary['count'] == 100 and
                secondary['majorityMarkerVisible'] is True, 'secondary probe incomplete')
    app = data['app-accepted54.json']
    require(app['majorityWriteSucceeded'] is True and app['adminDenied'] is True,
            'application contract failed')
    times = {key: timestamp(read(name)) for key, name in (
        ('capture_start', 'capture-start54.txt'), ('capture_end', 'capture-end54.txt'),
        ('incident', 'incident54.txt'), ('restore_start', 'restore-start54.txt'),
        ('accepted', 'recovery-accepted54.txt'), ('fence', 'fence-final56.txt'))}
    ordered = [timestamp(contract['approvedBeforeDrill']), times['capture_start'],
               times['capture_end'], timestamp(later['acknowledgedAt']), times['incident'],
               times['restore_start']]
    require(ordered == sorted(ordered), 'invalid capture/incident ordering')
    probes = [timestamp(data[n]['observedAt']) for n in (
        'seed54.json', 'primary-accepted54.json', 'r54b-accepted54.json',
        'r54c-accepted54.json', 'app-accepted54.json')]
    # Host timestamps have second precision; probe dates can include milliseconds.
    require(all(times['restore_start'] <= p < times['accepted'] + dt.timedelta(seconds=1)
                for p in probes), 'probe outside recovery interval')
    reviewed = timestamp(review['reviewedAt'])
    require(times['accepted'] <= times['fence'] <= reviewed and
            (reviewed - times['fence']).total_seconds() <= 300, 'stale final fence')
    duration = (times['accepted'] - times['incident']).total_seconds()
    require(0 <= duration <= contract['maxRecoverySeconds'], 'recovery time budget exceeded')
    fence = [json.loads(line) for line in read('fence-final56.jsonl').splitlines() if line.strip()]
    require(len(fence) == 3 and {x['name'] for x in fence} ==
            {'/mongodb-ch54-s-a', '/mongodb-ch54-s-b', '/mongodb-ch54-s-c'}, 'wrong source inventory')
    require(all(x['run'] == run and x['running'] is False and x['restart'] == 'no' and
                isinstance(x['networks'], dict) and
                set(x['networks']) == {'mongodb-ch54_source'} for x in fence), 'source fence failed')
    files = sorted(p for p in root.iterdir() if p.is_file())
    require(all(not p.is_symlink() for p in files), 'linked packet file')
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    return {'schema': 1, 'claim': 'reviewed_lab_recovery_readiness', 'runId': run,
            'scope': contract['scope'], 'recoverySeconds': duration,
            'recoveryPointAgeAtIncidentSeconds':
                (times['incident'] - times['capture_end']).total_seconds(),
            'lostAcknowledgedIds': [101], 'lostAmountCents': 1010,
            'acceptanceOwner': contract['acceptanceOwner'], 'reviewer': review['reviewer'],
            'productionCutoverAuthorized': False, 'inputSha256': hashes}

if __name__ == '__main__':
    try:
        require(len(sys.argv) == 2, 'usage: accept56.py INPUT_DIRECTORY')
        print(json.dumps(evaluate(sys.argv[1]), indent=2, sort_keys=True))
    except (ValueError, KeyError, TypeError, OSError, OverflowError) as error:
        print('REJECTED: ' + str(error), file=sys.stderr)
        sys.exit(1)
```

The evaluator validates selected recorded fields, not every server response. Voting-member configuration, exact index/validator checks and rejected writes were verified by the Chapter 54 live scripts; versions, restore exit and isolation remain explicit review gates. Hashes bind this report to packet bytes but provide no signature or tamper-proof audit trail. Retain approved copies externally where required.

## 11. Run acceptance without preserving a failed result

Within five minutes of the final fence observation, complete the review and evaluate the packet. If that interval expires, obtain a new fence observation and review it. Do not alter its timestamp to make old evidence look fresh.

```bash
test ! -e output/accepted56.json || exit 1
python3 scripts/accept56.py input > output/candidate56.json
status56=$?
if [ "$status56" -ne 0 ]; then
  mv output/candidate56.json output/rejected56.stdout
  exit "$status56"
fi
mv output/candidate56.json output/accepted56.json
sha256sum scripts/accept56.py output/accepted56.json > output/report56.sha256
sha256sum -c output/report56.sha256
```

Run this block in a shell without an automatic exit that skips its error branch, or implement an equivalent reviewed wrapper. A rejected stdout file is never renamed to accepted. Keep stderr and command logs with the exercise record. A prior acceptance file requires a new output directory/version rather than overwrite.

No accepted output should exist before a real drill. The static tests in Section 12 must use separate temporary synthetic packets and do not count toward runtime validation.

## 12. Test rejection behavior independently

Before relying on the evaluator, build a synthetic packet in a temporary test directory with all required fields and clearly label its run as synthetic. Import `evaluate()` and assert a valid synthetic packet succeeds. Then mutate one condition at a time and require an exception or CLI exit 1.

| Mutation | Required outcome |
|---|---|
| Missing secondary probe | Reject incomplete evidence |
| Different run in application result | Reject mixed drill records |
| Seed digest differs despite matching count/sum | Reject business mismatch |
| One member unhealthy or wrong hostname | Reject redundancy claim |
| Application administrative rejection false | Reject excessive application access |
| Review flag set to string `"true"` | Reject non-boolean assertion |
| Source running set to string `"false"` | Reject invalid fence observation |
| Source attached to an extra network | Reject unexpected topology |
| Recovery time over agreed budget | Reject slow recovery |
| Loss budget zero | Reject this fixture's known loss |
| Naive timestamp or acceptance before restore | Reject invalid timing |
| Final fence older than five minutes at review | Reject stale final evidence |

Also test canonical Extended JSON numeric/date wrappers from a real Chapter 54-shaped record. These tests establish evaluator behavior only. They do not exercise MongoDB, certificates, backup tools, member initial sync or application credentials.

## 13. Interpret RPO, recovery time and uncertainty

The report gives three distinct observations: readiness time, point age at incident, and known lost acknowledged IDs/value. Point age is the interval from the end of this quiet capture to the incident; it is not proof of an enterprise-wide RPO or arbitrary PITR coverage.

| Measurement | Start/end or basis | Limitation |
|---|---|---|
| Capture duration | Capture start to capture end | Quiet scoped dataset, not managed replay window |
| Point age | Capture end to incident | Backup end is usable only under this quiet-state contract |
| Lab readiness time | Incident to completed recovery probes | Excludes production traffic transition |
| Known write loss | External acknowledgment versus restored IDs | Covers this controlled acknowledgment ledger |
| Fence recency | Final source inspection to review | Point observation; restart controls still required |

Host clock synchronization matters. Record clock source and any skew for real multi-host drills. For detailed component timing, add provisioning, repository access, restore/index construction, initial sync, validation and application checks to the event ledger. Keep total elapsed time; do not sum overlapping phases and label it RTO.

## 14. Extend acceptance to a sharded recovery

Run a fresh [Chapter 55](55-sharded-cluster-backup-and-disaster-recovery.md) separately. The Python evaluator intentionally rejects a sharded track; its fixture, topology and evidence names do not describe a sharded cluster. Write a separate reviewed adapter if machine evaluation is required.

| Sharded gate | Chapter 55 evidence and inspection |
|---|---|
| Consistent capture | Cluster-wide write pause, balancer stopped, owned fsync lock and confirmed unlock |
| Complete fence | Both routers and all nine source `mongod` services stopped; restart controls reviewed |
| Independent destination catalog | New cluster ID, fresh config servers and separately registered shard sets |
| Correct placement | Destination pre-sharded with expected key, two chunks and data on both shards before balancing resumes |
| Exact business state | 100 orders/505,000 cents, missing acknowledged ID 101 worth 10,100 cents |
| Routed application behavior | Both routers read correctly; cross-shard transaction commits both expected changes |
| Redundancy and policy | Healthy CSRS/shard replica sets; original target balancer policy restored only after checks |

Preserve the fresh target config catalog; do not restore the source `config` database into it or use `--drop` to remove the prepared sharding metadata. A coordinated physical or Ops Manager restore is a different supported recovery path with its own catalog consistency requirements.

Chapter 55's runnable fresh topology has an isolated no-auth baseline; this does not satisfy a production TLS/authentication acceptance claim. Add actual certificate, credential, authorization, key-management and application tests for the secured deployment being assessed. Report this scope difference explicitly.

## 15. Exercise failure handling and recovery decisions

Inject failures into copied evidence for evaluator testing. Operational failures should be introduced only into owned disposable resources with a reviewed recovery plan. Never corrupt the sole retained archive or remove the only decryption key.

| Observed failure | Decision and next action |
|---|---|
| Artifact hash differs | Stop; retrieve verified independent copy; retain failed artifact for investigation |
| Restore exits nonzero | Reject target; inspect logs; rebuild a fresh target rather than assuming partial state is clean |
| Wrong documents or missing metadata | Reject; identify backup scope/cutoff problem and repeat from authoritative evidence |
| Secondary still initial-syncing | Wait within budget; inspect storage/network/oplog constraints; do not waive redundancy |
| Source restarts | Suspend authority transition; restore actual fencing and review divergence risk |
| Authentication or TLS fails | Correct intended identity/trust material; do not bypass verification to pass |
| Loss exceeds budget | Reject or make a separately documented business exception; preserve original failed result |
| Budget exceeded but data valid | Report recovery technically valid and readiness objective failed; investigate critical path |

After the target accepts writes, failback requires deliberate resynchronization or migration from the current authoritative history. Starting the stale source is not a rollback of the restore. Preserve the source, backup, acknowledgment ledger and endpoint decisions until the incident review is complete.

## 16. Deliver the acceptance packet and clean up

Deliver the contract, reviewed decision, report with input hashes, original probe evidence, command logs, backup integrity record, infrastructure identities and retained artifact reference. Include failed attempts and explain any repeated stages. A ready-only lab decision should identify the production work still untested: independent region recovery, external dependency recovery, actual fencing, production credentials and endpoint migration.

Use this handoff template:

```text
Run / scope:
Source and recovery identities:
Backup mechanism / recovery point / artifact reference:
Agreed readiness and loss budgets:
Observed readiness time / known lost IDs and business value:
Data, metadata, storage, redundancy and application results:
Source fence evidence and restart controls:
Failed attempts and unresolved limitations:
Decision / named acceptance owner / timestamp:
Retention and next exercise actions:
```

Only after the owner reviews retention, capture final logs and perform Chapter 54's guarded cleanup for its exact owned containers/networks. The source must remain stopped. Keep bind-mounted data and private materials under the stated retention and secure disposal policy. The evaluator supplies no deletion command and grants no cleanup authority for unrelated resources.

Acceptance checklist: fresh one-run evidence; approved budgets; successful verified capture and restore; exact business reconciliation; healthy recovery redundancy; both secondary probes; constrained application access; declared loss accepted; final fence reviewed; measured readiness within budget; limitations stated; packet retained. Static evaluator tests alone leave this chapter's runtime status pending.

## 17. References and next chapter

- [Back Up and Restore with MongoDB Tools](https://www.mongodb.com/docs/manual/tutorial/backup-and-restore-tools/)
- [mongorestore options and restrictions](https://www.mongodb.com/docs/database-tools/mongorestore/)
- [MongoDB 8.0 collection validation](https://www.mongodb.com/docs/v8.0/reference/command/validate/)
- [Chapter 49 — Backup Architecture RPO and RTO](49-backup-architecture-rpo-and-rto.md)
- [Chapter 54 — Replica Set Disaster Recovery](54-replica-set-disaster-recovery.md)
- [Chapter 55 — Sharded Cluster Backup and Disaster Recovery](55-sharded-cluster-backup-and-disaster-recovery.md)

Next: **[Chapter 57 — Ops Manager Architecture and Prerequisites](57-ops-manager-architecture-and-prerequisites.md)**.
