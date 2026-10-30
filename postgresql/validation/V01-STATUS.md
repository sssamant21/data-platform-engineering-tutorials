# PostgreSQL V01 — Static Validation Status

**Started:** 2026-10-30  
**Scope:** `postgresql/` only  
**Source revision:** `main` at validation kickoff; PostgreSQL directory blobs confirmed identical to `qa/redis-v01-static-validation-20261030`.  
**Working branch:** `qa/postgresql-v01-static-validation-20261030`  
**State:** **IN PROGRESS / NOT CERTIFIED**. The inventory and index inspection below are completed; the full on-checkout validator run is not yet evidenced.

## What was actually checked

| Item | Result | Evidence and boundaries |
|---|---|---|
| Chapter-file inventory | **PASS** | Exactly 100 numbered chapter Markdown files, one each for 001–100 |
| Core lab-file inventory | **PASS** | Exactly 100 top-level numbered lab Markdown files, one each for 001–100 |
| Additional lab assets | **INVENTORIED** | 187 nested files, including 111 files in `labs/sql/`; existence is not runtime verification |
| Other supporting assets | **INVENTORIED** | 62 files under `scripts/`, five monitoring files, one project report, one template |
| README chapter navigation | **PASS (target existence)** | Links to all 100 numbered chapters; no missing inline local targets found in README |
| PROGRESS chapter navigation | **PASS (target existence)** | Links to all 100 numbered chapters; no missing inline local targets found in PROGRESS |
| MASTER-PLAN chapter navigation | **FAIL / DRIFT** | Only chapters 001–031 are linked; entries for 032–100 are not linked as published chapters |
| Selected chapter spot-check | **REVIEWED** | Sampled chapters 001, 010, 025, 032, 037, 040, 063, 074, 095 and 100; associated chapter/lab/supporting-asset paths observed in repository tree |
| Entire-subtree link and code-fence scan | **PENDING CI/RUN** | Validator authored; no completed full-tree run or generated output claimed |
| SQL, Bash, Python execution | **NOT STARTED** | No live PostgreSQL 18 runtime execution evidence |
| Restore, failover, security, performance gates | **NOT STARTED** | Require isolated lab infrastructure, prerequisites, and retained evidence |

## Findings

### PG-V01-001 — Master plan diverges from published curriculum (high)

`MASTER-PLAN.md` describes chapters 032 onward using an older proposed sequence and lists many as **Planned**, whereas `README.md`, `PROGRESS.md`, and `chapters/` show 001–100 authored/published. Chapter 033 is a concrete example: the plan says *Unused, Duplicate and Bloated Index Diagnosis*, while the published chapter is *Index Build, Reindex and Concurrent Maintenance*. The master plan must be reconciled with the actual chapter filenames, module divisions, and status semantics before navigation certification.

**Acceptance:** Every chapter 001–100 in the canonical plan points to the matching published file and uses a status consistent with `PROGRESS.md`.

### PG-V01-002 — Short chapter/lab requires independent review (medium)

`chapters/037-table-and-index-maintenance-strategy.md` is approximately 1.8 KB and its core lab is approximately 1.1 KB. Chapter 040 is approximately 3.0 KB. Short content is **not automatically wrong**; review Chapters 032–040 for learning objectives, runnable setup, realistic expected observations, safety, cleanup, and evidence collection. The Chapter 037 lab references both `labs/sql/037-setup.sql` and `labs/sql/037-investigate.sql`, whose filenames are present.

**Acceptance:** Review the end-to-end instructional quality, actual referenced scripts and reproducibility before deciding whether to expand or keep concise.

### PG-V01-003 — Existing review labels are not independent certification (high)

`README.md` states that 001–100 are authored and statically reviewed; `PROGRESS.md` documents pending runtime lab execution. Treat previously recorded reviews as historical authoring evidence. V01 independently measures structure, links and Markdown formatting. It must not be labeled *runtime verified*, *enterprise certified*, or *production ready* without corresponding evidence.

**Acceptance:** Keep separate authoring, static QA, code review, runtime, and independent approval states.

## Validation sequence

1. **V01 — Structural/static:** run `python postgresql/validation/validate_v01.py --json-out postgresql-v01-evidence.json` from a complete repository checkout; review all reported errors and warnings, reconcile the master plan, and rerun until clean.
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

**Next action:** run and inspect the V01 validator; prioritize `MASTER-PLAN.md` drift and Chapter 037's instructional completeness.
