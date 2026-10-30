# PostgreSQL V02-C — Embedded SQL, Bash and PowerShell Audit

**Date:** 2026-10-30  
**Branch:** `qa/postgresql-v01-static-validation-20261030`  
**Result:** **Static inventory/syntax gate PASS; independent example review IN PROGRESS; PostgreSQL runtime NOT EXECUTED.**

## Reproducible CI evidence

- [Latest V02-D branch workflow including V02-C #41060774816](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41060774816)
- [Full per-block JSON evidence artifact](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41058577502/artifacts/12978047256) — `postgresql-v02c-evidence.json`
- Validator: [validate_v02c.py](validate_v02c.py), invoked in `.github/workflows/postgresql-v02-code-audit.yml`.

This validator **never executes embedded SQL, Bash, or PowerShell**. It extracts Markdown code fences, parses SQL with PostgreSQL 18-compatible `pglast` after `psql` interpolation stubbing, runs shell syntax checks (`bash -n`), uses PowerShell's AST parser without invoking the script, checks referenced repository paths, and inventories destructive-command patterns. A syntactically valid example may still be unsafe, incomplete, lack privileges, or produce unexpected output.

These updated counts reflect the new guarded Chapter 007 cleanup lab example added during V02-D; the prior run/artifact is retained as an earlier baseline.

## Complete inventory

| Code-block classification | Count | V02-C disposition |
|---|---:|---|
| Total fenced blocks in chapters and labs | **791** | Inventoried |
| Bash fences | 385 | Checked / classified |
| SQL fences | 252 | Checked / classified |
| PowerShell fences | 50 | Checked / classified |
| Other formatting / examples | 104 | Not claimed as runnable |
| **Executable-language syntax checks passing** | **668** | Static parse pass, not runtime verification |
| Manual-review items | **19** | 18 environment-specific placeholders; 1 `psql` meta-commands-only block |
| Missing referenced supporting files | **0** | Paths validated against repository |
| Fenced blocks with possible destructive operations | **50** | Risk-review queue; no commands executed |
| Blocks without nearby result/evidence phrasing | **108** | Editorial heuristic, not proven missing outcomes |
| Blocking scanner errors | **0** | CI pass |

## PG-V02C-001 — Quoted `psql` identifiers (resolved in auditor)

The initial scanner incorrectly transformed `:"schema_name"` into a SQL string literal rather than a quoted identifier placeholder in Chapter 005. `validate_v02.py` now replaces SQL identifier and value interpolation with different grammar-only placeholders. A rerun increased the passing block syntax count from 667 to 668. **Do not treat grammar substitution as a guarantee of safe runtime variable handling.**

## PG-V02C-002 — Nineteen context/manual-review items (open, bounded)

**Eighteen** commands use deliberate environment placeholders requiring operator-selected values, including:

- Chapter 001 and Lab 001: authorized lab credentials / connection parameters
- Labs 032–036 and 038–040: independently observed lab PostgreSQL cluster ID before destructive cleanup
- Lab 045: Chapter 045 incident/failure-injection target cluster ID
- Lab 047: guarded slot/schema cleanup identity
- Lab 007: extra Chapter 007 PostgreSQL system-identifier placeholder for the new guarded database cleanup
- Labs 048–050: named primary/standby hosts and cleanup target identifiers

**One** block in Chapter 005 consists only of interactive `psql` commands (`\\pset`, `\\x`, `\\timing`, etc.) and is intentionally not parsed as server SQL.

**Acceptance:** Verify placeholder substitution using disposable infrastructure; confirm that every example explicitly distinguishes required values and is copied only after the operator's independent target check. Runtime validation pending.

## PG-V02C-003 — 50 embedded potentially destructive-command matches (open)

These are **50 matching fenced blocks**, not 51 confirmed bugs or vulnerabilities. Three blocks are in chapters and 48 are in lab Markdown. Examples include `ALTER SYSTEM`, `DROP DATABASE/SCHEMA/TABLE`, replication and backend controls, and `REINDEX`. Some are deliberate positive/negative tests, restore commands, or cleanup workflows.

**Priority review order:**

1. Database deletion, configuration changes and service interruption: Chapter 007–015 lab examples, and high-risk operations around failover/recovery.
2. Backend signaling and security policy verification: Chapters 014, 020, and associated restricted-role labs.
3. Schema and fixture teardown: Chapters 016–031, with expected object ownership and operator confirmation checks.
4. Index maintenance and write workload examples: Chapters 032–040 and later lifecycle examples.

**Acceptance:** For each block, classify *read-only, synthetic write, intentional failure, privileged change, destructive cleanup, or production operation*. Inspect exact target restrictions, operator approval, stop/rollback conditions, postchecks and evidence. Only mark a match resolved after documented technical review; positive static parse is insufficient.

## PG-V02C-004 — 108 evidence-guidance flags (editorial queue)

The validator looks for terms such as *expected*, *verify*, *result*, *output*, *observe*, *evidence*, or *compare* near a code block. Its 108 flags are **heuristic**, not confirmed content defects. The first review priorities include interactive concurrency Chapters 017–020, maintenance Chapters 032–036, and backup/restore Chapters 042 and 063.

**Acceptance:** Check whether each exercise describes preconditions, illustrative vs executable syntax, expected observations or variability, interpretation, cleanup and evidence. Where guidance is elsewhere in the same chapter, record the cross-reference instead of duplicating prose.

## Validation status and next gate

- **V01:** PASS.
- **V02-A:** Source file syntax PASS.
- **V02-B:** 37 source-file risk matches inventoried and classified; cleanup guard presence checks PASS, runtime guard-negative tests pending.
- **V02-C:** Embedded block inventory and syntax PASS; **19 context items, 50 risk-matched blocks, and 108 editorial-heuristic flags remain open for independent review**.
- **V02-D next:** Validate the semantic and role/privilege assumptions of executable examples, beginning with Chapters 001–010, then proceed chapter by chapter and capture expected-versus-actual evidence.
- **V03:** Isolated PostgreSQL 18 live runtime only after deployment-specific safety prerequisites.

**Certification:** NOT CERTIFIED. No live PostgreSQL commands were executed as part of V02-C. Do not interpret the CI status as runtime or production readiness.
