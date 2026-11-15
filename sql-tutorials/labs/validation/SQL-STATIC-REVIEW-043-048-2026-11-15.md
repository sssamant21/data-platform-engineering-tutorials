# SQL static review — Chapters 043–048 (2026-11-15)

**Scope:** targeted source-based reasoning for six published Chapter 043–048 Markdown lessons and their six matching SQL labs, fetched from GitHub `main`. **No SQL was executed.** This is not comprehensive parser-based syntax validation, independent editorial review, production-safety certification, or PostgreSQL 18 runtime acceptance.

## Reviewed sources

| Chapter | SQL lab | Targeted expectation |
|---|---|---|
| 043 LEFT OUTER JOIN | [043](../043-left-outer-join-unmatched-rows.sql) | Four orders, 74.00 total; three matched / 65.00 and one unmatched / 9.00; ON filter retains four, WHERE returns two; customer-preserving join four rows |
| 044 RIGHT/FULL JOIN | [044](../044-right-full-outer-join.sql) | A 3/59.00; B 3/54.00; FULL four rows, two matched, one each unmatched; RIGHT and reversed LEFT three rows |
| 045 CROSS/SELF JOIN | [045](../045-cross-join-self-join.sql) | 3 regions × 2 modes = six combinations; four employees, three manager matches, one root, two direct reports to Avery |
| 046 Multi-table joins | [046](../046-multi-table-joins-condition-design.sql) | Four orders, five items, item total 100.00, payments 90.00, one orphan customer key; pre-aggregated order-grain report four rows |
| 047 1:N and M:N | [047](../047-one-to-many-many-to-many.sql) | Three customers, three orders / 65.00, four customer-left rows; four product-tag links, two links per tag |
| 048 EXISTS/NOT EXISTS | [048](../048-exists-not-exists-semi-anti-joins.sql) | Four customers, five orders, EXISTS three, NOT EXISTS one, four matched orders, one NULL customer key, unsafe NOT IN zero, paid customers two |

## Findings and corrective action

1. **Corrected Chapter 046 narrative contradiction:** the naive LEFT-joined order/item/payment query produces **seven** rows, not six: order 101 has 2 items × 2 payments = 4; orders 102, 103, and 104 contribute one row each (the unmatched payment on 104 is NULL-extended). The lesson previously said both six and seven in the same sentence. Fixed on `main` in commit [`3033c839a71d3867de51e6f83f6d2efda8674067`](https://github.com/sssamant21/data-platform-engineering-tutorials/commit/3033c839a71d3867de51e6f83f6d2efda8674067). The lab does not execute this naive example; its assertions concern the correctly pre-aggregated four-row report.
2. Chapter 043 deliberately models an unmatched foreign-key value without a foreign-key constraint; this is intentional staging/reconciliation data, **not** a recommended operational integrity model.
3. Chapter 048 uses a psql-specific `\\set ON_ERROR_STOP on` directive. Its `NOT IN` example intentionally returns no rows because a subquery key is NULL. The lesson must not imply this is a safe anti-join.
4. Chapters 043–047 allow PostgreSQL 18 **or later**; Chapter 048 pins major version 18. Actual runtime acceptance must separately prove PostgreSQL 18, not rely on the broader guards.
5. All six labs create temporary synthetic tables and perform INSERT operations within transactions ending in `ROLLBACK`. The SQL text includes version/database/standby guards and local timeouts. These are **not read-only** scripts, and name/version checks do not independently prove isolation. Run only on independently verified disposable infrastructure, never production.

## Validation boundaries and next actions

- **Authored/published:** 120/120 (previously reported).
- **Targeted structural QA:** 120/120 (previously reported; not comprehensive Markdown anchor QA).
- **Targeted SQL static review:** **48/120** (001–048, including this batch). The reviewed expected values are consistent with the synthetic fixtures after the Chapter 046 narrative correction.
- **Independent editorial review:** 0/120.
- **Actual isolated PostgreSQL 18 runtime validation:** 0/120. No runtime output, server identity, exit codes, or execution artifacts were collected in this review.
- **Pending:** Chapters 049–054 targeted SQL semantic and expected-output review; comprehensive Markdown-aware local anchors/external URLs, parser-based SQL syntax review, independently verified isolated PostgreSQL 18 execution with retained reproducible evidence, and tracked defect remediation.

**Evidence method:** compared fixture INSERT values, join cardinalities, NULL behavior, aggregate arithmetic and DO-block assertions against the published lesson expectations; inspected transaction/guard patterns. This method cannot detect all syntax errors or prove the scripts execute successfully.
