# Snowflake DBRE/SRE — Beginner Terminology Glossary

**Audience:** New DBRE/SRE engineers, administrators, application developers, analysts and other stakeholders.  
**Coverage:** Levels 1–7 of the [accelerated offline curriculum](../README.md).  
**Mode:** **OFFLINE learning only** — no Snowflake account, warehouse, CLI, personal credentials, or live SQL is needed.  
**Version note:** Concepts are written in plain language; feature permissions, editions and behavior must be checked against current official Snowflake documentation before real operational use.

**How to use:** Read the relevant level before class, say each term in your own words, then apply it to a **fictional** scenario. Definitions do not confirm runtime behavior. For an independent closed-answer assessment, the instructor can withhold this glossary until after the learner workbook has been completed.

## Level 1 — Platform and SQL fundamentals

| Term | Beginner explanation | Avoid this common confusion |
|---|---|---|
| Snowflake account | The logical service environment for an organization or workload, with its own users, roles and objects | Not the same as your laptop, a database or a warehouse |
| Organization | A grouping of one or more Snowflake accounts for administrative purposes | Not a SQL schema |
| Database | A named container holding schemas | A database is not the computer that executes its queries |
| Schema | A namespace **inside a database**, organizing tables, views and other objects | Not the shape of a single row in this context |
| Table | A stored collection of data organized into rows and columns | Not the same as a virtual warehouse |
| Row | One record, e.g. a fictional order | Not a column or an individual field name |
| Column | One named attribute in a table, e.g. REGION or AMOUNT | Not a separate database |
| Standard view | A saved SQL definition that generally evaluates underlying data when queried | Do not confuse with a materialized view, which maintains stored results |
| SQL | The language used to query and manipulate data and database objects | Reading a sample statement is not executing it |
| SELECT / GROUP BY | SELECT chooses results; GROUP BY organizes records into groups for aggregate calculations | GROUP BY is not simply sorting; ORDER BY sorts |
| OLAP vs OLTP | OLAP emphasizes analytical queries over substantial data; OLTP emphasizes frequent transaction-level operations | The terms describe workload patterns, not a promise that every system is optimized for both |
| Storage / compute / cloud services | Snowflake's three main architectural layers: data storage, processing resources and managed coordination/metadata services | Snowflake manages the underlying platform; the DBRE team still owns account-level operational choices |

## Level 2 — Administration and operations

| Term | Beginner explanation | Avoid this common confusion |
|---|---|---|
| Virtual warehouse | A managed compute cluster used by warehouse-backed SQL and other supported workloads | Not a database, and not the physical location of stored table rows |
| Warehouse size | Capacity setting controlling compute resources allocated to a warehouse | Bigger is not automatically the cheapest or best query plan |
| Auto-suspend | Suspends a warehouse after configured idle time to reduce idle compute usage | Does not guarantee zero cost or eliminate startup delay |
| Auto-resume | Allows a suspended warehouse to start automatically when an eligible request needs it | Does not mean all queries execute without provisioning time |
| User | A Snowflake identity that can authenticate subject to account policy | A user is not the same thing as a role |
| Role | A bundle of granted privileges used to authorize operations | A role name alone does not guarantee access |
| Privilege | Permission such as USAGE or SELECT on a particular object | TABLE SELECT alone may not grant usable parent database/schema access |
| Least privilege | Give only the approved permissions required for a specific task and scope | Do not use ACCOUNTADMIN as a workaround for a lab denial |
| Session | A connected working context containing current user, role and other settings | Independent worksheets/CLI commands may create separate sessions |
| Query tag | Optional metadata set on a session to help identify a query workload | A matching tag is not a unique execution ID |
| QUERY_ID | Unique identifier for an **actual executed** query | A fictional ID in a tabletop case is not runtime evidence |

## Level 3 — Query performance

