# 023 — Query Statistics with pg_stat_statements

Audience: DBRE and SRE only. PostgreSQL 18 baseline.
Status: authored/static reviewed; PostgreSQL execution pending.

[Previous: Statistics Windows](022-statistics-views-resets-and-measurement-windows.md) · [Hands-on lab](../labs/023-query-statistics-with-pg-stat-statements-lab.md) · [Master plan](../MASTER-PLAN.md)

## Operational outcome

Identify query families contributing execution time, call volume, buffer work and temporary I/O in an incident window. Establish collection coverage, compare compatible entries and select candidates for deeper analysis without claiming that aggregated query statistics explain every application failure.

pg_stat_statements supplies accumulated planning/execution observations, not individual request traces, stored execution plans or a latency histogram. Use it alongside activity, locks, host telemetry, logs and consumer SLIs.

## Enable the module at the correct layer

The server must preload pg_stat_statements through shared_preload_libraries. Adding or removing it requires restart because it allocates shared memory. CREATE EXTENSION installs SQL interfaces in one database; it does not replace preloading or itself activate server-wide collection.

Query identifiers must be calculated. Core compute_query_id auto/on works with the loaded module; an external provider has its own semantics. Verify effective settings on a fresh connection and check that the function can actually read statistics.

Collection spans databases on that server even when the SQL interface exists in only one database. Filter dbid and userid deliberately. Installing the extension in a monitoring database does not confine server collection to it.

In production, inventory the existing preload list and preserve its libraries. Confirm matching server-major extension packages, parameter-group mechanisms for managed services, restart ownership, maintenance impact and rollback. A missing or incompatible library can prevent startup. Do not overwrite an existing list with a one-library example.

The lab uses temporary command-line startup settings on the disposable primary, with a precondition that its original preload list is empty. It preserves configuration files, pauses the original standbys and restores normal Chapter 004 startup after cleanup. This is a lab-specific procedure, not a systemd or managed-service runbook.

## Understand entry identity and normalization

An entry is keyed by database OID, role OID, queryid and toplevel. Treat queryid as a signed 64-bit identifier; preserve it as text when exporting through systems that cannot represent large integers exactly.

Literal variants of a structurally equivalent statement often share one entry. Different semantic resolution, aliases, object identities or search_path can produce different entries. Conversely, hashing can merge statements and rare collisions are possible. Representative text is a sample, not every original SQL invocation.

Do not treat a queryid as a permanent application operation ID. Its stability has limits across schema changes, architectures and major versions. Physical replicas can share query identifiers but retain separate observed work; do not silently merge node costs. Logical replicas have weaker identity guarantees.

Parameter normalization is not a security sanitizer. Representative text can contain literals or identifying information, especially for utility commands and entry churn. Restricted users cannot see other users' text/query identifiers; pg_read_all_stats and superuser access expose more. Store text only through an approved restricted workflow.

The supplied [collector](../scripts/023-query-statistics-snapshot.sql) calls pg_stat_statements(false), omitting query text at retrieval. The function is still asked to enumerate entries; the filter controls exported rows, not server-wide collection.

## Know what the fields measure

| Field group | Operational question | Limitation |
|---|---|---|
| calls and rows | How often did execution complete, and how much output/work was counted? | Not logical requests or committed business outcomes |
| total_exec_time and mean_exec_time | Where is aggregate elapsed execution time spent? | Not CPU time or client end-to-end latency |
| min/max/stddev execution time | Is the observed distribution broad? | No p95/p99; extrema have their own reset epoch |
| plans and planning time | How much planning completed? | Requires track_planning; cached plans make plans differ from calls |
| shared/local block counters | Which families access or modify buffers? | PostgreSQL misses can be OS cache hits |
| temp blocks | Which families generate temporary I/O? | Investigate sort/hash plans and concurrency before tuning memory |
| WAL counters | Which successful statements generate WAL work? | Not committed application-write count or durability proof |
| stats_since and minmax_stats_since | Which entry epochs are being observed? | Distinct total-counter and extrema boundaries |

Planning and execution statistics are updated at their respective successful end phases. A successfully planned statement that fails during execution can contribute planning statistics without an execution call. Consequently calls cannot supply the denominator of an application error SLI. A canceled long query may be conspicuous in logs/activity and absent from successful execution totals.

Execution time includes elapsed server work and waits within its measurement boundary; it is not CPU utilization. Multiple sessions can overlap, so summed execution seconds can exceed wall-clock seconds. With track=all, nested and outer measurements can overlap too; do not sum them as disjoint costs.

