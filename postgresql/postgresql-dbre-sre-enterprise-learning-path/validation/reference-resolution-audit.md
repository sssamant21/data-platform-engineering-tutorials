# Reference resolution audit — PostgreSQL enterprise learning path

**Checkpoint:** 2026-11-09  
**Branch:** `main`  
**Scope:** Independent 20-chapter learning path only  
**Documentation baseline:** PostgreSQL 18  
**Validation type:** GitHub source/tree inspection only; no executable or live HTTP tests.

## Evidence and method

Read the track's `README.md`, `MASTER-TOC.md`, `STATUS-TRACKER.md`, `POSTGRESQL-18-BASELINE.md`, `STATIC-AUDIT-2026-11-03.md`, and existing `validation/semantic-review-progress.md` before resuming the unfinished link gate. The GitHub recursive `main` tree was reported as **not truncated**.

Fetched the eight Markdown sources for **Chapters 01–04 and their four labs**. Extracted ordinary inline Markdown links, resolved relative paths against each source directory (including cross-curriculum links), and compared targets against exact blob paths in the GitHub tree. Counts below represent link occurrences, not unique URLs.

| File | Inline link occurrences | Missing relative-file targets |
| --- | ---: | ---: |
| Chapter 01 lesson | 12 | 0 |
| Chapter 01 lab | 1 | 0 |
| Chapter 02 lesson | 12 | 0 |
| Chapter 02 lab | 7 | 0 |
| Chapter 03 lesson | 12 | 0 |
| Chapter 03 lab | 6 | 0 |
| Chapter 04 lesson | 12 | 0 |
| Chapter 04 lab | 7 | 0 |
| **Total** | **69** | **0** |

**Result:** 69 ordinary inline Markdown link occurrences inventoried across eight files; no broken relative-file targets found by exact tree-path resolution. The chapters also contain intentional links to the separate 100-chapter curriculum. These targets were *read-only verified as file paths*, not edited.

## Limits and outstanding checks

- This parser covers ordinary `[label](destination)` links with simple destinations. It does **not** establish exhaustive coverage of reference-style definitions, multiline/escaped destinations, raw HTML links, or autolinks.
- No fragment/anchor links were found by this extraction in the eight files; heading-slug/fragment resolution remains untested.
- The PostgreSQL 18 documentation URLs were **inventoried but not HTTP-fetched or semantically checked**. No claim is made about HTTP status, redirects, page sections, or version correctness.
- Chapters 05–20 and their labs, plus supporting Markdown files, still need this deeper reference pass.
- Historical PostgreSQL 17 runtime assumptions are unchanged. **0/20 labs runtime validated**; **0/20 PostgreSQL 18 runtime validated**. Independent technical approval and production certification remain pending.

## Next safe action

Continue the same source-tree reference check for Chapters 05–08 and their labs, then subsequent batches. Verify reference-style links, fragments and official PostgreSQL 18 destinations separately. Record only confirmed errors and make scoped fixes. Do not advance runtime statuses without isolated execution, version/image/volume identity, sanitized outputs, and cleanup proof.

## Batch 2 — Chapters 05–08 and labs (2026-11-09)

Fetched eight source files from GitHub main and compared ordinary inline Markdown relative destinations against exact blob paths in the non-truncated recursive repository tree. Counts are occurrences, not distinct destinations.

| File | Inline links | Relative links | External URLs | Missing relative targets |
| --- | ---: | ---: | ---: | ---: |
| chapters/05-indexes-query-plans-and-performance.md | 14 | 6 | 8 | 0 |
| labs/chapter-05/README.md | 9 | 2 | 7 | 0 |
| chapters/06-postgresql-on-bare-metal.md | 14 | 6 | 8 | 0 |
| labs/chapter-06/README.md | 8 | 2 | 6 | 0 |
| chapters/07-postgresql-on-aws-rds.md | 24 | 6 | 18 | 0 |
| labs/chapter-07/README.md | 9 | 2 | 7 | 0 |
| chapters/08-postgresql-on-kubernetes.md | 15 | 7 | 8 | 0 |
| labs/chapter-08/README.md | 10 | 4 | 6 | 0 |
| **Batch total** | **103** | **35** | **68** | **0** |

