# MongoDB Enterprise — DBRE/SRE Production-Readiness Audit

> Scope: existing 80 chapters, unchanged numbering and chapter titles.  
> Phase 3 status: **80/80 static command-safety reviews completed**. Phase 4: validation framework established, **0/80 runtime-certified**. No chapter is runtime-validated by this audit.

## Acceptance rubric (10 controls)

For each chapter, record **Pass / Partial / Gap / Not applicable / Not yet inspected** for:

1. **Version and topology contract** — exact MongoDB/driver/operator version, edition, topology, permissions, prerequisites.
2. **Operational objective and ownership** — production risk, owner, impact, change approval and maintenance boundaries.
3. **Executable lab** — complete commands, synthetic fixtures, bounded resource use, deterministic assertions.
4. **Fault scenario** — safe, isolated fault injection or clearly identified offline simulation.
5. **Detection and observability** — MongoDB metrics/logs, client signals, alerts, thresholds and missing-data behavior.
6. **Diagnosis** — evidence capture, differential diagnosis, stop conditions, escalation.
7. **Safe remediation** — prechecks, blast radius, rollback/recovery path and post-change verification.
8. **Reliability criteria** — relevant SLI/SLO, RPO/RTO, data correctness, performance/capacity or explicit N/A.
9. **Security and cleanup** — least privilege, secrets, no production-destructive defaults, owned-resource cleanup.
10. **Validation evidence** — tested environment, expected/actual outputs, automation results, timestamp, reviewer and limitations.

**Ratings:** Pass = supported by inspected evidence; Partial = present but not fully testable or complete; Gap = absent; N/A = justified; Not inspected = no conclusion. Keyword presence is not a Pass. A written example is not a runtime test.

## Baseline and audit scope

- All **80 chapter Markdown files exist** in `mongodb-enterprise/` on `main` as of 2026-10-19.
- Curriculum baseline: MongoDB 8.0; review 7.0 compatibility and Enterprise entitlements per the existing master layout.
- Current curriculum claim: **80/80 written; runtime validation pending**. Preserve that distinction.
- Audit must retain the existing 80-chapter structure and existing chapter numbering.
- Changes to high-risk operational labs must use synthetic data and isolated environments; never treat a simulated recovery as a proven production RTO/RPO.

## Initial evidence-based spot audit (10/80 inspected)

| Chapter | Evidence observed | DBRE/SRE follow-up to verify or strengthen | Status |
|---|---|---|---|
| 01 — Fundamentals | Synthetic CRUD lab, duplicate-key failure exercise, health inspection, cleanup and acceptance checklist | Tie basic health signals to ownership, incident triage and explicit SLO applicability | Partial |
| 20 — TTL and index lifecycle | TTL behavior, failure exercise, observability, production retention-change runbook and cleanup | Validate safeguards for retention-policy changes and rollback limitations in an isolated environment | Partial |
| 29 — Replication lag and oplog sizing | Lag measurement, bounded secondary lag exercise, sizing model, guarded resize and recovery evidence | Exercise alert behavior and measured recovery thresholds; document version/topology test matrix | Partial |
| 49 — Backup architecture and RPO/RTO | Recovery objectives, strict timeline evaluator, negative planning cases and isolated restore plan | Execute an actual restore drill and record measured RPO/RTO rather than only modeled results | Partial |
| 60 — Kubernetes Operator | Compatibility matrix, CRDs, reconciliation, certificates, workload gate and cleanup | Verify supported operator combinations and actual Kubernetes disruption/reconciliation tests | Partial |
| 69 — Metrics, logs and FTDC | Sampling, rate calculations, false-spike exercise, dashboard acceptance and evidence handling | **Improved on audit branch:** operational ownership, collector-outage acceptance, incident sequence and evidence gate added; live monitoring tests and independent review still pending | Improved — runtime pending |
| 70 — Alert thresholds and SLOs | Executable SLO evaluator, burn-rate scenarios, missing-data drills and capacity model | **Improved on audit branch:** alert lifecycle, error-budget governance, capacity runbook, offline edge-case suite and live acceptance gate added; real backend/routing tests pending | Improved — runtime pending |
| 75 — Disk/cache/resource incidents | Read-only triage, pressure cases, recovery branches and Kubernetes correlation | Run safe resource-pressure drills with alert evidence and explicit stop/rollback gates | Partial |
| 78 — HA failover project | Controlled primary handoff, application reconciliation and failure drill | Record actual failover duration, client error rate, write consistency and recovery SLOs | Partial |
| 80 — Final readiness | Evidence matrix, smoke checks, executable readiness gate and exceptions | Run complete end-to-end acceptance with signed evidence and independent review | Partial |

**Important:** “Partial” means the inspected document contains relevant material but its full 10-control acceptance and runtime evidence have **not** been established. It is not a claim that the chapter is deficient in every listed follow-up area.

## Change log

- 2026-10-20 — Queried commit `8de1f4762faef8f69d897d90751f482d990a3c1d` for combined commit statuses (empty) and associated workflow runs (empty). The available workflow-run lookup filters PR-triggered runs, so these results **do not prove that the push-triggered Phase 4 workflow ran or succeeded**. CI remains unverified; no Actions run ID, logs or artifacts available for verification. Runtime-certified 0/80.


