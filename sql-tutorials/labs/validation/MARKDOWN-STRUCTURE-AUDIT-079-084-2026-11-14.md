# Targeted Markdown structural audit — Chapters 079–084

Date: 2026-11-14 (America/New_York). Scope: existing published chapter Markdown and corresponding lab SQL on GitHub `main`; **no SQL execution**.

## Method

Fetched the six chapter files and six matching SQL labs from `main` through the GitHub connector. Counted physical lines, ATX headings, line-start backtick fence candidates, Markdown inline local/external link occurrences, and scanned labs for textual `BEGIN`, `ROLLBACK`, `READ ONLY`, `statement_timeout`, and PostgreSQL/version references. These are heuristic textual checks, **not** a Markdown parser, anchor resolver, SQL parser, external-link checker, or runtime/safety certification.

| Chapter | Markdown lines | ATX headings | Backtick fence candidates | Local inline links | External inline links | Lab SQL lines |
|---|---:|---:|---:|---:|---:|---:|
| 079 | 161 | 9 | 6 | 9 | 4 | 102 |
| 080 | 142 | 9 | 6 | 11 | 4 | 109 |
| 081 | 156 | 11 | 8 | 8 | 4 | 81 |
| 082 | 126 | 12 | 10 | 8 | 4 | 51 |
| 083 | 132 | 12 | 10 | 8 | 4 | 64 |
| 084 | 132 | 11 | 8 | 8 | 4 | 86 |
| **Total** | **849** | **64** | **48** | **52** | **24** | **493** |

All six chapter files have even candidate backtick-fence counts. All six SQL labs contain the five listed textual safety/version patterns. A narrow scan did not find `Next chapter ... planned/forthcoming/not yet published` wording. This scan did **not** prove local targets or heading anchors resolve; earlier [local-link smoke evidence](MARKDOWN-LINK-SMOKE-079-084-2026-11-14.md) reports a separate limited path check.

## Outstanding acceptance

- Full Markdown-aware relative links, heading anchors and external URL checks.
- SQL syntax and semantics, synthetic fixture correctness, expected output and SQL lab guardrail review.
- Actual isolated PostgreSQL 18 execution, with database identity, version, commands, output, cleanup and reproducible evidence.
- Independent editorial review.

**State:** published chapters 120/120; limited targeted structural audit 84/120; independent editorial review 0/120; actually PostgreSQL 18 runtime validated 0/120. Next: Chapters 085–090 targeted structural audit. Do not treat the above textual safeguards as proof of safe execution.
