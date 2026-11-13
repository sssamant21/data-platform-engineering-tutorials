# Markdown local-link smoke test — Chapters 007–012

Date: 2026-11-13. Branch: `main`. Pinned Git tree SHA: `245d1b2c20593e6ccd45d063227bd12296ef9b6a`.

## Method

Fetched each of the six numbered Markdown chapters from GitHub main and extracted inline Markdown links matching `[label](target)`. For local links, resolved `.` and `..` relative to the containing chapter and compared the normalized path against the pinned recursive Git tree. External HTTP(S) references were counted but **not** checked for availability. This is a narrow path-existence smoke test, not comprehensive Markdown parsing, anchor verification, or SQL execution.

| Chapter | Local links checked | Missing local targets |
|---|---:|---:|
| 007 | 7 | 0 |
| 008 | 7 | 0 |
| 009 | 7 | 0 |
| 010 | 7 | 0 |
| 011 | 7 | 0 |
| 012 | 10 | 0 |
| **Total** | **45** | **0** |

Additionally observed 26 external HTTP(S) link occurrences; no inline local fragment anchors were present in this matched set. Duplicate link occurrences count separately. No missing local paths were found in the tested set.

## Limitations and next work

The regex does not validate reference-style Markdown links, HTML links, heading-anchor slugs, external URL reachability, code-block exclusion, or every chapter. Chapters 001–006 were covered by an earlier separate smoke test. Continue 013–018 and build a comprehensive Markdown-aware repository-wide validator. Independent editorial review and actual isolated PostgreSQL 18 runtime acceptance remain pending (0/120). No PostgreSQL was executed in this pass.