- 2026-10-20 — Phase 4 runbook copy/paste review found four doubled shell-continuation backslashes in the documented `lab_preflight.py` and `ch01_04_smoke.py` commands. Corrected them to single backslashes (`88f8129`) so operators can execute the multi-line examples as intended. This is a documentation fix only; CI run status and live lab execution remain unverified, runtime-certified 0/80.


- 2026-10-20 — Phase 4 CI workflow review found the Chapters 01–04 contract step used two literal trailing backslashes on `--root mongodb-enterprise`, unlike the one-backslash shell line continuation needed. Fixed in `.github/workflows/mongodb-enterprise-phase4.yml` (`db2e242`). The workflow is configured to run on audit-branch pushes, but its actual run conclusion and uploaded artifacts have **not been retrieved or verified**. Runtime-certified 0/80.


- 2026-10-20 — Phase 4 follow-up identified a blocking integration bug in the committed `structure_check.py`: its parser accessed `fence.group(1)` and `group(2)`, but the `FENCE` regex had no capture groups, causing an `IndexError` when a fenced block was present. Corrected the regex to capture marker and trailing text in commit `118dd25`. The earlier 80/80 read-only GitHub inspection used separate equivalent JavaScript logic, **not** this Python implementation; it did not establish Python CI success. Full Python test execution and CI remain unverified; runtime-certified 0/80.


- 2026-10-20 — Phase 4 safety review of the actual GitHub Chapter 01–04 integration smoke harness found a remaining `assert build.get("version")` in Chapter 04. Replaced with explicit `RuntimeError` so the guard remains active under `python -O` (`c23ba55`); strengthened source regression to reject this pattern (`1cbc891`). **Changes committed; full CI and live smoke execution not verified.** Runtime-certified 0/80.


- 2026-10-20 — Phase 4 direct GitHub local Markdown link review: fetched all 80 chapter files in seven batches and examined 183 relative Markdown-style link targets (35+27+24+35+34+20+8). Compared `.md` references against the 80 chapter names in `MASTER-LAYOUT.md` plus known curriculum indexes; **0 unknown Markdown targets or out-of-root targets flagged**. Scope limitation: does not prove anchor fragments, external URLs, or all non-Markdown relative file targets; not an execution of the Python filesystem L0 validator or GitHub Actions. Runtime-certified 0/80.


- 2026-10-20 — Phase 4 direct GitHub content inspection: fetched all 80 chapter Markdown files from audit branch in five batches (01–18, 19–36, 37–54, 55–72, 73–80). Each was checked for a Markdown heading and matching fenced-code markers/closing lengths using read-only equivalent logic. **80/80 fetched, 80/80 passed these two checks, 0 errors observed.** This was **not** execution of the repository's Python structure checker or GitHub Actions; local-link checks and full offline suite remain unverified. No MongoDB runtime tests; runtime-certified 0/80.


- 2026-10-20 — Phase 4 L0 fence parser improved: now tracks opening fence marker, matching character and minimum closing length, including tilde fences (`c91fdaf`); added unequal-length and tilde-fence tests (`71ffe3d`). This corrects a blind spot in simple odd/even counting. Changes are committed but **CI and full-repository audit results are not verified**; no live MongoDB tests. Runtime certification 0/80.


- 2026-10-20 — Phase 4 L0 audit correctness: discovered that the Markdown code-fence regex lacked multiline mode, so it could silently miss unbalanced fences after the first line. Fixed multiline detection (`73dd73a`) and added a regression with an unterminated fence after a chapter heading (`21edc89`). **GitHub Actions execution and real 80-chapter audit result remain unverified**; no MongoDB integration tests executed; runtime certification 0/80.


- 2026-10-20 — Phase 4 local offline execution expanded: ran a **reconstructed local suite** containing 9 preflight and 4 Chapters 01–04 contract unit tests using Python 3.13.5: **13 tests passed, 0 failures**. This is not execution of the exact GitHub checkout or all CI tests; actual 80-chapter L0 and GitHub Actions evidence remain unverified. No MongoDB integration was run. Runtime certification remains 0/80.


- 2026-10-20 — Phase 4 first observed offline test result: executed a **locally reconstructed copy** of `lab_preflight.validate_inputs` and the nine preflight tests using Python 3.13.5; **9/9 passed**. This is a limited local reconstruction result, **not** a verified checkout of the GitHub revision, GitHub Actions run, full validation suite or MongoDB integration test. GitHub DNS resolution failed from the execution container. Runtime certification remains 0/80.


- 2026-10-20 — Phase 4 smoke-test correctness: replaced Python `assert` statements in integration acceptance checks with explicit runtime failures (`0b78384`) so checks remain active under optimized Python (`-O`). Added offline regression invariants (`108260f`). GitHub checkout still cannot resolve github.com in the execution container; **CI execution and full-repository L0 remain unverified**, and no live MongoDB run was performed. Runtime certification 0/80.


- 2026-10-20 — Phase 4 safety correction: integration smoke pilot now refuses preexisting run-named collections and does not attempt cleanup when fixture insertion did not complete; ownership verification requires exactly one run-marked record (`4076360`). Added three offline smoke-harness safety-invariant tests (`e73f2c5`, cleanup `e40fb2d`). Compared Chapters 01–04 heading/disclaimer contracts against repository content; these appeared aligned, but the checker and CI have **not** been executed. Local git access failed due to DNS resolution. Runtime certification remains 0/80.


