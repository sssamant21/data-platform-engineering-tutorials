# PostgreSQL V01 — Static Validation Status

**Started:** 2026-10-30  
**Scope:** `postgresql/` only  
**Source revision:** `main` at validation kickoff; PostgreSQL directory blobs confirmed identical to `qa/redis-v01-static-validation-20261030`.  
**Working branch:** `qa/postgresql-v01-static-validation-20261030`  
**State:** **V01 STATIC PASS / RUNTIME NOT CERTIFIED**. Full on-checkout validation passed in [GitHub Actions run 41053566641](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41053566641); eight editorial-depth warnings remain for independent review.

## What was actually checked

| Item | Result | Evidence and boundaries |
|---|---|---|
| Chapter-file inventory | **PASS** | Exactly 100 numbered chapter Markdown files, one each for 001–100 |
| Core lab-file inventory | **PASS** | Exactly 100 top-level numbered lab Markdown files, one each for 001–100 |
| Additional lab assets | **INVENTORIED** | 187 nested files, including 111 files in `labs/sql/`; existence is not runtime verification |
| Other supporting assets | **INVENTORIED** | 62 files under `scripts/`, five monitoring files, one project report, one template |
| README chapter navigation | **PASS (target existence)** | Links to all 100 numbered chapters; no missing inline local targets found in README |
| PROGRESS chapter navigation | **PASS (target existence)** | Links to all 100 numbered chapters; no missing inline local targets found in PROGRESS |
| MASTER-PLAN chapter navigation | **PASS AFTER REPAIR** | All 100 published chapters now linked to matching files in the QA branch |
| Selected chapter spot-check | **REVIEWED** | Sampled chapters 001, 010, 025, 032, 037, 040, 063, 074, 095 and 100; associated chapter/lab/supporting-asset paths observed in repository tree |
| Entire-subtree link and code-fence scan | **PASS IN CI** | 222 Markdown files, 977 local relative links, zero errors; eight short-content warnings |
| SQL, Bash, Python execution | **NOT STARTED** | No live PostgreSQL 18 runtime execution evidence |
| Restore, failover, security, performance gates | **NOT STARTED** | Require isolated lab infrastructure, prerequisites, and retained evidence |

## Verified CI evidence

- [Initial V01 run — failed](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41053295069): 1 navigation error (MASTER-PLAN missing links 032–100), 8 warnings; failure preserved as remediation evidence.
- [Repaired V01 run — passed](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41053566641): **100 chapters**, **100 numbered top-level labs**, **222 Markdown files**, **977 local relative links**, **0 errors**, **8 warnings**. All three navigation documents link to all 100 chapters.
- GitHub Actions retained a JSON artifact named `postgresql-v01-evidence` on each run. The V01 pass validates static repository structure and markdown path/fence checks **only**; it does not parse SQL, run shell scripts, or establish database recovery reliability.

## Findings

### PG-V01-001 — Master plan diverged from published curriculum (high; resolved on QA branch)

`MASTER-PLAN.md` describes chapters 032 onward using an older proposed sequence and lists many as **Planned**, whereas `README.md`, `PROGRESS.md`, and `chapters/` show 001–100 authored/published. Chapter 033 is a concrete example: the plan says *Unused, Duplicate and Bloated Index Diagnosis*, while the published chapter is *Index Build, Reindex and Concurrent Maintenance*. The master plan must be reconciled with the actual chapter filenames, module divisions, and status semantics before navigation certification.

**Resolution:** Rebuilt the published 20-module index using the actual README chapter paths and reconciled publication/runtime status language. All chapters 001–100 now have valid links. **Verified** in passing CI run 41053566641. The original proposed standalone managed-service and Kubernetes tracks remain an explicit scope difference rather than being silently claimed as delivered.

### PG-V01-002 — Short chapter/lab requires independent review (medium)

`chapters/037-table-and-index-maintenance-strategy.md` is approximately 1.8 KB and its core lab is approximately 1.1 KB. Chapter 040 is approximately 3.0 KB. Short content is **not automatically wrong**; review Chapters 032–040 for learning objectives, runnable setup, realistic expected observations, safety, cleanup, and evidence collection. The Chapter 037 lab references both `labs/sql/037-setup.sql` and `labs/sql/037-investigate.sql`, whose filenames are present.

**Acceptance:** Review the end-to-end instructional quality, actual referenced scripts and reproducibility before deciding whether to expand or keep concise.

### PG-V01-003 — Existing review labels are not independent certification (high)

`README.md` states that 001–100 are authored and statically reviewed; `PROGRESS.md` documents pending runtime lab execution. Treat previously recorded reviews as historical authoring evidence. V01 independently measures structure, links and Markdown formatting. It must not be labeled *runtime verified*, *enterprise certified*, or *production ready* without corresponding evidence.

**Acceptance:** Keep separate authoring, static QA, code review, runtime, and independent approval states.

## Validation sequence

1. **V01 — Structural/static: PASS (2026-10-30).** Run `python postgresql/validation/validate_v01.py --json-out postgresql-v01-evidence.json` from a complete repository checkout. CI found 0 errors across 222 Markdown files and 977 local relative links. Eight nonblocking warnings remain assigned to editorial review.
2. **V02 — Code/command safety:** classify all fenced examples and referenced SQL/Bash/Python/PowerShell; parse or lint where possible; identify privileged, destructive and version-specific commands; verify rollback and stop conditions.
3. **V03 — Lab prerequisites:** check Docker/Linux/Windows requirements, version pinning, service accounts, access controls, paths, expected outputs and cleanup.
4. **V04 — Runtime smoke:** execute read-only and disposable PostgreSQL 18 labs sequentially in a controlled environment; capture PostgreSQL version, command, expected vs actual result, and exit code.
5. **V05 — Reliability exercises:** verify backups/restore, WAL/PITR, replication/failover, locks, VACUUM, PgBouncer and alerting with measured SLO/RPO/RTO evidence.
6. **V06 — Independent acceptance:** application/security/DBRE review, findings remediation, rerun evidence, status reconciliation and documented sign-off.

## Guardrails

- Static checks must be repeatable without any database connection.
- Destructive or failover tests require a disposable environment and explicit operator control.
- Do not attach a certification label to a chapter on the basis of a successful Markdown check.
- Track defects by chapter, severity, reproduction steps, evidence, owner, and closure commit.

**Next action:** V02 code/command safety review, plus manual assessment of the eight short-content warnings before proceeding to disposable PostgreSQL lab execution.
