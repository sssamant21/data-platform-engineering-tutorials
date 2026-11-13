# Targeted Markdown local-link smoke check — Chapters 037–042

Date: 2026-11-13. Branch: `main`. Inspected non-truncated Git tree: `15177341979733ec4050597e66de758a5a5fcf73` (269 paths under `sql-tutorials/`).

## Method

Fetched each of the six chapter Markdown files from `main`; extracted inline Markdown link destinations using a simple regular expression, excluded HTTP(S), mailto and fragment-only links, URL-decoded and normalized relative paths against the chapter directory, and compared resulting paths against the Git tree. This checks **path existence only**; it does not validate reference-style links, heading fragments, Markdown parser behavior, external URL availability, SQL semantics, or execution.

| Chapter | Local inline link occurrences | Missing tracked targets | External HTTP(S) occurrences |
|---|---:|---:|---:|
| 037 | 6 | 0 | 6 |
| 038 | 8 | 0 | 7 |
| 039 | 7 | 0 | 4 |
| 040 | 9 | 0 | 5 |
| 041 | 8 | 0 | 3 |
| 042 | 7 | 0 | 3 |
| **Total** | **45** | **0** | **28** |

## Acceptance and limitations

Targeted inline local-path existence check: **PASS** (45/45 paths present). External URLs were counted but **not tested**. The six chapter file blob SHAs are, respectively: `350992dd22656c192e17c84ea4607aebcf58546c`, `676bb7676c66ceae1a5931679e156ab43f5946df`, `0d2ebddb89cd642bebe83799af9e8262dd2bff11`, `2cf9bebae7f53024380235efed107e3dd5524aaf`, `7973e2f54b0246ad210f17712ec422e151149471`, `3642632fb37ce1ceac9c20b468c1297070ec82a3`.

Cumulative targeted local-path smoke coverage: **42/120 chapters**. Independently editorially reviewed: **0/120**. Actually executed and validated on isolated PostgreSQL 18: **0/120**. No production environment or credentials were used.

Next: Chapters 043–048 targeted local-path checks, then comprehensive reference/anchor parsing, SQL syntax/expected-output review, lab safety, and isolated PostgreSQL 18 runtime evidence.