- 2026-10-20 — Phase 4 Chapter 01–04 isolated integration pilot: published opt-in, mutation-enabled [ch01_04_smoke.py](validation/ch01_04_smoke.py) (`8a38b70`, refinement `ebf06d3`) for disposable loopback standalone only. Preflights all four namespaces before any writes; requires separate lab and mutation approvals; tests bounded CRUD/duplicate-key, BSON identity mismatch, buildInfo/sentinel and build/fixture checks; cleans up only run-owned collections, not databases. Documented limits and manual execution in [validation/README.md](validation/README.md) (`227d237`). **Not executed.** It is not in GitHub Actions and cannot certify full chapter labs. Runtime-certified 0/80.


- 2026-10-20 — Phase 4 CI correctness: identified and fixed an extra backslash in the Chapters 01–04 contract command in GitHub Actions (`145f703`), which could have broken command argument continuation. Added four offline positive/fail-closed unit tests for the chapter contract (`043041a`). **CI execution still unverified; no runtime tests or certification performed.**


- 2026-10-20 — Phase 4: added Chapters 01–04 L0 documentation contract checker (`479e61c`) and integrated its JSON evidence into offline CI (`9fb4bbb`). These checks do not execute MongoDB labs. Repository checkout was unavailable in this execution environment, and CI outcomes have not been verified. Runtime certification remains 0/80.


- 2026-10-20 — Phase 4 Batch 1 preflight hardening: constrained the prototype to local-loopback MongoDB pending authenticated TLS and independently verified cluster identity; rejected URI query options, database paths and remote hosts (`d8e7f6d`), added three negative tests (`06174bf`) and revised usage guidance (`3cbdb12`). **No test execution or CI outcome verified.** Loopback is not itself proof of a disposable cluster; operator must reject production tunnels. Runtime certification 0/80.


- 2026-10-20 — Phase 4 Batch 1: GitHub connector lookup for commit-associated PR workflow runs returned no runs (it only reports PR-triggered runs; this does **not** establish that push/manual workflow never ran). Added opt-in, read-only MongoDB Chapters 01–04 preflight (`5936088`), six offline input-validation tests (`d0c255a`), and usage/scope limitations (`d764369`). No integration endpoint was supplied or contacted, and CI result remains unverified. Runtime certification **0/80**.


- 2026-10-20 — Phase 4 execution automation: added [GitHub Actions offline L0 workflow](../.github/workflows/mongodb-enterprise-phase4.yml) (`3728e35`) scoped to audit-branch pushes/manual dispatch. It compiles the validation scripts, runs synthetic positive/negative unit tests, checks the actual 80-chapter Markdown tree and uploads a JSON result artifact (when present). **Workflow execution and result not yet verified; runtime certification remains 0/80.** Isolated MongoDB integration tests remain to be implemented and run only with explicitly authorized lab infrastructure.


- 2026-10-20 — Phase 4 Batch 1 preparation (Chapters 01–04): reviewed chapter lab sections and prerequisites; corrected over-escaped regular expressions in the new L0 checker (`5737d69`) so numbered filenames, headings, fences and Markdown links can be recognized. Added synthetic positive/negative standard-library unit tests (`aa822da`) for 80-file success, missing chapter/link rejection and unbalanced fence rejection. **Not yet executed** against an actual repository checkout or MongoDB server. Chapters 01–04 remain **runtime not certified**; next gate is to run tests and capture exit status and real chapter L0 results, then build isolated integration fixtures.


- 2026-10-20 — **Phase 4 initiated:** added [validation/README.md](validation/README.md) with L0–L4 evidence levels, preflight/cleanup/approval gates, evidence schema and first 01–04 pilot; added [validation/structure_check.py](validation/structure_check.py), a read-only standard-library checker for 80 chapter files, heading/code-fence balance and local links. Framework commits `c245e85` and `61b0df7`. **Checker not yet executed against a repository checkout; no L0 result claimed. No MongoDB live lab run or runtime certification.**


- 2026-10-20 — **Phase 3 detailed command-safety review complete: Chapters 77–80, now 80/80 (100% static review).** Inspected production data modeling/query tuning and guarded state transitions (77), HA failover application-intent ledger and non-forced stepdown (78), isolated backup/restore with acknowledged-loss and two-database reconciliation (79), and final readiness evidence gate and go/no-go ownership (80). **Remediated all four chapters** with exact owned database-name checks before destructive cleanup, including both source and recovery databases in Chapter 79 (commits `a8cf59a`, `b96876f`, `954c058`, `76bb03f`). **Scope caveat:** this is completion of documentation/command-safety static review, **not** runtime lab certification, security sign-off, independent production readiness, or authorization to merge into main. Remaining work: run executable labs on isolated authorized infrastructure; verify backup/PITR and application correctness, TLS/auth and role boundaries, sharded and replica-set failover, Kubernetes storage/upgrade safety, metrics/alerts, CDC and external integrations; capture exact environment versions, logs, evidence and independent reviews; resolve failures and only then consider canonical promotion.


