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


## Supporting-document reference checkpoint — 2026-11-09

**Method:** Re-read the current `README.md`, `MASTER-TOC.md`, `STATUS-TRACKER.md`, `POSTGRESQL-18-BASELINE.md`, historical static audit and semantic-review log. Inventoried ordinary single-line Markdown inline links in the four active navigation/policy documents; did not repeat the 40 chapter/lab link inventory. The counts below are syntactic link occurrences, not a full Markdown parse or complete target verification.

| Source | Ordinary inline links inventoried | Relative destinations inventoried |
| --- | ---: | ---: |
| README.md | 49 | 45 |
| MASTER-TOC.md | 29 | 29 |
| STATUS-TRACKER.md | 4 | 4 |
| POSTGRESQL-18-BASELINE.md | 8 | 1 |
| **Total** | **90** | **79** |

**Direct GitHub source checks:** The cross-curriculum `postgresql/README.md` and `postgresql/PROGRESS.md` files exist on `main`; both were read-only checked and left untouched. The track's baseline policy and semantic-review progress files also exist and were fetched. These checks verify those **four exact file paths only**; they do not establish that every relative link or anchor in the inventory resolves.

**Finding:** The status tracker still describes Chapter 01's ordinary inline links as needing inventory, although the earlier Batch 1 audit already inventoried Chapter 01 and its lab. This is stale tracking language, not a broken link. Defer tracker wording reconciliation until the full reference gate is finished to avoid suggesting that anchors and external HTTP links were verified.

**Remaining:** Parser-aware reference definitions, escaped/multiline/HTML/autolinks, relative and external fragments, full relative-target resolution for supporting documents, and HTTP/semantic checks of PostgreSQL 18 documentation URLs. The audit report's literal `[label](destination)` examples must not be counted as actual links. No server, Docker, cloud or destructive commands were executed. Runtime evidence remains 0/20; independent approval and certification are pending.


## Targeted non-inline reference syntax checkpoint — 2026-11-09

**Scope (six source files):** track `README.md`, `MASTER-TOC.md`, `STATUS-TRACKER.md`, `POSTGRESQL-18-BASELINE.md`, Chapter 01 lesson, and Chapter 01 lab README. This is a **new syntax-category check**, not a repetition of the 397-link ordinary-inline inventory.

Fetched each current `main` source and excluded triple-backtick fenced code before scanning for Markdown reference-definition lines (`[id]: target`), ordinary inline-link destinations containing `#`, raw HTML `<a href=...>` elements, and angle-bracket HTTP(S) autolinks. Results:

| Syntax category | Matches in six files |
| --- | ---: |
| Reference-style definitions | 0 |
| Inline destinations containing fragments | 0 |
| Raw HTML anchor elements | 0 |
| Angle-bracket HTTP(S) autolinks | 0 |

**Interpretation:** No instances of these four syntactic categories were found by these targeted scans in the six named files; therefore no missing fragment or reference target was confirmed in this subset. This is **not** a complete CommonMark/GFM parse. Multiline definitions, escaped constructs, nested parentheses, indentation edge cases, and other files remain unchecked. The earlier 90-link supporting-document inventory is still only an inventory, not full target validation.

**Actionable tracker discrepancy retained:** `STATUS-TRACKER.md` still says Chapter 01's inline links need inventory, although Batch 1 completed that inventory. Reconcile wording alongside the final reference-gate status update; do not misrepresent external HTTP or anchor verification as complete.

**Next:** Extend syntax-aware checks to Chapters 02–20 and labs plus remaining supporting files, resolve actual fragment targets, and HTTP-check official PostgreSQL 18 documentation endpoints. Preserve 17 historical evidence. No Docker, psql, shell, PowerShell, cloud or destructive command was executed; 0/20 runtime-validated labs, independent review pending, production certification not established.


## Non-inline syntax checkpoint — Chapters 02–04 and labs (2026-11-09)

**Scope:** Six files: Chapter 02, 03 and 04 lessons and their respective lab READMEs. Re-read the track README, TOC, status tracker, PostgreSQL 18 baseline, historical static audit and semantic-review evidence before resuming this unfinished syntax-category gate. This pass does not repeat the ordinary inline-link inventory.

Fetched each of the six files from GitHub `main` and scanned for line-based reference-style link definitions, inline Markdown links containing fragment identifiers, raw HTML named/id anchors, and angle-bracket HTTP(S) autolinks. This is a targeted source-level scan, **not** a full Markdown parser, anchor-resolution proof or HTTP request.

