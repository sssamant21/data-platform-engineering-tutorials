# SQL static review — Chapters 007–012 (2026-11-15)

## Scope and method

Reviewed the six SQL lab files from the current `main` branch textually for synthetic input rows, SQL expression semantics, expected outputs, deterministic ordering, version/database guards, and read-only transaction boundaries. Read `MASTER-TOC.md`, `README.md`, and `STATUS-TRACKER.md` before this review. This is **targeted static inspection**, not independent editorial certification, complete syntax parsing, or PostgreSQL 18 execution. No SQL was executed.

| Chapter | File | Static observations |
|---|---|---|
| 007 | [SELECT fundamentals](../007-select-fundamentals.sql) | Six synthetic orders; paid IDs 7001, 7003, 7004; paid total 120+40+60=220; 2 pending; acceptance agrees |
| 008 | [Aliases and calculations](../008-aliases-expressions-calculated-columns.sql) | 2×19.95=39.90, 3×10=30.00; 90% amounts 35.91 and 27.00; gross 69.90 and net 62.91; acceptance agrees |
| 009 | [Types and NULL](../009-data-types-null-explicit-conversion.sql) | One NULL email and one empty string; integer 1/3=0; numeric 1/3 rounded to 0.33; parsed 12.50+7.25=19.75; acceptance agrees |
| 010 | [First lab](../010-lab-01-explore-sample-database.sql) | Order totals 31, 30, 12.50, 4; aggregate 77.50; 3 customers, 4 orders, 5 lines, one customer without orders; acceptance agrees |
| 011 | [WHERE operators](../011-where-comparison-operators.sql) | Paid 201,203,206; >=100 202,203,204,206; >100 203,206; <>paid 202,205 (NULL excluded); missing status 204; before Nov 4: 201,202,203; acceptance agrees |
| 012 | [Boolean precedence](../012-and-or-not-boolean-precedence.sql) | AND binds more tightly than OR; expected C1 301,302,303,306,307 versus C2 302,303,306,307; NOT excludes NULL status; acceptance agrees |

## Safety and portability

All six labs use `BEGIN READ ONLY` and `ROLLBACK`, only inline synthetic `VALUES`/CTEs, a database-name and PostgreSQL-major-version assertion, and fail-closed arithmetic acceptance assertions. The database name and version checks **do not prove endpoint isolation**. Run only against a separately verified disposable PostgreSQL 18 instance with least-privilege credentials, `psql -X -v ON_ERROR_STOP=1`, and externally enforced statement/lock timeouts. No production credentials or production database may be used.

Portable concepts include SELECT, WHERE, CASE, NULL, joins, grouping, and Boolean precedence. PostgreSQL-specific details include `::numeric`, `FILTER`, `array_agg`, array literals, regex `~`, `current_setting`, and the exact environment guard. `BEGIN READ ONLY` support and behavior vary across vendors.

## Findings and limitations

- **No arithmetic or expected-ID-set contradiction identified** in this six-lab targeted inspection.
- Some expected outputs appear only in comments; this review did not independently compare every chapter prose example against each lab statement.
- Guardrails were inspected as text, not exercised; arithmetic fail-closed assertions and runtime behavior remain unverified.
- PostgreSQL 18 parser, query execution, SQLSTATE handling, query-plan behavior, external reference availability, and full Markdown anchors/links remain **pending**.
- **Independent editorial review: 0/120. Actual isolated PostgreSQL 18 runtime validation: 0/120.**

## Next

Targeted SQL static review Chapters 013–018; then comprehensive cross-chapter semantic and Markdown anchor/link checks, followed by isolated PostgreSQL 18 runtime acceptance with retained command, environment identity, stdout/stderr, exit codes and reproducible evidence.