- 2026-10-20 — Phase 3 detailed command-safety review Chapters 73–76: inspected query plan/index regression diagnosis and reversal (73), TLS/auth fresh-session failure classification and independent recovery identity (74), disk/cache/IO incident read-only triage and logical-vs-physical reclamation (75), and replica-set election/sharding incident safety with non-forced stepdown and acknowledged-write reconciliation (76). **Remediated all four chapters** by checking exact expected lab database identity in the final cleanup block immediately before the ownership and destructive database-drop steps (commits `4a7801d`, `16df02f`, `1bdef9c`, `42245ad`). **Pending:** live query-plan and index regression, TLS/SCRAM failures and recovery, resource-pressure observations, election/topology convergence and full application correctness. Detailed command-safety review now 76/80.


- 2026-10-20 — Phase 3 detailed command-safety review Chapters 69–72: inspected restart-safe metric rates, FTDC/log retention and dashboard failure visibility (69), paired-window SLO alert/capacity acceptance (70), owner-approved index hide/unhide with maintenance stop gates (71), and reliability-aware FinOps/licensing decisions (72). **Remediated Chapters 69 and 71:** require exact expected lab database name before `dropDatabase()` in addition to existing ownership checks (commits `3859261`, `fe401f6`). Chapters 70 and 72 are evaluator/model and approval-focused; no concrete unsafe destructive command identified in this static pass. **Pending:** live collector freshness/alerts, maintenance planner and index recovery, independent capacity inputs, licensing/entitlement evidence. Detailed command-safety review now 72/80.


- 2026-10-20 — Phase 3 detailed command-safety review Chapters 65–68: inspected time-series TTL/bucket-aware retention and policy restoration (65), GridFS lifecycle plus capped collection rollover (66), MongoDB-to-Snowflake direct integration and owned schema retirement (67), and JSON/BSON transfer with typed reconciliation and guarded three-database cleanup (68). **Remediated Chapters 66–68** with exact expected owned database-name checks before destructive cleanup (commits `4da8b59`, `fc05fc3`, `798bdfd`). Chapter 65 already checks its exact lab namespace and ownership marker before database drop; no additional code edit required. **Pending:** live TTL timing/bucket behavior, GridFS abort/orphan reconciliation, Snowflake source-to-target identity and failure replay, and migration metadata/type acceptance. Detailed command-safety review now 68/80.


- 2026-10-20 — Phase 3 detailed command-safety review Chapters 61–64: inspected UID-bound Kubernetes eviction with PDB/CSI/identity acceptance (61), staged binary upgrade and separate FCV transition (62), driver pool/deadline/uncertain-write reconciliation (63), and CDC resume/checkpoint/invalidation handling (64). **Remediated Chapter 64:** optional destructive `orders.drop()` now checks exact training database, presence of run-specific marker, chapter identity and matching `RUN64` before deletion (commit `5520100`). Chapters 61–63 already require reviewed ownership and prohibit force eviction/downgrade shortcuts; no concrete command change identified in this static pass. **Pending:** live eviction and storage identity, binary/FCV staged upgrade, client retries/elections, and CDC crash/replay/invalidation evidence. Detailed command-safety review now 64/80.


- 2026-10-20 — Phase 3 detailed command-safety review Chapters 57–60: reviewed Ops Manager architecture/prerequisite endpoint checks (57), Agent automation one-field change/convergence and interruption recovery (58), Linux TLS/auth systemd service restart and retained-data cleanup (59), and Kubernetes controller/CRD/StatefulSet/PVC ownership and guarded retention (60). No concrete unsafe destructive command identified requiring edits in this static batch: Ch57 is non-mutating planning/probing; Ch58 requires reviewed UI automation and avoids hand-crafted config replacement; Ch59 checks the run marker and exact service before stopping, retains data; Ch60 refuses force deletes, finalizer stripping and unqualified namespace deletion. **Pending:** live Ops Manager enrollment/convergence, systemd restart, Kubernetes operator compatibility and CSI/PV ownership tests. Detailed command-safety review now 60/80.


- 2026-10-20 — Phase 3 detailed command-safety review Chapters 53–56: inspected selective insert-only recovery and guarded staging promotion (53), fenced replica-set recovery with acknowledged-write loss accounting (54), sharded logical backup with lock/unlock, source fencing and independent catalog (55), and evidence-based recovery acceptance with fail-closed evaluator (56). **Remediated Chapter 53** by checking exact source namespace before intentional `orders.drop()` and both exact owned database names before cleanup (commit `7f7faa2`). Chapters 54–56 already distinguish isolated restore from production cutover and disclose limitations of a single-host lab, source snapshot consistency and evaluator attestations; no concrete code remediation identified in this static pass. **Pending:** execute source fencing, replica/sharded restore, coordinated unlock, transaction acceptance, real loss reconciliation, RPO/RTO and independent evidence review. Detailed command-safety review now 56/80.


- 2026-10-20 — Phase 3 detailed command-safety review Chapters 49–52: inspected RPO/RTO planning evaluator, logical dump and isolated namespace restore, clean-stop physical copy and separate restored instance, and Ops Manager PITR into a distinct managed target. **Remediated Chapter 50** with exact source/recovered namespace checks immediately before both `dropDatabase()` calls (commit `3b63c33`). Chapter 49 is planning-only; Chapter 51 uses a verified stopped data tree, immutable backup and separate writable restore clone; Chapter 52 requires completed base snapshot, available replay cutoff and an independently identified disposable restore target. No additional concrete unsafe cleanup defect identified in 49/51/52 in this static pass. **Pending:** live logical and physical restores, Ops Manager PITR, key/access recovery, and independent measured RPO/RTO/application validation. Detailed command-safety review now 52/80.