| Category | Chapter 02 + lab | Chapter 03 + lab | Chapter 04 + lab |
| --- | ---: | ---: | ---: |
| Reference-style definition matches | 0 | 0 | 0 |
| Inline link destinations with fragments | 0 | 0 | 0 |
| Raw HTML id/name anchor matches | 0 | 0 | 0 |
| Angle-bracket HTTP(S) autolinks | 0 | 0 | 1 |

**New finding:** Chapter 04's lesson contains one valid angle-bracket autolink, `<https://www.postgresql.org/docs/18/wal-intro.html>`, in the WAL-before-data explanation. The previous ordinary-inline-only inventories do not cover this occurrence. Its PostgreSQL 18 URL is version-pinned, but endpoint availability and semantic correspondence were **not** tested. No change to the lesson is warranted from this finding alone.

**Limitations:** The scan is regex-based; multiline/escaped reference definitions, nested Markdown syntax, fragments in other link forms and code-fence-aware parsing are not exhaustively resolved. The absence of matches is not a complete CommonMark compliance finding. No Docker, PostgreSQL, PowerShell, shell, cloud or destructive operation was executed. Runtime acceptance remains 0/20, and independent review and certification remain pending.

**Next:** Continue the same non-inline syntax scan for Chapters 05–08 and labs, then remaining chapters and supporting documents; resolve actual fragments and check external PostgreSQL 18 URLs separately. Reconcile the stale Chapter 01 inventory wording in the status tracker only with an accurate gate-status update.


## Non-inline syntax batch — Chapters 05–08 and labs (2026-11-09)

Fetched all eight Markdown sources from `main` after reviewing the track README, master TOC, status tracker, PostgreSQL 18 policy, historical static audit, semantic-review progress and prior reference-resolution results. A targeted source scan (excluding triple-backtick fenced examples) checked reference-style link definitions and uses, inline fragment-only links, raw HTML `<a>` tags carrying `href`/`id`/`name`, and angle-bracket HTTP(S) autolinks.

| Source files | Reference definitions | Reference uses | Fragment-only links | HTML anchor/link tags | HTTP(S) autolinks |
| --- | ---: | ---: | ---: | ---: | ---: |
| Chapter 05 lesson and lab | 0 | 0 | 0 | 0 | 0 |
| Chapter 06 lesson and lab | 0 | 0 | 0 | 0 | 0 |
| Chapter 07 lesson and lab | 0 | 0 | 0 | 0 | 0 |
| Chapter 08 lesson and lab | 0 | 0 | 0 | 0 | 0 |

**Disposition:** No new non-inline reference occurrence or confirmed defect in these eight sources. This targeted regex-based check is not a full Markdown parser: escaped/multiline constructs, inline links with fragments, generated heading anchors, HTML outside the searched `<a>` form, and external HTTP/redirect/fragment validity remain unverified. Prior ordinary-inline inventories for these files are not repeated. The historical PostgreSQL 17 semantic reviews are unchanged; PostgreSQL 18 technical/runtime migration and actual execution remain pending (0/20 labs). No Docker, PostgreSQL, cloud or destructive operation was executed.

**Next:** Continue non-inline syntax checks for Chapters 09–12 and labs, then remaining chapters and supporting Markdown. Follow with parser-aware fragment resolution and external PostgreSQL 18 endpoint/semantic checks. Do not advance runtime or certification statuses without genuine evidence.


## Non-inline syntax batch — Chapters 09–12 and labs (2026-11-09)

Reviewed the current track README, master TOC, status tracker, PostgreSQL 18 policy, prior static audit, semantic-review log and preceding reference audit. Fetched the eight chapter/lab Markdown sources from GitHub `main`. Excluding fenced examples, performed targeted source scans for reference-style definitions/uses, inline destinations containing fragments, HTML anchor/link tags and angle-bracket HTTP(S) autolinks. This is a syntax-category scan, **not** a full CommonMark parse or lab execution.

| Source pair | Reference definitions | Reference uses | Inline fragment URLs | HTML anchor/link tags | HTTP(S) autolinks |
| --- | ---: | ---: | ---: | ---: | ---: |
| Chapter 09 + lab | 0 | 0 | 0 | 0 | 0 |
| Chapter 10 + lab | 0 | 0 | 0 | 0 | 0 |
| Chapter 11 + lab | 0 | 0 | 2 | 0 | 0 |
| Chapter 12 + lab | 0 | 0 | 0 | 0 | 0 |