| Term | Beginner explanation | Avoid this common confusion |
|---|---|---|
| Query Profile | Visualization of a query's execution steps, including scans, joins and potential bottlenecks | An unexecuted sample does not have a real Query Profile |
| Query History | Records and statistics about query executions visible to permitted roles | History visibility, lookback and lag depend on the specific source |
| Compilation | Preparing and optimizing a SQL statement before execution | Not the same as time spent running execution operators |
| Execution time | Time consumed actually executing a query | Total elapsed time can include queueing and other waiting |
| Provisioning queue | Delay while required warehouse resources are becoming available | Different from overload due to busy running workload |
| Overload queue | Delay when a warehouse has more eligible work than can be served immediately | Not proof that SQL text itself is slow |
| Transaction blocking | Wait caused by a conflicting lock/transaction | Different from provisioning or compute overload |
| Micro-partition | Snowflake-managed small unit of columnar table storage with metadata useful for skipping irrelevant data | Not a user-created B-tree index or manually assigned shard |
| Partition pruning | Avoiding reads of micro-partitions that cannot match relevant filters | Large scans can still occur when predicates cannot prune effectively |
| Spill | Work or intermediate data that moves to slower storage when available memory is insufficient | Not automatically evidence that adding warehouse size fixes the whole query |
| p95 latency | The value at or below which approximately 95% of measured latencies fall, given a defined sample and window | Not the average or a universal SLO |

## Level 4 — Monitoring and FinOps

| Term | Beginner explanation | Avoid this common confusion |
|---|---|---|
| SLI / SLO | SLI is a measured service behavior; SLO is an agreed target for that behavior | An arbitrary dashboard threshold is not an approved SLO |
| Account Usage | Snowflake-provided historical account telemetry views | Some views have material latency and privilege requirements; not always real time |
| Information Schema | Database-associated views/functions to inspect metadata and certain historical activity | It is not interchangeable with account-wide historical telemetry |
| AVG_QUEUED_LOAD | Queued-overload query time summed over an interval, divided by the interval duration | It is a load ratio, **not the number of distinct queued users/queries** |
| Credit | Unit Snowflake uses to meter certain compute and service consumption | A credit count is not itself a dollar invoice |
| CREDITS_USED | Usage metric that can represent gross warehouse consumption | Not automatically the account's final billed credits |
| CREDITS_BILLED | Billing-oriented meter for the applicable billing scope | Do not compare two sources without aligning time range, scope and adjustments |
| Resource monitor | Controls/notifies about credit use by covered warehouses | Does not cover all serverless feature or AI service spending |
| Budget | Snowflake cost-control feature for monitoring scoped spending, including sources beyond user-managed warehouses | Different from a warehouse resource monitor |
| Historical telemetry lag | Delay between an event and appearance in an account usage view | An empty recent result does not prove the service is healthy |

## Level 5 — Security and governance

| Term | Beginner explanation | Avoid this common confusion |
|---|---|---|
| RBAC | Role-based access control: privileges assigned to roles, roles granted along authorized paths | Merely knowing a user's name does not reveal all effective permissions |
| USAGE | Privilege enabling use or reference of certain objects such as warehouses, databases and schemas | Does not by itself grant table SELECT |
| SELECT privilege | Permission to read permitted data from a table or view | Parent USAGE and compute authorization may also be needed |
| Secondary roles | Other enabled roles that can contribute privileges in supported sessions | Must not assume the primary role alone represents every effective grant |
| Masking policy | Controls the values of sensitive columns returned to different authorized users | Different from a row access policy |
| Row access policy | Controls which rows a given role/user may see | Does not directly replace masking for individual columns |
| Secure view | A Snowflake view with stronger safeguards for the underlying query definition/data sharing behavior | Not a blanket guarantee that all result data is safe to export |
| Audit data | Activity metadata used to investigate access and compliance | User names, IP addresses or raw query text may be sensitive too |
| Synthetic data | Fictional/test data that does not expose actual patient, customer or confidential information | A nonproduction database may still contain sensitive real data |

## Level 6 — Data protection, recovery and DR

