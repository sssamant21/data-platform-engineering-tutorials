# 024 — Logs, Slow Statements and Correlation with Application Traces

Audience: DBRE and SRE only. PostgreSQL 18 baseline.
Status: authored/static reviewed; PostgreSQL logging and client execution pending.

[Previous: Query Statistics](023-query-statistics-with-pg-stat-statements.md) · [Hands-on correlation lab](../labs/024-logs-slow-statements-and-application-traces-lab.md) · [Master plan](../MASTER-PLAN.md)

## Operational outcome

Find the server evidence for a slow or failed database operation, correlate it with an application span, and explain what each observation covers. Preserve source identity, timestamps and session context without turning query logs into an unrestricted store of application data.

A slow application request may spend its time waiting for a pool connection, establishing a connection, transferring results, executing SQL or retrying. A server duration measures a different boundary from the full request. A missing slow-log record does not prove that PostgreSQL was uninvolved.

## Identify the log path before searching

PostgreSQL can emit stderr, CSV, JSON, syslog and platform-specific destinations. CSV/JSON output requires logging_collector. Without it, stderr goes to the configured process supervisor, container stream or pg_ctl redirection. Do not assume pg_current_logfile points to a usable file when the collector is off.

Record physical source, database, destination, collection path, timezone and access boundary. pg_current_logfile('jsonlog') identifies a current collector file when that destination is active. current_logfiles tracks collector destinations; it is not an inventory of every external logging sink.

For production, verify delivery, rotation, disk capacity, retention, ingestion lag and access controls. Structured output simplifies parsing but does not guarantee central delivery. Logging throughput itself can become a bottleneck; collector backlog can affect server work.

The lab temporarily starts the disposable primary with JSON logging and a dedicated relative log directory. Existing configuration files are preserved and original Chapter 004 startup is restored afterward.

## Choose the event policy

| Setting | Evidence it controls | Important boundary |
|---|---|---|
| log_min_duration_statement | Completed statements at or above the threshold | -1 disables; 0 logs all; explicit units avoid ambiguity |
| log_min_duration_sample and log_statement_sample_rate | Sampled duration evidence | Samples cannot prove a complete request population |
| log_statement | Statement-category logging | Can expose SQL and increase volume; not a complete error audit |
| log_duration | Duration records for completed statements | Does not by itself include each statement's text |
| log_min_error_statement | SQL text associated with qualifying errors | Separate from completed slow-statement logging |
| log_lock_waits | Lock waits beyond deadlock_timeout | Threshold is related to deadlock checks, not an overall request deadline |
| Parameter-length settings | Bind values in supported normal/error records | Do not remove literals embedded in SQL or other diagnostic fields |

Choose thresholds from operational goals and volume, with an explicit temporary-investigation owner and expiry. Enabling all statements across a busy fleet is not a routine incident step. Check parameter context and privileges before deciding whether a change needs reload, restart or only a scoped session setting.

Duration thresholds override sampling for statements above the full-logging threshold. When statement-category logging and duration logging are combined, statement text and duration may appear in separate records; use session identity rather than searching for one convenient combined line.

Canceled and failed statements need error evidence. A query that fails before completion is not guaranteed to appear as a completed slow statement. Preserve the original SQLSTATE instead of interpreting a later failed-transaction error as the cause.

## Interpret protocol and time boundaries

In the extended protocol, Parse, Bind and Execute durations can be logged independently. A driver span may include those phases plus network and client handling. A simple-protocol psql demonstration is not proof of behavior in a production prepared-statement driver.

Use server timestamps with timezone and client monotonic durations. Wall-clock skew can move events outside a tight correlation window; define a small documented tolerance and monitor clock health. Do not manufacture causality by widening a window until some query matches.

A 900 ms database client span and a 700 ms server execution record do not prove precisely 200 ms of network delay. Pooling, protocol phases, instrumentation boundaries, scheduling, result processing and clock precision all matter. First locate the span boundaries and compare operations on the same connection.

Result consumption may extend beyond server-side completion depending on protocol, driver and query behavior. Large result sets and a slow consumer can create a client-visible problem even when the SQL plan appears reasonable.

## Build the correlation contract

| Identity | Use | Limitation |
|---|---|---|
| Verified physical source | Select the right node and epoch | An endpoint can route to different nodes |
| Database and service application_name | Narrow the workload | application_name is client supplied, not authenticated identity |
| PID with session_id / backend start | Match one server session | PID alone can be reused |
| Query identifier | Connect query family evidence | Not one invocation, trace ID or permanent application identifier |
| Trace ID and span ID | Follow one logical operation and its attempts | PostgreSQL does not automatically attach distributed trace context |
| SQLSTATE and attempt number | Explain outcome/retry behavior | One logical request can produce multiple attempts |

