# PostgreSQL DBRE V03 — Monitoring, Alerting and Security Source Audit

**Review date:** 2026-11-01 UTC
**Disposition:** SOURCE REVIEW COMPLETE, RUNTIME AND SECURITY CERTIFICATION PENDING
**Scope:** Page 03 monitoring guide, current Community postgres_exporter upstream source, PostgreSQL predefined roles, Prometheus/Grafana alerting guidance.

## 1. Verified source findings

| Metric | Current upstream source | Finding |
|---|---|---|
| pg_stat_database_xact_commit | collector/pg_stat_database.go | Counter, datid/datname labels |
| pg_stat_database_xact_rollback | collector/pg_stat_database.go | Counter, datid/datname labels |
| pg_stat_database_deadlocks | collector/pg_stat_database.go | Counter, datid/datname labels |
| pg_database_size_bytes | collector/pg_database.go | Gauge, datname label; database collector must be enabled |
| pg_stat_activity_count | collector/pg_stat_activity.go | Gauge, state/backend_type plus user and application labels |
| pg_up | exporter/postgres_exporter.go | Exporter-provided database reachability/scrape gauge |
| pg_exporter_last_scrape_error | exporter/postgres_exporter.go | Exporter-side scrape error gauge |
| up | Prometheus | Prometheus-to-exporter scrape status; not proof of DB or application service health |

These source names match reviewed current upstream implementation, not independently observed production series. Metric name/labels/collectors/flags can vary with installed exporter version. The Community exporter namespace is pg. Exporter issue #1120 describes a scenario in which pg_up may falsely remain healthy on DB connection failure: test deployed version with real failure injection.

## 2. Documentation changes

| Finding | Resolution |
|---|---|
| Prometheus up was treated as only scrape health without DB differentiation | Added pg_up and an independent application/database probe requirement |
| Missing exporter series could silently produce no alert | Added unless-based pg_up absence check |
| Absent job is not identical to absent individual target | Added absent_over_time job-wide check and independent target inventory rule |
| Database size described as optional custom metric | Confirmed standard database collector metric pg_database_size_bytes |
| Active session count mixes backend types | Added backend_type=client backend filter to active count |
| No collector failure metric example | Added pg_exporter_last_scrape_error reference |
| Role grants underexplained | Recommended minimal monitoring role and differentiated pg_read_all_stats from broader pg_monitor |
| Potential PHI and identifying labels | Required restricted exporter endpoint, safe labels and secure secret handling |
| Unsafe universal critical thresholds | Only exporter health warnings in sample; no automatic destructive action |

## 3. Security and permissions

- Dedicated PostgreSQL monitoring connection and permitted database CONNECT.
- Test pg_read_all_stats first. pg_monitor grants broader read-all-settings and stat-scan-table monitoring capabilities.
- No superuser, pg_signal_backend, table write/DDL, file access or replication management permissions for routine exporter.
- Restrict TLS, secret stores, endpoint exposure (typically exporter port 9187), Grafana/Prometheus query access and logs.
- Audit stat_activity collector labels, which may contain usernames and application names; forbid PHI, patient identifiers and full SQL query text in labels/incident records.
- On managed RDS/Aurora, Azure Flexible Server and Cloud SQL, explicitly test provider-specific monitoring privileges and cloud metrics.
- A successful grant check does not prove scrapes, collector coverage or safe data classification.

## 4. Alerting design

Reference template: [V03-prometheus-alerts.example.yml](V03-prometheus-alerts.example.yml).

Five warning examples: exporter scrape failed, DB exporter scrape failed, pg_up missing, no targets in entire job, last exporter scrape error. The examples rely on job=postgres-exporter; replace with real deployment labels. They do not cover disappearance of ONE specific target while the job still has other targets; monitor expected target inventory separately. Prometheus does not automatically fire when a query returns no series.

Before use:
1. Confirm actual exporter version and /metrics HELP, TYPE and labels.
2. Run promtool check rules and promtool test rules in an authorized test environment.
3. Test all ten V03-T01 through V03-T10 negative/positive scenarios in Page 03.
4. Validate Alertmanager/Grafana on-call routing, silences, duplicate suppression and no-data states.
5. Cross-check client SLOs, pooler, OS/cloud disk, WAL, replication and backup monitors.
6. Obtain independent DBRE, PLT, APP and SEC review.

## 5. Monitoring role preflight

Read-only, execute only with an authorized test role:

~~~~sql
SELECT current_user AS monitor,
       current_database() AS db,
       pg_has_role(current_user, 'pg_read_all_stats', 'MEMBER') AS stats_member,
       pg_has_role(current_user, 'pg_monitor', 'MEMBER') AS monitor_member,
       pg_has_role(current_user, 'pg_signal_backend', 'MEMBER') AS signal_member;
~~~~

Check effective grants, role inheritance, network ACL, TLS and collector SQL separately.

## 6. Required test evidence

| ID | Scenario | Result |
|---|---|---|
| V03-T01 | Exporter scrape down | Pending |
| V03-T02 | DB unreachable while exporter up | Pending |
| V03-T03 | Expected pg_up missing | Pending |
| V03-T04 | Entire job disappears | Pending |
| V03-T05 | Single service-discovery target removed | Pending |
| V03-T06 | Collector disabled/permission denied | Pending |
| V03-T07 | Stats reset/restart and false-alert review | Pending |
| V03-T08 | PHI/user label policy and restrictions | Pending |
| V03-T09 | TLS/secret rotation and audit controls | Pending |
| V03-T10 | Client SLO and independent HA/PITR signals | Pending |

Each result must name cluster/provider, version, exporter build, role, timestamp, query, expected/actual alert firing and routing, security evidence, reviewer and link.

## 7. Verification limits

**Not performed:** no live database, Prometheus, Grafana, monitoring role, provider API or production alert change; no promtool execution or incident simulation. The YAML is only a source-reviewed example and has not been proven operational. No security or PHI certification was performed.

**V03 conclusion:** Documentation/source review published. Runtime, synthetic, alerts/no-data, role and security sign-offs still required.

## References

- [Prometheus Community postgres_exporter collector source](https://github.com/prometheus-community/postgres_exporter/tree/master/collector)
- [Exporter implementation and pg_up](https://github.com/prometheus-community/postgres_exporter/blob/master/exporter/postgres_exporter.go)
- [Exporter database permissions](https://github.com/prometheus-community/postgres_exporter/blob/master/docs/database-permissions.md)
- [PostgreSQL predefined roles](https://www.postgresql.org/docs/current/predefined-roles.html)
- [Prometheus alert rule syntax](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [Prometheus absent_over_time function](https://prometheus.io/docs/prometheus/latest/querying/functions/)
- [Grafana missing data](https://grafana.com/docs/grafana/latest/alerting/guides/missing-data/)
- [Upstream pg_up issue](https://github.com/prometheus-community/postgres_exporter/issues/1120)