| Term | Beginner explanation | Avoid this common confusion |
|---|---|---|
| Time Travel | Access to eligible historical object/data states within the **effective retention** window | Cannot query table history from before table creation or beyond retention |
| DATA_RETENTION_TIME_IN_DAYS | Configured/inherited retention setting for eligible objects | Account minimum and object type can affect effective retention |
| UNDROP | Restores certain previously dropped objects when the applicable recovery prerequisites hold | Not an unlimited general backup |
| Zero-copy clone | Creates a new object sharing existing storage initially, with copy-on-write behavior as data diverges | An untested clone does not prove disaster recovery readiness |
| Fail-safe | Snowflake-operated last-resort recovery period for eligible historical data | Not routine self-service Time Travel or a user-run backup |
| Replication / failover | Copying supported objects/state and switching workloads to a designated recovery environment under supported configurations | Do not assume every object/feature is covered or that failover is automatic |
| RPO | Recovery Point Objective: maximum **acceptable data loss expressed as time** | Not the time needed to restore service |
| RTO | Recovery Time Objective: maximum **acceptable time to usable service** | Not a substitute for data validation or RPO |
| Recovery rehearsal | Controlled demonstration of recovery and data-integrity checks in an authorized environment | A tabletop document is not a successfully executed restore |

## Level 7 — Incident response and production reliability

| Term | Beginner explanation | Avoid this common confusion |
|---|---|---|
| Incident severity | Agreed priority reflecting user impact and urgency | A high metric alone does not always imply a P0 incident |
| Triage | Check scope, impact, evidence and plausible causes before selecting mitigation | Not a license to cancel unknown production queries |
| Query latency vs. freshness | Query latency concerns response delay; freshness concerns how recently source data has arrived | A stale dashboard can be caused by ingestion, tasks or upstream systems |
| Mitigation | Authorized action to reduce user impact while the underlying cause is investigated | Must consider downstream consequences and rollback |
| Rollback | Approved method to reverse a change when its outcome is unsafe or ineffective | Some data operations are not easily reversible |
| RCA | Root Cause Analysis: a blameless, evidence-driven explanation of an incident and prevention | Avoid blaming individuals or presenting hypotheses as verified facts |
| Action owner | Person/team responsible for a specific remediation and follow-up date | An unassigned action is not a reliable prevention plan |
| Evidence | Actual query IDs, permitted telemetry, timestamps and other verifiable records | Hypothetical exercise results are not actual environment observations |

## Mini reference: what to avoid saying

- **Not:** “The SQL example passed.” **Instead:** “The workbook includes an expected result, but V03 SQL has NOT RUN.”
- **Not:** “Snowflake Account Usage is live.” **Instead:** “Its latency varies by view; verify incident data source suitability.”
- **Not:** “We have only one warehouse.” **Instead:** “Warehouse compute, Snowflake storage and cloud services are separate concepts.”
- **Not:** “Cost credits equal the invoice.” **Instead:** “First compare matching billing views, periods and adjustment scope.”
- **Not:** “The restore is proven.” **Instead:** “Recovery is a tabletop until authorized restoration and validation are executed.”
- **Not:** “Our review passed.” **Instead:** “Automated author QA passed. The owner skipped V04 human review, without approval.”

## Source references for further reading

- [Snowflake architecture and concepts](https://docs.snowflake.com/en/user-guide/intro-key-concepts)
- [Virtual warehouses](https://docs.snowflake.com/en/user-guide/warehouses-overview)
- [Query History](https://docs.snowflake.com/en/sql-reference/functions/query_history)
- [Warehouse Load History](https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_load_history)
- [Resource monitors and serverless limitations](https://docs.snowflake.com/en/user-guide/resource-monitors)
- [RBAC](https://docs.snowflake.com/en/user-guide/security-access-control-overview)
- [Time Travel](https://docs.snowflake.com/en/user-guide/data-time-travel)
- [Fail-safe](https://docs.snowflake.com/en/user-guide/data-failsafe)

**Accuracy boundary (2026-10-31):** This glossary uses documented general concepts and current linked Snowflake documentation. No independent review, SQL execution, learner assessment, incident rehearsal or certification has occurred. **V03: USER-DEFERRED / NOT RUN 0/7; V04: SKIPPED BY OWNER / NOT APPROVED; V05: NOT CERTIFIED.**