**Finding:** No missing relative-file targets in this batch. Chapter 08's linked cluster-example.yaml exists. Exact file-path resolution does not establish YAML correctness, HTTP availability, anchor resolution, or runtime correctness. Regex extraction is not a complete Markdown parser and does not prove coverage of reference-style, escaped, or multiline links. No external HTTP checks were performed. Documentation baseline PostgreSQL 18; 0/20 runtime-validated labs.

**Next:** Chapters 09–12 and labs, followed by remaining batches, parser-aware references/anchors, and official PostgreSQL 18 HTTP and semantic verification. Preserve historical PostgreSQL 17 evidence and certification gates.


## Batch 3 — Chapters 09–12 and labs (2026-11-09)

Read the current track README, master TOC, status tracker, PostgreSQL 18 baseline policy, historical static audit, and semantic-review progress. Fetched the eight chapter/lab Markdown files on `main` and compared ordinary inline Markdown relative destinations with the exact blob paths in GitHub's non-truncated recursive `main` tree.

| File | Inline links | Relative links | External URLs | Missing relative targets |
| --- | ---: | ---: | ---: | ---: |
| chapters/09-selecting-the-right-enterprise-postgresql-architecture.md | 16 | 8 | 8 | 0 |
| labs/chapter-09/README.md | 10 | 2 | 8 | 0 |
| chapters/10-streaming-replication-and-high-availability.md | 13 | 7 | 6 | 0 |
| labs/chapter-10/README.md | 8 | 3 | 5 | 0 |
| chapters/11-backup-restore-pitr-and-disaster-recovery.md | 13 | 6 | 7 | 0 |
| labs/chapter-11/README.md | 6 | 2 | 4 | 0 |
| chapters/12-monitoring-alerting-and-observability.md | 13 | 6 | 7 | 0 |
| labs/chapter-12/README.md | 7 | 2 | 5 | 0 |
| **Batch total** | **86** | **36** | **50** | **0** |

**Finding:** No missing relative-file destinations were detected. Cumulative ordinary inline-link path inventory now covers Chapters 01–12 and their labs (24 of 40 chapter/lab files). This batch inventories 50 external URL occurrences without testing HTTP status, redirects, or PostgreSQL 18 semantic correctness. The extraction does not exhaust reference-style definitions, escaped/multiline links, HTML links, or fragment anchors; these remain pending. Counts are link occurrences, not distinct URLs.

**Next:** Continue Chapters 13–16 and labs; then 17–20 and labs. Complete parser-aware link/fragment checks and PostgreSQL 18 documentation endpoint and semantic verification before changing runtime claims. No Docker, PostgreSQL, PowerShell, failover, or destructive commands were executed. Historical PostgreSQL 17 evidence and the 0/20 runtime status remain unchanged; independent review and production certification are pending.


## Batch 4 — Chapters 13–16 and labs (2026-11-09)

