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
| 06 DR, backup, restore | Planned | Not started | Pending |
| 07 Index lifecycle and cleanup | Planned | Not started | Pending |

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

## Definition of done

These pages may be promoted from Draft to Approved only after DBRE, Application, Platform, Data Owner, Security and Change Management review the responsibilities relevant to their areas, staging validations pass, and a named document owner signs off. Never equate GitHub publication with production certification.
