# 72 — Cost Optimization and Enterprise License Planning

Part 9 — Specialized Data and Observability

**Audience:** DBREs, SREs, Platform Engineers, FinOps and procurement owners.  
**Goal:** Build a complete cost baseline, evaluate savings without weakening service/recovery requirements, and assemble an evidence-based Enterprise entitlement and renewal packet.  
**Baseline:** MongoDB 8.0 / FCV 8.0 inventory from Chapters 60–71; Python 3.11+ for offline cost exercises; exact recorded mongosh for the optional read-only inventory. Enterprise feature/entitlement review uses the organization's actual contract and authorized records.  
**Status:** Written; executable offline cost/acceptance checks complete; actual billing, entitlement and candidate deployment validation pending.  
**Prerequisites:** Chapters 4, 17–24, 41–62 and 69–71; service SLOs, RPO/RTO, capacity reserve, resource inventory and cost ownership.  
**Estimated time:** 60–90 minutes offline; contract and production candidate review are separate owned activities.

## 1. Optimization acceptance contract

An optimization is accepted when the measured economic benefit is real, its service and recovery requirements pass, and the implementation has an owned reversal/recovery path. Lower monthly compute charges alone are not sufficient evidence.

This chapter's core lab is offline. It models a synthetic three-node deployment, compares a cheaper compute candidate, includes implementation cost and labor, and blocks acceptance when performance, recovery or entitlement evidence is missing. The optional MongoDB inventory is read-only. No resources are resized, licenses changed, data deleted or external messages sent.

Acceptance requires:

- A cost baseline with currency, period, source, allocation and uncertainty.
- Separate recurring run cost, one-time implementation cost and realized savings.
- A candidate that preserves the declared topology/service/recovery contract.
- Rejected invalid inputs and blocked candidates with unknown entitlement or failed acceptance.
- Actual inventory mapped to the applicable commercial terms by the contract owner.
- A renewal forecast covering growth, temporary migrations and recovery environments.

All rates in the Python fixture are fictional planning inputs. They are not cloud prices, MongoDB quotes or statements of a license billing metric.

## 2. Establish the full cost boundary

| Cost area | Baseline evidence | Common omission |
|---|---|---|
| Compute | Actual instance/node allocation, runtime and effective billed rate | Idle/nonproduction instances and shared node allocation |
| Storage | Provisioned capacity, performance tiers and throughput/IOPS charges | Additional performance charges and temporary migration copies |
| Backup | Retained snapshots/objects, requests, retrieval and restore capacity | Restore drills and cross-region copies |
| Network | Intra/inter-zone, region and outbound transfer by billing category | Replication, backups and downstream movement |
| Management/monitoring | Ops Manager infrastructure, agents, logs/metrics and monitoring services | Management database and retention cost |
| Subscription/support | Signed order/contract and approved allocation | Assumed discounts, renewal changes and optional add-ons |
| Operations | Measured engineering toil and loaded labor rate | Incident work and maintenance effort |
| Change | Migration, performance/failover tests and dual-run period | One-time work omitted from payback |

Use consistent currency and period. Record whether rates are list, effective billed, committed or negotiated. Allocate shared infrastructure with a declared rule, such as reserved resources plus agreed shared overhead. Report unallocated cost rather than attributing the entire shared host to one database.

Separate cash invoices from internal labor estimates. The lab combines them into an economic run-cost model and also reports direct spend. Do not claim that reducing staff effort creates an immediate reduction in the cloud invoice.

## 3. Evidence before selecting a candidate

Collect a representative business cycle using Chapters 69–70. Include peak traffic, batch ingestion, restore/recovery activity, member failure and growth. Idle CPU in a quiet interval is not proof that the node can be downsized.

Record current topology, memory/cache, disk latency/IOPS/throughput, network, replication/history headroom, client concurrency and application latency/error objectives. The capacity boundary may be storage rather than CPU.[1]