Re-read the track README, master TOC, status tracker, PostgreSQL 18 baseline policy, prior reference audit and semantic-review progress. Fetched all eight Markdown files for Chapters 13–16 and their labs from `main`. Inventoried ordinary inline Markdown links and independently fetched all twelve distinct relative destination files (including Chapter 15's `inventory.sql` and `drift.sql`) using GitHub's file API. This batch uses destination-file fetches rather than a complete Markdown parser; no HTTP requests to external documentation endpoints or executable lab tests were made.

| File | Inline links | Relative links | External URLs | Missing relative targets |
| --- | ---: | ---: | ---: | ---: |
| chapters/13-vacuum-autovacuum-bloat-and-maintenance.md | 12 | 6 | 6 | 0 |
| labs/chapter-13/README.md | 7 | 2 | 5 | 0 |
| chapters/14-troubleshooting-and-incident-response.md | 14 | 6 | 8 | 0 |
| labs/chapter-14/README.md | 9 | 3 | 6 | 0 |
| chapters/15-fleet-inventory-and-governance.md | 11 | 3 | 8 | 0 |
| labs/chapter-15/README.md | 12 | 3 | 9 | 0 |
| chapters/16-security-roles-secrets-and-compliance.md | 10 | 1 | 9 | 0 |
| labs/chapter-16/README.md | 10 | 0 | 10 | 0 |
| **Batch total** | **85** | **24** | **61** | **0** |

**Finding:** All 24 ordinary inline relative-file link occurrences point to existing files; all 12 distinct destination paths were fetched successfully. Chapter 16's lab README has no relative inline navigation links; this is an editorial navigation opportunity, not a broken target. The Chapter 13 lesson contains an external PostgreSQL 18 storage-parameters fragment anchor, which remains unverified. External URL HTTP status, redirects, fragment anchors, reference-style/HTML links, and technical correctness remain pending. Link occurrences are not distinct URLs.

**Cumulative path-inventory coverage:** Chapters 01–16 plus labs (32/40 files); this is not full reference validation. **Next:** Chapters 17–20 plus labs, then parser-aware internal fragment and external PostgreSQL 18 documentation checks. Runtime-validated labs remain 0/20; no PostgreSQL, Docker, PowerShell, destructive or cloud operations were executed. Historical PostgreSQL 17 evidence, independent-review and production-certification gates are unchanged.


## Batch 5 — Chapters 17–20 and labs (2026-11-09)

Read the track README, MASTER-TOC, STATUS-TRACKER, PostgreSQL 18 baseline policy, historical static audit, semantic-review log, and preceding reference-audit batches. Fetched the eight chapter/lab Markdown files from GitHub main. Counted ordinary inline Markdown links with the same limited extraction method used in prior batches. All five distinct relative destinations were among the eight fetched source files, confirming their existence on main; no external HTTP endpoint or anchor was tested.

| File | Inline links | Relative links | External URLs | Missing relative targets |
| --- | ---: | ---: | ---: | ---: |
| chapters/17-lifecycle-upgrades-and-automation.md | 8 | 1 | 7 | 0 |
| labs/chapter-17/README.md | 4 | 0 | 4 | 0 |
| chapters/18-capacity-planning-performance-and-finops.md | 8 | 1 | 7 | 0 |
| labs/chapter-18/README.md | 5 | 0 | 5 | 0 |
| chapters/19-application-requirement-gathering-and-database-design.md | 8 | 1 | 7 | 0 |
| labs/chapter-19/README.md | 5 | 0 | 5 | 0 |
| chapters/20-enterprise-postgresql-dbre-sre-capstone.md | 10 | 1 | 9 | 0 |
| labs/chapter-20/README.md | 6 | 1 | 5 | 0 |
| **Batch total** | **54** | **5** | **49** | **0** |

**Finding:** No broken ordinary inline relative-file references were found in this batch. Chapters 17–19 labs contain no relative navigation links; optional editorial improvement, not a missing-file defect. These counts represent occurrences, not distinct destinations. No lesson or lab was modified.

**Cumulative ordinary inline-link path inventory:** 397 occurrences across all 40 chapter/lab Markdown files (69 + 103 + 86 + 85 + 54); this does **not** establish exhaustive link validity. Next: inspect reference-style definitions, escaped/multiline/HTML links, internal and external fragment anchors, supporting Markdown files, and HTTP/semantic validity of official PostgreSQL 18 documentation links. Retain the 17-only historical evidence. Runtime validation remains 0/20 for both legacy and PostgreSQL 18 targets; independent review and production certification are pending. No Docker, PostgreSQL, PowerShell, cloud or destructive commands were executed.
