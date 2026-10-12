# 70 — Alert Thresholds SLOs and Capacity Forecasting

Part 9 — Specialized Data and Observability

**Audience:** DBREs, SREs, Platform Engineers and service owners.  
**Goal:** Define measurable reliability objectives, evaluate actionable alerts and forecast resource headroom with explicit uncertainty.  
**Baseline:** MongoDB 8.0 / FCV 8.0 monitoring inventory from Chapter 69; Python 3.11+ for offline exercises. Exact monitoring/backend/exporter versions must be recorded before rule deployment. No Enterprise-only feature is exercised.  
**Status:** Written; offline SLO/alert/forecast helper checks complete; deployed monitoring and live capacity acceptance pending.  
**Prerequisites:** Chapters 24, 29, 49, 64 and 69; service ownership, monitoring coverage and recorded recovery/capacity budgets.  
**Estimated time:** 60–90 minutes offline, plus a separately scheduled monitoring acceptance drill.

## 1. Acceptance contract

An alert is useful when its signal is trustworthy, its owner can act, and the action can reduce user impact or prevent a foreseeable failure. A threshold copied from another deployment does not establish that contract.

This chapter's lab runs entirely offline. It calculates request-based error budgets, evaluates paired burn-rate windows, exposes low-volume/missing-data cases and projects storage/oplog headroom. It does not stop MongoDB, publish alert rules or send notifications.

Acceptance requires:

- An SLI specification with clear good/eligible events and measurement scope.
- Exact error-budget and burn-rate calculations for known fixtures.
- Alerts that require both recent and longer-window evidence.
- Separate handling of no traffic, missing coverage and low volume.
- A forecast that includes maintenance reserve, growth scenarios and remediation lead time.
- A rule owner, runbook, routing/recovery test and recorded rollout plan.

## 2. Define MongoDB-related SLIs

Measure user-visible operations from the application/client boundary. Database process counters describe work; they are not automatically eligible business requests. Chapter 69's server read mean cannot supply application P99.

| Objective | Eligible event | Good event | Measurement owner |
|---|---|---|---|
| Read reliability | Valid service read request | Successful correct response within agreed deadline | Application/service |
| Write reliability | Valid requested business mutation | Correct acknowledgement and application outcome within deadline | Application with DBRE review |
| Data freshness | Expected pipeline evaluation at a defined cadence | Materialized source position within agreed freshness bound | Pipeline owner |
| Recovery | Accepted recovery drill or incident | Verified recovery meets RPO/RTO and correctness contract | Recovery owner |

A timeout with an uncertain write outcome is not automatically a confirmed failed mutation. Define how the application counts retries, logical operations, validation errors, client cancellations and ambiguous acknowledgements. Report correctness separately when it cannot be measured directly in the request SLI.

For a combined latency/success SLI, good means both successful and within the deadline. Count each bad logical event once, even if it is both slow and erroneous. Alternatively keep distinct availability and latency SLIs; do not sum their error budgets.

Document exclusions before measuring. Do not exclude failed requests after the fact to make the SLO pass. Maintenance treatment, tenant/workload scope, reporting period and owners must be agreed in advance.

## 3. Error budget and burn rate

For target S, eligible events N and bad events B:

- Allowed bad events: `N × (1 − S)`.
- Observed bad fraction: `B / N`.
- Burn rate: `(B / N) / (1 − S)`.
- Budget consumed: `B / [N × (1 − S)]` over the same reporting scope.

The lab target is 99.9% good events over a 30-day reporting period. This is a teaching choice, not a default production MongoDB guarantee. With 1,000,000 eligible events, the budget is 1,000 bad events. If 400 are bad, 40% of that observed-period budget is consumed and 600 remain.

For request-based budgets, allowed bad events depend on actual eligible traffic. A projected exhaustion time assumes future traffic and error fraction. Under roughly stable traffic, a burn rate of 12 sustained for an hour consumes about `12 × 1 / 720 = 1.67%` of a 30-day budget. With strongly variable traffic, compute actual bad-event consumption instead of treating that time approximation as exact.

