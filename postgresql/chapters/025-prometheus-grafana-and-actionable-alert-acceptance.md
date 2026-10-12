# 025 — Prometheus, Grafana and Actionable Alert Acceptance

Audience: DBRE and SRE only. PostgreSQL 18 baseline.
Status: authored/static reviewed; live monitoring-stack verification pending.

[Previous: Logs and Traces](024-logs-slow-statements-and-correlation-with-application-traces.md) · [Hands-on acceptance lab](../labs/025-prometheus-grafana-and-actionable-alert-acceptance-lab.md) · [Master plan](../MASTER-PLAN.md)

## Operational outcome

Collect PostgreSQL telemetry through a restricted role, distinguish monitoring failure from database failure, build a dashboard that preserves unknown states, and prove that an actionable alert fires, reaches its intended test receiver and resolves.

A dashboard importing successfully does not establish monitoring coverage. A firing rule does not establish notification delivery. A delivered notification does not establish that its recipient can diagnose the incident.

## Establish the signal path

The lab uses PostgreSQL → postgres_exporter → Prometheus → Alertmanager → a local capture endpoint. Grafana queries Prometheus for visualization. Application SLIs, host/storage telemetry and logs are complementary sources rather than products of the exporter.

| Layer | Evidence | Failure distinction |
|---|---|---|
| PostgreSQL statistics access | Monitoring role can perform required reads | Permissions, tracking policy and version compatibility |
| Exporter HTTP scrape | Prometheus up metric | Reachability/HTTP collection path |
| Exporter database connection | pg_up | Successful exporter connection to its configured database |
| Exporter collection status | pg_exporter_last_scrape_error | Collection can fail even when a connection succeeds |
| Discovery/inventory | Expected target exists in the monitoring system | Removed targets can disappear instead of reporting zero |
| Rule evaluation | Pending/firing state with stable labels | Correct expression, continuity and evaluation health |
| Notification routing | Local receiver receives firing and resolved evidence | Routing, suppression and delivery are separate from evaluation |

up=1 means Prometheus successfully scraped the endpoint. It does not mean PostgreSQL can serve a consumer request. pg_up is an exporter connection observation, not Chapter 021's application availability SLI.

## Pin the collection contract

The lab targets postgres_exporter v0.20.1, verified against its tagged README/source. Record PostgreSQL minor, exporter, Prometheus/promtool, Alertmanager and Grafana versions. Keep rule tests alongside the configuration. Review metric names, labels and collector behavior before upgrading.

Do not assume a community dashboard matches your exporter version or enabled collectors. Inspect actual /metrics HELP/TYPE lines and Prometheus series. pg_stat_database_xact_commit is an internal cumulative counter; pg_stat_database_numbackends is a gauge. Custom exporter queries and flags can change coverage.

Version-aware defaults matter on PostgreSQL 18. Validate every enabled collector through its collection status and actual series. A syntactically valid scrape can still carry partial evidence. Never expose representative query text as a high-cardinality metric label merely to make a dashboard more descriptive.

## Use restricted access and bounded collection

Reuse the disposable lab_observer role with pg_monitor for the lab. Production should have a dedicated monitored account, approved permissions, CONNECT scope, secret rotation, TLS verification and network isolation. Some optional collectors need privileges beyond a basic role; assess them individually rather than granting superuser.

The lab supplies credentials using DATA_SOURCE_PASS_FILE supported by its pinned exporter. The URI contains no password. Its loopback-only listener and plaintext database connection are specific to Chapter 004's isolated local environment.

Set a collection deadline shorter than scrape_timeout, which must not exceed scrape_interval. The lab uses a five-second exporter deadline, ten-second scrape timeout and fifteen-second interval. Monitor collection duration and SQL overhead before applying that cadence fleet-wide.

Do not enable every table/index/query collector on every database by default. Cardinality grows with databases, objects, nodes and query families. Label service, environment, cluster and source deliberately; never use raw SQL, request IDs, trace IDs or parameter values as metric labels.

## Design a dashboard around questions

The [starter dashboard](../monitoring/025/grafana-dashboard.json) shows exporter reachability, database connection status, collection errors, internal transaction rates, connected backends and scrape duration. It does not fabricate a PostgreSQL latency histogram or application error rate.

Choose physical instance and database explicitly when comparing sources. Use units, legends, rate windows and UTC time ranges consistently. Add application good/total events and request latency histograms through a separately validated instrumentation contract.

For counters, apply rate before aggregating so individual resets are handled. Do not turn numbackends into a transaction rate or compute an application error ratio from rollbacks/commits. Rolled-back work can be expected behavior.