**New evidence:** The two Chapter 11 fragment occurrences both target `https://www.postgresql.org/docs/18/runtime-config-wal.html#RUNTIME-CONFIG-WAL-RECOVERY-TARGET`. The official PostgreSQL 18 page was fetched and shows the **19.5.6 Recovery Target** section. This confirms the destination page and relevant section exist; the fragment identifier itself was not independently checked against raw HTML id attributes, and no claim of complete external URL/anchor validation is made. Source: https://www.postgresql.org/docs/18/runtime-config-wal.html (checked 2026-11-09).

**Disposition:** No confirmed broken references or lesson edits in this batch. Counts exclude fenced code; escaped/multiline constructs, exact anchor-id resolution, redirects, and other external destinations remain pending. Historical PostgreSQL 17 semantic reviews and lab assumptions remain intact; PostgreSQL 18 is the documentation baseline, not an executed runtime claim. **0/20 runtime-validated labs.** No Docker, psql, PowerShell, shell, cloud or destructive operation was executed. Independent review and production certification remain pending.

**Next:** Continue non-inline syntax categories for Chapters 13–16 and labs, then 17–20. Complete actual fragment-id and external HTTP/semantic checks before declaring the reference gate complete; correct the status tracker's stale Chapter 01 inventory wording without overstating verification.


## Non-inline syntax batch — Chapters 13–16 and labs (2026-11-09)

Re-read the track README, master TOC, status tracker, PostgreSQL 18 baseline policy, prior static audit, semantic-review progress and this report. Fetched eight lesson/lab Markdown sources from GitHub `main`. Excluded triple-backtick fenced lines for a targeted scan of reference definitions, inline fragments, raw HTML anchors and angle-bracket autolinks; this is **not** a complete Markdown parser or live URL check.

| Chapter and lab pair | Reference definitions | Inline fragment links | HTML anchors | HTTP autolinks |
| --- | ---: | ---: | ---: | ---: |
| 13 | 0 | 1 | 0 | 0 |
| 14 | 0 | 0 | 0 | 0 |
| 15 | 0 | 0 | 0 | 0 |
| 16 | 0 | 0 | 0 | 0 |

**Fragment requiring exact anchor verification:** Chapter 13 points to `https://www.postgresql.org/docs/18/sql-createtable.html#SQL-CREATETABLE-STORAGE-PARAMETERS`. Source scan confirms the link string, **not** the HTTP response or HTML ID.

**Confirmed content defect corrected:** Chapter 16 lab's cleanup `docker ps` line was truncated, leaving an unclosed code fence, duplicated acceptance checklist and duplicate official references. Replaced the malformed tail with a complete read-only post-cleanup listing, a closed fence, one acceptance checklist and one reference section. The revised file was re-fetched byte-for-byte after commit. This is a **static source repair**, not evidence of Docker execution.

**Additional high-priority finding (unresolved):** Chapter 15 lab README currently contains 71 lines beginning with Markdown code fences (odd parity) and a visibly truncated cleanup section. The file must receive a dedicated, carefully reconciled repair against its original intended steps before it can be considered safe or executable. Do **not** run its cleanup instructions in their present state. Avoid treating a fence-count heuristic as exhaustive proof of the exact corruption extent.

**Next:** Repair and re-review Chapter 15's damaged cleanup instructions, continue non-inline reference scans for Chapters 17–20, and check exact PostgreSQL 18 anchor IDs and external URLs. Existing PostgreSQL 17 evidence remains historical. No Docker, PostgreSQL, PowerShell, shell, cloud, destructive or failover command was executed in this checkpoint. Runtime validation remains 0/20; independent review and production certification remain pending.


## Chapter 15 cleanup repair and Chapters 17–20 non-inline scan (2026-11-09)

Reviewed track README, master TOC, status tracker, PostgreSQL 18 policy, existing reference-resolution evidence, and semantic-review history. The previously recorded Chapter 15 defect was confirmed: the README repeated the entire lesson after a truncated `docker ps` line and contained broken cleanup fences. Restored a single coherent Section 11 with read-only context, full creation-ID, label, mount and volume-reference checks; a fail-closed stop condition; manual destructive commands only after verification; and post-cleanup absence checks. Preserved Sections 1–10 and the final acceptance/reference sections. The file shrank from 644 to 255 lines; 28 triple-backtick fence lines have even parity and the chapter title appears once. This is a **static documentation repair**, not execution or proof that deletion is race-free. Commit: https://github.com/sssamant21/data-platform-engineering-tutorials/commit/dcb70996bbfa04370c1a31c957037317207e00ce (re-fetched and byte-compared).