For text logs, a reviewed log_line_prefix can include timestamp, PID, session, service, database, SQLSTATE and query identifier. JSON logs expose structured equivalents such as session_id, state_code, application_name and query_id. Query IDs require computation; statement-category logs can be emitted before one is calculated and may show zero.

Capture backend identity from the connection actually used for the operation. A separate health-check connection's PID is not the worker's PID. With transaction-pooling middleware, logical client connections may use different backends across transactions; record mapping at the relevant scope.

Production instrumentation should carry trace/span context in application telemetry and map it to database session/query evidence. OpenTelemetry database spans provide a common vocabulary, but the exact boundaries and attributes depend on the instrumentation version and driver. Verify what your stack emits rather than assuming every client has the same fields.

If a request temporarily changes application_name, scope and restore it correctly. SET LOCAL inside an explicit transaction can limit lifetime; session SET can leak across pooled requests. Pool checkout/reset and transaction-pooling behavior must be tested. Never use high-cardinality trace IDs as Prometheus labels.

## Protect sensitive content at collection time

SQL logs can expose literals, customer values, schema details, error diagnostics and parameter data. Setting log_parameter_max_length and its error counterpart to zero limits supported bind-value logging; it does not sanitize query text, messages, detail, context or utility statements.

Prefer parameterized application SQL, reviewed logging policy, restricted raw-log access and short retention appropriate to the incident. Statement normalization in pg_stat_statements is not a substitute for log controls. Sanitization after shipping does not undo exposure in the raw source.

The [lab summarizer](../scripts/024-correlate-json-logs.py) exports only allowlisted identity, timing and error-code fields. It discards statement/message/detail/context text from output. It still reads raw restricted logs; it is not a sanitizer for the source files or a general security filter.

## Use logs with statistics and traces

Start from the affected request or operation class. Inspect its database span outcome and attempts. Locate the physical node and recorded session, then review server events in the same interval. Correlate waits with Chapter 020's blocking evidence and aggregate families with Chapter 023's query statistics.

Distinguish these findings:

- A completed slow statement with matching identity explains measured server elapsed work.
- A timeout error with matching identity establishes a server-side cancellation event.
- A long span without a matching record may reflect thresholds, sampling, dropped delivery, connection failure or work outside the logged boundary.
- Several attempts in one trace can amplify database load even if one final attempt succeeds.

A sampled set of slow records cannot calculate an unbiased p99 or availability denominator. Use request counters/histograms and trace sampling knowledge for service SLIs. A query-text substring is a weak correlation key and can mix services, sessions and parameter variants.

Avoid attributing elapsed time to CPU, storage or locking without supporting evidence. A sleep in this lab is deliberately slow but has no expensive query plan. Production diagnosis needs waits, resource signals and representative-plan analysis.

## Verify delivery and operational usefulness

Acceptance for a logging change includes a known synthetic event arriving at the approved destination, correct timezone/source identity, a recoverable session join, measured ingestion delay and reviewed exposure. Test malformed/partial records, duplicate delivery and unknown future JSON fields.

Keep the raw event and the extracted summary linked through source/session/line identity. Record missing matches and ambiguity; do not choose a convenient match silently. Recovery evidence should show the application outcome, database evidence and return of the relevant latency/error signal.

The lab generates a fast success, slow success and timeout using fresh dedicated sessions. Its trace-shaped JSON is an educational client record, not an OpenTelemetry SDK export or a production pool simulation. Offline parser checks do not verify actual PostgreSQL delivery.

## Official references

- [PostgreSQL 18 logging settings and JSON fields](https://www.postgresql.org/docs/18/runtime-config-logging.html)
- [Frontend/backend protocol flow](https://www.postgresql.org/docs/18/protocol-flow.html)
- [Activity/session metadata](https://www.postgresql.org/docs/18/monitoring-stats.html)
- [SET and SET LOCAL](https://www.postgresql.org/docs/18/sql-set.html)
- [OpenTelemetry database client spans](https://opentelemetry.io/docs/specs/semconv/db/database-spans/)
- [pg_ctl startup/restoration behavior](https://www.postgresql.org/docs/18/app-pg-ctl.html)

Next: Chapter 025 — Prometheus, Grafana and Actionable Alert Acceptance.
