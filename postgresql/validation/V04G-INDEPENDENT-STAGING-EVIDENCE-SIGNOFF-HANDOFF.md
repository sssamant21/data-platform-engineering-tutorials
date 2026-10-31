# PostgreSQL V04-G — Independent Staging Evidence and Final Sign-off Handoff

**Current decision: BLOCKED / NO_GO / NOT_CERTIFIED (2026-10-31 UTC)**  
**Applies to:** PostgreSQL 18 Chapter 050 HA/DR staging acceptance  
**Change activity:** No real staging failover has been performed. PR #44 must remain draft and unmerged until the appropriate independent reviews conclude.

## Why V04-G cannot be completed from GitHub

The laboratory workflows and V04-A through V04-F *synthetic/offline* validators have been tested successfully. They do **not** prove the former primary is independently fenced, demonstrate real client recovery, authenticate signers, or establish compliance with business RPO/RTO. Genuine staging artifacts, source-system access and approved operators have not been supplied. The final acceptance decision therefore belongs in the organization's private change and evidence systems.

**Do not run failover, fencing, pg_rewind, or other live operations on the strength of a green PR.** No CI result, synthetic data packet, evidence-file SHA-256 or metadata-only result is a change authorization or an enterprise certificate.

## Assign accountable roles before requesting a window

| Review responsibility | Required owner (assign internally) | What that owner must confirm |
|---|---|---|
| DBRE technical lead | **UNASSIGNED** | PostgreSQL 18 cluster/role identity, candidate freshness, replication, PITR, rewind/rebuild, single-writer proof |
| Infrastructure/fencing lead | **UNASSIGNED** | Independent old-primary write/restart/reschedule/routing/storage exclusions from a separate control plane |
| Application owner | **UNASSIGNED** | Client routing, real application transaction success, connection recovery and business correctness |
| Backup/DR owner | **UNASSIGNED** | Physical backup, off-host WAL continuity, separate PITR, recovery timeline and restore-point evidence |
| Change authority | **UNASSIGNED** | Approved staging scope/window, approved business RPO/RTO, explicit authorization and abort owner |
| Independent final reviewers | **UNASSIGNED** | Four distinct DBRE, security/fencing, application and change-management reviews *after* the exercise |

Names and signed attestations are retained in **private** change records, not in this public tutorial repository. V04-B and V04-D require review separation; one operator cannot sign for all of these controls.

## Evidence collection request (external handoff)

The source owners should create a **private change ticket** linked to an **approved restricted-access evidence location** containing:

1. **Identity and permissions:** exact staging system identifier, PostgreSQL major, all node IDs/endpoints, non-production approval, UTC window, authorized operator, independent change authority and incident commander.
2. **Before any operation:** approved HA RPO/RTO and PITR RPO/RTO objectives (in seconds), source approval signatures, independently observed candidate replay and business transaction boundary.
3. **Independent fencing:** evidence that the former primary cannot become writable after service restart, orchestrator re-scheduling or direct/routing bypass, with storage exclusion where applicable. This must be witnessed through a separate control plane.
4. **Rollback and recovery:** retained original PGDATA/backup, WAL archive and manifest checks, isolated restore proof, safe rewind or rebuild fallback, abort criteria and named incident commander.
5. **Approved rehearsal:** manually authorized staging-only run records, external control-plane fence recheck, exactly-one-writer observation, real client transaction restoration, read-only former-primary rejoin and business-level UTC outage boundaries.
6. **Negative scenarios:** fence failure must refuse promotion; stale candidate must refuse promotion; archive gap must fail safely; partial rewind must trigger safe fallback; application routing rollback must succeed. Stage these only under separate approved safety controls.
7. **Chapter 050 acceptance:** all 11 mandatory rows with original source evidence and 4 actual HA/PITR RPO/RTO measurements compared to their approved thresholds.
8. **Custody and authenticity:** 20 immutable artifacts (11 acceptance, 5 negative, 4 metrics) with source IDs, original SHA-256, approved redacted copy SHA-256, export/transfer receipts and independent comparison to the **real original source systems**.
9. **Final outcome:** four independent post-test sign-offs, recorded exceptions, go/no-go and business-owner acceptance in the private change ticket.

If an artifact is missing, unverifiable or shows a failed objective, keep the status **NO_GO**. Do not automatically generate placeholder names, invent thresholds, or convert unreviewed evidence into PASS.

## Recommended review sequence

| Phase | Evidence source | Decision |
|---|---|---|
| **Intake** | V04-A staging and V04-B independent-review packets | Source reviewers must authenticate the original approvals and cluster identities |
| **Pre-rehearsal** | V04-C request and external control-plane fencing proof | A separate human change authority grants or rejects a restricted staging-only rehearsal |
| **Execution** | Approved staging runbook and actual client/infra logs | Human operators supervise fencing, candidate promotion, recovery, rollback and abort |
| **Final acceptance** | V04-D 11-gate worksheet, 5 negative paths and 4 measured SLOs | Independent reviewers check each claim against its source record |
| **Evidence custody** | V04-E byte checks and V04-F original-source/transfer receipts | Independent reviewers validate original provenance and meaning |
| **Release decision** | Signed private change and risk record | Change authority may accept, reject or defer; a tool cannot certify production |

For private offline screening instructions, see [V04-A gates](V04-STAGING-HA-DR-ACCEPTANCE-GATES.md), [V04-B review](V04B-INDEPENDENT-STAGING-REVIEW.md), [V04-C preflight](V04C-STAGING-REHEARSAL-PREFLIGHT.md), [V04-D acceptance](V04D-FINAL-CH050-ACCEPTANCE.md), [V04-E artifacts](V04E-EVIDENCE-INTEGRITY-INTAKE.md) and [V04-F handoff](V04F-SECURE-EVIDENCE-HANDOFF.md). **Run offline checks against private records only, not in public CI.**

## Sign-off decision record (complete in private change system)

| Required decision field | Current known value |
|---|---|
| Approved private staging change ticket | **NOT PROVIDED** |
| Independent fencing evidence validated against source | **NOT PROVIDED** |
| Approved business RPO/RTO targets | **NOT PROVIDED** |
| Independent owner signatures | **NOT PROVIDED** |
| Actual staging rehearsal results | **NOT EXECUTED** |
| Measured application HA/PITR RPO/RTO | **NOT MEASURED** |
| Backup/WAL/rollback validation in actual staging | **NOT VERIFIED** |
| Original evidence authenticity review | **NOT PERFORMED** |
| Independent Chapter 050 sign-offs | **NOT PROVIDED** |
| External final acceptance decision | **NO_GO / PENDING** |
| Enterprise certification | **NOT_CERTIFIED** |

**Exit criteria for V04-G:** an authorized independent reviewer confirms all mandatory private source artifacts, no outstanding NO_GO condition, and separately records an approved final decision with scope, date, signers, residual risks and explicit business-owner sign-off. Until then, leave this milestone blocked rather than creating additional synthetic success records.

**Explicit hold:** PR #44 stays draft/unmerged. Do not initiate a staging rehearsal from CI or from this documentation.