| Candidate | Evidence to obtain | Acceptance risk |
|---|---|---|
| Query/schema improvement | Correctness, examined work, latency and index/write impact | Different result semantics or workload regression |
| Remove redundant index | Full-cycle usage and all query/constraint/TTL dependencies | Missing rare query or uniqueness/retention requirement |
| Retention/archive policy | Data owner, retrieval/recovery and compliance requirements | Irrecoverable deletion or archive access failure |
| Compute change | Peak/failure-mode load, memory, networking and disk limits | Latency/replication regression under failure |
| Storage tier/performance change | Device limits and sustained/burst I/O evidence | Lower capacity price with unacceptable I/O latency |
| Nonproduction schedule | Required availability, retained state and restart acceptance | Lost test data or unavailable required environment |
| Automation/toil reduction | Measured hours and actual ownership transfer | Hidden support work or broken recovery procedure |

Preserve the declared redundancy and recovery objectives. Replacing a data-bearing secondary with an arbiter changes redundancy and recovery behavior; it is not an equivalent cost-only change. Removing a member or backup to reduce cost requires a new architecture/risk contract, not acceptance under the old baseline.

## 4. Read-only MongoDB inventory

Connect using Chapter 42's verified TLS/SCRAM observer identity. Gather exact build/edition, topology and configured resource context without printing full secrets-bearing configuration.

```javascript
var admin = db.getSiblingDB("admin");
var build = admin.runCommand({ buildInfo: 1 });
if (build.ok !== 1) throw new Error("Build inventory failed");
printjson({ observedAt: new Date(), version: build.version, modules: build.modules,
            architecture: build.bits, hello: db.hello() });
var status = admin.runCommand({ serverStatus: 1 });
if (status.ok !== 1) throw new Error("Process inventory failed");
printjson({ host: status.host, process: status.process, uptime: status.uptime,
            cache: status.wiredTiger && status.wiredTiger.cache && {
              configuredBytes: status.wiredTiger.cache["maximum bytes configured"],
              usedBytes: status.wiredTiger.cache["bytes currently in the cache"]
            } });
```

Map this member to actual VM/Kubernetes requests/limits, allocated storage, device performance and billing resource IDs. Repeat for the declared deployment scope. A binary module inventory is technical evidence; it does not prove entitlement or support coverage.

For one already authorized business namespace, inspect index sizes/options and process-local usage evidence:

```javascript
var inventoryDb = db.getSiblingDB("your_recorded_database");
var inventoryCollection = inventoryDb.getCollection("your_recorded_collection");
printjson(inventoryCollection.getIndexes());
printjson(inventoryCollection.aggregate([{ $indexStats: {} }]).toArray());
```

Replace both placeholders with the approved scope before executing. Record process uptime and observation start. Zero usage on one member over a short period is not proof that an index is unused across all workloads. A hidden index remains maintained and consumes resources; hiding is a reversible planner experiment, not immediate index-storage savings.[2] Review Chapter 71's hide/restore lab before any change.

## 5. Lab A — complete fictional monthly cost model

Create a fresh local `ch72-lab` directory. Save Sections 5–7 consecutively as `ch72_cost.py`; no packages beyond Python's standard library and no credentials are required.

The model describes three identically priced data nodes. Storage quantities are aggregate billed quantities for this scope, already including the modeled copies. Do not multiply them by replica count again.

