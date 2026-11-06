# Redis Enterprise V02 — Focused Command and Expected-Output Review

**Date:** 2026-10-30  
**Draft PR:** [#42](https://github.com/sssamant21/data-platform-engineering-tutorials/pull/42)  
**CI evidence:** [Run #41055085220](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41055085220) — **PASS** (22 example/lab checks + 4 safety-inventory fixture checks).  
**Scope:** Selected, source-backed command semantics and expected outputs; no Redis command was executed.

## Safety-pattern closure

All **81** baseline matches from commit `3126418f22e741d032049fe3fdddb2553c717807` have been classified and preserved in [V02 safety adjudication](V02-SAFETY-81-ADJUDICATION-2026-10-30.md):

- 79 instructional *do-not-run*, restriction, or warning examples (`FLUSH*`, `KEYS *`, TLS-bypass).
- 1 deliberately cautionary inline-password illustration (Chapter 02).
- 1 copyable/recommended insecure example (Chapter 15), corrected to certificate-validated TLS and privately supplied credentials.

**Current scanner:** 80 residual matches, all from classified intentional warning/illustration patterns. This is *not* a blanket security certification: other command families and unsafe code can exist beyond the seven configured safety regexes.

## Focused command semantics review

| Chapter | Command / example | Precondition and expected result | Review verdict |
|---|---|---|---|
| 01 | `PING` via Redis CLI | Authorized reachable endpoint: `PONG`; TLS trust must be valid | Documented; actual network result **not executed** |
| 01 | Read-only API `curl` commands | Management TLS uses trusted CA; interactive credentials rather than command-argument password | **Fixed** previous inline credentials and TLS bypass examples |
| 03 | `HSET key name value price value stock value category value` | Absent disposable key: integer **4** newly added fields, not four arbitrary writes | **Fixed** malformed interactive multiline example; now single Redis command |
| 03 | `HSET` update of existing hash field | Existing hash TTL is retained after updating a field | Consistent with Redis EXPIRE documentation; runtime untested |
| 04 | `SET key first NX EX 300` followed by second NX | First **OK**, second **nil/null**; `GET` preserves first value | Expected outputs **clarified** |
| 04 | `SET missing value XX`, `EXISTS missing` | Conditional SET returns nil/null; EXISTS returns integer **0** | Expected outputs **clarified** |
| 04 | Counter lab `INCR`, `INCR`, `INCRBY 8` after SET 0 | Final GET returns string value **10** | Documentation-consistent arithmetic, no execution |
| 10 | `SET ... EX 900` then `TTL` | String GET matches the stored value; TTL is positive and at most 900 seconds before expiry | Documentation-consistent; inspect environment timing |
| 10 | Counter `INCR` then `INCRBY 9` after SET 0 | Final GET returns **10** | Documentation-consistent; no Redis run |
| 11 | `TTL` on persistent/missing keys | **-1** when present without expiry; **-2** when missing (modern Redis) | Verified against official TTL docs |
| 11 | `EXPIRE NX/XX/GT/LT` | These conditional options require **Redis 7.0+**; persistent key is treated as infinite TTL for GT/LT | **Fixed** version and semantics note |
| 15 | Authenticated CLI and Python Redis connection patterns | Remote lab connection requires TLS and trusted CA; local unauthenticated mode is restricted to loopback | **Fixed** CLI inline-password example and guard in all three Python client initializations; runtime not executed |
| 47 | `SET NX EX`, `GET`, `TTL`, `UNLINK`, `EXISTS` | Synthetic data only; initial SET OK, expected value/positive TTL, exact key removed and EXISTS=0 | Staging-only lab now documented; not run |
| 51 | `XGROUP CREATE`, `XADD`, `XREADGROUP`, `XPENDING`, `XACK` | Pending count transitions 1→0 after XACK of the same ID; no guarantee for application-level consumer correctness | Staging-only lab documented; no stream consumer test run |
| 69 | `SCAN` | Previous snippet was incomplete `SCAN` shown as Bash; now starts with `SCAN 0 MATCH 'tutorial:chapter69:*' COUNT 100`, requires cursor iteration until 0, warns COUNT is a hint | **Fixed** instructional syntax/expected-output gap |

The table represents **15 focused review cases**, not 15 complete chapter certifications. Supporting official command documentation: [HSET](https://redis.io/docs/latest/commands/hset/), [SET](https://redis.io/docs/latest/commands/set/), [TTL](https://redis.io/docs/latest/commands/ttl/), [EXPIRE](https://redis.io/docs/latest/commands/expire/), [SCAN](https://redis.io/docs/latest/commands/scan/), [XREADGROUP](https://redis.io/docs/latest/commands/xreadgroup/), [XACK](https://redis.io/docs/latest/commands/xack/), [UNLINK](https://redis.io/docs/latest/commands/unlink/).

## Latest CI counts

| Metric | Result |
|---|---:|
| Chapters scanned | 80/80 |
| Fenced blocks | 8,138 |
| Python AST parse findings | 0 of 162 |
| JSON syntax findings | 0 of 34 |
| Explicit command blocks | 1,122 |
| Untyped command candidates | 373 |
| No-nearby-output-cue candidates | 1,028 |
| Residual safety scanner hits | 80, already classified from original 81 |
| Validator / lab-contract tests | 22 PASS |
| Safety inventory tests | 4 PASS |

**Interpretation:** V02 static tooling is healthy. The 1,028 expected-output cues and 373 untyped examples are heuristically generated and **not 1,401 confirmed defects**.

## Further actions before V02 content sign-off

1. Continue command/output semantics review in Chapters 01, 03, 04, 10 and 11 with exact version applicability. The table above is a deliberately bounded sample.
2. Chapter 15 still contains some **one-off CLI commands** written without the new TLS/auth connection wrapper. Standardize these to a consistently reusable approved test connection helper before calling the full lab copy/paste-ready.
3. Review untyped command blocks (373 candidates) and whether dangerous examples should be converted to non-executable explanatory text.
4. Manually adjudicate remaining expected-output candidates; prioritize examples that users are instructed to execute.
5. Reserve staging runtime, security, HA, DR, backup and application integration checks for a separate approved phase; do not mark production certified.

**Decision:** 81 baseline safety flags adjudicated; selected command semantics reviewed and documented; V02 overall **IN PROGRESS** and PR remains **DRAFT**.