- 2026-10-20 — Phase 3 detailed command-safety review Chapters 45–48: inspected offline encrypted-data backup/restore and wrong-key isolation (45), client-side/QE key vault and KMS dependency (46), service-identity rotation and access-drift recovery (47), and hardening acceptance/evidence ledger (48). **Remediated** Chapters 46–48 by checking exact `mongodb_enterprise_tutorial_chNN` database identity before user/role/collection or database disposal (commits `5f359cd`, `12b02fe`, `bb81f5e`). Chapter 45's restore exercises operate on separate offline copies with guarded paths and no database drop; no actionable code change identified in this static pass. **Pending:** live Enterprise at-rest encryption and restore, QE library/provider compatibility, actual fresh-connection revocation tests and acceptance evidence on the target deployment. Detailed command-safety review now 48/80.


- 2026-10-20 — Phase 3 detailed command-safety review Chapters 41–44: inspected authenticated identity/role lifecycle, TLS/x.509 trust and renewal, external authentication compatibility gates and native audit evidence/cleanup. **Remediated:** Chapter 41 now checks both exact owned database names before two database drops; Chapters 42–43 check exact owned database names before cleanup; Chapter 44 checks the exact owned database name before dropping its user/role/collection (commits `16ff49d`, `ff9641e`, `44659fd`, `68d1987`). Existing UUID/ownership markers and privilege checks remain intact. Chapter 43's local SCRAM control is not evidence that OIDC/Kerberos/LDAP integrations work; Chapter 44 requires an actual Enterprise audit-capable binary and protected evidence handling. **Pending:** live least-privilege negative tests, TLS trust/renewal, external IdP integrations and native audit event coverage/recovery. Detailed command-safety review now 44/80.


- 2026-10-20 — Phase 3 detailed command-safety review Chapters 37–40: inspected targeted/scatter-gather explain and manual range migration, shard-key refinement and resharding interruption boundaries, config/shard outage recovery, and scaling acceptance with fixed workload. Each chapter asserted drop success but lacked an immediate exact-name check; **remediated Chapters 37–40** with `mongodb_enterprise_tutorial_chNN` guards (commits `182302d`, `a5d81e1`, `fdf0c8d`, `dfd4947`). Chapter 38 explicitly records balancer/AutoMerger states and pause intent before global change, treats lost reshard command response as uncertain and restores shared policy only after verifying terminal operation and unrelated settings. Chapter 40 distinguishes manual range redistribution from automatic-balancer validation and avoids inferring physical space reclamation from logical migration. **Pending:** live sharded routing, resharding, policy restoration, member outages, and workload acceptance in owned cluster. Detailed command-safety review now 40/80.


- 2026-10-20 — Phase 3 detailed command-safety review Chapters 33–36: inspected synthetic sharding architecture, shard-key analysis, owned sharded-cluster bootstrap and collection balancing/zone migration lifecycle. Chapters 33–36 had successful-drop assertions but lacked immediate exact-name guards; **remediated** with `mongodb_enterprise_tutorial_chNN` checks before database deletion (commits `37229ea`, `5ca9022`, `1d53eab`, `cb16227`). Chapter 35 confines `addShard` to its disposable lab; Chapter 36 records original balancer/zone policy and provides scoped restoration, with automatic balancing—not manual move—as acceptance evidence. **Follow-up:** verify real shard/mongos topology and capacity, manual migration boundaries, zone cleanup and original policy restoration through controlled live execution; project volume teardown remains destructive and requires ownership verification. Detailed command-safety review now 36/80.


- 2026-10-20 — Phase 3 detailed command-safety review Chapters 29–32: inspected bounded lag/oplog resize and restoration, one-at-a-time initial sync/member storage replacement, isolated-primary network partition and rollback classification, and quorum-loss/failover recovery. All four chapters had successful-drop assertions but lacked immediate exact-name guards before `dropDatabase`; **remediated Chapters 29–32** with `mongodb_enterprise_tutorial_chNN` checks (commits `38367d1`, `1770c68`, `4332431`, `d029fa0`). Chapter 31 does not claim rollback unless divergent write and rollback evidence exist; Chapter 32 reconciles acknowledged/uncertain operation IDs before cleanup. **Pending:** controlled live topology drills, independent member storage/Compose ownership checks, and verification of network healing, initial sync, oplog restoration and quorum recovery. Detailed command-safety review now 32/80.


- 2026-10-20 — Phase 3 detailed command-safety review Chapters 25–28: inspected read-only oplog/topology diagnostics, dedicated three-member replica set creation and owned Compose teardown, read/write concern guarantees, and planned maintenance/stepdown readiness. All four chapters had a `dropDatabase()` without immediate exact-name check; **remediated Chapters 25–28** with `mongodb_enterprise_tutorial_chNN` guards and drop-result checks (commits `9f9b50b`, `bb4d2a3`, `eb8cb8c`, `d8f1727`). Chapter 28 uses non-forced `replSetStepDown` after health checks and explicitly verifies resulting topology rather than treating a disconnect as success; Chapter 26 warns that `docker compose -p mongodb-ch26 down --volumes` deletes six named project volumes and must not be used on retained/shared projects. **Follow-up:** verify actual project resource ownership before destructive Compose teardown and exercise member restart/stepdown and concern semantics in a controlled lab. Detailed review now 28/80.


