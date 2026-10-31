# PostgreSQL V04-B — Independent Staging Evidence Review

**As of 2026-10-31 UTC: NO_GO / GENUINE_STAGING_EVIDENCE_NOT_PROVIDED**  
**Scope:** PostgreSQL 18 Chapters 049–050 staging only. PR #44 remains draft.

## Review boundary

V04-B provides an offline metadata cross-check for the [V04-A readiness packet](v04_staging_evidence.template.json) and a separate [V04-B reviewer packet](v04_independent_review.template.json). The [review checker](v04_independent_review.py) checks binding to the same change ticket, cluster system identifier, staging environment and exact change window; it also requires an unchanged canonical SHA-256 of the staging metadata and independent reviewer records.

**Neither checker contacts PostgreSQL, change-management systems, or external evidence storage. Neither verifies identity, cryptographic signatures, underlying artifacts or physical fencing. A complete packet never authorizes promotion or failover.**

## Required real, independently retained evidence

| Domain | Minimum independent verification | Reviewer role |
|---|---|---|
| Environment and cluster scope | Approved staging ticket, PG18 system identifier, role/endpoint identities, maintenance window | DBRE |
| Former-primary fencing | Direct writes, restarts, orchestration rescheduling, proxy bypass and relevant storage paths denied from an independent control plane | Security/fencing |
| Backup, archive and PITR | Verified base backup, off-node WAL continuity, separate recovery target and known-good row checks | DBRE |
| Approved business RPO/RTO | Signed HA/PITR loss and recovery targets with UTC measurement methodology | Change management |
| Application routing | Client connection plan, post-promotion transaction smoke tests, rollback and dual-writer prevention | Application |
| Rollback/abort | Preserved original PGDATA, rewind/rebuild fallback, abort owner, independent fence revalidation | Change management |

Four distinct initial approvers (DBRE, application owner, fencing owner and change manager) are required in V04-A. Four *different*, independent V04-B reviewers (DBRE, security/fencing, application and change management) must not overlap one another, the packet preparer, or the initial approvers.

The review packet has six corresponding claims. Each requires an external evidence reference, a 64-character lowercase SHA-256 of the retained evidence artifact, an observation UTC time and a matching responsible reviewer. The fencing claim also requires an independently observed control-plane assertion. Digest strings and declarations remain **untrusted self-reported metadata** until separately authenticated by the change authority.

## How to run offline

Keep both real evidence packets in a **private, access-controlled location** outside the public Git repository. Do not commit approver identities, internal links, connection strings, credentials, or staging logs.

~~~bash
# 1. Validate the private V04-A staging packet (exit 2 on NO_GO).
python3 postgresql/validation/v04_staging_readiness.py \
  --evidence /secure/change/staging-evidence.json \
  --json-out /secure/change/v04a-screen.json

# 2. Bind V04-B metadata to the canonical digest of that exact staging packet.
PYTHONPATH=postgresql/validation python3 -c \
  'import json,sys,v04_independent_review as r; print(r.digest(json.load(open(sys.argv[1],encoding="utf-8"))))' \
  /secure/change/staging-evidence.json

# 3. Review the separately signed private packet (exit 2 on NO_GO).
python3 postgresql/validation/v04_independent_review.py \
  --staging /secure/change/staging-evidence.json \
  --review /secure/change/independent-review.json \
  --json-out /secure/change/v04b-screen.json
~~~

A fully populated V04-B packet can yield REVIEW_PACKET_COMPLETE_UNAUTHENTICATED, which merely confirms metadata completeness. Outputs always state authorization=NONE, execution=NEVER and reviewed_real_staging=false. Human reviewers must authenticate the artifacts in their original systems and separately approve any staging change; the script cannot do so.

## Actual outstanding blockers

| Requirement | Actual genuine evidence supplied? | Result |
|---|---|---|
| Staging change ticket, exact cluster identity and UTC window | No | NO_GO |
| Independently observed old-primary write/restart fencing | No | NO_GO |
| Approved four business RPO/RTO objectives | No | NO_GO |
| Four named initial approvals and four distinct independent attestations | No | NO_GO |
| Six immutable referenced evidence artifacts | No | NO_GO |
| Verified staging backup/WAL and application routing/rollback | No | NO_GO |
| Real staging failover rehearsal and business transaction recovery | Not executed | NOT_CERTIFIED |

Do not substitute synthetic CI records, assumed names or guessed SLO thresholds. The [V04-B CI workflow](../../.github/workflows/postgresql-v04-independent-review.yml) tests only the offline parser's refusal behavior, not the reality of any staging evidence.

**Disposition: V04-B code prepared; genuine independent review NOT PERFORMED; V04-C staging failover NO_GO; enterprise certification NOT_CERTIFIED.**
