# Snowflake Learning Path — DBRE / SRE / Beginners

**One learning path. No duplicated tutorials.**

This is a **navigation-only learning path** pointing to the two existing Snowflake teaching resources in this repository: the **[canonical 90-chapter curriculum](../MASTER-LAYOUT.md)** for comprehensive topic-specific tutorials, and the **[seven-session accelerated DBRE/SRE course](../accelerated-dbre-sre/README.md)** for concise 60-minute onboarding workshops. Each topic has an authoritative tutorial source, so updates do not need to be copied into a third set of chapter files.

**Safety and publication:** All seven accelerated lessons have offline author/static QA; live Snowflake SQL testing is **USER-DEFERRED / NOT RUN (0/7)**. Human review was **SKIPPED BY OWNER / NOT APPROVED**. **Production NOT CERTIFIED**. The changes are in draft [PR #43](https://github.com/sssamant21/data-platform-engineering-tutorials/pull/43), **not on main**.

## Start here — guided beginner-to-DBRE/SRE route

| Step | Recommended reading (single authoritative source) | Suggested duration | Focus |
|---|---|---|---|
| 01 | [Accelerated Level 1 — Snowflake Fundamentals](../accelerated-dbre-sre/level-01-snowflake-fundamentals.md) | 60 min | Architecture, database, schema, table, row, column and SQL |
| 02 | [Accelerated Level 2 — Administration](../accelerated-dbre-sre/level-02-administration-fundamentals.md) | 60 min | Warehouses, roles, permissions and query history |
| 03 | [Accelerated Level 3 — Query Performance](../accelerated-dbre-sre/level-03-performance-query-optimization.md) | 60 min | Query Profile, execution/waiting, pruning and safe tuning |
| 04 | [Accelerated Level 4 — Observability and Cost](../accelerated-dbre-sre/level-04-monitoring-observability-cost.md) | 60 min | Historical usage, credits, SLOs and monitoring |
| 05 | [Accelerated Level 5 — Security and Governance](../accelerated-dbre-sre/level-05-security-rbac-governance.md) | 60 min | Least privilege, RBAC, masking and audit safety |
| 06 | [Accelerated Level 6 — Recovery and DR](../accelerated-dbre-sre/level-06-data-recovery-disaster-recovery.md) | 60 min | Time Travel, clones, retention, RPO and RTO |
| 07 | [Accelerated Level 7 — Incident Response](../accelerated-dbre-sre/level-07-production-incident-response.md) | 60 min | Investigation, root cause analysis and prevention |
| 08 | [Canonical 11 — Stages](../11-stages-internal-external.md), [12 — File Formats](../12-file-formats.md), [13 — COPY INTO](../13-copy-into-bulk-data-loading.md), [15 — Load Troubleshooting](../15-data-loading-troubleshooting-validation.md), [16 — Snowpipe](../16-snowpipe.md) | Self-paced | Data loading and ingestion; [unique offline worksheet](exercises/chapter-08-ingestion-tabletop.md) |

**Time accounting:** Steps 01–07 are **seven 60-minute sessions = 420 minutes**. Step 08 is **self-paced reading from the canonical curriculum**; it is *not* an additional authored 60-minute lesson, and we do not claim a fixed total for it.

## Next advanced study — use existing canonical chapters

Continue directly to the canonical Snowflake tutorials; do **not** create another copy:

- **Incremental CDC pipelines:** [18 — Streams and CDC](../18-streams-change-data-capture.md), [19 — Tasks](../19-tasks-scheduled-processing.md), [21 — Streams + Tasks Pipelines](../21-streams-tasks-production-pipelines.md), [22 — MERGE and Upserts](../22-merge-upsert-incremental-processing.md).
- **Warehouse performance:** [36 — Query Processing Internals](../36-snowflake-query-processing-internals.md), [37 — Query Profile](../37-query-profile-deep-dive.md), [43 — Warehouse Sizing](../43-warehouse-sizing-scaling.md).
- **Operations:** [75 — Production Administration](../75-snowflake-production-administration-runbook.md), [76 — Query Slowness](../76-snowflake-query-slowness-troubleshooting.md), [80 — Incident Investigation](../80-snowflake-production-incident-investigation-runbook.md).

## Offline study, learner and instructor resources

| Resource | Purpose |
|---|---|
| [Beginner glossary](../accelerated-dbre-sre/validation/BEGINNER-SNOWFLAKE-GLOSSARY.md) | 70 terms explained in plain language |
| [Answer-free workbook for accelerated Levels 1–7](../accelerated-dbre-sre/validation/LEARNER-OFFLINE-WORKBOOK.md) | 35 knowledge prompts and seven tabletop cases |
| [Ingestion worksheet for Step 08](exercises/chapter-08-ingestion-tabletop.md) | Unique fictional CSV troubleshooting activity; no copied tutorial |
| [Seven-session course delivery checklist](../accelerated-dbre-sre/validation/COURSE-DELIVERY-CHECKLIST.md) | Teaching the 420-minute accelerated course |
| [Instructor guide and rubrics](../accelerated-dbre-sre/validation/INSTRUCTOR-OFFLINE-ACCEPTANCE.md) | Instructor-only model reasoning; keep separate during closed-answer assessment |
| [Learning-path status](STATUS.md) | Tracks navigation validity and the deferred runtime boundaries |

Use the workbook and a fictional scenario without requesting credentials or running Snowflake SQL. Knowledge-check answers are in the linked accelerated lessons; distribute the answer-free learner workbook for independent assessments.

## Authoritative-content policy

- `snowflake/` canonical Chapter 01–90 Markdown files are the **single detailed topic reference**.
- `snowflake/accelerated-dbre-sre/` provides a **distinct seven-session teaching format** (60-minute agendas and instructor materials), not a mirror of the canonical 90 chapters.
- `snowflake/learning-path/` contains **navigation plus a unique paper exercise**, **no tutorial chapter copies**. The former eight copied Markdown chapters have been removed from this branch. Chapter 09 was never published.
- Update the canonical chapter or accelerated lesson **at its source**. Update this learning path only when a link or study sequence changes. Do not add duplicate chapter copies.
- Only [offline navigation tests](validation/test_learning_path.py) run here; they cannot establish Snowflake runtime/operational validity.

**Validation boundaries:** V03 **DEFERRED / NOT RUN**, V04 **SKIPPED BY OWNER / NOT APPROVED**, V05 **NOT CERTIFIED**. The PR remains **DRAFT / UNMERGED**.