Use burn-rate windows to detect sustained significant degradation and a shorter window to establish that it is still occurring.[1] This chapter deliberately uses its own illustrative thresholds/windows. Review detection speed, reset behavior and traffic volume against the service's incident budget.

## 4. Alert classes and threshold ownership

| Class | Example | Expected response |
|---|---|---|
| User impact | Sustained request SLO burn | Page an owner able to mitigate impact |
| Data/recovery risk | Replication or CDC history headroom near exhaustion | Investigate before recoverability is lost |
| Capacity risk | Forecast crosses reserve before expansion can finish | Schedule/expedite remediation |
| Monitoring health | Expected member or SLI series stale | Restore measurement coverage |
| Diagnostic context | Cache occupancy, CPU or connection trend | Dashboard/runbook context unless actionable risk is established |

Do not page solely because WiredTiger cache occupancy is high. Evaluate application latency, eviction/read I/O, host pressure and workload. Similarly, high connection count needs configured limits, available headroom and client pool context.[2]

Each alert needs an owner, source metric, unit, labels, threshold rationale, evaluation cadence, firing/recovery behavior, notification route, escalation, runbook and expiry/review date. Record which user-impact alert it complements. Avoid simultaneous pages for every causal symptom of the same event.

Thresholds for lag, free disk and source-history headroom should derive from recovery objectives and response lead time. A universal “lag above X seconds” rule cannot distinguish tolerable analytical lag from loss of recovery history.

## 5. Lab A — executable SLO and paired-window evaluator

Create a fresh local `ch70-lab` directory and save the next Python blocks consecutively as `ch70_lab.py`. No credentials or network connection are needed.

The fixture uses already-aggregated event counts for each window. The recent window is contained in the longer window, so the evaluator checks subset consistency. Missing coverage remains an explicit state.

```python
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class Window:
    eligible: int
    bad: int
    complete: bool = True


def check(condition, message):
    if not condition:
        raise ValueError(message)


def validate(window):
    check(isinstance(window.eligible, int) and not isinstance(window.eligible, bool),
          "Eligible count must be an integer")
    check(isinstance(window.bad, int) and not isinstance(window.bad, bool),
          "Bad count must be an integer")
    check(0 <= window.bad <= window.eligible, "Invalid event counts")


def burn(window, target=0.999):
    check(isfinite(target) and 0 < target < 1, "Invalid SLO target")
    validate(window)
    if not window.complete:
        return None, "missing_coverage"
    if window.eligible == 0:
        return None, "no_traffic"
    return window.bad / window.eligible / (1 - target), "valid"


def paired_alert(long_window, short_window, threshold,
                 minimum_long, minimum_short, target=0.999):
    check(isfinite(threshold) and threshold > 0, "Invalid burn threshold")
    validate(long_window)
    validate(short_window)
    check(short_window.eligible <= long_window.eligible and
          short_window.bad <= long_window.bad and
          short_window.eligible - short_window.bad <=
          long_window.eligible - long_window.bad, "Recent window not a subset")
    long_burn, long_status = burn(long_window, target)
    short_burn, short_status = burn(short_window, target)
    if long_status != "valid" or short_status != "valid":
        return {"decision": "unavailable", "long_status": long_status,
                "short_status": short_status}
    if (long_window.eligible < minimum_long or
            short_window.eligible < minimum_short):
        return {"decision": "low_volume_review", "long_burn": long_burn,
                "short_burn": short_burn}
    return {"decision": "fire" if long_burn >= threshold and
            short_burn >= threshold else "clear",
            "long_burn": long_burn, "short_burn": short_burn}


def budget(window, target=0.999):
    validate(window)
    check(isfinite(target) and 0 < target < 1, "Invalid target")
    if not window.complete or window.eligible == 0:
        return {"status": "unavailable"}
    allowed = window.eligible * (1 - target)
    return {"status": "valid", "allowed_bad": allowed,
            "consumed_fraction": window.bad / allowed,
            "remaining_bad": allowed - window.bad}
```

The minimum-volume values below are illustrative. A low-volume gate can suppress a real outage; its fallback must be owned. Low-volume review is neither healthy nor an automatic page. Use reviewed synthetic probes and service-specific evidence where request traffic is sparse.

