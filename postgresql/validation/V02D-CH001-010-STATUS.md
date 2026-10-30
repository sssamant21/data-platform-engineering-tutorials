# PostgreSQL V02-D — Technical Review of Chapters 001–010

**Date:** 2026-10-30  
**QA branch:** `qa/postgresql-v01-static-validation-20261030`  
**Review scope:** Ten chapters, ten matching top-level labs and their referenced SQL/Python/Bash source files.  
**Disposition:** **Static curriculum/source contract checks PASS; semantic review partial; live PostgreSQL 18 execution NOT RUN; independent operational certification PENDING.**

## Evidence

- [Passing GitHub Actions V02 run #41060774816](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41060774816)
- [V02-D regression tests](test_v02d_ch001_010.py) — 8 tests, 8 passes on GitHub Actions Python 3.11
- [V02-A SQL parser](validate_v02.py) — **157/157 SQL files parsed** on the same commit; all 13 Python, 5 Bash and 2 PowerShell source files passed their respective static checks
- [V02-B safety checks](validate_v02b.py) — passed; its established ten guarded cleanup files unchanged
- [V02-C embedded code audit](validate_v02c.py) — 791 fenced blocks, 668 statically syntax-checked, 19 context/manual-review items, zero scanner blockers
- [PostgreSQL 18 pg_settings reference](https://www.postgresql.org/docs/18/view-pg-settings.html), [predefined monitoring roles](https://www.postgresql.org/docs/18/predefined-roles.html), [CREATE DATABASE](https://www.postgresql.org/docs/18/sql-createdatabase.html), [pg_database catalog](https://www.postgresql.org/docs/18/catalog-pg-database.html), and [monitoring views](https://www.postgresql.org/docs/18/monitoring-stats.html).

**Important:** A passing syntax, link or Python unit test is not proof that a PostgreSQL command returns the expected results, affects only authorized objects, or safely withstands failure.

## Chapter-by-chapter review

| Chapter | Lab/source relationship | Static technical observations | Next acceptance gate |
|---|---|---|---|
| **001 — DBRE/SRE responsibilities** | Lab 001 + first-response snapshot SQL | Bounded read-only diagnostics, separate `pg_isready` and authenticated probes, intentional session timeout clearly distinguished from outage | Verify actual permissions, visibility and expected timeout behavior in disposable PG18 |
| **002 — Processes, memory, storage and WAL** | Lab 002 + architecture snapshot SQL | PostgreSQL 18 checkpointer/WAL receiver terminology cross-checked; WAL delta labeled instance-wide, not workload-only | Verify synthetic WAL row count, replication visibility and privileges |
| **003 — Linux/network/storage** | Lab 003; OS command examples, no companion SQL asset required | Readiness exercises are mainly read-only; wrong-port negative probe must not be mislabeled server outage | Run on supported Linux host and collect cgroup, mount, port and DNS evidence |
| **004 — Reproducible PG18 lab** | Lab 004 + 004-operations-lab.sh | Non-root, loopback binding, private marker and destroy guard are documented; BASH syntax passes | Provision primary + two standby instances, test replication and guarded teardown; no runtime evidence yet |
| **005 — psql and catalogs** | Lab 005 + safe-catalog inspection SQL | SQL uses read-only transaction, schema variable quoting and explicit timeout/search-path controls | Verify observer/application privileges, psql command behavior, rollback |
| **006 — Packages and directories** | Lab 006 + path inventory SQL | Separates package-managed service and manual disposable cluster; acknowledges binary PATH/permission differences | Confirm 18 binaries/package provenance on Debian/RPM and actual configured paths |
| **007 — Init/checksums/locale** | Lab 007 + inventory SQL + **new guarded 007-drop-lab-databases.sql** | Correct builtin/libc provider catalog codes verified against PG18 docs. **High-priority unguarded DROP DATABASE examples replaced** with fail-closed exact-cluster cleanup | Exercise successful database creation/collation, wrong-token/wrong-cluster denials and positive cleanup on a disposable instance |
| **008 — Config precedence** | Lab 008 + config inspection SQL | Differentiates session/local settings, `ALTER SYSTEM` reload vs restart, baseline reset; intentionally modifies only lab primary | Confirm privileges, pending_restart transitions, standby reconnect and rollback |
| **009 — Service/crash recovery** | Lab 009 + lifecycle inspection SQL | Smart/fast/immediate shutdown tests scoped to isolated lab; distinguishes PostgreSQL immediate stop from storage/kernel crash | Verify actual shutdown/recovery log, committed/uncommitted fixtures, standbys |
| **010 — Drift and acceptance** | Lab 010 + capture/compare/inspection assets | **Role-visibility dependency corrected.** Low-privilege snapshots use `server_version` instead of `data_directory`; lab-admin separately verifies PGDATA. Baseline comparator has 8 passing CI tests | Run observer/app captures and injected drift on PG18; verify provenance, restart, failed-start recovery, final settings |

All chapter/lab pairs and the explicitly required script references are checked by the 8-test CI suite. The table reflects static reading, cross-file alignment and targeted PostgreSQL 18 documentation checks, **not a full independent semantic proof of every line**.

## Confirmed fixes

### V02D-001 — Chapter 007 destructive cleanup (HIGH; statically mitigated)

**Before:** The lab contained two direct `psql -c "DROP DATABASE ..."` commands, relying on a warning about disposable scope.

**After:** The lab calls the new `postgresql/scripts/007-drop-lab-databases.sql`, which refuses to run unless all controls match: PostgreSQL 18, loopback:55432, database `postgres`, login `lab_admin`, an independently supplied PostgreSQL system identifier, expected Chapter 004 `/tmp/postgresql-dbre-lab.<id>/primary` path, primary role, exact chapter-specific confirmation token, the two expected database names and provider codes (`c` libc / `b` builtin), lab-admin ownership, and absence of active sessions in either database. Both DROP statements are standalone and **not atomic**, so partial failure needs inspection.

**Remaining risk:** Static guard presence and parsing passed. Wrong-cluster/permission/partial-state behavior must be tested on disposable PostgreSQL; system ID and confirmation tokens do not constitute production authorization. After a partial CREATE, this script deliberately refuses because both databases are not present; manual review is required.

### V02D-002 — Chapter 010 ordinary-role configuration visibility (MEDIUM; statically mitigated)

**Before:** The 12-setting comparison captured `data_directory` through both application and monitoring sessions and expected it to be present. Config values and `sourcefile` visibility can differ by role; application roles should not be granted `pg_read_all_settings` just to pass a lab.

**After:** Captures and comparator both use `server_version` in place of `data_directory`, still preserving 12 tracked settings. The privileged `lab_admin` identity guard separately proves the actual data directory. The lab guide explicitly explains that `sourcefile` may be NULL for an application role, while `lab_observer` inherits `pg_read_all_settings` through `pg_monitor`. Each profile gets a separate approved baseline.

**Eight CI tests passed:** chapter/lab/script contracts; Chapter 007 cleanup guard presence; Chapter 010 12-setting parity and role-aware collection; equal-baseline acceptance; changed values/provenance; pending-restart detection; CSV roundtrip/missing-setting rejection; and wrong-major/duplicate-row rejection. These use synthetic CSVs only, no live connections.

## Outstanding findings / conditions

1. **Chapters 001–010 are not runtime validated.** No PostgreSQL 18 cluster was provisioned for this task and no SQL or lab teardown was executed.
2. **Privilege and error-code checks pending.** Confirm actual permissions for `pg_read_all_settings`, `pg_file_settings`, `pg_control_system` and role-specific views; capture SQLSTATE where the lab predicts failure.
3. **Configuration provenance must be verified with real sessions.** `pg_settings.sourcefile` may be NULL based on privileges or settings origin. A NULL sourcefile is not proof that configuration came from defaults.
4. **Chapter 007 cleanup remains deliberately partial-state sensitive.** Both comparison DBs must exist with expected providers and owner before the guarded script executes. A failed second CREATE requires human-approved recovery.
5. **Chapter 004's OS-side safeguards need real negative tests.** Verify wrong path, symlink, root, nested mount and running-instance refusal in a disposable environment, along with start/stop.
6. **Further semantic coverage is needed.** V02-C still has context, risk and expected-outcome queues. The present V02-D tests check contract and comparator logic, not entire Markdown commands.

## Next

- **V02-D Chapters 011–020:** continue source/role/transaction/locking semantic validation and add targeted automated tests.
- **V03 PG18 isolated runtime:** first exercise Chapter 004 and negative safety preflights; then run 001–010 using recorded environment, command exit status, observed outputs and rollback evidence. No enterprise certification until peer review and runtime proof.
