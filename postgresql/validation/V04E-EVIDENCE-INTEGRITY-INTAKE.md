# PostgreSQL V04-E — Private Staging Evidence Integrity Intake

**State:** TOOLING ONLY. **No genuine staging evidence has been supplied.**  
**Actual staging rehearsal:** NOT EXECUTED. **Enterprise:** NOT_CERTIFIED.

## Purpose

The [V04-D Chapter 050 final gate](V04D-FINAL-CH050-ACCEPTANCE.md) checks reported evidence hashes and references but cannot verify that any local artifact contains those bytes. This V04-E [offline checker](v04e_artifact_integrity.py) closes that *specific* integrity gap for an **approved private review copy**: it recomputes SHA-256 from local evidence files, compares those bytes with V04-D's recorded SHA-256 and evidence reference, and screens collection metadata.

**It does not retrieve real records, validate log meaning, verify signatures, authenticate a source system or person, independently confirm infrastructure fencing, or grant an operational GO or enterprise certification.** Even a full set of matching bytes yields LOCAL_ARTIFACT_BYTES_MATCH_METADATA_UNAUTHENTICATED, certification=NOT_CERTIFIED, authorization=NONE and execution=NEVER.

## Collection responsibilities and evidence scope

Collect a locally accessible, **already approved and redacted** review copy of exactly these **20** required Chapter 050 artifacts:

| Artifact group | Count | Evidence |
|---|---:|---|
| Acceptance gates | 11 | Verified base backup, WAL archive, PITR, independent fencing, standby freshness, one writer, application success, read-only rejoin, business HA/PITR targets and alert/runbook review |
| Failure scenarios | 5 | Fence failure refusal, stale-standby refusal, archive gap, rewind failure/rebuild fallback and application-route rollback |
| Measured HA/PITR objectives | 4 | Actual client/commit-boundary HA RPO/RTO and PITR RPO/RTO with original observation records |

The checker requires the **exact evidence_ref** and original recorded sha256 for each role, a separate ordinary file under the approved root, byte length, original source record ID, collector, source system, collection timestamp and redaction indicator. It rejects missing items, unexpected roles, unsafe relative paths, symlinks, multi-hard-linked files, altered bytes, duplicates and oversized (>16 MiB) files. It reads bytes locally but never prints file contents or raw paths.

**A hash match only proves local consistency with submitted metadata.** An adversary can fabricate a file and its hash; the independent security/DBRE/application review team must still access the original evidence system to verify authenticity and completeness. The redacted indicator is **self-reported** and the script does not inspect content to remove secrets or sensitive clinical/patient data. Redact and approve files **before** transferring them; never upload source logs or private evidence into GitHub Actions.

## Secure procedure

1. Independent operators export original staging records through approved access-controlled processes. Keep an untampered original in the enterprise evidence system.
2. Make a separately approved, **redacted** copy of each of the 20 required artifacts in a secure local directory. Each file must have a distinct relative path and must be an ordinary non-symlinked file. Split oversized logs into approved individually referenced excerpts with appropriately documented SHA-256 references.
3. Complete the private [V04-D acceptance packet](v04d_ch050_acceptance.template.json) from the actual authorized staging rehearsal. Do not invent a passing rehearsal or values.
4. Copy the [V04-E inventory template](v04e_evidence_inventory.template.json) **privately**. Each artifact key must match the acceptance or scenario ID, or measurement name: e.g. acceptance/base_backup_verified, scenario/fence_failure_no_promotion, measurement/ha_rto_seconds.
5. For each record add relative_path, sha256, size_bytes, evidence_ref, collector, source_system, original_record_id, collected_at_utc and redacted_for_review=true. Set the top-level v04d_manifest_sha256 to the canonical digest of the completed V04-D JSON. Never put credentials, names or internal endpoint identifiers in the public repository.
6. Run the offline check in the approved private workspace. Treat **any** failure as NO_GO for evidence intake; preserve the original file, do not silently modify/re-hash evidence to make checks green.
7. Independent reviewers must authenticate the original files, attest to their meaning, review the four business objectives, complete Chapter 050 and independently approve or deny any enterprise acceptance. No automation is authorized to certify.

## CLI (private local machine only)

~~~bash
PYTHONPATH=postgresql/validation python3 -c \
  'import json,sys,v04_independent_review as g; print(g.digest(json.load(open(sys.argv[1],encoding="utf-8"))))' \
  /secure/change/final-ch050-acceptance.json

python3 postgresql/validation/v04e_artifact_integrity.py \
  --acceptance /secure/change/final-ch050-acceptance.json \
  --inventory /secure/change/v04e-evidence-inventory.json \
  --evidence-root /secure/change/redacted-evidence \
  --json-out /secure/change/v04e-integrity-screen.json
~~~

The built-in [V04-E CI workflow](../../.github/workflows/postgresql-v04e-evidence-integrity.yml) uses **synthetic files only**. It must pass positive byte-integrity tests and demonstrate that the deliberately incomplete public templates exit 2 with NO_GO and NOT_CERTIFIED. **Do not pass private staging content into that CI workflow.**

## Final status

V04-D's external final certification remains blocked. Genuine staging evidence, infrastructure fencing, separately signed change approval, real client RPO/RTO, all eleven mandatory results and independent acceptance reviews are **still pending**.

**Decision: EVIDENCE_INTAKE_NOT_PERFORMED / STAGING_NOT_EXECUTED / ENTERPRISE_NOT_CERTIFIED / PR #44 DRAFT.**
