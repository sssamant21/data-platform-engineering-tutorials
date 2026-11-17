# Part 11 — Targeted Markdown navigation, fragment and fence QA (2026-11-16)

**Scope:** Published Chapters 101–110 in `sql-tutorials/part-11-security-operations/` on `main`. Read the current Master TOC, README, status tracker, all ten chapter files, and Chapter 108/110 in full. This is a limited static review, **not** a CommonMark parser run, rendered GitHub anchor check, SQL parser run, or PostgreSQL 18 runtime execution.

## Observations

- Ten numbered chapter Markdown files inspected (101–110), matching the ten Chapter 101–110 README links.
- Zero local inline fragment-link occurrences found by the targeted pattern; Chapter 108 contains one external PostgreSQL documentation URL with a fragment. External URL and rendered anchor were **not** tested.
- Triple-backtick opening/closing marker counts were even in all ten files: 101=6, 102=6, 103=6, 104=8, 105=6, 106=10, 107=10, 108=4, 109=4, 110=2. This is a delimiter-count heuristic and does **not** establish well-formed Markdown fences.
- No reference-style definitions matched the simple line-start pattern; this does not establish absence of all reference links.
- Chapter 108 had stale successor navigation labeling Chapter 109 as planned, although Chapter 109 is already published. Fixed by replacing that text with a relative Markdown link to the existing Chapter 109 file. Fix commit: [`fb82e3a69e5171f2cb00e653531ff6b5860b328a`](https://github.com/sssamant21/data-platform-engineering-tutorials/commit/fb82e3a69e5171f2cb00e653531ff6b5860b328a). Fetched Chapter 108 from `main` after the fix and confirmed the new link is present.

## Safety and limitations

No SQL, backup, restore, or failover command was executed. No production environment or credential was accessed. The Chapter 110 recovery exercise is synthetic decision logic, not real restore evidence. Prior published counts remain 120/120 chapters, targeted SQL static review 120/120, scoped link-path audit 120/120. Independent editorial review remains 0/120; actual isolated PostgreSQL 18 runtime validation remains 0/120.

## Next

Run Part 12 targeted navigation/fragment/fence checks, then implement parser-aware Markdown link/heading/reference/fence validation across the curriculum, followed by SQL parser and expected-output review and isolated PostgreSQL 18 execution with reproducible evidence.
