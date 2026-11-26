# Targeted SQL expected-output review — Chapters 079–084

Date: 2026-11-26. Manual source review only; no PostgreSQL execution or independent editorial acceptance.

| Chapter | Chapter blob | Lab blob | Source-derived findings |
|---|---|---|---|
| 079 | 347d9194bd816ad50c415ebe7114ad78cddfd2f1 | 286a21befa998754aaba1a90610744a9e02afcde | 10 events, 6 users; cohort sizes 3/2/1; observed retention 100/66.67/33.33, 100/50, 100 percent; user 1 gaps 7 days. |
| 080 | 12754cf9636e9698c7134217cb3b46650d922486 | e5c76de6dbd3716a0d4526ad3236aa066d13d536 | 7 events, 5 purchases, 4 customers, 3 active; spend 50+50+15+0=115; dense ranks 1/1/2/3. |
| 081 | 9f1ddc442e91a7dca7fb19ba789858456fd8e2ce | 0825294f22fc538ecb71deb21557afb719fdd1af | Five rows, 2 valid/2 invalid/1 missing; trimmed lengths 17/15/NULL/13/17; case-insensitive match differs for lowercase code. |
| 082 | babd8a8d5b6da27b70fdedef7e6c9c56e4b64cb1 | 7a6766538c937ddc8d54692ba374ad1f9391e0d2 | UTC instants map to New York 01:30, 03:30, 20:00 on March 8; two in UTC day, three in New York day; elapsed hour. Daily assertion correction 20e1e3f4bba09877540ed1657a2686f697730293. |
| 083 | dd73eefcfb9ad8217bee09ada7b8965eebc6246b | 82c3ee0fc0e087c8bdcaea81bf8628c0e69ac80f | 4 rows/3 measured; raw 30.100, rounded aggregate 30.10, rounded lines 30.11; integer quotient 2, decimal 2.5, undefined ratio NULL; negative tie -1.24. |
| 084 | adafcf1d48cd0b5ad689f1ed37b29dca454460f7 | 1cda26ba482225793a445536a2b5e946b3f264c9 | 4 events/3 payloads, 2 API/1 file, 2 tags, one explicit JSON null, one absent key, one SQL NULL payload. |

All six lab acceptance queries compare expected and actual multisets bidirectionally and use fail-closed assertions. These are synthetic read-only labs; database-name/version guards do not prove isolation. Chapter 082's separate two-event teaching example is not the three-event lab fixture. Chapter 084 asserts summary and tag rows, not every displayed extraction column. These findings are scoped, not exhaustive syntax or semantic certification.

Source navigation: [README](../../README.md), [Master TOC](../../MASTER-TOC.md). Next: 085–090, comprehensive Markdown and SQL QA, regression execution, and isolated PostgreSQL 18 acceptance with retained evidence.