- 2026-10-20 — Phase 3 detailed command-safety review Chapters 21–24: inspected explain plan experiments, scoped profiler activation/restoration, WiredTiger metric snapshots and bounded capacity fixtures. Each chapter previously called `labNN.dropDatabase()` without an immediate exact database-name guard; **remediated Chapters 21–24** with namespace checks and successful-drop assertions (commits `879d674`, `8aaa38c`, `7fe33df`, `537be56`). Chapter 22's profiling `try/finally` covers ordinary exceptions, with a saved recovery command for shell termination; actual restoration across interrupted sessions remains untested. Chapters 23–24 explicitly avoid claiming instant cache/volume reclamation after database deletion. **Pending:** live query-plan/profiler restoration and metrics/IOPS acceptance. Detailed command-safety review now 24/80.


- 2026-10-20 — Phase 3 detailed command-safety review Chapters 17–20: inspected index creation/removal, uniqueness failure paths, TTL/collMod lifecycle and full cleanup sections. All four chapters previously invoked `labNN.dropDatabase()` without an immediate exact-name check. **Remediated on audit branch:** Chapters 17–20 now require exact `mongodb_enterprise_tutorial_chNN` namespace before database deletion and assert successful drop result (commits `2383569`, `13f5d56`, `bace97f`, `a3689f2`). Chapter 20 explicitly warns that TTL hiding does not suspend expiration and that restoring TTL settings does not recover already deleted data. **Pending:** live index build/plan behavior, TTL asynchronous deletion and index-collMod compatibility, cleanup execution. Detailed command-safety review now 20/80.


- 2026-10-20 — Phase 3 detailed command-safety review Chapters 13–16: Chapters 13–15 guard chapter database names before collection cleanup; Chapter 13 uses read-only aggregation (no `$merge`/`$out`), Chapter 14 checks source cardinality, and Chapter 15 tests signed/tenant-scoped pagination. Chapter 16 includes transaction abort/uncertain commit handling but previously called `lab16.dropDatabase()` without an immediate namespace guard. **Remediated on audit branch in commit `f5e83a6`:** require exact `mongodb_enterprise_tutorial_ch16` database name and check drop result before proceeding. Runtime transaction and cleanup validation still pending. Detailed command-safety review now 16/80.


- 2026-10-19 — Phase 3 detailed command-safety sample Chapters 09–12: manually inspected risky write operations, final assertions and cleanup blocks. All four guard the exact chapter database before dropping enumerated fixtures. Chapter 09 scopes array updates and distinguishes object/array shape failures; Chapter 10 `updateMany` uses a provider ID plus expected version and explicitly notes non-atomic cross-document freshness; Chapter 11 `collMod` migration/rollback requires scoped administration and differentiates warn mode from actual schema enforcement; Chapter 12 `updateMany` filters by typed/absent migration field and verifies counts, ordered/unordered partial bulk outcomes and replay behavior. **Follow-up:** confirm Chapter 11's restoration path on a real training server, and Chapter 12's error/result semantics with pinned server and mongosh versions; neither was executed here. Detailed spot review now covers 12/80 chapters.


- 2026-10-19 — Phase 3 detailed command-safety sample Chapters 05–08: inspected section structure, risky command matches and full cleanup blocks. Chapter 05 gates collection removal on exact lab database and restricts container/volume deletion to `mongodb-ch05`/`mongodb-ch05-data`; Chapter 06 uses `mongodb-ch06`-scoped containers, volumes and explicit certificate filenames rather than recursive deletion; Chapters 07–08 guard the database name and enumerate exact fixture collections. Chapter 08 explicitly warns against empty-filter bulk writes. **Follow-up:** Chapter 05/06 cleanup still requires operator confirmation that named Docker resources belong to this lab; names alone do not establish ownership, especially after interrupted/reused environments. No runtime command execution or repeatability testing performed.


- 2026-10-19 — Phase 3 detailed command-safety sample Chapters 01–04: inspected exact filenames, section structure, risky command occurrences and cleanup contexts. Chapters 01–03 use chapter-specific databases/collections and explicit namespace guards before `.drop()`, with `docker stop`/`docker rm` scoped to chapter-named optional containers; Chapter 02 explicitly warns not to remove shared training servers. Chapter 03 optional restart evidence is distinguished from required acceptance. Chapter 04 is a deployment comparison lab with no risky command match in this sample. **Finding:** no unguarded broad database drop or `rm -rf` observed in these four chapter texts. This is a manual spot review, not full command semantic proof, actual shell execution or security acceptance. Next review should inspect command dependencies and failure-path cleanup in Chapters 05–08.


