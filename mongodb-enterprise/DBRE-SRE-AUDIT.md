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
| 70 — Alert thresholds and SLOs | Executable SLO evaluator, burn-rate scenarios, missing-data drills and capacity model | Validate alert rules end-to-end in a monitoring backend, including paging/noise behavior | Partial |
| 75 — Disk/cache/resource incidents | Read-only triage, pressure cases, recovery branches and Kubernetes correlation | Run safe resource-pressure drills with alert evidence and explicit stop/rollback gates | Partial |
| 78 — HA failover project | Controlled primary handoff, application reconciliation and failure drill | Record actual failover duration, client error rate, write consistency and recovery SLOs | Partial |
| 80 — Final readiness | Evidence matrix, smoke checks, executable readiness gate and exceptions | Run complete end-to-end acceptance with signed evidence and independent review | Partial |

**Important:** “Partial” means the inspected document contains relevant material but its full 10-control acceptance and runtime evidence have **not** been established. It is not a claim that the chapter is deficient in every listed follow-up area.

## Change log

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
