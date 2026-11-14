# Targeted Markdown structural audit — Chapters 013–018 (2026-11-14)

## Scope and method

Read the current `main` versions of `MASTER-TOC.md`, `README.md`, `STATUS-TRACKER.md`, Chapters 013–018 in `part-02-filtering/`, and the corresponding six SQL lab files in `labs/`. Counts below are textual checks of ATX headings, fence-delimiter candidates, and inline Markdown links, **not** a full CommonMark parser or SQL execution.

| Chapter | Physical lines | ATX headings | Fence delimiter candidates | Inline local links | Inline external HTTP(S) links |
|---|---:|---:|---:|---:|---:|
| 013 | 186 | 14 | 14 | 9 | 4 |
| 014 | 171 | 14 | 12 | 9 | 4 |
| 015 | 149 | 14 | 12 | 10 | 4 |
| 016 | 160 | 12 | 10 | 10 | 4 |
| 017 | 163 | 12 | 8 | 10 | 4 |
| 018 | 156 | 12 | 10 | 10 | 5 |
| **Total** | **985** | **78** | **66** | **58** | **25** |

Each chapter has an even number of candidate fence delimiter lines. Zero inline fragment-only links were observed. This does not establish correctly nested fences, resolved heading anchors, or valid external URLs. Previously published local-file path smoke checks cover 120/120 chapters; those checks are separate from this structural audit.

## Lab safety text inspection

Read `labs/013-null-three-valued-logic.sql`, `014-in-between-range-predicates.sql`, `015-like-wildcards-ilike.sql`, `016-distinct-duplicate-handling.sql`, `017-order-by-deterministic-sorting.sql`, and `018-limit-offset-fetch-top.sql`. Each file contains textual `BEGIN READ ONLY` (or equivalent), `ROLLBACK;`, and a PostgreSQL/version reference. This is **not** a safety certification: guard effectiveness, SQL syntax, expected outputs, permissions, and isolation were not tested.

## Findings and follow-up

- Chapter 013 refers to Chapter 014 as **planned**, Chapter 014 to 015 as **planned**, Chapter 015 to 016 as **planned**, Chapter 017 to 018 as **planned**, and Chapter 018 to 019 as **planned**; all successor chapters are already published. Update these navigation labels to direct chapter links during the editorial cleanup. Chapter 016 uses a Master TOC link without the stale planned label.
- No runtime SQL execution was performed. Independent editorial review remains **0/120**, actual isolated PostgreSQL 18 runtime validation remains **0/120**.
- Next: Chapters 019–024 structural audit, repair stale navigation labels, implement Markdown-aware anchor validation and systematic SQL/expected-output/safety review. Runtime acceptance requires isolated PostgreSQL 18 execution with reproducible evidence.

**Status:** targeted textual structural inspection only; **18/120** cumulative structural coverage after this batch; **120/120** previously published; **120/120** previously completed limited local-path smoke coverage.
