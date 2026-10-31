# Snowflake Learning Path — Navigation Status

**Updated:** 2026-10-31  
**Scope:** `snowflake/learning-path/` is a **navigation-only index**, not an independent curriculum.  
**Authoritative sources:** [Canonical Snowflake curriculum — 90/90](../MASTER-LAYOUT.md); [Accelerated DBRE/SRE course — 7/7](../accelerated-dbre-sre/README.md).

## Deduplication record

The previously authored **eight copied tutorial files** in `learning-path/chapters/` have been deleted from the draft feature branch. The same instructional topics continue to be available in the original canonical and accelerated teaching sources. No canonical 90-chapter file or accelerated lesson is deleted by this cleanup.

| Area | Authoritative source | Learning-path action |
|---|---|---|
| Fundamental concepts through incident response | [Seven accelerated 60-minute lessons](../accelerated-dbre-sre/README.md) | Link to the original seven lessons; no duplicates |
| Ingestion, CSV, COPY INTO and Snowpipe | [Canonical 11–16](../MASTER-LAYOUT.md) | Link to canonical files; retain one answer-free [tabletop worksheet](exercises/chapter-08-ingestion-tabletop.md) |
| CDC, streams, tasks and MERGE | [Canonical 18–22](../MASTER-LAYOUT.md) | Link to canonical files, no new Chapter 09 |
| Detailed enterprise topics | [Canonical 90-chapter curriculum](../MASTER-LAYOUT.md) | Continue using original tutorial files |

**Course timing:** The accelerated curriculum remains **7 × 60 = 420 minutes**. Canonical ingestion and CDC reading is **self-paced**, not an eighth or ninth authored 60-minute course.

## QA and safety gates

- [Navigation-only regression tests](validation/test_learning_path.py) ensure a nonduplicating index and actual local targets.
- [Ingestion worksheet checks](validation/test_chapter_08_ingestion.py) confirm that the unique fictional exercise stays answer-free and avoids live SQL or privileged actions.
- **[GitHub Actions #413 — PASS](https://github.com/sssamant21/data-platform-engineering-tutorials/actions/runs/41215988701): 104 accelerated curriculum regression tests + 13 navigation/worksheet tests passed (117 Python tests total)**. PowerShell syntax and mock-only preflight checks also passed. **No live Snowflake connection or SQL execution occurred.**
- **V03 Snowflake runtime:** **USER-DEFERRED / NOT RUN (0/7 accelerated smoke scripts)**. No ingestion worksheet ran in Snowflake.
- **V04 human review:** **SKIPPED BY OWNER / NOT APPROVED**. This is not a human approval.
- **V05 production certification:** **NOT CERTIFIED**.
- [PR #43](https://github.com/sssamant21/data-platform-engineering-tutorials/pull/43) stays **DRAFT / UNMERGED** until an explicit merge decision.

## Maintenance rule

Keep **one authoritative document per tutorial topic**. A learning path is a set of links and suggested reading steps, not another location for copying lesson Markdown. When a tutorial changes, update its original file only and fix index links if paths change.