- 2026-10-19 — Phase 2 prerequisite/lab *presence* scan Chapters 65–80: all 16 have explicit MongoDB 8.0/FCV 8.0 baseline, topology/deployment and privilege/auth references, fenced code, assertions/acceptance, cleanup and recovery/rollback terminology. Targeted inspection: Chapter 69 explicitly leaves live metrics/log/FTDC checks pending; Chapter 70's offline SLO checks do not substitute for deployed monitoring acceptance; Chapter 78 requires a live HA handoff and application reconciliation; Chapter 79 requires isolated live restore and DR acceptance; Chapter 80 explicitly requires runtime evidence from all earlier gates and does not equate writing with production readiness. **Prerequisite/documentation presence scan now covers 80/80 chapters; no live runtime execution performed, no blanket safety or correctness certification implied.** Next phase: detailed semantic prerequisite/command safety audit, offline fixture execution and controlled live labs.


- 2026-10-19 — Phase 2 prerequisite/lab *presence* scan Chapters 49–64: all 16 include versioned baseline information, topology/deployment references, privileges/auth, executable-language code fences, acceptance/verification language, cleanup and recovery/rollback terminology. Fourteen match a generic MongoDB 8.0 text regex; Chapters 61 and 64 explicitly pin **Enterprise 8.0/FCV 8.0**, so these are regex false negatives. Targeted inspection: Chapter 55 requires Chapters 35–40 and 49–54 plus capacity for a two-shard recovery lab; Chapter 60 requires authorized Kubernetes/Ops Manager/PKI/storage and approved controller compatibility; Chapter 61 requires accepted Chapter 60 state and explicitly excludes PVC deletion; Chapter 64 requires an accepted replica-set deployment and pinned PyMongo. These are documentation-presence findings, **not successful live restore, controller deployment, storage continuity or CDC execution**.


- 2026-10-19 — Phase 2 prerequisite/lab *presence* scan Chapters 33–48: all 16 have explicit topology, privileges/auth, fenced code, assertions/acceptance, cleanup and recovery/rollback terminology. Fifteen match the general `MongoDB 8.0` keyword pattern; Chapter 45 instead explicitly pins **MongoDB Enterprise 8.0** and authorized binaries (false negative, not missing version baseline). Targeted reading: Chapter 38 pins Chapter 35 sharded topology and FCV; Chapter 43 separates retained TLS/SCRAM control from eligible external identity provider integration; Chapter 45 separates local keyfile demonstration from KMIP/production policy; Chapter 48 requires live evidence for accepted security controls and does not claim compliance certification. These are documentation checks only; Enterprise/KMIP/IdP and Kubernetes/live runtime acceptance remain pending.


- 2026-10-19 — Phase 2 prerequisite/lab *presence* scan Chapters 17–32: all 16 contain MongoDB 8.0 baseline, topology and privilege/auth terminology, executable-language fences, verification/acceptance language, cleanup and rollback/recovery/stop terminology. Section scans found explicit prerequisite, failure, troubleshooting and acceptance sections throughout. Targeted document inspection: Chapter 20 bounds TTL/index lifecycle to a training server; Chapter 22 separates core self-managed profiler lab from Atlas-eligible optional query statistics; Chapter 28 uses disposable 3-member rs26 and non-forced stepdown; Chapter 30 requires owned volumes, Chapter 26 setup and healthy topology. **These are documentation presence findings, not code execution or live acceptance.**


- 2026-10-19 — Phase 2 prerequisite/lab *presence* scan Chapters 01–16: all 16 include MongoDB 8.0 baseline, a role/permission/auth mention, fenced executable-language code, assertions/expected results and cleanup terminology. Five chapters (11–15) do not match generic topology keywords; manual inspection confirms Chapter 11 states a Community/Enterprise training database and Chapter 16 explicitly requires replica set or sharded cluster. Seven chapters (03, 06, 08–10, 13–14) lack a generic rollback/stop/restore keyword, which is a review prompt, **not proof of missing safety controls**. These are heuristic presence checks, not syntax execution or full rubric passes. No live labs run.


- 2026-10-19 — Phase 2 first-pass link audit: fetched all 80 indexed chapter files in five groups; chapter titles match index, no missing/duplicate chapter numbers, no unresolved recognized local chapter Markdown link destinations, and no mismatched parsed previous/next destinations. Two Chapter 63 references are external GitHub URLs, not missing local files. This scan does not validate external URL reachability, all non-chapter relative assets, anchor fragments, or prerequisites; live runtime testing remains pending.


- 2026-10-19 — Navigation repair follow-up: Chapters 60–63 now include explicit backward navigation (commits `57397442`, `61ba5959`, `cf4f774b`, `6328695a`); Chapter 63 forward link now targets published Chapter 64. Prior repairs covered Chapters 39–48 and 56–59. Full link-target/prerequisite verification remains pending; **no runtime acceptance claimed**.

- 2026-10-19 — Navigation review: confirmed reference-section backward links in sampled Chapters 39–40 and 56–57; restored Chapter 64 forward link to Chapter 65 at commit `3162c35`. Remaining absent `Previous:` labels require a separate consistent-footer pass; complete link-target validation is pending. **No runtime tests executed.**

- 2026-10-19 — Phase 2 chapter existence and heading audit: individually fetched all 80 chapter files referenced by MASTER-LAYOUT; **80/80 exist and match indexed headings**. Navigation label scan flagged absent explicit `Previous:` in Chapters 39–48 and 56–63, and absent explicit `Next:` in Chapter 64 (Chapter 80 is terminal). These are format observations; link-target and prerequisite validation remain pending. **No runtime tests executed.**

