# PostgreSQL V04-C — Authorized Staging Rehearsal Preflight

**State: NO_GO — genuine external evidence and independent authorization absent.**  
**Scope:** PostgreSQL 18 Chapters 049–050, explicitly approved staging only.  
**Actual staging rehearsal:** NOT EXECUTED.

## Strict limits

The V04-C [offline preflight](v04c_rehearsal_preflight.py) screens three private metadata packets:

1. [V04-A staging evidence manifest](v04_staging_evidence.template.json): change ticket, exact staging cluster, approved HA/PITR RPO/RTO, initial approvals, backup/WAL, candidate replay and fencing claims.
2. [V04-B independent reviewer packet](v04_independent_review.template.json): four distinct reviewer attestations and six independently supported evidence domains.
3. [V04-C rehearsal request template](v04c_rehearsal_request.template.json): exact cross-packet cluster/ticket/window identity, canonical SHA-256 bindings, two additional named authorities, and five short-lived observations.

The local checker does **not** authenticate source documents, confirm control-plane fencing or authorize any work. A fully populated packet yields **REQUIRES_LIVE_CHANGE_AUTHORITY_GO** (metadata complete) and **authorization=NONE / execution=NEVER / fencing_verified_by_tool=false**. Incomplete evidence yields **NO_GO** (exit code 2). There is no machine-issued operational GO outcome.

Do not upload real approver names, connection strings, private database endpoints, secrets, internal logs or evidence artifacts to the public repository. Store approved packets only in the organization's private evidence system.

## Hard prerequisites for a genuine staging-only rehearsal

| Gate | Required independent evidence | Blocker |
|---|---|---|
| Staging identity | Approved change window, exact PG18 system identifier, source/candidate identities and routes | Any mismatch: NO_GO |
| Replay freshness | Recent WAL/candidate replay observation and acknowledged test marker | Stale candidate: NO_GO |
| Physical and logical fencing | Old primary denied direct writes, restart, rescheduling, routing bypass and relevant storage ownership; separately observed | Any ambiguity: NO_GO |
| Recovery | Physical backup, off-node WAL continuity, isolated restore and rewind/rebuild fallback | Missing backup: NO_GO |
| Client service | Approved client-routing probes, connection pools, rollback and health thresholds | Unverified app plan: NO_GO |
| Approved objectives | Signed business HA RPO/RTO and PITR RPO/RTO, no synthetic targets | No targets: NO_GO |
| Authorities | Four original approvers, four separate independent V04-B reviewers, independent incident commander and change authority | Missing/duplicate: NO_GO |
| Abort conditions | Independent fencing and exactly-one-writer checks before and after promotion | Any failed check: NO_GO |

The V04-C packet additionally requires **five observations within the previous five minutes**: independent fencing, candidate replay, application health, backup/WAL recovery readiness and rollback readiness. The two V04-C authority attestations must also be fresh and separate from all original and review participants.

## Operator decision protocol (no executable infrastructure actions)

1. Independently verify the real staging environment and exact change ticket. Authenticate the referenced source artifacts in their original systems, not by accepting hashes or self-attested metadata alone.
2. Independently prove the former primary cannot become writable after a service restart or orchestrator rescheduling, including all bypass paths. An ordinary service stop does **not** count as independent fencing.
3. Confirm candidate replay, approved loss threshold, verified backups, WAL durability and client routing rollback.
4. Require both human incident commander and change authority to record an explicit decision in the private change-management system. This script can never make that decision.
5. Only if all independent gates pass and a separate live authorization exists, authorized operators may perform the platform-specific, approved staging rehearsal under the existing operational runbook. This milestone supplies **no stop, promote, fencing or rewind command**.
6. Measure actual client-facing RPO/RTO, rehearse aborted/failed promotion behavior, verify one writable node, restore backups if needed and obtain post-event review. Repeat independent fencing verification before any rejoin.

A passing staging rehearsal by itself does not equal enterprise certification; all Chapter 050 independent sign-offs remain mandatory.

## Offline invocation

Use separately prepared, access-controlled packet files and run from the repository root:

~~~bash
python3 postgresql/validation/v04c_rehearsal_preflight.py \
  --staging /secure/change/staging-evidence.json \
  --review /secure/change/independent-review.json \
  --request /secure/change/rehearsal-request.json \
  --json-out /secure/change/v04c-no-go-report.json
~~~

The [V04-C CI workflow](../../.github/workflows/postgresql-v04c-rehearsal-preflight.yml) tests the program with **synthetic evidence only**; public sample packets are deliberately incomplete and must return nonzero NO_GO. A green workflow does not prove genuine staging readiness or authorize failover.

**Current decision: V04-C NO_GO / STAGING REHEARSAL NOT EXECUTED / ENTERPRISE NOT_CERTIFIED.**