## Select collection policy deliberately

pg_stat_statements.track defaults to top. all includes nested statements, while none disables collection. track_utility controls utility-command coverage. track_planning defaults off and can add meaningful contention/overhead on busy systems with similar statements; enable it only with a measured purpose.

pg_stat_statements.max bounds distinct entries and requires server start for changes. pg_stat_statements_info.dealloc records entry deallocation activity. If it increases during an incident window, some query history may have been lost. Larger capacity consumes more shared memory; assess retention and resources together.

save controls saving statistics across clean shutdown. It does not justify comparing across a node restart without validation. I/O timing fields require the relevant timing configuration; zero with timing disabled is not evidence that I/O was fast.

SHOW in the observer exposes that connection's policy, not every actor's overrides. Check effective workload settings where an application or privileged session can change them.

## Rank by the question, using interval deltas

A lifetime top list can highlight yesterday's batch rather than today's incident. Take before/after snapshots, retain raw samples and validate node, database, role, extension version, policy and epoch continuity.

For one compatible entry:

~~~text
interval calls = after.calls - before.calls
interval execution ms = after.total_exec_time - before.total_exec_time
interval mean execution ms = interval execution ms / interval calls
interval rows per call = delta(rows) / interval calls
~~~

Do not subtract cumulative means to obtain an interval mean. A zero call delta has no interval average. Never subtract min/max or standard deviations as though they were counters. Extrema since minmax_stats_since can provide context but do not isolate a custom window automatically.

| Ranking | Useful for |
|---|---|
| Largest execution-time delta | Largest measured aggregate time contribution |
| Largest call delta | Chatty operations and amplification |
| Largest interval mean, with a call-volume threshold | Expensive completed executions |
| Largest read/temp/WAL deltas | Specific resource contributors |

Normalize by actual elapsed window where needed. Compare rows per call and data distribution before declaring a plan regression. A high average does not establish a tail-latency objective failure, and a low average can conceal rare severe waits.

The [offline ranking helper](../scripts/023-query-window-rank.py) rejects incompatible samples and changing global retention/reset markers. It checks per-entry stats_since and counter monotonicity, excludes new entries until they have a baseline, and reports disappeared entries. It ranks only the exported role/database cohort; it does not claim complete server coverage.

## Respect the reset boundary

pg_stat_statements_reset can target userid/dbid/queryid; omitted or zero selectors broaden scope. Calling it without selectors resets all collected statements across databases, even when invoked through a database-local interface.

A selective reset may not change the global full-reset timestamp. Compare entry stats_since as well. PostgreSQL 18's minmax_only option has separate extrema semantics; minmax_stats_since changes without making cumulative counter subtraction invalid. Do not use a min/max reset as an interval-counter reset.

A capacity eviction and later reinsertion can also create a new entry epoch. Missing/new rows need explicit classification. The same database reset discussed in Chapter 022 is not interchangeable with the extension's reset domain.

Capture useful evidence before any approved reset. Production incident collection should ordinarily avoid resets. The lab deliberately uses a fully specified, database-and-role-scoped reset only after keeping measurements; it performs no unqualified global reset.

## Move from ranking to diagnosis

Take the leading candidate's query identity into an approved text/trace workflow. Confirm the affected operation, call amplification, parameters/data skew, locks and time window. Use EXPLAIN on representative safe inputs; EXPLAIN ANALYZE executes work and needs its own scope and safeguards.

Check whether the change came from more calls, more rows, more waiting or more work per call. A query that waited on a lock can dominate elapsed execution without needing a new index. Raising work_mem globally based on one temporary-I/O entry can multiply memory across concurrent operations.

After a bounded change, capture another compatible interval under comparable load. Confirm service latency/errors and correctness, not just a smaller mean in a warmed cache. Keep tuning, query-plan and application changes for their dedicated chapters.

## Acceptance and official references

Complete the linked lab: activate preloading, demonstrate literal normalization, rank seeded families by interval contribution, show that an execution failure is not a successful call, reject a selective-reset boundary and restore the original cluster startup.

- [PostgreSQL 18 pg_stat_statements](https://www.postgresql.org/docs/18/pgstatstatements.html)
- [Statistics collection and windows](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [Query identifier configuration](https://www.postgresql.org/docs/18/runtime-config-client.html)
- [pg_ctl startup and restart options](https://www.postgresql.org/docs/18/app-pg-ctl.html)
- [EXPLAIN execution semantics](https://www.postgresql.org/docs/18/sql-explain.html)

Next: Chapter 024 — Logs, Slow Statements and Correlation with Application Traces.
