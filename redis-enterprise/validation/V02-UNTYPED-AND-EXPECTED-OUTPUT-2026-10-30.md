# Redis Enterprise V02 — Untyped Fences and Command-Output Review, Pass 2

**Review date:** October 30, 2026  
**Branch:** `qa/redis-v02-code-examples-20261030`  
**Draft PR:** [#42](https://github.com/sssamant21/data-platform-engineering-tutorials/pull/42)  
**Verified CI:** [run #41107220740](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41107220740) — **SUCCESS** (60 offline tests).  
**Execution policy:** No Redis, Redis Enterprise, Kubernetes, shell lab, or cluster command was executed in this pass.

## What changed

### 1. Untyped example context triage

Added the offline, reusable `redis-enterprise/tools/review_v02_untyped_fences.py` and its **8 fixture tests**, integrated into `.github/workflows/redis-enterprise-v02.yml`. The CI artifact `redis-v02-untyped-review.json` retains an individual, line-referenced contextual triage entry for **each of the 371 remaining** text/unlabeled blocks that contain command-like tokens. Its classifications are **heuristic**, not reviewed/approved execution status.

After reclassifying 2 executable examples as correctly typed command fences, the categories are:

| Provisional category | Blocks |
|---|---:|
| Command vocabulary or reference lists | 154 |
| Ambiguous narrative/reference text | 136 |
| Diagrams, comparisons, or symbolic arrows | 43 |
| Formula/symbolic text | 14 |
| Potentially runnable instructions requiring context review | 20 |
| Negative/warning examples requiring context review | 4 |
| **Total** | **371** |

The classifier deliberately treats `TTL = 3600`, `set only if the key exists`, pseudocode branching and command lists as **non-executable explanations**, not paste-ready Redis instructions.

**Focus set — Chapters 01, 03, 04, 10, 11:** **62** original unlabeled matches were inspected using their text, nearby headings and context. These are overwhelmingly lists, tables, diagrams, templates or TTL examples; no confirmed unsafe runnable recommendation was found in that focus set. This is not blanket certification of every textual example.

### 2. Two executable inspection examples corrected

- **Chapter 09 (Administration):** Reclassified five `rladmin` inspection commands from a `text` fence to `bash`; added authorized cluster-node context, installed-release compatibility, read-only scope, expected node/db/shard/proxy output and evidence for unsupported or unauthorized operations.
- **Chapter 76 (Capacity Project):** Reclassified `INFO memory` from a `text` fence to `redis`; added approved authenticated/TLS endpoint prerequisite, expected `used_memory` and `used_memory_rss` fields, and caution that one INFO reply is not an authoritative whole-cluster memory report.

Remaining **20 priority** untyped blocks include conceptual examples such as `GET document`, application retry flows, read-modify-write diagrams, workload command-mix tables, and illustrative REST method examples. They remain a **manual context review queue**. A label alone does not fix whether an example is correct or authorized.

### 3. High-value expected-result corrections

| Chapter | Reviewed examples and change |
|---|---|
| **01 — Fundamentals** | Isolated write-flow example now uses an expiring tutorial key, clarifies `SET`=`OK` does not prove replica acknowledgment/durability, and includes cleanup. Adds actual expected `HSET` new-field count, `INCR`, `LPUSH` list order, and repeat-run caveats |
| **04 — Commands** | Adds `TTL` and `PTTL` timing and absent/persistent outcomes, `INCR` behavior for missing/repeated keys, and `HSET`/`HINCRBY` new-field versus existing-field results |
| **10 — Acceptance** | Adds `SCAN` cursor iteration and COUNT hint plus `UNLINK` return-count and delayed memory-reclamation interpretation |
| **11 — TTL** | Adds precise outcomes for ordinary `SET` replacement dropping expiration, `EXPIRE`, `PERSIST`, and Redis 7.0+ conditional `EXPIRE NX`, with repeat/missing key alternatives |
| **09 and 76** | Typed, scoped inspection commands and expected output rather than executable-looking text |

Five additional regression/contract tests were added for these material command/output corrections. The total CI tests rose from **47** to **60** across six suites, including 8 new untyped-fence fixtures.

## Reproducible CI evidence

| Check | Latest result |
|---|---:|
| Chapters inventoried | 80 / 80 |
| Fenced code blocks | 8,141 |
| Explicit executable-language blocks | 1,126 |
| Text/unlabeled command-like candidates | 371 |
| Likely runnable untyped candidates (heuristic) | 20 |
| Python syntax candidates | 0 of 162 |
| JSON syntax candidates | 0 of 34 |
| Redis-language fences pattern-gated | 558 |
| Redis continuation/bare-SCAN syntax findings | 0 |
| Full inventory: missing-nearby-output-cue candidates | 969 |
| Offline unit/contract tests | **60 / 60 PASS** |

The 969 missing-nearby-output-cue items are not confirmed mistakes: headings, conditional outcomes, warning examples and nearby explanatory prose vary. The rule counts use different populations and are not additive.

### What is NOT proven

- **No live Redis command execution**, including neither local containers nor staging/Enterprise clusters.
- No release-specific validation of `rladmin` output, Redis modules, ACL/TLS, memory metrics, HA/failover, DR/backup/restore, or workload performance.
- No full human review of all 371 unlabeled blocks, all 969 output-cue candidates, or all 80 chapters.
- No production certification or permission to perform destructive operations.

## Next V02 milestone

Prioritize the **20 untyped possibly runnable examples** with a human intent verdict and retype only genuinely executable commands. Continue expected-output reviews for executable chapters and version-sensitive operations, especially the administrative API, Streams and test-lab scenarios. Retain the PR in draft until independent DBRE/SRE/security acceptance and an explicitly approved **separate staging runtime-validation phase**.
