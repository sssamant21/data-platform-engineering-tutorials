# V01 Editorial and Navigation Review — 2026-10-30

**Scope:** Chapters 42, 44, 47 and 51, plus the 80-chapter navigation entry point.  
**Evidence:** GitHub `main` curriculum and draft [PR #41](https://github.com/sssamant21/data-platform-engineering-tutorials/pull/41).  
**Decision:** Editorial findings triaged; navigation index added and mechanically checked. **No runtime testing or production certification.**

## Summary

The four short chapters are meaningful checklists and operational guidance, **not empty placeholder chapters**. Their smaller size alone is not a defect. The substantive review finds gaps in **reproducible lab steps, sample evidence, and explicit expected results** relative to adjacent expanded chapters (for example, 41 and 50).

| Chapter | What already exists | Evidence gap and suggested edit | Priority |
|---|---|---|---|
| 42 — Upgrades and change engineering | Compatibility, recovery, N-1 and go/no-go gates; 10-step nonproduction exercise; 10 failure modes; runbook flow and sign-off checklist | Add a **version-scoped preflight and post-step evidence template** showing expected observations, abort triggers, ownership, and supported rollback/restore route. Do not invent cross-release upgrade commands. | P2 |
| 44 — Governance and readiness | Ownership, ORR package, exceptions, risk and audit controls, templates, 10 governance gap scenarios | Add one **fully worked synthetic ORR and exception record** showing required evidence, failed gate, remediation, and final disposition. This is an evidence-workflow lab, not a Redis command lab. | P2 |
| 47 — Database lifecycle | Classification, provisioning standards, drift/resize/retirement flow, acceptance checklist, 10 failure scenarios | Existing hands-on exercise is a high-level paragraph. Add **numbered staging procedures and expected pass/fail observations** for deployment, TLS/auth smoke, metrics, safe resize, drift and controlled retirement. Exact commands depend on deployment mode. | P1 |
| 51 — End-to-end project | Integrated workload requirements, scenario matrix, 15 failure modes, production evidence scorecard, cleanup guidance | Representative lab is high-level and has **zero fenced code examples**. Add a **self-contained synthetic lab or version-scoped staging lab** with exact inputs, commands, expected outputs, cleanup and evidence. Never mark this capstone production-certified on simulated evidence. | P1 |

## Navigation review and fix

**Before:** No `redis-enterprise/README.md` index. The 80 chapter bodies contained no recognized relative Markdown links, so prior V01 local-link checks were not exercising navigation.

**Change:** Added `redis-enterprise/README.md` with **80 clickable chapter links grouped into 13 parts**. The V01 validator now checks:
- Chapter index exists and covers 01–80 **exactly once** in its chapter-index section.
- Every local Markdown target in the index exists on disk.
- Index chapter links stay inside the expected chapter folder.
- Missing, duplicate, or incorrect chapter links fail CI.
- 4 extra validator tests cover valid, missing, duplicated, and broken chapter navigation.

**Open editorial work:** Previous/next links inside every individual chapter and external reference URL health are **not** covered. Those should be a separate navigation/editorial enhancement; the entry-point index is now complete.

## Recommended execution gates

1. **V01:** CI tests and structural navigation pass; keep the four depth warnings in the review log. Do not conflate size warnings with failed chapters.
2. **V02:** Inventory all executable and illustrative code fences, check syntax where safe, identify commands with side effects, and map each step to expected output. Repair P1 evidence gaps in 47/51 first.
3. **V03/V04:** Review reproducibility, safety, and release-specific correctness with subject-matter reviewers; stage only after approved nonproduction environment and product version are known.

**Safety boundary:** No credentials in repository, no live failover/restore/upgrade tests in this phase, no shared-environment FLUSHDB/FLUSHALL cleanup.
