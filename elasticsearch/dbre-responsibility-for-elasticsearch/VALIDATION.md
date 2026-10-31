# DBRE Responsibility for Elasticsearch — Validation Register

**Status:** NOT CERTIFIED FOR PRODUCTION | **Last document update:** 2026-10-31

These pages are Confluence-ready drafts; they are not a record of live Elasticsearch, Prometheus, Grafana or incident tests.

| Milestone | Documentation | Live validation | Stakeholder approval |
|---|---|---|---|
| 01 Ownership and RACI | Drafted | Ownership inventory pending | Pending |
| 02 Operations cadence | Drafted | Staging APIs and initial operational review pending | Pending |
| 03 Monitoring, alerts, SLO | Drafted | Exporter/Prometheus/APM dashboard tests pending | Pending |
| 04 Incident troubleshooting | Drafted | Runbook staging/tabletop exercises pending | Pending |
| 05 Capacity, growth and costs | Drafted | Per-index collection, forecast validation and node-role staging load tests pending | Pending |
| 06 DR, backup, restore | Drafted | SLM scope, repository permissions, isolated restore, DR exercise and RPO/RTO verification pending | Pending |
| 07 Index lifecycle and cleanup | Drafted | Read-only discovery, owner mapping, ILM staging exercises and deletion-safety test suite pending | Pending |

## QA checklist

- [ ] Confirm current ES versions, providers, roles and node topology.
- [ ] Validate every API in staging with the intended monitoring role.
- [ ] Confirm exporter version, scrape flags and exact metric/label names.
- [ ] Validate PromQL with Prometheus and record missing/duplicate series.
- [ ] Instrument APP search P95/P99, errors and freshness using actual service metrics.
- [ ] Approve service SLO, RPO, RTO, warning and critical thresholds.
- [ ] Check safe handling of sensitive patient data in logs, labels and runbooks.
- [ ] Complete DBRE/APP/PLT/DATA/SEC/SM RACI sign-off.
- [ ] Test alert routing, exporter down and no-data cases.
- [ ] Run representative shard failure, heap pressure, disk pressure and restore exercises in staging.
- [ ] Establish actual index ownership and no-deletion-without-approval policy.
- [ ] Validate per-index primary/total store series, calendar-period index churn and export completeness.
- [ ] Review 30/60/90-day forecasts against actual node disk, watermarks and failure-domain reserve.
- [ ] Confirm representative peak-workload data and data/coordinator right-sizing test criteria.
- [ ] Record pre/post node specs, benchmark evidence, rollback exercise and cost outcomes.
- [ ] Verify snapshot SUCCESS state, shard/index/feature coverage and SLM completion.
- [ ] Verify one-writer/read-only DR repository, encryption and audited cloud IAM.
- [ ] Perform approved staging isolated restore and APP/DATA reconciliation.
- [ ] Measure business recovery data watermark, observed RPO and end-to-end RTO.
- [ ] Run controlled regional/full-cluster DR exercise including secure config/secret recovery.
- [ ] Classify all production index families by owner, app dependency, retention and legal holds.
- [ ] Confirm data-stream/alias write-index and feature/system index exclusions.
- [ ] Validate read-only weekly discovery report and telemetry coverage (no deletion API).
- [ ] Test dual-owner approval, changed index UUID, expired sign-off and wildcard rejection.
- [ ] Stage-test rollover and any separately approved ILM retention policies with recovery evidence.
- [ ] Verify Confluence Markdown rendering, internal links and navigation.
- [ ] Record exact version-specific caveats and unsupported lifecycle risk.

## Evidence table

| Check | Cluster/environment | Date (UTC) | Owner | Evidence URL | Result |
|---|---|---|---|---|---|
| API checks | TBD | TBD | TBD | TBD | Pending |
| Exporter label verification | TBD | TBD | TBD | TBD | Pending |
| SLO signal verification | TBD | TBD | TBD | TBD | Pending |
| Alert routing | TBD | TBD | TBD | TBD | Pending |
| Runbook exercise | TBD | TBD | TBD | TBD | Pending |
| Restore test | TBD | TBD | TBD | TBD | Pending |
| Per-index growth history and forecast | TBD | TBD | TBD | TBD | Pending |
| Right-sizing / failure test | TBD | TBD | TBD | TBD | Pending |
| Cost realization review | TBD | TBD | TBD | TBD | Pending |
| Snapshot policy, repository and retention coverage | TBD | TBD | TBD | TBD | Pending |
| Isolated restore and APP/DATA checks | TBD | TBD | TBD | TBD | Pending |
| Timed RPO/RTO/DR exercise | TBD | TBD | TBD | TBD | Pending |
| ILM/ownership and candidate discovery pilot | TBD | TBD | TBD | TBD | Pending |
| Retention approval and 15 deletion-safety tests | TBD | TBD | TBD | TBD | Pending |

## Definition of done

These pages may be promoted from Draft to Approved only after DBRE, Application, Platform, Data Owner, Security and Change Management review the responsibilities relevant to their areas, staging validations pass, and a named document owner signs off. Never equate GitHub publication with production certification.