```python
from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP


D = Decimal


def require(condition, message):
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True)
class CostInputs:
    nodes: int
    hours_per_node: Decimal
    compute_rate_per_hour: Decimal
    storage_gib_month: Decimal
    storage_rate: Decimal
    backup_gib_month: Decimal
    backup_rate: Decimal
    network_gib: Decimal
    network_rate: Decimal
    monitoring_month: Decimal
    subscription_month: Decimal
    labor_hours_month: Decimal
    labor_rate: Decimal
    currency: str = "USD"


def cost(inputs):
    require(isinstance(inputs.nodes, int) and not isinstance(inputs.nodes, bool)
            and inputs.nodes > 0, "Invalid node count")
    require(inputs.currency == "USD", "Fixture currency mismatch")
    values = [value for key, value in vars(inputs).items()
              if key not in {"nodes", "currency"}]
    require(all(isinstance(value, Decimal) and value.is_finite() and value >= 0
                for value in values), "Use nonnegative finite Decimal inputs")
    require(inputs.hours_per_node > 0, "Runtime must be positive")
    components = {
        "compute": inputs.nodes * inputs.hours_per_node * inputs.compute_rate_per_hour,
        "storage": inputs.storage_gib_month * inputs.storage_rate,
        "backup": inputs.backup_gib_month * inputs.backup_rate,
        "network": inputs.network_gib * inputs.network_rate,
        "monitoring": inputs.monitoring_month,
        "subscription": inputs.subscription_month,
        "labor": inputs.labor_hours_month * inputs.labor_rate,
    }
    direct = sum(value for key, value in components.items() if key != "labor")
    return {"components": components, "direct_spend": direct,
            "economic_run_cost": direct + components["labor"]}


def comparison(before, after, implementation_cost, transition_cost):
    require(before.currency == after.currency, "Mixed currencies")
    for value in (implementation_cost, transition_cost):
        require(isinstance(value, Decimal) and value.is_finite() and value >= 0,
                "Invalid one-time cost")
    baseline, candidate = cost(before), cost(after)
    savings = baseline["economic_run_cost"] - candidate["economic_run_cost"]
    upfront = implementation_cost + transition_cost
    return {"monthly_economic_savings": savings,
            "monthly_direct_savings": baseline["direct_spend"]-candidate["direct_spend"],
            "upfront_cost": upfront,
            "payback_months": upfront / savings if savings > 0 else None,
            "first_year_net_benefit": savings * 12 - upfront}


baseline = CostInputs(
    nodes=3, hours_per_node=D("730"), compute_rate_per_hour=D("0.80"),
    storage_gib_month=D("3000"), storage_rate=D("0.10"),
    backup_gib_month=D("600"), backup_rate=D("0.04"),
    network_gib=D("100"), network_rate=D("0.09"),
    monitoring_month=D("100"), subscription_month=D("1200"),
    labor_hours_month=D("20"), labor_rate=D("75"),
)
candidate = replace(baseline, compute_rate_per_hour=D("0.65"))
base_cost = cost(baseline)
new_cost = cost(candidate)
result = comparison(baseline, candidate, D("900"), D("0"))
require(base_cost["economic_run_cost"] == D("4885.00"), "Baseline mismatch")
require(base_cost["direct_spend"] == D("3385.00"), "Direct spend mismatch")
require(new_cost["economic_run_cost"] == D("4556.50"), "Candidate mismatch")
require(result["monthly_economic_savings"] == D("328.50"), "Savings mismatch")
require(result["first_year_net_benefit"] == D("3042.00"), "Year-one benefit mismatch")
print("baseline", base_cost)
print("candidate", new_cost)
print("comparison", result)
print("payback_months_rounded", result["payback_months"].quantize(
    D("0.01"), rounding=ROUND_HALF_UP))
```

Expected economic run costs: USD 4,885.00 before and USD 4,556.50 after; direct baseline spend USD 3,385.00; recurring savings USD 328.50/month; USD 900.00 one-time work; approximately 2.74 months payback; year-one net benefit USD 3,042.00. The rates and USD 1,200 subscription input are entirely fictional.

The 730-hour month is a planning convention. Use actual billing/calendar periods for reconciliation. The hypothetical candidate preserves all other quantities and subscription terms for arithmetic comparison; verify those assumptions before using a real quote.

## 6. Lab B — savings uncertainty and regressions

A cheaper resource can increase labor or require more storage/IOPS. Model those changes instead of holding them implicitly at zero.

```python
# Extra toil cancels the apparent compute saving.
toil_candidate = replace(candidate, labor_hours_month=D("26"))
toil_result = comparison(baseline, toil_candidate, D("900"), D("0"))
require(toil_result["monthly_economic_savings"] == D("-121.50"), "Toil effect missed")
require(toil_result["payback_months"] is None, "Negative savings got a payback")

# A dual-run month is a separate transition charge, not recurring steady-state savings.
transition_result = comparison(baseline, candidate, D("900"), D("1000"))
require(transition_result["upfront_cost"] == D("1900"), "Transition cost omitted")
require(transition_result["first_year_net_benefit"] == D("2042.00"),
        "Transition year-one arithmetic failed")

# Unknown license cost is not encoded as zero: obtain evidence or leave the estimate pending.
try:
    cost(replace(baseline, subscription_month=None))
except ValueError:
    pass
else:
    raise AssertionError("Unknown subscription silently accepted")
print("toil_regression", toil_result)
print("dual_run", transition_result)
```

