# Redis Enterprise V02 — Executable Expected Outputs and Release-Sensitive Commands (Pass 3)

**Date:** October 30, 2026  
**Branch:** `qa/redis-v02-code-examples-20261030` · [Draft PR #42](https://github.com/sssamant21/data-platform-engineering-tutorials/pull/42)  
**Confirmed GitHub Actions run:** [#41120299035](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41120299035) — **SUCCESS**.  
**Review scope:** Repository-wide offline *ranking* of the original 966 missing-nearby-expected-output-cue candidates, then targeted manual documentation checks and corrections for high-priority runnable and version-sensitive examples. **No lab code was executed and no Redis database was contacted.**

## Milestone outcome

Original cue queue: **966**. After this review, the same heuristic yields **946** candidates (**20 fewer**). A missing cue means the script did not detect the keyword within its limited proximity window; it does **not** demonstrate incorrect Redis syntax or a wrong result. Likewise, a nearby cue is not proof that an expected output is correct.

A new offline triage tool `tools/review_v02_expected_output_priority.py` sorts all candidates by explicit executable fence, version-sensitive command pattern, side effects, administrative workflow and cautionary context. It writes a **full JSON queue** into the CI artifact `redis-v02-output-priority.json`. This is the repeatable worklist for the remaining review, not a certificate.

| Remaining classification | Blocks |
|---|---:|
| Enterprise/admin/workflow command patterns | 50 |
| Write side-effect patterns | 177 |
| Read-only command patterns | 251 |
| Generic commands, warnings or text | 468 |
| **Total expected-cue candidates** | **946** |

**680** remaining entries are in executable-language Markdown fences; the rest are text/unlabeled command-like candidates. **0 current release-sensitive candidates** means zero matches for the scanner's **limited enumerated set** *among blocks with no nearby expected cue*, after corrections and filtering text-only command vocabulary. It emphatically does **not** prove version compatibility or correctness across all commands.

## Corrected findings

### Chapter 11 — KEEPTTL and conditional EXPIRE (confirmed setup defect)

The preceding lab intentionally replaced a key using normal `SET`, removing its TTL (`TTL=-1`), but the next `KEEPTTL` exercise attempted to demonstrate retaining a finite TTL without restoring one. Fixed by requiring `EXPIRE tutorial:chapter11:item 300` before `SET ... KEEPTTL` and `TTL` observations. Expected: `EXPIRE=1` for the owned existing key, `SET=OK`, TTL remains positive and decreasing, and `GET=value3`. Documented version **Redis 6.0+**, prerequisite failure and the persistent-key case. Clarified conditional `EXPIRE NX/XX` expected integer **1** versus **0** and version **7.0+**, with explicit conceptual/not-on-production boundaries.

Official references: [SET/KEEPTTL](https://redis.io/docs/latest/commands/set/) and [EXPIRE conditional options](https://redis.io/docs/latest/commands/expire/).

### Chapter 14 — Stream group and acknowledgment results

Explained the difference between `XGROUP CREATE ... $` (new messages only) and `0` (existing stream entries eligible for group delivery), with `OK` first creation, `BUSYGROUP` on duplicate creation, pending delivery through `XREADGROUP ... >`, and `XACK=1` on actual pending IDs (`0` otherwise). A distinct disposable `writers-lab` group avoids colliding with the conceptual `writers` example. The documented reply depends on the group offset, previous deliveries and generated stream IDs. Commands require Redis 5.0+ and appropriate ACLs; **no live group was created**.

Official references: [XGROUP CREATE](https://redis.io/docs/latest/commands/xgroup-create/) and [XREADGROUP](https://redis.io/docs/latest/commands/xreadgroup/).

### Chapter 33 — XAUTOCLAIM (release-sensitive reply shape)

Explicit Redis **6.2+** prerequisite, `0-0` scan completion marker, bounded COUNT semantics, possible empty claim result, requirement for real pending entries/idle time and the fact that claiming **does not acknowledge** a message. Redis **7.0+** includes a third reply component listing deleted IDs cleaned out of the pending list; this is not part of the original Redis 6.2 reply. No production reclaim threshold change, group reset or acknowledgment was performed.

Official reference: [XAUTOCLAIM](https://redis.io/docs/latest/commands/xautoclaim/).

### Chapter 55 — RedisJSON command setup and expected results

Replaced **14** unqualified `redis-cli` examples with interactive Redis-command blocks requiring a separately established **CA-verified TLS and ACL-authenticated** session in a disposable database with RedisJSON v2 JSONPath support. Added explicit expected `JSON.SET=OK`, whole-object `JSON.GET` JSON, JSONPath arrays (e.g., `["Ava"]`), numeric increment from 1 to 2, append/array lengths, and path deletion `1` versus `0`. Documented RESP/client reply shape and repeat-run side effects. Converted `redis-cli --scan` to scoped `SCAN 0 MATCH ... COUNT 100` with cursor iteration. Two conceptual shell-like snippets are labeled as `text`, not runnable host-shell commands.

Official references: [JSON.GET](https://redis.io/docs/latest/commands/json.get/), [JSON.NUMINCRBY](https://redis.io/docs/latest/commands/json.numincrby/), [JSON.SET](https://redis.io/docs/latest/commands/json.set/) and [JSONPath syntax](https://redis.io/docs/latest/develop/data-types/json/path/).

### Chapter 56 and 59 — RedisJSON command boundaries

- **Chapter 56:** Converted a host-shell `redis-cli JSON.SET` example into a complete single interactive Redis command with a scoped key, expected `OK`, optional JSONPath price read (`[89.99]`), and prerequisite checks for module/Search capability and TLS/ACL. JSON document success alone **does not certify** the Search index.
- **Chapter 59:** Converted core SET/GET and JSON.SET/JSON.GET examples to interactive Redis fences, scoped/expiring tutorial key, and expected `OK`, `ok` and JSONPath array values (`["ok"]`) with module version/ACL/TLS gates.

## Automated checks and limitations

Added `review_v02_expected_output_priority.py`, **5 fixture tests**, and CI JSON artifact export. Added **8 chapter-level regression contracts** covering KEEPTTL, EXPIRE NX/XX, XGROUP/XREADGROUP/XACK, XAUTOCLAIM, RedisJSON JSONPath result types, interactive command syntax, and security prerequisites. Existing V02 syntax/safety inventories are still run.

**Latest [CI run #41120299035](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41120299035):**
- **76/76** offline Python unit/contract/triage tests passed: 50 validator/lab-contract + 4 safety + 5 executable command triage + 4 interactive Redis syntax + 8 untyped fence + 5 expected-output priority.
- **80/80** numbered chapters; **8,143** total fenced blocks; **1,129** explicit executable-language blocks; **370** untyped command-like candidates.
- Python AST findings **0/162**, JSON parsing findings **0/34**; **580** Redis-language fences checked for the two narrow syntax patterns, **0 findings**.
- **946** remaining expected-output heuristic candidates, **680** in executable-language blocks; no Redis command was executed.

The output-cue and risk counts are not additive and are not certification results. The different scanners use different patterns and populations. Their results identify further review, not unsafe or correct-by-default instructions.

## Next milestone

Review the remaining **50 enterprise/administration/workflow** missing-cue cases first (especially recurring `rladmin` examples in Chapters 01, 05, 06, 09), then the **177 side-effecting** command candidates and **251 read-only** command candidates. Prioritize **actual lab prerequisites, expected outputs, ACL/TLS scope and product release** over changing prose simply to reduce heuristic flags. Use owner-approved, isolated Redis Software/Enterprise staging only in a distinct runtime-certification phase after access/change approvals.

**V02 verdict:** Offline static regression PASS; full manual semantic review IN PROGRESS; independent DBRE/SRE/security review PENDING; runtime validation NOT EXECUTED; production certification NOT CERTIFIED. Keep PR #42 **draft**.
