# SQL static expected-output review — Chapters 055–060 (2026-11-15)

**Scope:** `sql-tutorials/` only, GitHub `main`. Reviewed current Master TOC, README, status tracker, six Part 06 chapters and six corresponding PostgreSQL-oriented lab SQL scripts. **Source-based inspection, not execution, parser certification or independent editorial signoff.**

| Chapter | Targeted review and expected results | Finding |
|---|---|---|
| 055 — Time buckets | Six events totaling 210.00; four distinct UTC dates (Jan 31, Feb 1, Feb 28, Mar 1); UTC months Jan 1/10, Feb 3/90, Mar 2/110; New York boundary conversions | **Corrected** prose claiming five daily groups when fixture yields four; chapter commit `3d442b807e622341112593d5b8e310b78b740f4d` |
| 056 — Text normalization | Six events totaling 120.00; NORTH 2/50, SOUTH 2/55, UNKNOWN 1/10, WEST 1/5; CAPTURED 4/100, PENDING 1/15, UNKNOWN 1/5 | No contradiction identified in targeted reasoning; normalization and NULL collisions documented |
| 057 — Ratios | Claims 125/150=83.33%; events 39/50=78%; overall 164/200=82%; unweighted nonempty batch mean 83.75% | No targeted arithmetic contradiction; zero denominator returns NULL |
| 058 — Grouping sets | Six events / 155.00; 5 detail groups, 3 region subtotals, 1 grand total = 9 ROLLUP rows; CUBE adds 2 channel subtotals = 11 | Real NULL region versus generated NULL subtotal distinguished with GROUPING flags |
| 059 — Pivot/unpivot | Eight events / 180.00; East web/store 30/30, North 15/10, West 40/55; 3 wide rows, 6 unpivoted rows | No targeted arithmetic contradiction; fixed allowlist for channels |
| 060 — Monthly KPI capstone | Eight batches: accepted 380, rejected 60, processed 440, overall 86.36%; Jan 130/20/150, Feb 80/20/100, Mar 170/20/190 | Monthly source split Jan 100/50, Feb 80/20, Mar 100/90; zero-volume batch rate NULL |

## Safety and limitations

All six lab scripts use synthetic temporary tables and INSERT operations, transaction-local statement/lock/idle timeouts, version/database checks, and ROLLBACK. They are **not read-only**. Version and database-name guards cannot prove the endpoint is isolated; verify disposable PostgreSQL 18 instance identity independently before running. Chapter 055 prints month grouping, not the prose's daily example; the four-day expectation was checked against the fixture by source reasoning only.

No SQL was executed. No PostgreSQL 18 instance identity, psql output, exit status or rollback evidence was captured. No comprehensive parser-based SQL syntax verification, Markdown anchor validation, external-reference availability testing or independent editorial review was performed. Expected results are static hypotheses pending reproducible isolated runtime acceptance.

**Progress after this batch:** published 120/120; previously reported targeted structural QA 120/120; targeted SQL expected-output static review 60/120 (50%); independently editorially reviewed 0/120; actually isolated PostgreSQL 18 runtime-validated 0/120.

**Next:** Chapters 061–066 targeted SQL semantic/expected-output review; then comprehensive Markdown-aware links/anchors, SQL parser/semantic checks, and PostgreSQL 18 isolated runtime acceptance with retained evidence.
