# PostgreSQL V02-D — Chapter 021–030 technical review

**Date:** 2026-10-30  
**Branch:** `qa/postgresql-v01-static-validation-20261030`  
**Status:** Targeted static review and remediation published. **28/28 cumulative V02-D unit/contract checks passed on code commit `85eac56`**; latest documentation-only branch CI rerun may remain queued. **No live PostgreSQL testing.** **Not runtime-validated or enterprise-certified.**

## Scope

Chapters 021–030 cover service-level indicators/objectives, PostgreSQL statistics windows, `pg_stat_statements`, structured logs/traces, Prometheus/Grafana alerting, performance triage, safe EXPLAIN, planner/extended statistics, CPU/memory/I/O/wait analysis, and an end-to-end slowness project.

The review compared each of the ten chapters with its lab guide, supporting SQL/Python/Bash files, declared inputs/outputs, safety bounds and expected results. Evidence from automated parsers and tests is static, not execution of PostgreSQL or its services.

## Source and regression evidence

- [New test suite — Chapters 021–030](test_v02d_ch021_030.py): **10/10 PASS** in [GitHub Actions run #41103490392](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41103490392), job `124226307845` (commit `85eac56`). Cumulative V02-D suites **8 + 10 + 10 = 28/28 PASS**. GitHub workflow-level completion may lag the already completed successful job.
- [V02 workflow](../../.github/workflows/postgresql-v02-code-audit.yml) enforces this suite alongside earlier Chapters 001–020 suites, SQL parsing and guard checks.
- [SLO evaluator](../scripts/021-slo-evaluate.py), [statistics delta helper](../scripts/022-statistics-window-delta.py), [query ranking](../scripts/023-query-window-rank.py), [JSON log correlation](../scripts/024-correlate-json-logs.py), [alert receiver](../scripts/025-lab-alert-receiver.py), and [EXPLAIN plan summarizer](../scripts/027-plan-summary.py) are exercised by synthetic offline inputs.
- SQL setup changes for [Chapter 028](../scripts/028-statistics-setup.sql) and [Chapter 030](../scripts/030-project-setup.sql) add SQL-level fail-closed controls.

## Review matrix

| Chapter | Static review finding | Runtime acceptance still required |
|---|---|---|
| **021** Database SLIs/SLOs | Availability versus timely-success denominator, half-open windows, low-volume handling and malformed target validation reviewed; rejected nonfinite targets | Verify end-to-end sampled SQL probes, latency timing, denominator inclusion and budget policy with approved fixture |
| **022** Statistics snapshots | Delta helper checks source/database identity, reset epochs, counter monotonicity, collection chronology and gap limits | PostgreSQL 18 real stats snapshot timing, async flush and selective reset boundaries |
| **023** `pg_stat_statements` | Ranking requires consistent cohort, entry epoch, global reset/deallocation and fixed policy; malformed samples now fail explicitly | Actual extension preload, tracked query families, query IDs, reset/dealloc and permission behavior |
| **024** Logs and trace correlation | Match requires constrained source/app/PID/session/timestamp; raw SQL/messages not exported; duplicate-conflict behavior unit tested | Capture real JSON logs, validate session IDs, slow-duration and SQLSTATE correlation, rotation and safe cleanup |
| **025** Prometheus/Grafana alerts | Receiver accepts bounded lab-only labels and deliberately sanitized payloads; offline foreign-cluster refusal tested | PromQL rule tests with `promtool`, scrape/exporter availability, alert timing/routing, recipient behavior and dashboard acceptance |
| **026** Performance triage | Snapshot and collector scripts are bounded and distinguish database evidence from host/namespace evidence | Real lock, wait state, OS resource and collection-failure evidence |
| **027** Safe EXPLAIN | JSON summarizer validates node structure, inclusive buffer fields and actual rows/loops; SQL exercise notes sequence consumption even after rollback | Confirm real plan formats, bounded read/write plans, planning locks, and nonrollbackable sequence side effects |
| **028** Planner statistics | **Fixed:** setup SQL now rejects wrong DB/role/host/port/version/cluster-data-directory and standby before fixture creation | Observe planner estimates before/after ANALYZE, dependencies/MCV/ndistinct behavior and restricted cleanup |
| **029** CPU/memory/I/O/waits | Collector caps snapshot counts, times and private evidence; separates waits from CPU and temporary-work memory | Sample live waits and host metrics during bounded CPU, sleep, lock and spill exercises |
| **030** Slowness capstone | **Fixed:** setup SQL now refuses targets outside Chapter 004 PG18 disposable primary; fixed eight-request probe and rollback workflow inventoried | Reproduce incident chain, 700ms lock deadline, baseline/incident/recovery, planner hypothesis and independent reviewer report |

## Concrete fixes

### PG-V02D-021 — SLO target validation (LOW, fixed)

`021-slo-evaluate.py` now explicitly checks `target.is_finite()` before interval comparisons. An invalid nonfinite target is a deterministic rejected input, not an unhandled decimal comparison trap. Positive and empty-window calculations remain unchanged.

### PG-V02D-023 — Query ranking sample shape (MEDIUM, fixed)

`023-query-window-rank.py` now rejects non-object JSON roots and non-object array entries with explicit `ValueError`. This improves the expected fail-closed behavior of the offline ranking CLI without changing valid comparisons.

### PG-V02D-028/030 — SQL setup identity gates (HIGH, statically mitigated)

Previously these scripts depended on the lab guide's shell-level guard. Both now independently require `ops_lab`, `lab_admin`, PostgreSQL 18, primary role, loopback address and port 55432 and the Chapter 004 disposable `data_directory` path pattern. An exception inside the initial transaction prevents setup DDL if the target differs.

**Limitations:** These checks do not prove a physical cluster is safe or production-authorized when the operator can control its configuration. Runtime negative tests for wrong role, port, path, standby and version are mandatory. Use only on the independently verified Chapter 004 disposable instance.

## 10 new targeted regression checks

1. Exactly one chapter/lab pair and required script references for each 021–030.
2. Both Chapter 028/030 setup scripts retain the SQL-level identity controls.
3. SLO arithmetic with three included events, one failed and one successful-but-slow.
4. Empty windows and invalid SLO target values.
5. Valid stats counter delta plus reset and impossible counter rejection.
6. Query-window mean/rank behavior and per-entry epoch exclusion.
7. Non-object/truncated query-statistics input refusal.
8. Sanitized trace/log matching, exact duplicates and conflicting duplicate refusal.
9. Loopback receiver's strict lab cluster/environment labels.
10. EXPLAIN node/loop/buffer calculations and malformed plan rejection.

The tests use **synthetic Python data only**. No PostgreSQL client commands, server connections, live Prometheus/Grafana, kernel or host fault injection.

## Open certification gates

- The code-bearing commit `85eac56` passed all 28 V02-D tests and the V02 parser. Confirm the final documentation-only QA commit's workflow completes before merge; do not equate a queued workflow with a pass.
- Independently classify remaining V02-C embedded code risk and evidence-guidance flags; the block counts change as documentation changes.
- In a disposable PostgreSQL 18 environment, first exercise negative identity tests, then execute Chapter 021–030 labs in order. Retain SQLSTATE/exit status, identity, expected-versus-observed values and cleanup evidence.
- Verify role privileges, `pg_stat_statements` extension configuration, real structured log/session correlation, PromQL/alert behavior and planner statistics with actual postgresql/hardware conditions.
- Require an independent operational/security reviewer before any production certification.

**Next:** V02-D Chapters **031–040** (indexes, VACUUM/autovacuum, partitioning and lifecycle safety). **No live data modifications occurred during this review.**