Expected: direct compute savings still exist in the toil case, but economic run cost increases. A no-payback result is an explicit outcome, not a division error. Savings estimates must include engineering work and transition overlap under the actual chosen boundary.

For real proposals, calculate baseline/adverse cost scenarios for effective rate, workload growth, additional performance capacity, subscription changes and labor. Report a range and assumption owner rather than false precision from a single nominal rate.

## 7. Lab C — acceptability and entitlement gate

The economic comparison is independent of technical/commercial acceptance. This gate blocks a proposal when reviewed evidence is missing or failed. Its booleans represent a completed owned review, not a license-compliance scanner.

```python
@dataclass(frozen=True)
class CandidateEvidence:
    service_accepted: bool
    peak_and_failure_load_accepted: bool
    redundancy_accepted: bool
    recovery_accepted: bool
    capacity_reserve_accepted: bool
    security_accepted: bool
    entitlement_verified: bool
    rollback_verified: bool


def acceptance(evidence, comparison_result):
    reasons = []
    for field, accepted in vars(evidence).items():
        require(isinstance(accepted, bool), "Acceptance evidence must be explicit boolean")
        if not accepted:
            reasons.append(field)
    if comparison_result["monthly_economic_savings"] <= 0:
        reasons.append("no_positive_recurring_economic_savings")
    return {"decision": "candidate_for_owned_rollout" if not reasons else "blocked",
            "reasons": reasons}


accepted = CandidateEvidence(True, True, True, True, True, True, True, True)
require(acceptance(accepted, result)["decision"] == "candidate_for_owned_rollout",
        "Accepted candidate blocked")
for name in vars(accepted):
    evidence = replace(accepted, **{name: False})
    gate = acceptance(evidence, result)
    require(gate["decision"] == "blocked" and name in gate["reasons"],
            "Missing evidence did not block candidate")
    print(name, gate)
require(acceptance(accepted, toil_result)["decision"] == "blocked",
        "Negative economic saving accepted")
print("PASS: complete evidence accepted; missing evidence and negative saving blocked")
```

Run `python ch72_cost.py`. Expected: all cost arithmetic and gate assertions pass. No approved pricing, entitlement or deployment evidence is created by running the offline fixture. A real candidate remains pending until its actual acceptance packet exists.

## 8. Enterprise inventory and entitlement packet

Enterprise Advanced is a commercial subscription offering with Enterprise Server, management/security capabilities and support; optional offerings can have distinct terms.[3] Product documentation describes features, but your signed order, applicable agreement and verified entitlement records define the purchased scope.

Do not infer a per-vCPU, per-core, per-node or per-cluster billing rule from this tutorial. Do not assume nonproduction, passive secondary, disaster recovery, ephemeral replacement or temporary migration resources are free/excluded. Obtain an explicit answer under the actual contract.

| Inventory field | Required evidence/owner |
|---|---|
| Legal/customer entity | Contract/order owner and applicable entity scope |
| Deployment | Environment, topology, hosting account/region and resource IDs |
| Software | Edition, exact server/FCV, operator/agent/Ops Manager versions |
| Used capabilities | Auditing, encryption, external auth, management/backup and any optional add-ons |
| Resource footprint | Recorded contractual measurement inputs as defined by the actual agreement |
| Lifecycle | Steady state, failover/DR, nonproduction, replacement and migration overlap |
| Entitlement | Applicable purchased scope, covered features/environments and verification reference |
| Support | Purchased support scope, response terms and contact/escalation owner |
| Renewal | Expiry/renewal notice dates, growth forecast, lead time and accountable owner |
| Exceptions | Unresolved scope questions and required procurement/vendor clarification |

A node inventory must map actual deployments to entitlement evidence, not just count processes. Record both intended and running resources, including stale/temporary environments. Reconcile infrastructure inventory, automation/CMDB, billing and contract records at a declared point in time.

