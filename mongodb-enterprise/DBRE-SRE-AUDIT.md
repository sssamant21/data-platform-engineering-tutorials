# MongoDB Enterprise — DBRE/SRE Production-Readiness Audit

> Scope: existing 80 chapters, unchanged numbering and chapter titles.  
> Audit status: **in progress**. No chapter is runtime-validated by this audit.

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