## 6. Lab B — incident, recovery, missing-data and noise drills

```python
# Example fast-impact pair: 1 hour and its last 5 minutes, burn threshold 12.
fast = paired_alert(Window(60000, 1200), Window(5000, 100), 12, 1000, 100)
check(fast["decision"] == "fire", "Sustained impact should fire")

# Longer window still contains the incident, but recent traffic has recovered.
recovered = paired_alert(Window(60000, 1200), Window(5000, 0), 12, 1000, 100)
check(recovered["decision"] == "clear", "Recent recovery should clear the pair")

# Short spike only: high recent burn without sustained longer-window burn.
spike = paired_alert(Window(60000, 100), Window(5000, 100), 12, 1000, 100)
check(spike["decision"] == "clear", "Short spike should not satisfy this pair")

# Low traffic must trigger a reviewed alternate decision, not a healthy state.
low_volume = paired_alert(Window(10, 1), Window(2, 1), 12, 1000, 100)
check(low_volume["decision"] == "low_volume_review", "Low volume lost")
no_traffic = paired_alert(Window(0, 0), Window(0, 0), 12, 1000, 100)
check(no_traffic["decision"] == "unavailable", "No traffic falsely healthy")
missing = paired_alert(Window(60000, 1200, False), Window(5000, 100), 12, 1000, 100)
check(missing["decision"] == "unavailable", "Missing coverage falsely healthy")

period_budget = budget(Window(1000000, 400))
check(abs(period_budget["allowed_bad"] - 1000) < 1e-8, "Budget arithmetic failed")
check(abs(period_budget["consumed_fraction"] - 0.4) < 1e-8, "Budget fraction failed")
check(abs(period_budget["remaining_bad"] - 600) < 1e-8, "Remaining budget failed")

for name, result in [("fast", fast), ("recovered", recovered), ("spike", spike),
                     ("low_volume", low_volume), ("no_traffic", no_traffic),
                     ("missing", missing), ("period_budget", period_budget)]:
    print(name, result)
```

Expected: fast fires; recovered and isolated spike clear this particular pair; low-volume requires review; no traffic/missing coverage are unavailable; the budget is 1,000 allowed, 400 consumed, 600 remaining. The spike can still deserve another reviewed fast-outage rule. One paired rule does not claim to detect every significant incident.

Add a slower pair if required, for example six hours and 30 minutes at an independently selected threshold. Test it against sustained lower degradation and recovery. Avoid copying thresholds between reporting periods without recalculating budget implications.

## 7. Monitoring-backend implementation contract

The Python evaluator is an offline reference, not a Prometheus rule file. Map it to the installed backend using actual application counters/histograms and reset-safe recording rules from Chapter 69.

| Input | Backend contract |
|---|---|
| Eligible events | Sum of eligible logical request increases within the scope/window |
| Bad events | Sum of bad logical request increases with the same scope/window |
| Latency events | Histogram bucket boundary exactly matches the agreed deadline, or explicit good counter |
| Coverage | Expected series present and fresh; collector/source health independently checked |
| Volume gate | Reviewed count/rate gate with documented low-volume fallback |
| Burn pair | Both longer and recent burn exceed the selected threshold |
| Deduplication | Page labels identify service/deployment/SLO, not request IDs |

Never average per-instance error ratios: aggregate bad and eligible counts first, then divide. Ratios with different denominators should not be combined. Do not clamp an empty denominator to a fake request count and label the SLI healthy.

Percentile panels help investigation, but an SLO fraction should count eligible events satisfying the deadline. A P99 series alone does not directly count monthly bad events. Histogram boundaries and aggregation must be reviewed against the actual instrumentation.

Shadow-evaluate rules before paging. Compare decisions to incidents, deployments, maintenance and low-volume intervals. Review expected pages per incident, reset delay and missed detection cases. Alert transport failures need independent visibility.

## 8. Capacity model — operational reserve before physical exhaustion

Measure a constrained member/volume individually; cluster totals can hide a full shard or skewed primary workload. Use physical allocated/free filesystem bytes for disk forecasting and distinguish them from logical collection sizes or reusable storage.

The lab model is:

`headroom = capacity − currently_used − maintenance_reserve`

`days_to_reserve = headroom / positive_daily_growth`

`required_capacity = used + growth × planning_days + reserve`

Reserve covers agreed maintenance work, index builds, recovery, temporary old/new copies and burst allowance. It is an explicit planning input, not an assumption that MongoDB needs the same fixed percentage everywhere.

With a 1,000 GiB volume, 700 GiB used, 150 GiB reserve and 10 GiB/day growth, reserve is reached in 15 days. A 30-day horizon needs 1,150 GiB under those assumptions. At 20 GiB/day, reserve is reached in 7.5 days and the horizon needs 1,450 GiB.

A forecast predicts when a modeled limit is crossed; it does not establish performance suitability. Disk IOPS/throughput and latency can become limiting before disk capacity. CPU, cache and network require representative workload and failure/load tests, not extrapolation from storage growth alone.

## 9. Lab C — storage forecast and lead-time risk

Append this code to `ch70_lab.py`. Inputs use GiB and days consistently. It handles flat/negative growth explicitly and validates stale inputs.

```python

def forecast(capacity_gib, used_gib, reserve_gib, growth_gib_day,
             horizon_days, lead_days, sample_age_hours, maximum_age_hours=24):
    values = (capacity_gib, used_gib, reserve_gib, growth_gib_day,
              horizon_days, lead_days, sample_age_hours, maximum_age_hours)
    check(all(isfinite(x) for x in values), "Nonfinite forecast input")
    check(capacity_gib > 0 and 0 <= used_gib <= capacity_gib, "Invalid capacity/use")
    check(0 <= reserve_gib < capacity_gib, "Invalid reserve")
    check(horizon_days > 0 and lead_days >= 0 and sample_age_hours >= 0 and
          maximum_age_hours >= 0, "Invalid time budget")
    if sample_age_hours > maximum_age_hours:
        return {"status": "stale_input"}
    headroom = capacity_gib - used_gib - reserve_gib
    # Negative growth is not credited as guaranteed future space reclamation.
    planning_growth = max(0, growth_gib_day)
    required = used_gib + planning_growth * horizon_days + reserve_gib
    if headroom <= 0:
        days = 0.0
        status = "reserve_breached"
    elif planning_growth == 0:
        days = None
        status = "no_positive_growth_review"
    else:
        days = headroom / planning_growth
        status = "lead_time_risk" if days <= lead_days else "planning"
    return {"status": status, "headroom_gib": headroom,
            "days_to_reserve": days, "required_capacity_gib": required,
            "planning_growth_gib_day": planning_growth}


normal = forecast(1000, 700, 150, 10, 30, 10, 1)
burst = forecast(1000, 700, 150, 20, 30, 10, 1)
flat = forecast(1000, 700, 150, 0, 30, 10, 1)
negative = forecast(1000, 700, 150, -5, 30, 10, 1)
stale = forecast(1000, 700, 150, 10, 30, 10, 48)
breached = forecast(1000, 900, 150, 0, 30, 10, 1)
check(normal["days_to_reserve"] == 15 and normal["required_capacity_gib"] == 1150,
      "Normal forecast failed")
check(burst["days_to_reserve"] == 7.5 and burst["status"] == "lead_time_risk" and
      burst["required_capacity_gib"] == 1450, "Burst scenario failed")
check(flat["days_to_reserve"] is None, "Flat growth falsely extrapolated")
check(negative["planning_growth_gib_day"] == 0, "Negative growth credited")
check(stale["status"] == "stale_input", "Stale forecast accepted")
check(breached["status"] == "reserve_breached", "Reserve breach missed")
for name, result in [("normal", normal), ("burst", burst), ("flat", flat),
                     ("negative", negative), ("stale", stale), ("breached", breached)]:
    print(name, result)
```

Run `python ch70_lab.py`. Expected: all SLO and capacity assertions pass; the burst scenario is a lead-time risk. Save outputs as synthetic evidence. A flat-growth result is not proof of unlimited future capacity.

Lead time should include investigation, approval/procurement, maintenance scheduling, expansion/rebalancing, validation and contingency. If forecasted reserve crossing occurs sooner, prioritize remediation even if current free-space percentage looks comfortable.