Keep contract documents and license-sensitive records under appropriate access control. The technical chapter should store a reference and status, not reproduce confidential commercial terms. Use procurement/contract owners for interpretation of ambiguous rights or terms.

## 9. Renewal and growth planning

Build the renewal packet early enough for procurement, negotiation and deployment validation. Include current verified footprint and forecast changes from Chapter 70:

- Expected data/workload growth and required resource changes.
- New environments and added operational/security features.
- Temporary old/new deployments during upgrades or migration.
- DR/restore-test resources and replacement-member overlap.
- Support requirements and observed incident/operational needs.
- Retired resources whose removal has been verified.

Compare scenarios under the same service, security and recovery objectives. A migration from Enterprise to Community or another hosting model must review feature dependencies, commercial terms, supported operations, automation, backup and migration/recovery behavior. Changing a package label does not preserve those contracts automatically.

Public feature descriptions and marketing examples do not replace the exact installed-version compatibility checks from Chapters 43, 45, 57–60 and 62. Review add-ons separately rather than assuming every current product feature is included in the existing subscription.

## 10. Optimization experiment and rollout

| Stage | Evidence | Stop condition |
|---|---|---|
| Baseline | Actual cost allocation and representative service/resource measurements | Missing cost/metric coverage |
| Proposal | One concrete change, expected saving, uncertainty and entitlement scope | Unknown commercial or technical dependency |
| Lab/canary | Correctness, peak demand, failover, backup/restore and candidate limits | Any required contract fails |
| Change packet | Authoritative config/IaC, owner, duration, reversal and observation window | No usable recovery path |
| Controlled rollout | One accepted scope/member stage at a time as architecture requires | Lag, latency, errors or reserve exceed agreed limits |
| Acceptance | Post-change service/capacity/recovery and billing evidence | Saving only modeled, not yet realized |
| Follow-up | Actual invoices/allocation, toil and renewal footprint | Unexpected charges or displaced risk |

Use the Chapter 71 maintenance gates and authoritative operator/IaC owner. Do not manually resize an operator-managed deployment and assume the setting will persist. For storage decreases, verify whether the platform supports shrinking; a migration to a new volume may be required.

A smaller primary or secondary must be evaluated under the role it may assume after failover. Testing only secondary idle load does not establish primary suitability. Keep disk/network performance limits in the candidate inventory; cheaper compute families can change them.

Reversal may be a configuration restoration before new writes, but capacity/storage migrations need a data-consistency recovery plan. Budget temporary dual-run resources rather than attempting an unsafe in-place shortcut to preserve nominal savings.

## 11. Realized savings and ongoing unit economics

After a complete comparable billing period, reconcile candidate resources to actual charges and effective rates. Normalize workload volumes only under a documented method; a quieter month can appear cheaper without an optimization.

Useful unit measures include cost per successful eligible operation, cost per retained GiB and engineering hours per accepted maintenance/recovery cycle. Each needs the same allocation scope and denominator. A lower cost per stored GiB can still hide worse application latency or lost recovery capability.

Report:

| Measure | Interpretation |
|---|---|
| Modeled recurring saving | Forecast under declared assumptions |
| Actual direct saving | Comparable billed/allocation reduction |
| Economic saving | Direct reduction plus verified labor change |
| Implementation/transition cost | One-time work, overlap and testing |
| Service/recovery acceptance | Conditions that make the saving acceptable |
| Contract footprint | Verified entitlement/renewal impact |

Retire old resources only after the new deployment's acceptance and recovery retention period. Confirm deletion/deallocation in inventory and subsequent billing. Data deletion alone may not reduce provisioned storage charges or allocated filesystem bytes.

## 12. Failure exercises and troubleshooting

