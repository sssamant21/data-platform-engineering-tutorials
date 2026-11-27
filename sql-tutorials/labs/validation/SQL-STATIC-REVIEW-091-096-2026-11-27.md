# Targeted SQL source review — Chapters 091–096

Date: 2026-11-27. Scope: manual fixture arithmetic, assertion design and safety inspection of six published chapter/lab pairs on main. Not independent editorial acceptance, parser certification or runtime evidence.

| Chapter | Source-derived expectation | Scope limitation |
|---|---|---|
| 091 | Four orders; three paid; customer 1: 2/35.00, customer 2: 1/10.00, customer 3: 0/0; paid total 45.00 | Estimated EXPLAIN only; no measured latency |
| 092 | Ten events: failed 2/0.20, paid 7/0.70, pending 1/0.10 | Inline rows do not test physical scan choices |
| 093 | Point 103/8.00; half-open range 102–104 totals 25+8+40=73; all five total 100 | No physical B-tree |
| 094 | Tenant 10 paid IDs 101 and 103 in range, total 50; all tenant-10 paid 3/100; tenant 20 paid 1/40 | No composite index benchmark |
| 095 | Open 4/100; tenant 10 open 3/60, ordered IDs 105,103,101; lower-case email matches 1,3 | No partial/expression/covering index created |
| 096 | Eight rows, tenant 10 four, paid four, joint three (37.5%); independence estimate two; tenant 20 pending three | No statistics refresh or vacuum; catalog rows environment-dependent |

## Source links and reviewed lab blobs

- [091](../../part-10-performance/091-read-execution-plans-with-explain.md) / [lab](../091-read-execution-plans-with-explain.sql): af418c9bf7287ef862f7dbfd43ddb77b1a7a24c0
- [092](../../part-10-performance/092-table-scans-index-scans-row-estimates-and-selectivity.md) / [lab](../092-scans-estimates-selectivity.sql): f78858cd683d2724a772f105162addee79f12acc
- [093](../../part-10-performance/093-btree-indexes-and-common-index-access-patterns.md) / [lab](../093-btree-index-access-patterns.sql): 409de8c71c25e3fd06f62ad46ed610233f11be21
- [094](../../part-10-performance/094-composite-indexes-and-column-order.md) / [lab](../094-composite-indexes-column-order.sql)
- [095](../../part-10-performance/095-partial-expression-and-covering-indexes.md) / [lab](../095-partial-expression-covering-indexes.sql): 285cfb739eb720262b0fde5dd9796cd7c6b4497b
- [096](../../part-10-performance/096-optimizer-statistics-and-postgresql-maintenance-basics.md) / [lab](../096-optimizer-statistics-maintenance.sql): 58bf51b1a59c2a82b58cd4d049115b55dfd41336

All six use synthetic data, psql ON_ERROR_STOP, read-only transactions, local timeouts, database/version guards and rollback. Guards do not prove infrastructure isolation. Bidirectional EXCEPT ALL checks result multiplicity, not ordering; ordered display requires separate runtime verification. No SQL executed. No targeted arithmetic contradiction identified. Physical performance and maintenance claims require separate representative isolated benchmarks. PostgreSQL-specific EXPLAIN, catalog queries, casts and psql directives are not portable SQL.

Next: 097–102 targeted review, comprehensive Markdown and parser QA, regression execution and isolated PostgreSQL 18 acceptance. No production access.
