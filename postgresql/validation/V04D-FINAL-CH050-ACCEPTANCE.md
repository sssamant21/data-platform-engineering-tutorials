# PostgreSQL V04-D — Final Independent Chapter 050 Acceptance Review

**Actual status: NO_GO / staging not rehearsed / enterprise NOT_CERTIFIED**  
**Scope:** Approved PostgreSQL 18 staging HA and PITR rehearsal only  
**Production changes:** NONE. No independent real staging failover has been executed.

## Final acceptance control

The [V04-D offline evidence checker](v04d_ch050_acceptance.py) and [deliberately incomplete acceptance packet](v04d_ch050_acceptance.template.json) extend the existing [V04-A staging readiness](V04-STAGING-HA-DR-ACCEPTANCE-GATES.md), [V04-B independent review](V04B-INDEPENDENT-STAGING-REVIEW.md), and [V04-C pre-rehearsal review](V04C-STAGING-REHEARSAL-PREFLIGHT.md).

V04-D does **not** initiate any database, cloud or fencing operation. It compares metadata from all four documents and requires:

- Exact staging system identifier, change ticket, environment, UTC maintenance window and SHA-256 bindings to the three earlier packets.
- Historical preflight screen reference and a separately approved and recorded manual change-authority GO **before** the exercise, plus independent old-primary fence-recheck evidence.
- Genuinely conducted **staging** rehearsal evidence: one writable server, restart-proof fencing, client transaction restoration, no unauthorized promotion, successful read-only rejoin, recorded abort controls and immutable source logs.
- All eleven mandatory Chapter 050 acceptance rows marked PASS with original observation references, named witnesses and SHA-256 evidence digests.
- Five negative scenarios demonstrated safely in approved staging, with independent refusal/fallback evidence: failed fence, stale candidate, archive gap, rewind failure/rebuild, and application-route rollback.
- Four actual observed and documented HA/PITR RPO/RTO values, compared **individually** against the approved V04-A objectives. RPO requires an acknowledged-commit boundary; RTO requires client-level timestamps. The checker rejects missing, nonnumeric, negative, inconsistent, or out-of-SLO values.
- Four post-exercise independent review attestations (DBRE, application, security/fencing, change management), recorded after the rehearsal and distinct from the exercise operator and preflight change authorities.

A satisfied offline packet returns **READY_FOR_EXTERNAL_CERTIFICATION_REVIEW**, not CERTIFIED. Output always says **certification=NOT_CERTIFIED**, **authorization=NONE**, **execution=NEVER**, **evidence_authenticated_by_tool=false**. The tool does not retrieve or verify any external evidence; hashes and names alone do not prove authenticity or allow automatic certification.

## Mandatory Chapter 050 scorecard

| Gate | Real staging result |
|---|---|
| Physical base backup verified | PENDING |
| WAL archive continuity | PENDING |
| Isolated PITR recovered valid rows | PENDING |
| Former primary independently fenced | PENDING |
| Candidate freshness approved | PENDING |
| Exactly one writable primary | PENDING |
| Client-level application smoke tests | PENDING |
| Former primary read-only rejoin | PENDING |
| HA RPO/RTO within approved business limits | PENDING |
| PITR RPO/RTO within approved business limits | PENDING |
| Alerts, escalation, abort and runbooks reviewed | PENDING |

**All eleven are mandatory; no numeric score or green CI workflow can waive a failed or missing row.**

## Pre-rehearsal vs post-rehearsal evidence

An independent reviewer must authenticate the source systems: actual change approvals, physical/network/orchestrator fencing, original SQL and application logs, WAL retention, backup manifests, old-primary deny-write and restart attempts, read-only rejoin, client success, timeline/LSN and all UTC timestamps. A test using synthetic markers or CI on one host is not production-like staging evidence.

V04-D accepts *historical* staging observations after an approved test window, so it compares immutable identities and pre-rehearsal sign-off times instead of rerunning a five-minute V04-C freshness gate days later. Live authorization and fence proof **must** be verified during the change, and the final reviewers must attest only **after** the exercise.

## Offline review command

Keep all completed packets in approved private evidence storage. Do **not** commit operator names, internal routes, credentials, screenshots, signatures or actual staging data to this public tutorial.

~~~bash
python3 postgresql/validation/v04d_ch050_acceptance.py \
  --staging /secure/change/staging-evidence.json \
  --review /secure/change/independent-review.json \
  --preflight /secure/change/rehearsal-request.json \
  --acceptance /secure/change/final-ch050-acceptance.json \
  --json-out /secure/change/ch050-final-no-go-report.json
~~~

Exit 2 means NO_GO; exit 0 means the **untrusted metadata packet is complete for external review only**. This tool can **never** emit enterprise certification or an operational GO.

The [V04-D offline CI workflow](../../.github/workflows/postgresql-v04d-final-acceptance.yml) runs synthetic regression scenarios and rejects the incomplete checked-in template with nonzero NO_GO. A green workflow tests validator behavior, not real HA/DR readiness.

## Release decision

**As of 2026-10-31, no actual staging packets or independent source evidence have been supplied.** V03 isolated CI is successful, but no real independent fence, live business RPO/RTO or approved staging rehearsal has been authenticated. Chapter 050 remains **staging NOT_EXECUTED / enterprise NOT_CERTIFIED**; PR #44 must remain draft and unmerged pending authorized review.