## 10. Estimate growth from real observations

Collect at least a representative business cycle from the actual constrained volume. Align timestamps, units, volume identity and restart/replacement history. Include recurring ingestion and retention jobs. Split trends at expansions, retention changes, bulk deletes, resharding and large backfills.

For two observations, growth is `(used2 − used1) / elapsed_days`. A two-point slope is only an initial estimate. For production use multiple windows, compare typical and adverse growth scenarios, and record uncertainty. Do not fit a line through an expansion step and treat it as workload demand.

Physical allocation may remain after TTL or deletion; it can be reused without shrinking the filesystem. Negative logical document growth does not guarantee physical free-space recovery. Review filesystem evidence and maintenance work before crediting reclaimed space.

Record baseline/adverse forecast dates, assumptions, model age and owner. Recalculate after operational changes. A capacity report without remediation lead time is not an actionable risk assessment.

## 11. Oplog, CDC and recovery headroom

Measure retained oplog time per relevant source member and compare it to secondary/CDC outage plus catch-up requirements. The oplog is a finite history boundary whose effective time span changes with write volume.[3] Configured byte size alone does not prove a fixed number of retained hours.

For a simplified CDC budget:

`required_history = maximum_outage + catchup_time + safety_margin`

`history_headroom = observed_retained_history − required_history`

If 18 hours are retained and the design requires 8 hours outage, 6 hours catch-up and 4 hours margin, headroom is zero. If a write surge reduces history to 10 hours, the design is short by 8 hours. Raise a recoverability-risk alert before a restart token becomes unusable.

Catch-up time depends on net drain rate. When source arrives at 100 events/s and the sink applies 200 events/s, a 360,000-event backlog takes about one hour to drain if those rates hold. If apply rate is at or below arrival rate, the backlog cannot shrink under that model. Verify actual BSON/event size, downstream materialization and sustained throughput.

Add an independent backup age and restore-test freshness signal. A healthy MongoDB process with expired recoverable history or an untested backup does not satisfy recovery objectives. Review source token/target recovery alignment from Chapters 64 and 67.

## 12. Production alert acceptance and rollout

| Drill | Expected decision/evidence |
|---|---|
| Sustained user degradation | Paired burn alert fires with measured delay and correct route |
| Recent recovery | Impact pair clears under documented reset semantics |
| Short spike | Its selected rule outcome matches the intended policy; other outage rules reviewed |
| Low volume/no traffic | Alternate review/probe path used; not silently declared healthy |
| Stale/missing metric | Monitoring-health signal and unavailable SLI |
| Storage growth burst | Adverse scenario crosses reserve before lead time and opens remediation work |
| Member/volume replacement | Trend segmented; historical data not assigned to new capacity |
| Lost history headroom | Recovery-risk signal includes rebuild/catch-up runbook |
| Alert transport failure | Independent routing/delivery test identifies the gap |
| Maintenance | Scope/time-bound suppression reviewed; user impact and monitoring health still visible |

Live rule and notification tests require the existing authorized test-monitoring environment and its routing owner. Do not send pages to production responders as an unannounced lab. This chapter does not deliver notifications; the offline exercise is complete without contacting anyone.

Start with shadow mode, review historical decisions, then enable an owned test route. Confirm grouping, escalation and resolved notifications before production routing. Keep rules/version history and a concrete rollback that disables only the new rule group. Do not disable the entire collector to roll back an alert.

## 13. Incident response and capacity decisions

User-impact pages should link the SLI scope/window, burn rates, recent changes, member/resource context and mitigation runbook. Capacity alerts should link the constrained volume, model inputs, adverse scenario, reserve date and lead-time owner.

Potential actions include reducing uncontrolled ingestion/concurrency, correcting expensive query patterns, bounding retries, expanding appropriate resources, rebalancing skew or fixing retention. Choose an action from observed bottleneck evidence. Adding CPU does not resolve a disk-throughput limit; larger storage does not guarantee higher I/O capacity unless the device configuration supports it.

