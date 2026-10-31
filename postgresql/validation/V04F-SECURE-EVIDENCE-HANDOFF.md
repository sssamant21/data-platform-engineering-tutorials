# PostgreSQL V04-F — Secure Evidence Handoff and Independent Source Review

**Milestone state:** Offline tooling implemented. **No genuine staging records supplied.**  
**Real staging rehearsal:** NOT_EXECUTED. **Enterprise:** NOT_CERTIFIED. **PR #44:** draft.

## Purpose and explicit limits

V04-E establishes whether locally held review copies of the 20 Chapter 050 evidence items have SHA-256 values matching a private V04-D metadata packet. V04-F adds a **chain-of-custody metadata screen** for those review copies and the claimed original evidence: separate named collectors/exporters/receivers/source reviewers; original record IDs and hashes; UTC chronology; private transfer receipts; evidence-source review attestations; retention/transfer policies and redaction approvals.

[V04-F checker](v04f_secure_evidence_handoff.py) calls the [V04-E local-byte checker](v04e_artifact_integrity.py) first, so it refuses incomplete or tampered local review copies. It is **offline and read-only**. It does not retrieve source logs, validate signature cryptography or identities, check change-system entitlements, confirm real fencing, run a PostgreSQL command, authorize promotion or grant certification. An apparently complete packet returns only HANDOFF_METADATA_COMPLETE_UNAUTHENTICATED with certification=NOT_CERTIFIED and authorization=NONE.

## Secure operator handoff checklist

The **source owner** must retain unredacted originals in the organization's approved evidence system. The **exporter** produces a separately approved redacted review copy, preserves original SHA-256 and original immutable source record reference, and independently records export time. The **receiver** verifies the transferred copy, records its V04-E relative path and SHA-256, and attests to receipt in private evidence storage. A **different independent source reviewer** must open the actual original in its source system, compare its record ID/hash and original context, and document source-review results. The tool checks that these four named roles are distinct **per artifact**; it cannot confirm who really performed the steps.

Every one of the **20 required artifacts** needs an immutable transfer receipt, independent source-review reference, original artifact hash, reviewed original hash, exported/received/verified UTC timestamps, approved-redaction attestation and record ID. A reviewer should reject tampering, missing evidence, lost context, ambiguous provenance or conflicting source identity rather than re-hashing altered files to obtain a pass.

No actual staging credentials, connection details, real names, unredacted logs or sensitive application/patient data belong in this public repository. Approved private packets should stay in encrypted, access-controlled organizational storage and remain outside GitHub Actions.

## Private packet workflow

1. Complete the actual V04-D acceptance packet only after an independently approved staging rehearsal. A human reviewer must authenticate those records.
2. Complete V04-E [local evidence inventory](v04e_evidence_inventory.template.json) using approved redacted copies. Check all local file hashes and provenance. Retain the integrity report privately.
3. Copy the [V04-F handoff packet template](v04f_handoff.template.json) into the approved private review location, and bind it to the **exact canonical SHA-256** of both the V04-D and V04-E JSON packets.
4. For each key matching V04-E roles, complete original_record_id, source_system, original_artifact_sha256 and reviewed_source_sha256, original_source_record_ref, redacted_review_sha256, redacted_review_evidence_ref, receipt_id, named export/receive/source reviewers, UTC timestamps and attestation refs. Keep human sign-offs distinct.
5. Confirm secure transfer policy, retention/access policy, redaction approval and independent review of the original source. Never substitute the local review copy or its hash for authentication of the original.
6. Run the V04-F offline screen. **NO_GO (exit 2)** indicates unresolved missing or inconsistent metadata. **HANDOFF_METADATA_COMPLETE_UNAUTHENTICATED (exit 0)** means only that submitted claims and local hashes align; original source evidence still requires independent expert authentication outside this script.

### Example private invocation

~~~bash
python3 postgresql/validation/v04f_secure_evidence_handoff.py \
  --acceptance /secure/change/final-ch050-acceptance.json \
  --inventory /secure/change/v04e-evidence-inventory.json \
  --handoff /secure/change/v04f-handoff.json \
  --evidence-root /secure/change/redacted-evidence \
  --json-out /secure/change/v04f-review-no-go.json
~~~

The public templates are intentionally empty and must yield **NO_GO / NOT_CERTIFIED**. The [V04-F GitHub Action](../../.github/workflows/postgresql-v04f-secure-handoff.yml) uses only synthetic files and self-attested fixtures to test refusal of missing receipts, forged changes, overlapping roles, source digest mismatches, bad chronology and missing redaction documentation. A green CI result **cannot** be used as operational evidence or enterprise certification.

## Actual outstanding handoff decision

No genuine staging evidence, independent fencing proof, real RPO/RTO measurements, signed change approvals or human-authenticated source artifacts have been supplied. **V04-F genuine handoff NOT PERFORMED; V04-C rehearsal NO_GO; Chapter 050 NOT_CERTIFIED.**