Fetched all eight Chapter 17–20 lesson/lab Markdown files on `main` and excluded triple-backtick fenced examples before scanning for reference definitions, inline fragment destinations, raw HTML anchors and HTTP(S) autolinks.

| Pair | Reference definitions | Inline fragment occurrences | HTML anchor tags | HTTP autolinks |
| --- | ---: | ---: | ---: | ---: |
| 17 lesson + lab | 0 | 0 | 0 | 0 |
| 18 lesson + lab | 0 | 2 | 0 | 0 |
| 19 lesson + lab | 0 | 0 | 0 | 0 |
| 20 lesson + lab | 0 | 0 | 0 | 0 |

Both Chapter 18 links target `https://www.postgresql.org/docs/18/functions-admin.html#FUNCTIONS-ADMIN-DBSIZE`. Exact HTML anchor, HTTP response, redirects and semantic correspondence **remain unverified**. These are targeted regex scans, not a full CommonMark parse or comprehensive link validation.

**Next:** Resolve exact PostgreSQL 18 fragments identified in Chapters 11, 13 and 18; HTTP-check remaining external references; reconcile the stale status-tracker description; and independently review the Chapter 15 cleanup safety before isolated runtime use. Keep legacy PG17 commands separate from PG18 image/volume migration. No Docker, psql, SQL, shell, PowerShell, AWS or Kubernetes commands were executed. Runtime 0/20, PG18 runtime 0/20; independent review and production certification pending.


## PostgreSQL 18 documentation section verification — 2026-11-09

**Scope:** Three distinct PostgreSQL 18 external page/fragment destinations previously inventoried in Chapters 11, 13 and 18 (five occurrences total). Re-read the track README, TOC, tracker, baseline and prior validation history before this targeted follow-up. This is not a repeat of the source-link inventory.

| Chapter(s) | Version-pinned destination | Evidence | Exact HTML fragment ID |
| --- | --- | --- | --- |
| 11 (two occurrences) | `runtime-config-wal.html#RUNTIME-CONFIG-WAL-RECOVERY-TARGET` | Official PostgreSQL 18 page loaded and includes §19.5.6 Recovery Target | **Not independently verified** |
| 13 (one occurrence) | `sql-createtable.html#SQL-CREATETABLE-STORAGE-PARAMETERS` | Official PostgreSQL 18 CREATE TABLE page loaded and includes Storage Parameters | **Not independently verified** |
| 18 (two occurrences) | `functions-admin.html#FUNCTIONS-ADMIN-DBSIZE` | Official PostgreSQL 18 System Administration Functions page loaded and includes §9.28.7 Database Object Management Functions and Table 9.102 Database Object Size Functions | **Not independently verified; possible legacy fragment name to investigate** |

Source pages read on 2026-11-09:
- https://www.postgresql.org/docs/18/runtime-config-wal.html
- https://www.postgresql.org/docs/18/sql-createtable.html
- https://www.postgresql.org/docs/18/functions-admin.html

**Finding and limitation:** All three destination *pages* and relevant subject sections are present in the current official PostgreSQL 18 manual. HTTP page retrieval does not prove a fragment is a valid HTML `id`: the retrieval interface strips anchor metadata, and a separate direct raw-HTML retrieval was blocked by network DNS resolution. In particular, do not declare `FUNCTIONS-ADMIN-DBSIZE` valid solely because database-size functions appear on the page. Inspect the actual HTML IDs or use a browser DOM check before correcting any fragment; a guessed replacement risks another broken link. No lesson URL changed on insufficient evidence.

**Tracker correction:** Updated `STATUS-TRACKER.md` to distinguish completed Chapter 01/supporting-document inline-link inventory and 20-pair targeted non-inline scans from unfinished exhaustive resolution. This is a tracking-only correction, not a validation status promotion.

**Next:** Obtain raw HTML/DOM IDs for the three fragment destinations, correct only confirmed mismatches, then check remaining external endpoints, redirects, and semantic relevance. Complete independent Chapter 15 cleanup safety review before runtime testing. No Docker, PostgreSQL, psql, shell/PowerShell lab, cloud or destructive command executed; PG17/PG18 runtime evidence remains 0/20 and independent review/production certification remain pending.


