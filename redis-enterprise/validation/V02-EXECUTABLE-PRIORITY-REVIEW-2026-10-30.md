# Redis Enterprise V02 — Executable Example and Output-Cue Priority Review

**Date:** 2026-10-30  
**Draft pull request:** [#42](https://github.com/sssamant21/data-platform-engineering-tutorials/pull/42)  
**CI proof:** [run #41056794606](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41056794606) — SUCCESS  
**Scope:** Static/code/documentation review only. **No Redis, Kubernetes, or cluster-management commands were executed.**

## 1. Chapter 15 — CLI consistency substantially completed

Prior review found 20 standalone `redis-cli GET/SET/TTL/PTTL/DEL/EXISTS` lab calls that silently targeted the local default connection rather than the TLS-authenticated Redis Software/Enterprise endpoint used earlier in the chapter.

**Changes committed:**

- Defined a reusable **`rcli` Bash helper** that targets the explicitly approved `REDIS_HOST`/`REDIS_PORT`. Non-loopback hosts require `REDIS_TLS=1` and a readable CA bundle, or the function refuses the connection.
- For a named Redis ACL user, use `REDIS_USER`; mutual TLS deployments must add the approved client certificate and key before running.
- Replaced all 20 later one-off Redis CLI commands with `rcli`. The plain localhost `redis-cli` connectivity example remains explicitly restricted to isolated local, unauthenticated sandboxes.
- Preserved `REDISCLI_AUTH` across the Bash lab steps until final cleanup; all three Python Redis client examples can use this same environment variable or an approved `REDIS_PASSWORD` source.
- Added expected results for synthetic cache/lock/TTL tests, conditional `SET NX` replies, expiration, and exact-key `UNLINK`/`EXISTS` cleanup.
- Updated Chapter 15 cleanup to use read-only scoped `rcli SCAN`, review cursor behavior, and remove **only five individually known lab keys**, using the current authenticated endpoint. Jitter keys require explicit owner confirmation.
- Added Bash parse and CLI regression assertions. Passing these tests means the examples are structurally consistent, **not** runtime-validated.

### Chapter 15 acceptance boundary

The scripts intentionally simulate workload concurrency; run them only on a dedicated and approved nonproduction database. Output and scheduling vary. The sample does not demonstrate actual end-to-end Redis Software/Enterprise compatibility, secure secret-store integration, scale SLOs or production single-flight correctness.

## 2. High-risk operation triage across 80 chapters

Added `redis-enterprise/tools/review_v02_executable_commands.py` and `test_review_v02_executable_commands.py` with 5 fixture tests. The GitHub Actions workflow now retains a **per-line JSON review artifact**, in addition to the earlier V02 safety and example inventories.

| Static queue | Count | Meaning |
|---|---:|---|
| Chapter files inspected | 80 | Complete numbered curriculum |
| Explicit executable-language fenced blocks | 1,124 | Redis, Bash, PowerShell, shell etc.; not necessarily runnable |
| Fences with no nearby expected-result cue | 745 | Heuristic candidates; expected text may be elsewhere |
| **High-risk pattern matches** | **95** | 90 FLUSH command-line matches, 1 inline-password warning, 2 TLS-bypass warnings, 2 Kubernetes cordon examples |
| Medium-risk pattern matches | 174 | 134 key-deletion, 27 SCAN, 12 KEYS *, 1 stress-load example; not confirmed problems |

**Important distinction:** This new queue matches *individual source lines*, whereas the original 81-item safety review counted **unique block-pattern pairs**. Thus 90 FLUSH line matches here do **not** mean 90 new high-risk defects. The prior [81-item safety adjudication](V02-SAFETY-81-ADJUDICATION-2026-10-30.md) remains authoritative for its scoped categories.

### Non-FLUSH high-risk context review (all five)

| Chapter | Match | Verdict |
|---|---|---|
| 02 | Inline `redis-cli -a` | Intentionally cautionary under "Avoid Password Exposure"; retained with safer alternative |
| 09 | `curl -k` | Explicit "Do not normalize" TLS bypass warning; not recommended execution |
| 43 | `curl -k ...` | Explicit prohibition as an insecure production standard; not recommended execution |
| 45 (concept) | `kubectl cordon <node>` | Added warning that it is a *cluster-scoped scheduling change*, not an arbitrary copyable inspection command |
| 45 (lab) | `kubectl cordon <lab-node>` | **Updated:** dedicated lab node only; Kubernetes-owner approval, context/pod/PDB preflight, read-only status verification, `true` when cordoned and absent/`false` after uncordon, rollback and `NOT EXECUTED` evidence |

Official Kubernetes reference: [cordon and uncordon](https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands).

**Verdict:** No newly confirmed unsafe *recommended* operations within these five non-FLUSH matches after the Chapter 45 clarification. The scanner's pattern set is limited: it does not prove all code and operational workflows are safe.

## 3. Command and expected-output improvements

**Chapter 10 — Foundation Acceptance Lab:** Added documented outcomes for:

- `SET` -> `OK`, `GET` -> exact synthetic value, `TTL` -> positive integer no greater than 900 seconds.
- `HSET` adding two fields to an absent lab key -> **2**; `EXPIRE` -> **1**; `HGETALL` contains both field-value pairs in unspecified order; `TTL` bounded.
- Three `ZADD` calls adding new members -> **1 each**; `EXPIRE` -> **1**; `ZREVRANGE ... WITHSCORES` returns **user2=200, user3=150, user1=100**, with Redis CLI display format distinguished from schematic pairs.

**Chapter 15:** `PING`, `GET`, `TTL`, `PTTL`, `DEL`, conditional `SET NX`, and `UNLINK/EXISTS` results now include expected replies and time-dependent alternatives.

**Chapter 45:** `kubectl get node ... jsonpath='{.spec.unschedulable}'` documented before and after approved `cordon/uncordon`; disruptive operations remain `NOT EXECUTED`.

## 4. Latest CI results

| Offline check | Result |
|---|---:|
| Chapter inventory | 80/80 |
| Validator/lab-contract tests | 26 PASS |
| Original safety inventory tests | 4 PASS |
| New executable/expected-result triage tests | 5 PASS |
| **Total** | **35 PASS** |
| Python AST syntax | 0 findings / 162 blocks |
| JSON syntax | 0 findings / 34 blocks |
| Total fenced blocks | 8,141 |
| V02 baseline output-cue candidates | 1,018 |
| V02 untyped command candidates | 373 |
| Original safety-rule scanner remaining matches | 80; classified negative/cautionary |

The **745** output-cue candidates in the new executable-only tool and the **1,018** candidates in the earlier V02 mixed-language tool are **different filters**, not contradictory measurements. Neither count is a count of confirmed errors.

## 5. Remaining V02 technical acceptance

1. Systematically review the high-volume manual output-cue queue for actual semantic errors, version gates, placeholders, and missing expected outputs. Prioritize *executable instructions* over conceptual or negative examples.
2. Review remaining medium-risk candidates (especially deletion, SCAN and load-testing commands) for namespace ownership, operational bounds, and exact target context.
3. Review the 373 potentially untyped command fences for readability, correct command syntax, and copy/paste safety.
4. Test actual command behavior, ACL/TLS client compatibility, failover, performance, persistence, Redis Streams and backup/restore **later in an approved isolated staging environment**, never as part of the static V02 audit.
5. Require independent DBRE/SRE, product-version and security review before merging or certifying the curriculum.

**Current gate:** V02 automation tests PASS; high-risk-pattern triage completed for this review; full 80-chapter command/expected-output semantic review and runtime certification remain **IN PROGRESS**. PR #42 stays **draft**.
