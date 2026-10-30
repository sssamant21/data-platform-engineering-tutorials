# PostgreSQL V02 — Code and Command Validation

**Date:** 2026-10-30  
**Branch:** `qa/postgresql-v01-static-validation-20261030`  
**Automated parsing:** **PASS (0 failures)**  
**Independent code/safety review:** **V02-B static triage complete; V02-C syntax inventory passed; V02-D Chapters 001–030 reviewed; 18 prior CI tests passed and 10 new offline tests added; latest CI verification pending**  
**Runtime lab execution and certification:** **NOT STARTED**

## GitHub Actions evidence

- [Latest successful V02 workflow run #41062449652](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41062449652)
- [Machine-readable V02-A/B/C artifact on the passing Chapter 011–020 run](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41062449652/artifacts/12979761963): `postgresql-v02-evidence`
- Earlier V02 attempts failed because the auditor initially treated some `psql` variable expressions and standalone `\gexec` directives as plain SQL. Parser preprocessing was corrected and the affected SQL files now parse.

**Important limitation:** SQL grammar parsing uses `pglast==8.7` (PostgreSQL 18 grammar) after separating `psql` meta-commands and replacing `psql` client-side variables with parser placeholders. This confirms parseability of the transformed SQL, not correctness of its runtime semantics, query results, privileges, shell integrations, SQL injection resistance, or production safety.

## V02-A — Completed automated checks

| Scope | Count | Result |
|---|---:|---|
| Standalone SQL source files | 159 | 159 parsed; zero errors |
| Python files | 13 | 13 AST syntax passes |
| Bash scripts | 5 | 5 `bash -n` passes |
| PowerShell scripts | 2 | 2 AST parser passes on GitHub runner |
| JSON files | 1 | 1 parsed |
| YAML files | 5 | 5 parsed |
| `psql` directive lines excluded from SQL grammar parser | 620 | Classified as client commands, not executed |
| Markdown fenced `sql` code blocks | 252 | V02-C inspected/parsed where complete; contextual review remains pending |
| Markdown fenced `bash` blocks | 386 | V02-C inspected/parsed where complete; contextual review remains pending |
| Markdown fenced `powershell` blocks | 50 | V02-C inspected/parsed where complete; contextual review remains pending |
| Distinct assets referenced in prose / command examples | 126 | Existence checked; zero missing references flagged |

Other fenced content includes 89 text, 11 conf, 2 ini, one PromQL and one Mermaid block. These have not all been technically verified.

**Updated risk-pattern accounting:** The original 37-match V02-B triage is a frozen baseline. The guarded Chapter 007, Chapter 011 and Chapter 014 database cleanup SQL files each add one intentional `DROP DATABASE` pattern, bringing the current V02-A source risk inventory to **40** matches (not 40 confirmed defects). See the V02-D reports for mitigations and remaining runtime gates.

## V02-B follow-up — published static safeguards

- [V02-B 37-match register](V02B-RISK-REGISTER.md): every scanner match given a classification, rationale and next acceptance step.
- [V02-B guard checker](validate_v02b.py): enforces the three-input cleanup pattern and corresponding guide arguments on 10 scripts; verifies that Chapters 032–036 setup scripts do not automatically drop schemas.
- [CI workflow](../../.github/workflows/postgresql-v02-code-audit.yml) now runs both V02 SQL/static parser checks and V02-B guard checks and retains their JSON evidence.
- The Chapter 045 deliberate corruption/incident SQL now checks the expected database, cluster system identifier, PostgreSQL version, presence of its synthetic table, and `045-INCIDENT` authorization token. The lab guide is synchronized.
- Static guard checks are *presence checks* only. They do not prove that an operator-controlled script cannot affect production when misused, nor do they replace isolated PostgreSQL execution and peer approval.

## V02-B — Safety findings and remediation

The scanner reports **37 keyword/pattern matches across checked source files**, not 37 confirmed vulnerabilities. All 37 were assigned a file-specific static classification and runtime gate in the [V02-B risk register](V02B-RISK-REGISTER.md). Comments, privilege statements, lab setup scope and intentional negative tests require different interpretations.

| Category | Matches | Review target |
|---|---:|---|
| SQL UPDATE | 15 | Confirm bounded synthetic rows, transaction guard, rollback and expected results |
| DROP SCHEMA | 10 | Verify all are explicit lab cleanup commands; require approved target identity and interactive confirmation |
| SQL DELETE | 6 | Confirm WHERE/scope and intentional retention or failure-injection behavior |
| TRUNCATE | 2 | Check destructive scope, backup assumptions and exact fixture schema |
| Backend signaling | 1 | Require verified PID, role, application name and no accidental production targeting |
| REINDEX | 1 | Validate concurrency, index scope, lock/WAL/disk budgets and recovery |
| `pg_ctl stop` | 1 | Confirm only the isolated disposable lab instance can be stopped |
| Recursive deletion | 1 | Confirm canonical-path ownership checks, explicit confirmation and symlink protections |

### PG-V02-001 — Automatic destructive setup reset (HIGH; mitigated)

Original setup scripts for **Chapters 032, 033, 034, 035 and 036** contained unconditional `DROP SCHEMA IF EXISTS chNNN CASCADE` followed by `CREATE SCHEMA`. This would erase previously existing same-named objects when the scripts were pointed at the wrong database. On the QA branch, the automatic DROP was **removed from all five setup files**. Existing schemas now cause setup to stop at `CREATE SCHEMA`, requiring a separately reviewed cleanup decision.

**Verification:** V02 risk classification changed from **5 `automatic_destructive_setup` matches** to **0** in the passing run. This is a static remediation and has not been executed against a database.

### PG-V02-002 — Manual cleanup scripts need database identity checks (HIGH; mitigated statically)

The remaining `DROP SCHEMA` candidates include lab cleanup scripts. Example: `labs/sql/040-cleanup.sql` executes `DROP SCHEMA ch040 CASCADE`. A narrowly named schema is not by itself proof of a safe database target. All 10 cleanup scripts now require an exact database name, independently observed PostgreSQL 18 cluster system identifier and chapter-specific confirmation. The matching lab guides were revised. This blocks accidental execution without the required inputs, but **the guards have not been exercised in a live PostgreSQL instance**. Never run these scripts against production.

**Remaining closure:** pass negative/positive guard tests, verify object ownership/dependencies, and record exact cleanup changes in a disposable PostgreSQL 18 environment.

### PG-V02-003 — SQL and shell examples inside Markdown (MEDIUM; open)

The 252 embedded SQL blocks, 384 Bash blocks and 50 PowerShell blocks are only inventoried here. Some are deliberately partial examples and cannot be treated as independently executable scripts. Use a second-pass extractor to classify standalone snippets versus templates/outputs before syntax or semantic acceptance. Compare commands to the referenced fixture scripts, expected results and rollback instructions.

### PG-V02-004 — Runtime correctness, privileges, and recovery proofs (HIGH; open)

Parser success does not prove that setup scripts use correct PostgreSQL privileges, create the intended fixture, or cleanly restore state. It does not establish consistent results for VACUUM, PITR, replication, PgBouncer, TLS or multi-region failover. Runtime and destructive-failure exercises remain deliberately blocked pending isolated lab controls.

## Next validation tasks

1. **V02-B:** **37/37 risk matches statically classified** in [the risk register](V02B-RISK-REGISTER.md); 10 cleanup scripts and the Chapter 045 incident script strengthened. CI guard regression checks pass; negative/positive PostgreSQL runtime checks still pending.
2. **V02-C:** **automated embedded-code audit PASS** in [V02C-STATUS.md](V02C-STATUS.md): 792 fences inventoried, 666 static syntax passes, 22 manual-context items, 48 risk matches and 107 editorial-context flags on the Chapters 011–020 V02-D commit. Full technical sign-off and live examples remain pending.
3. **V02-D:** [Chapters 001–010 static review](V02D-CH001-010-STATUS.md) published: all 10 chapter/lab pairs checked, two fixes (Chapter 007 guarded database deletion and Chapter 010 low-privilege configuration capture), **8/8 regression tests passing**. [Chapters 011–020 security/concurrency review](V02D-CH011-020-STATUS.md) also published with three guarded-operation fixes and **10/10 additional regression tests passing**. See [Chapters 021–030 observability/performance review](V02D-CH021-030-STATUS.md) for two fail-closed SQL setup guards, input-validation fixes in the SLO and query-statistics utilities, and 10 new offline regression tests (latest CI run pending). Runtime proof and independent sign-off remain pending; next Chapters 031–040.
4. **V03:** execute disposable PostgreSQL 18 lab smoke tests with explicit evidence and fault-injection gates.

**Certification rule:** V02 automated syntax checks have passed. **Do not label V02 fully certified**, and do not advance any chapter to runtime verified or enterprise certified without recorded execution and independent sign-off.
