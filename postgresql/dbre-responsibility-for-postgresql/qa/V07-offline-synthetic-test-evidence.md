# V07 — Offline Synthetic Gate Test Evidence

**Date:** 2026-11-01 UTC  
**State:** Synthetic checks only. Real DB, provider, backup, RPO/RTO, SEC and change approvals NOT TESTED.

The gate's *pure assessment function* was executed against synthetic evidence objects and confirmed 14 scenario outcomes. The exact assessment function source is embedded in [V07-evidence-gate.mjs](V07-evidence-gate.mjs) and can be independently tested with Node.js 18+. No database, cloud, network or filesystem operations were required for these in-memory function tests.

| Test case | Required outcome | Result |
|---|---|---|
| Complete internally consistent synthetic HA package | READY_FOR_INDEPENDENT_REVIEW (never certified) | PASS |
| Missing recovery proof | BLOCKED | PASS |
| Missing required PITR result | BLOCKED | PASS |
| Tabletop in place of runtime test | BLOCKED | PASS |
| RPO exceeds approved threshold | BLOCKED | PASS |
| RTO exceeds approved threshold | BLOCKED | PASS |
| Old-primary fence unproven | BLOCKED | PASS |
| Source and destination identity same | BLOCKED | PASS |
| Reviewer equals executor | BLOCKED | PASS |
| DATA approval missing | BLOCKED | PASS |
| Duplicate result ID | BLOCKED | PASS |
| UTC timestamp not canonical | BLOCKED | PASS |
| Result proof URL missing | BLOCKED | PASS |
| Separately declared PITR-only scope with required evidence | READY_FOR_INDEPENDENT_REVIEW (never HA certified) | PASS |
| Blank actual-use template | BLOCKED with missing evidence errors | PASS |

**Limitation:** This proves only that the assessment function responds to a constrained set of artificial inputs. It cannot demonstrate authenticity of approval claims, external URLs, or real cluster behavior. The published Node CLI, if used, must be independently executed and reviewed in the DBRE team's environment before depending on it for a governance process.

**Execution output:** Synthetic cases: 14 passed of 14 expected; default template: BLOCKED.

**Real staging tests:** 0 executed. **Production-certified environments:** 0.