Display missing data as unknown. Avoid filling absent availability series with zero or one without a declared semantic reason. A panel showing no data should lead the operator to targets, collection health and inventory. Compare a panel with the raw query before declaring it trustworthy.

For tail latency, use a real histogram contract and correct bucket aggregation. Averaging database means or per-host p99s does not establish fleet p99. Chapter 021's good-event denominator remains necessary.

## Make alerts distinct and actionable

The [lab rules](../monitoring/025/rules.yml) separate five conditions: failed exporter scrape, failed database connection while exporter is reachable, partial collection error, missing pg_up while scrape succeeds, and disappearance of the known lab target. All are warning-level lab alerts; they are not universal production paging thresholds.

A target-specific absence rule works for one expected static endpoint. absent_over_time over a whole job does not detect one missing member while another remains. Production inventory needs per-target expected membership, reconciled with discovered/scraped targets.

The one-minute for clause requires the condition to persist across evaluations. It does not add one minute to the original incident with perfect timing: scrape/evaluation alignment, delivery grouping and missing samples matter. Test pending, sustained firing, recovery and a transient failure.

Use stable labels for alert identity and routing. Put the owner, severity, environment and cluster in labels; put explanation and runbook links in annotations. Changing a label can create a new alert identity and restart pending time. Do not place rapidly changing values or trace IDs in labels.

## Triage

| Alert | First checks | Intended next action |
|---|---|---|
| PgExporterScrapeFailed | Target error, process, HTTP path, network and scrape duration | Restore collection; assess application independently |
| PgDatabaseProbeFailed | Correct endpoint/role, secret, HBA/TLS and direct approved client path | Resolve connection cause without assuming server outage |
| PgCollectionError | Exporter logs, failed collector, permissions and schema/version | Repair collection and confirm all required metrics return |
| PgMetricMissing | Enabled metrics, exporter version and relabel/drop policy | Restore the declared metric contract |
| PgTargetMissing | Expected inventory versus discovery/configuration | Restore or document retirement of this exact target |

A connection alert during credential rotation calls for authentication diagnosis, not an immediate database restart. A scrape alert can reflect exporter failure while applications remain healthy. A collection error can conceal a dangerous condition; route it to the monitoring owner with explicit urgency.

For production paging, connect consumer SLO burn or imminent irreversible risk to a runbook and an owner. Disk exhaustion and transaction-ID risk may need independent preventive alerts even during low traffic. Avoid copying generic thresholds without workload evidence.

## Prove the alert lifecycle

The [promtool fixtures](../monitoring/025/rules.test.yml) cover healthy state, pending/firing distinction, transient failure, connection failure, missing metrics, collection failure, target absence and recovery. They test PromQL evaluation only when run with the actual matching promtool.

The lab then injects exporter unavailability and an invalid database account, preserving the real PostgreSQL service. Notification capture uses a loopback HTTP endpoint, not email/Slack/paging. Require firing and resolved records with the correct labels.

Alertmanager grouping, deduplication, silences and inhibition affect delivery. Review grouping keys, group_wait, group_interval, repeat_interval and send_resolved. A silence is an intentional notification boundary, not proof that evaluation stopped. Test production routes through approved test destinations before enabling paging.

The local receiver stores an allowlisted notification summary. It neither implements durable notification infrastructure nor verifies your real on-call escalation chain.

## Acceptance record and change control

Retain versions, effective metric/label inventory, validated configs, promtool output, target/rule states, dashboard evidence, local firing/resolved delivery and cleanup. Record measured detection/delivery time rather than promising an exact second.

Acceptance is incomplete if only the dashboard is green. Demonstrate no-data behavior, a useful runbook, intended routing, recovery and secret/process cleanup. Do not make telemetry loss disappear with a zero-fill transformation.

Manage rules and dashboards as reviewed artifacts. Re-run relevant unit and live acceptance tests after metric, label, discovery or routing changes. Keep deployment rollback separate from database intervention; a bad monitoring change should not require restarting PostgreSQL.

## Official references

- [Pinned postgres_exporter documentation](https://github.com/prometheus-community/postgres_exporter/blob/v0.20.1/README.md)
- [Prometheus scrape configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)
- [PromQL functions and absent/rate semantics](https://prometheus.io/docs/prometheus/latest/querying/functions/)
- [Alert rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [Rule unit tests](https://prometheus.io/docs/prometheus/latest/configuration/unit_testing_rules/)
- [Alertmanager routing](https://prometheus.io/docs/alerting/latest/configuration/)
- [Grafana dashboard import](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/import-dashboards/)
- [PostgreSQL monitoring roles](https://www.postgresql.org/docs/18/predefined-roles.html)

Next: Chapter 026 — Performance Triage and Evidence Collection.