## PostgreSQL 18 reference navigation and Chapter 18 safety follow-up — 2026-11-09

**Scope:** Re-read the track README, master TOC, status tracker, PostgreSQL 18 baseline, semantic-review log, preceding audit, and Chapter 18 lesson/lab. This checkpoint follows the previous page-content verification without repeating the 40-file inventory. No source lessons were edited.

**External reference evidence:** The official PostgreSQL 18 documentation pages for [WAL recovery targets](https://www.postgresql.org/docs/18/runtime-config-wal.html), [CREATE TABLE](https://www.postgresql.org/docs/18/sql-createtable.html), and [system administration functions](https://www.postgresql.org/docs/18/functions-admin.html) were retrieved again via a web reader on 2026-11-09. Their navigation exposes the relevant Recovery Target and Database Object Management Functions sections, and CREATE TABLE documents storage parameters. Following the official section navigation succeeds at the page level. **This does not verify the exact raw HTML id values** for the legacy fragments `RUNTIME-CONFIG-WAL-RECOVERY-TARGET`, `SQL-CREATETABLE-STORAGE-PARAMETERS`, or `FUNCTIONS-ADMIN-DBSIZE`. The web reader strips the fragment from its displayed URL, while direct raw HTML retrieval from the isolated validation shell failed DNS resolution. Thus these five link occurrences remain **anchor-unverified**, not confirmed broken or confirmed valid. Do not guess replacement fragments.

**Chapter 18 source-level safety observation:** The lab uses `postgres:17`, no published port, a fixed container name, and a manual absent-container preflight. The `docker rm -v pg-dbre-ch18` cleanup is destructive to the lab container and any anonymous volumes associated with it; the instructions request identity and mount inspection, but the example cleanup does **not** bind removal to a captured immutable container ID, owner label, and verified mount list. Treat this as a **cleanup guardrail improvement requiring independent review before automated execution**, not as a runtime failure. Do not silently migrate this lab to `postgres:18`; the 18 image requires a fresh isolated volume and `/var/lib/postgresql/18/docker` PGDATA layout under `/var/lib/postgresql`.

**Reproducible next check:** Retrieve each official documentation page as raw HTML in a network-enabled isolated review environment; enumerate `id` attributes using an HTML parser, compare exact case-sensitive fragment strings, and record URL, retrieval time, response status, redirect target, observed IDs, and section semantics. Correct only confirmed mismatches. Then complete the remaining external URL checks and a bounded Chapter 18 cleanup guardrail review. No Docker, psql, SQL, shell lab, cloud or destructive operations executed. PostgreSQL 17 and 18 runtime validation remain **0/20**; independent approval and production certification remain pending.


## Chapter 18 cleanup safety correction — 2026-11-09

After inspecting the track README, master TOC, status tracker, PostgreSQL 18 baseline, prior semantic evidence, and preceding audit, corrected the previously identified Chapter 18 cleanup guardrail defect in [the lab README](../labs/chapter-18/README.md). Commit: https://github.com/sssamant21/data-platform-engineering-tutorials/commit/13b653060b925e14616e3e0197fe0dd5837a0cbd (file re-fetched and byte-compared).

**Source changes:** New lab containers receive an explicit chapter-18 owner label. The manual cleanup procedure now requires Docker context, full immutable container ID, owner label, image identity and mount inspection, plus ID recheck before stop/remove. It uses the captured full ID rather than the mutable name for stop/removal. Removed `docker rm -v`; anonymous volumes are deliberately retained for separate reviewed disposition, not silently deleted. The checklist requires evidence of retained volumes. Pre-label containers must not be assumed owned. No changes were made to the PostgreSQL 17 image/mount assumptions; PostgreSQL 18 migration remains separate.

**Limitations:** This is a source-only safeguard, not a race-free automation implementation or independent safety approval. The `<VERIFIED_FULL_CONTAINER_ID>` placeholder must be manually substituted; never paste it unchanged. Cleanup is intentionally not fully automated. Retained anonymous volumes require explicit later ownership/reference review. No Docker, PostgreSQL, shell lab, cloud or destructive command executed. PG17/PG18 runtime 0/20; independent review and production certification pending.

**Next:** Finish exact PostgreSQL 18 fragment-ID and remaining external URL verification, obtain independent review of Chapter 15 and 18 cleanup procedures, then migrate and test labs in isolated version-correct Docker environments with genuine evidence.


## Reproducible PostgreSQL 18 fragment verification helper — 2026-11-09

Following the earlier unresolved Chapter 11/13/18 anchor findings, added [a read-only standard-library verifier](check_pg18_fragments.py) in commit [88ea88a](https://github.com/sssamant21/data-platform-engineering-tutorials/commit/88ea88a4bc9f3457a69663e738d513b0958fc060). It requests each of the three official PostgreSQL 18 pages, checks the final URL stays within the version-pinned official documentation, parses actual HTML `id` attributes and legacy named anchors, and reports each fragment as present, missing, or unverified. It exits nonzero unless all three are present. Its output includes UTC retrieval time, HTTP status, redirect destination and limited matching IDs; it does not execute SQL or Docker.

**Execution limitation:** This isolated review environment could not resolve `www.postgresql.org` via DNS for raw HTML retrieval. The helper was committed and fetched back from GitHub, but **not network-executed**; no fragment is newly marked valid or broken. To run in a network-enabled disposable review environment: `python validation/check_pg18_fragments.py --output validation/pg18-fragment-results.json` from the track root. Review the output before committing evidence; if a fragment is absent, verify section semantics and correct only the confirmed URL. The helper is not a substitute for exhaustive external URL checking or independent review.

**Remaining gates:** Full external URL/redirect and parser-aware link validation; Chapter 15/18 independent cleanup review; PostgreSQL 18 image/mount migration and actual isolated lab execution. PG17 and PG18 runtime statuses remain 0/20; production certification is pending. No other curriculum files changed.


## Offline regression coverage for PostgreSQL 18 fragment checker — 2026-11-09

Added [test_check_pg18_fragments.py](test_check_pg18_fragments.py) as an offline, mocked regression suite for the existing [fragment verifier](check_pg18_fragments.py). Eight test cases cover exact HTML `id`, legacy named anchors, visible heading text without an anchor, unexpected host/version redirects, non-HTML content, oversized responses, and DNS/network failure classified as unverified. This adds **test definitions**, not live documentation validation. The new file was fetched from GitHub `main` after publication.

Run from this track's root with Python 3:

```sh
python -m unittest discover -s validation -p 'test_check_pg18_fragments.py' -v
python validation/check_pg18_fragments.py --output validation/pg18-fragment-results.json
```

**Execution status:** The unit suite has not been executed in this run; no passing test result is claimed. A direct outbound HTTPS attempt to `www.postgresql.org` from the current container failed DNS resolution (`URLError: [Errno -3] Temporary failure in name resolution`). Therefore exact live anchors and external endpoint status remain unverified. Review any generated JSON before committing; do not publish transient network errors as proof of invalid links.

**Next:** Execute offline unit tests in a Python-enabled checkout, then run the live verifier from a network-enabled environment and inspect exact HTML fragment IDs. Resolve confirmed link defects only; proceed to independently reviewed cleanup guards and isolated PostgreSQL 18 migration before any lab runtime status changes. PostgreSQL 17 and 18 runtime validation remain 0/20, and independent review/production certification remain pending.


## Endpoint-identity regression hardening — 2026-11-09

**Confirmed static defect:** The PostgreSQL 18 fragment verifier previously accepted an HTTPS redirect to *any* path under `www.postgresql.org/docs/18/`, even when the destination page differed from the requested documentation endpoint. An unrelated page with a matching HTML ID could therefore be reported as a verified original reference. The verifier now requires the final URL to equal the requested page URL exactly, and reports `unexpected_redirect` otherwise. This deliberately treats even potentially benign redirects as requiring manual review rather than silently validating a changed target.

Added an offline regression test for same-version, wrong-page redirects (nine tests now defined). This is a source correction and test addition **only**; the regression suite was not executed in this checkpoint. The local execution environment reports Python 3.13.5 but has no Docker executable and cannot resolve `github.com`; no PostgreSQL runtime or external HTTP verification was performed. Reproduce offline tests from the track root with `python -m unittest discover -s validation -p test_check_pg18_fragments.py -v`. In a network-enabled environment, run `python validation/check_pg18_fragments.py --output validation/pg18-fragment-results.json`, review and sanitize the output before committing any evidence. Exact anchors remain unverified; 0/20 labs runtime validated on PostgreSQL 17 or 18. Independent review and certification remain pending.