- 2026-10-19 — Phase 2 inventory checkpoint: master layout lists 80 unique numbered chapter links (01–80), with no missing numbers or filename-prefix mismatches; individually fetched Chapters 01–16 and confirmed matching headings. Chapters 17–80 and full link integrity still require verification. **No runtime validation claimed.**

- 2026-10-19 — Chapter 80 updated at commit `63ad829`: independent enterprise readiness board, GO/NO-GO, change invalidation, accountable review and fail-closed board manifest. **Live runtime validation and production approval remain pending.**

- 2026-10-19 — Chapter 79 updated at commit `40e0e0a`: independent restore and integrity controls, measured RPO/RTO, negative tests, regional cutover/failback and DR evidence gate. **Live restore and regional DR acceptance remain pending.**

- 2026-10-19 — Chapter 78 updated at commit `e90ca2b`: approved failover game day, client/ledger recovery timeline, quorum/consistency gates, scoped chaos scenarios and HA evidence manifest. **Live handoff and application failover validation remain pending.**

- 2026-10-19 — Chapter 77 updated at commit `52e9902`: representative workload benchmarks, tenant/schema/pagination/concurrency contracts, safe schema/index rollout and production acceptance gate. **Live workload and failover tests pending.**

- 2026-10-19 — Chapter 76 updated at commit `fd0b592`: quorum/election safety, acknowledged-write reconciliation, sharded incident boundaries, read-only triage and recovery evidence gate. **Live handoff and sharded recovery tests remain pending.**

- 2026-10-19 — Chapter 75 updated at commit `d09765a`: Kubernetes resource triage, storage expansion guardrails, cache/memory/CPU decision tree and incident evidence gate. **No live resource exhaustion, resize or recovery test performed.**

- 2026-10-19 — Chapter 74 updated at commit `e88091a`: layered access outage triage, Kubernetes discovery and secrets checks, rotation/recovery runbook, failure matrix and incident evidence gate. **No live TLS/credential or Kubernetes acceptance performed.**

- 2026-10-19 — Chapter 73 updated at commit `0e79a50`: production query incident severity, evidence ledger, safe remediation and manifest gate. **Live query and incident acceptance remain pending.**

- 2026-10-19 — Chapter 72 updated at commit `e2fbe7a`: reliability-aware rightsizing, Kubernetes and storage guardrails, recovery/entitlement checks, staged rollout and final FinOps evidence gate. **No live cost, contract or workload validation performed.**

- 2026-10-19 — Chapter 71 updated at commit `54be986`: index-owner review, safe hide/observe/reverse workflow, audit change packet and offline fail-closed approval gate. **No live maintenance or approval verification performed.**

- 2026-10-19 — Chapter 70 updated at commit `8cf0b54`: DBRE alert lifecycle, error-budget governance, capacity incident runbook, offline acceptance tests and live evidence gate. **Documentation/code authored; no runtime execution claimed.**

- 2026-10-19 — Chapter 69 updated on audit branch at commit `830dda2`: monitoring failure visibility, collector outage/recovery acceptance, DBRE investigation and machine-readable evidence gate. **Documentation change only; runtime acceptance remains pending.**

## Remaining chapters — inspection queue

- **01–16:** Fundamentals and application behavior; inspect 02–16.
- **17–24:** Indexing and performance; inspect 17–19 and 21–24.
- **25–32:** Replication and HA; inspect 25–28 and 30–32.
- **33–40:** Sharding and scale; inspect all.
- **41–48:** Security and governance; inspect all.
- **49–56:** Backup/restore and DR; inspect 50–56.
- **57–64:** Enterprise deployment and Kubernetes; inspect 57–59 and 61–64.
- **65–76:** Specialized workloads, observability and incidents; inspect 65–68, 71–74 and 76.
- **77–80:** Capstones; inspect 77 and 79.

## Implementation sequence

1. Complete all 80 document-level inspections, with concrete file/section references and control-by-control results.
2. Define shared DBRE/SRE acceptance conventions in the existing chapter standard without invalidating established labs.
3. Prioritize chapters 69–80, then 49–64, 25–40, 17–24, 41–48, and 01–16 according to risk and dependencies.
4. Improve one chapter at a time, preserving its original filename and subject, and update this tracker.
5. Perform static checks and run labs in supported isolated environments; attach observed results, versions and limitations.
6. Request technical/security review and independent verification before calling a chapter canonical or production-validated.

## Evidence log template

```yaml
chapter: 00
commit: "<commit SHA>"
review_date: "YYYY-MM-DD"
reviewer: "<reviewer>"
mongo_version: "<exact version>"
topology: "<isolated replica set/sharded cluster/etc>"
kubernetes_version: "<exact version or N/A>"
operator_version: "<exact version or N/A>"
controls:
  version_topology: not_inspected
  operational_objective: not_inspected
  executable_lab: not_inspected
  fault_scenario: not_inspected
  observability: not_inspected
  diagnosis: not_inspected
  remediation: not_inspected
  reliability_criteria: not_inspected
  security_cleanup: not_inspected
  validation_evidence: not_inspected
runtime_validation: pending
static_review: pending
security_review: pending
evidence_links: []
open_risks: []
```

This audit is an engineering worklist, not certification of the curriculum or its runtime behavior.
