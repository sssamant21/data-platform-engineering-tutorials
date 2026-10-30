# PostgreSQL V02-D — Chapters 031–040 Index, Maintenance and Partition Review

**Date:** 2026-10-30 · **QA branch:** `qa/postgresql-v01-static-validation-20261030`  
**Disposition:** Targeted static/source-contract review completed and specific risks mitigated. PostgreSQL 18 runtime/negative tests and independent operational certification **NOT PERFORMED**.

## Evidence and reproducibility

- [V02-D contract suite for Chapters 031–040](test_v02d_ch031_040.py): ten deterministic static tests; all earlier 28 tests retained in the workflow. Final branch-run conclusions must be checked before merging.
- [V02 static workflow](../../.github/workflows/postgresql-v02-code-audit.yml): pglast PostgreSQL 18 grammar, Python/Bash/PowerShell parser checks, V02-B cleanup guard checks, V02-C Markdown example inventory and V02-D unit/contract tests.
- [Passing initial corrected SQL/run #41105750160](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41105750160): **160/160 SQL assets parsed, 0 parser errors, 10/10 Chapters 031–040 checks passed**. Subsequent seven cleanup changes and stronger test assertions require the most recent CI run.
- [PostgreSQL 18 VACUUM](https://www.postgresql.org/docs/18/sql-vacuum.html) — cannot run inside an explicit transaction.
- [PostgreSQL 18 table partitioning](https://www.postgresql.org/docs/18/ddl-partitioning.html) and [ALTER TABLE](https://www.postgresql.org/docs/18/sql-altertable.html) — non-concurrent DETACH locks, CONCURRENTLY restrictions, retained standalone tables and ATTACH safety.

**Scope warning:** Parsing SQL after preprocessing psql client directives does not execute it; the presence of a guard does not prove effective refusal. Synthetic calculations and links alone are not production or enterprise certification.

## Chapter-by-chapter review

| Chapter | Checked contract or example | Outstanding runtime gate |
|---|---|---|
| 031 — B-tree and other indexes | Fixed 50k-row fixture, plan shape whitelist, read-only bounded EXPLAIN, separate index types and storage tradeoffs | Compare real index/operator-class behavior, query plans and index-maintenance impacts |
| 032 — Composite/partial/expression/covering | Source setup and index tests inventoried; cleanup now checks schema/table ownership and exact object removal, not CASCADE | Actual composite order, expression/partial predicate behavior, heap fetches, cleanup |
| 033 — Index builds and concurrent maintenance | CONCURRENTLY operations outside transaction, intentionally failing unique build and invalid-index inspection; cleanup tightened | SQLSTATE and invalid-index lifecycle; timed concurrent build, interruption, recovery and replica/WAL proof |
| 034 — Index usage/bloat | Bounded churn, statistics caveats and index lifecycle conditions inspected; cleanup now constrained | Distinguish physical bloat and usage-counter reset from legitimate index retirement |
| 035 — VACUUM and index cleanup | VACUUM separate from BEGIN/COMMIT, dead tuple/XID age and autovacuum caveats; cleanup narrowed | Real vacuum, visibility, lag, blocker and estimate variability |
| 036 — Autovacuum and freeze | Bounded per-table tuning and RESET; no anti-wraparound cancellation or global autovacuum disable; cleanup narrowed | Real threshold/age behavior, reloptions restoration, maintenance duration |
| **037 — Maintenance strategy** | **Remediated HIGH:** prior `CREATE SCHEMA IF NOT EXISTS` + `INSERT` risk and missing cleanup replaced by exact-target one-time setup/churn and no-CASCADE teardown | 100k-row setup, update 20k/delete 10k, VACUUM, refusal cases, 90k-row cleanup and evidence |
| 038 — Partition basics | Detach/reattach and pruning covered; cleanup checks expected three partitions and avoids CASCADE | Routing, bounds, detached-table ownership, locks and safe reattach |
| 039 — Pruning/local indexes | Generic vs custom prepared plans and partition pruning; cleanup bounded to three attached partitions | Plan variability, actual pruning and index-selection evidence, cleanup |
| **040 — Partition lifecycle** | **Remediated HIGH:** identity/token guards on setup and lifecycle; cleanup checks four attached partitions and 12,002 rows, using transactional exact table/schema deletion without CASCADE | Detach/reattach, January data preservation, independently restored archive and approved cleanup |

## Major fixes

### V02D-037 — Uncontrolled fixture reuse and incomplete teardown (HIGH; statically mitigated)

**Prior:** `037-setup.sql` used `CREATE SCHEMA IF NOT EXISTS ch037` and `CREATE TABLE IF NOT EXISTS`, then inserted 100,000 synthetic rows regardless of whether that schema/table was an existing fixture. Its lab described cleanup but provided no executable cleanup script.

**Now:** Three scripts require the exact disposable Chapter 004 PostgreSQL 18 target at 127.0.0.1:55432/ops_lab as lab_admin, the observed system identifier and explicit stage tokens:

- `037-CREATE`: rejects an existing `ch037` namespace; builds 100,000 rows transactionally and ANALYZEs afterward.
- `037-CHURN`: rejects changed/previously operated fixtures; checks 100,000 input rows, 20,000 update targets, 10,000 delete targets and ownership before one bounded run.
- `037-DROP`: checks identity, schema owner, 90,000 surviving rows and no unexpected independent tables, then atomically drops `ch037.orders` and `ch037` without CASCADE.

The [rewritten Chapter 037 lab](../labs/037-table-and-index-maintenance-strategy-lab.md) documents independent identity verification, stop conditions, exact commands and acceptance evidence. **All negative and positive SQL behavior still require disposable runtime testing.**

### V02D-040 — Partition cleanup could destroy unexpected detached data (HIGH; statically mitigated)

The previous cleanup used `DROP SCHEMA ch040 CASCADE`. If an attach failed, a detached January table could remain in the schema and be destroyed by broad cleanup.

Now the setup and lifecycle SQL require the independently verified Chapter 004 target, per-stage tokens `040-CREATE` and `040-LIFECYCLE`, and expected pre-lifecycle contents. Cleanup requires `040-DROP`, the matching cluster ID, owner, **12,002 parent-visible events and all four exact attached monthly partitions**. It drops `ch040.events` followed by `ch040` *without CASCADE* in one transaction; an unexpected detached child or independent dependency should block it. The [lab guide](../labs/040-partition-lifecycle-retention-and-recovery-project-lab.md) explicitly requires an independent archive restore before accepting retention cleanup. Archive creation/restore is **not automated** by the scripts and remains an open acceptance test.

### V02D-032/036/038/039 — Seven broad cleanup scripts narrowed (HIGH; static controls added)

The existing `032`, `033`, `034`, `035`, `036`, `038`, `039` cleanup scripts retained the V02-B database/system-identifier/token preflight. They now additionally require:

- An expected lab schema owned by the invoking user and the known owned table.
- No unexpected independent table/view/materialized/foreign objects in that schema.
- For partitioned 038/039, exactly three attached child partitions.
- Explicit `DROP TABLE` and `DROP SCHEMA` inside a transaction, without schema-wide `CASCADE`.

Unexpected external dependencies or partial fixture states should cause a failure and require manual recovery instead of widening the delete. **This is still not a complete proof of ownership or safety of every index/trigger dependency.** Runtime refusal/partial-state and concurrency tests are outstanding; operators must not use these scripts on production.

## Automated assertions

Ten new tests enforce all ten chapter/lab pairings, required files and the following contract invariants:

1. Chapter 031 read-only/whitelisted query plan and statement budgets.
2. Chapters 032–036/038–039 explicit cleanup tokens, owner/known-relation checks and no-CASCADE teardown.
3. Chapter 033 concurrent index lifecycle outside transaction blocks.
4. Chapter 036 bounded VACUUM and per-table tuning without `ALTER SYSTEM`.
5. Chapter 037 fail-closed fixture creation.
6. Chapter 037 one-time bounded churn (no repeatable silent mutations).
7. Chapter 037 explicit no-CASCADE cleanup with row/owner verification.
8. Chapter 040 exact-target setup and one-time lifecycle preconditions.
9. Chapter 040 atomic no-CASCADE cleanup with four expected child partitions.
10. All 10 chapter/lab pairs and navigation/coverage.

**All tests are static assertions, not live database operations.** V02-C still has manual-context and destructive-operation review items; statistics and plan outputs have not been independently reproduced.

## Next gates

- Check final V01/V02 Actions result on the report commit, retaining failing evidence if any.
- Execute isolated PostgreSQL 18 negative guard tests first (wrong token, wrong system ID, role, port, version, missing/wrong table, detached orphan, extra object, external dependency), then explicitly authorized positive fixture runs.
- Obtain real concurrent-index/REINDEX and VACUUM evidence, no global anti-wraparound intervention, and measure partition DETACH/ATTACH locks, state and exact row counts.
- Independently verify a backup/archive restore into another **disposable** cluster before accepting Chapter 040 retention.
- Require independent application/security/DBRE approval before any enterprise or production certification.

**Next sequence:** V02-D Chapters **041–050** (backup, PITR, replication, HA). Treat Chapters 031–040 as **statically reviewed only**, not runtime verified or safe for production execution.
