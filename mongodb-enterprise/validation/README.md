# Phase 4 — MongoDB Enterprise Lab Validation Framework

> **Status:** framework established; **0/80 chapters runtime-certified**. Phase 3 static safety audit is 80/80. All tests must run only in a specifically authorized disposable environment. Do not merge this branch into main based on static checks.

## Evidence levels

| Level | Evidence | Allowed conclusion |
|---|---|---|
| L0 | Chapter file exists, expected headings and code fences are balanced | Documentation structure checked |
| L1 | Offline scripts parse and deterministic unit/negative tests run with captured outputs | Offline behavior verified |
| L2 | Actual MongoDB 8.0 Enterprise-compatible lab and dependencies, real assertions, fixture cleanup | Isolated integration verified |
| L3 | Approved disruption, restore, failure/recovery or external integration, independent evidence | Operational drill verified |
| L4 | Independent technical/security review, traceable sign-off, version/topology applicability | Candidate for curriculum acceptance |

An L0/L1 pass is **never** a substitute for L2/L3. Not every chapter needs an L3 drill; record an explicit reviewed N/A when appropriate. No test may run automatically with production credentials.

## First execution milestone

1. Run the **read-only offline structure checker** in this folder, capturing its JSON output.
2. For Chapters 01–04, extract the executable blocks to separate reviewed files, inspect destructive commands and validate syntax/fixtures offline.
3. Prepare a disposable, owned MongoDB lab; pin actual MongoDB edition/version, mongosh, driver, TLS/auth, host OS, Kubernetes/operator where applicable.
4. Run each chapter's preflight, positive test, negative test, recovery, exact-namespace cleanup and post-cleanup verification. Record real outputs and unexpected errors.
5. Promote chapter status only after evidence and reviewer acceptance. Never infer test success from absence of errors in a script's source.

## Execution gates

- **Preflight:** lab owner/run ID, target identity, exact topology, cluster health, permissions, version matrix, resource budget, no competing change, and backup/restore evidence for stateful drills.
- **No default mutation:** this framework's first checker reads Markdown only. A later live harness must require an explicit lab endpoint allowlist, an exact run-owned namespace, explicit opt-in and a second approval for disruptive drills.
- **Stop:** wrong cluster, unexpected data, failed health, stale metrics, failed ownership, insufficient storage, unknown command result or unsupported version.
- **Cleanup:** scoped ownership checks before every drop/delete, exact resource IDs, evidence retained, verification after cleanup. Never use wildcard resource deletion or disable authentication.
- **Evidence:** run ID, chapter, git commit, UTC time, executor, environment fingerprint, test command/hash, expected/actual, logs, exit status, cleanup status, reviewer, exceptions and retention location.

## Chapter certification record

Use one JSON record per chapter under a controlled evidence store (do not commit credentials, customer data, unredacted logs or live resume tokens):

```json
{
  "chapter": 1,
  "source_commit": "REQUIRED_SHA",
  "environment": {"mongo_version": "PENDING", "edition": "PENDING", "topology": "PENDING"},
  "checks": {"structure": "not_run", "offline": "not_run", "integration": "not_run", "disruption": "not_applicable"},
  "cleanup": "not_run",
  "independent_review": "pending",
  "runtime_certified": false,
  "evidence_refs": []
}
```

Allowed check states: `passed`, `failed`, `not_run`, `blocked`, `not_applicable`. A chapter is **not** certified if any required check is failed, blocked or not run, or if cleanup and independent review are incomplete.

## Command

```bash
python3 mongodb-enterprise/validation/structure_check.py \
  --root mongodb-enterprise \
  --output mongodb-enterprise-structure-results.json
```

This uses Python's standard library, does **not** contact MongoDB, and never runs code from the tutorials. It checks exactly numbered chapter filenames (01–80), unique chapters, headings, fence balance and local Markdown links. Results are L0 only. The output is evidence for the review, not a production acceptance certificate.

## Initial backlog

| Priority | Chapters | Work |
|---|---|---|
| P0 | 01–04 | First offline and isolated integration pilot |
| P0 | 16–20, 41–48 | Destructive cleanup, privilege boundaries, TLS, encryption |
| P0 | 25–40, 49–56, 76–80 | Replica sets, sharding, backup/restore, failover and final acceptance |
| P1 | 57–64 | Ops Manager, Kubernetes maintenance/upgrade, driver retries, CDC |
| P1 | 65–75 | Retention, GridFS, Snowflake, migration, monitoring, maintenance and incidents |
| P2 | Remaining chapters | Complete coverage, independent review and evidence reconciliation |

**Current gate:** Phase 4 framework only. No runtime lab execution or certification has occurred.

## Chapters 01–04: opt-in lab preflight (read-only)

After obtaining authorization for a **disposable** MongoDB endpoint and reviewing network/credential configuration, install `pymongo` in the isolated environment. The pilot is currently **local-loopback only** (localhost or 127.0.0.1), requires one exact host, rejects URI query options/database paths and embedded credentials, and does not perform writes. It does **not** prove the host is nonproduction; an operator must verify cluster identity out of band. TLS/auth configuration and credentials must be supplied by an approved external connection setup; the current URI-only pilot does not support every enterprise TLS/auth mode. **Never supply production credentials or run against a production cluster.**

```bash
export MONGODB_LAB_APPROVED=YES
export MONGODB_LAB_URI='mongodb://127.0.0.1:27017'
python3 mongodb-enterprise/validation/lab_preflight.py \\
  --chapter 1 --run-id approved_run_001 \\
  --allowed-host 127.0.0.1 --output lab-preflight-ch01.json
```

This collects only server build/topology and owned-database existence. **Do not tunnel a production database to localhost**: loopback address alone does not establish lab identity. It neither runs chapter labs nor certifies them. Do not commit evidence containing internal endpoints or other sensitive environment details. Before adding mutation tests, implement TLS/auth, exact cluster-identity allowlisting, namespace ownership, explicit per-run approval and independently reviewed cleanup.