| Symptom | Evidence | Cause to test | Corrective action and verification |
|---|---|---|---|
| Quote cheaper but invoice unchanged | Resource IDs, effective rates and commitments | Unreleased allocation or fixed commitment | Reconcile billable retirement and allocation; revise realized savings |
| Lower compute cost, higher latency | Failure/peak workload, cache and storage limits | Candidate constrained outside idle baseline | Stop rollout; restore/recover accepted capacity and revalidate |
| Index hidden but storage unchanged | Index inventory and size | Hidden index still maintained | Treat hiding as planner experiment; separately review dropping |
| Retention reduction does not cut disk bill | Provisioned capacity, allocation and deletion history | Billing/physical storage not tied to row count | Verify actual reclaim/deallocation path; preserve recovery |
| Cost model shows huge savings | Replication/copy scope and shared allocation | Double-counted baseline or omitted candidate costs | Correct quantities and uncertainty; rerun arithmetic |
| Unknown subscription entered as zero | Contract evidence and model inputs | Missing quote represented as free | Leave proposal pending; obtain verified input |
| DR or migration overlaps omitted | Lifecycle/resource inventory and contract terms | Only steady-state scope counted | Include actual temporary scope and verify entitlement |
| Toil increases after downsizing | Engineering hours and incident/maintenance record | Apparent savings shifted to labor | Update economic comparison; reject unfavorable candidate |
| Renewal misses new features | Feature usage and add-on/order evidence | Product capability assumed included | Review actual entitlement with responsible owner |
| Community migration breaks controls | Security/backup/automation dependency inventory | Edition change treated as package swap | Rebuild and accept equivalent required controls before routing change |

For the offline failure lab, the toil regression and unknown subscription cases are exercised automatically. Live latency regression, bill reconciliation and commercial coverage cases remain pending until actual environment evidence exists.

## 13. Acceptance record, cleanup and review

| Check | Required evidence |
|---|---|
| Baseline | Currency/period, rates, quantities, allocation and bill/contract references |
| Arithmetic | 4,885.00 baseline; 4,556.50 candidate; 328.50 recurring saving; 2.74-month modeled payback |
| Failure cases | Toil regression has negative economic saving; unknown input rejected |
| Candidate gate | Every required acceptance field passes; missing fields block |
| Inventory/entitlement | Actual resources/features/lifecycle mapped to verified commercial scope |
| Renewal plan | Dates, forecast, overlaps, support needs and owner |
| Rollout/realization | Controlled technical acceptance and comparable actual cost period |

Record passed, failed or not run for each item. The offline lab writes no database data, resizes no resources and changes no entitlement. Retain local script/output in the exact owned directory until the lab retention policy expires; inspect its contents before deleting it. Actual deployment or contract changes stay under their recorded owners and accepted change/recovery process.

Review questions:

1. How do direct spend and economic run cost differ?
2. Why does a cheaper hourly rate not establish a valid downsizing decision?
3. Why are storage quantities already including replica copies not multiplied again?
4. What must be verified before using an Enterprise subscription input?
5. Why must temporary DR/migration resources appear in the entitlement inventory?
6. Why does hiding an index not directly produce index-storage savings?
7. What evidence separates modeled from realized savings?
8. How can reduced resource cost increase total operational cost?

## 14. Official references and validation status

1. [MongoDB 8.0 — Analyzing Performance](https://www.mongodb.com/docs/v8.0/administration/analyzing-mongodb-performance/).
2. [MongoDB 8.0 — Hidden Indexes](https://www.mongodb.com/docs/v8.0/core/index-hidden/).
3. [MongoDB — Enterprise Advanced](https://www.mongodb.com/products/self-managed/enterprise-advanced): product overview; purchased terms and entitlement require actual contract verification.

Documentation reviewed on 2026-10-12. The cost categories, rates, monthly quantities, labor estimates, gate and renewal packet are teaching designs. Python/JavaScript syntax and actual offline Decimal arithmetic/acceptance cases were checked, including invalid/missing inputs. No actual pricing quote, contract interpretation, billing access, license change, downsizing, failover test or resource retirement was performed.

**Chapter completion:** Written with offline cost/gate acceptance complete. Runtime/commercial validation remains pending until actual inventory, entitlement, technical candidate tests and realized billing evidence are recorded.

Previous: [Chapter 71 — Daily Administration and Maintenance Runbook](71-daily-administration-and-maintenance-runbook.md).  
Next: Chapter 73 — Query Slowness Investigation Runbook.