Record the expected improvement and stop conditions before mitigation. Afterward verify application correctness/latency, resource trends, replication and recovery headroom. Avoid lowering thresholds or changing exclusions merely to make the alert disappear.

## 14. Troubleshooting

| Symptom | Evidence | Cause to test | Action and verification |
|---|---|---|---|
| Page storm for one incident | Labels, grouping and affected SLI | Duplicate symptom/routing rules | Group/inhibit appropriately; verify impact remains visible |
| High P99 but SLO looks healthy | Eligible/good counters and histogram boundary | Wrong deadline or missing requests | Repair instrumentation and recompute actual event fraction |
| Bad ratio changes when instances scale | Aggregation query and per-instance counts | Ratios averaged without weighting | Sum bad/eligible counts before division |
| Zero traffic appears green | Denominator and freshness | Missing/no-traffic coerced to zero errors | Expose unavailable status and alternate probes |
| Low-volume outage suppressed | Gate and test-route history | Volume policy lacks fallback | Add owned fallback; test representative sparse workload |
| Forecast jumps after expansion | Volume identity and change record | Structural step fitted as demand | Segment history and rebuild model |
| Delete job predicts unlimited headroom | Logical versus physical bytes | Reclamation assumed | Use observed filesystem allocation and adverse growth |
| Forecast stale but status green | Input timestamp and freshness budget | No model-age check | Reject stale input and assign refresh owner |
| CDC restart fails despite healthy lag | Token/history window and outage duration | Recovery history exhausted | Follow rebuild/reconciliation protocol; resize based on evidence |
| Alert fires but nobody receives it | Route/delivery acknowledgements | Notification failure | Restore route and independently retest delivery |

## 15. Acceptance packet, cleanup and review

| Item | Required evidence |
|---|---|
| SLI specification | Good/eligible definitions, deadline, scope, target, period and exclusions |
| Error budget | Known counts and exact expected fractions |
| Alert evaluator | Incident/recovery/spike/low-volume/no-traffic/missing cases |
| Capacity forecast | Reserve, growth scenarios, lead time, model age and expected outputs |
| Recovery headroom | Measured history and outage/catch-up assumptions |
| Production rollout | Rule mapping, shadow review, test route, owner/runbook and rollback |

The offline lab creates only local scripts/output in the owned directory; it changes no database or monitoring configuration. Retain the evidence according to the lab policy. Remove only that exact directory after reviewing its contents if no longer needed. Live test rules or routes require their recorded owners to restore prior configuration and verify coverage.

Review questions:

1. Why must logical retries be defined in an eligible-event contract?
2. Why are ratios aggregated from counts rather than averaged across instances?
3. What does the shorter burn window add to a longer-window alert?
4. Why does low-volume gating need a separate failure policy?
5. How can reserve crossing be urgent before physical disk exhaustion?
6. What assumptions can invalidate a linear capacity forecast?
7. Why is retained oplog time more useful than byte size alone for CDC recovery?
8. Which evidence proves alert delivery and monitoring freshness?

## 16. Official references and validation status

1. [Google SRE Workbook — Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/): burn-rate and multi-window concepts. Lab thresholds and fixtures are independently selected teaching choices.
2. [MongoDB 8.0 — Analyzing Performance](https://www.mongodb.com/docs/v8.0/administration/analyzing-mongodb-performance/): workload, resources and connection context.
3. [MongoDB 8.0 — Replica Set Oplog](https://www.mongodb.com/docs/v8.0/core/replica-set-oplog/): retained history and write-volume considerations.

Documentation reviewed on 2026-10-11. Python syntax and actual SLO/paired-window/forecast helper cases were executed offline, including invalid counts, unavailable traffic/coverage, reserve breach and stale input. No MongoDB workload, production metrics, monitoring rule publication, notification routing or live capacity remediation was executed.

**Chapter completion:** Written with offline calculation acceptance complete. Runtime/deployed monitoring validation remains pending until real metric mapping, shadow decisions, test routing and capacity evidence are recorded.

Previous: [Chapter 69 — Metrics Logs FTDC and Dashboard Design](69-metrics-logs-ftdc-and-dashboard-design.md).  
Next: Chapter 71 — Daily Administration and Maintenance Runbook.
