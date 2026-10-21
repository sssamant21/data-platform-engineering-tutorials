# Chapter 075 — Amazon MSK Enterprise SRE Operations, Disaster Recovery and Security Acceptance Capstone

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 15 — Amazon MSK and AWS Kafka Operations (5/5; final capstone)  
**Primary client runtime:** Amazon EKS / Kubernetes  
**Kafka platform:** Amazon MSK (validate provisioned/serverless feature differences)  
**Prerequisites:** Chapters 001–074, especially 071–074  
**Status:** Published · **Live integrated labs:** Pending · **Independent technical/security review:** Pending

> **Safety:** This is an evidence-driven acceptance framework, **not** authorization for production fault injection. All broker/AZ/region failures, credential compromise, cross-VPC mutation, DR cutover, failback, scaling and Kafka version upgrades are **Tabletop** unless explicitly approved in disposable infrastructure with synthetic data. Never enable public listeners, delete Kafka data, weaken TLS, leak IAM/SCRAM secrets, or claim zero RPO without measured proof.

## 1. Capstone mission

Integrate the four Amazon MSK chapters into a production-grade operational readiness review: architecture, EKS networking, IAM/TLS, broker durability, CloudWatch observability, performance and capacity, regional DR, security response, safe change control and independent acceptance.

**Outcomes:** produce an auditable architecture/identity map; verify Kafka RF/minISR and client correctness; design measurable RPO/RTO; assess regional failover/failback; implement SLO-based incident command; and obtain security/SRE/platform approval without conflating publication with live execution.

## 2. Enterprise architecture and ownership

```text
     Git-reviewed IaC and change ticket
                    |
         AWS MSK control plane
                    |
      +-------------+-------------+
      | Provisioned / Serverless  |
      |    MSK (Region A)         |
      | Kafka partitions, RF/ISR  |
      +-------------+-------------+
                    |
       VPC/DNS/SG + TLS/IAM/SCRAM
                    |
       EKS producer / consumer Pods
       workload identity / app SLO
                    |
        CloudWatch + client metrics
                    |
       Replicator or MirrorMaker 2
                    |
          MSK DR (Region B)
                    |
       single-writer cutover/fencing
                    |
        event-ID ledger + RPO/RTO
                    |
        SRE + security signoff
```

**AWS manages** the supported MSK broker infrastructure and service control plane. **The customer owns** topics, partitions, replication factor, minISR, identity policies, network trust, client correctness, DR design, event replay, monitoring and incident command. EKS is the application runtime, not an MSK broker orchestrator.

## 3. Acceptance gates and no-go policy

| Gate | Required evidence | No-go condition |
|---|---|---|
| AWS account/region/service | approved profile, type/version, quotas | unsupported operation |
| Network path | EKS Pod -> broker advertised DNS, SG/routes | bootstrap-only success |
| Authentication | least-privilege IAM/TLS/SCRAM and denial tests | credential leak or wildcard admin |
| Kafka durability | healthy RF/minISR, URP/offline partitions | degraded ISR |
| Storage/capacity | broker CPU/network/disk, skew, reserve | insufficient recovery headroom |
| Observability | CloudWatch dimensions, EKS metrics, alerts | blind incident response |
| Client correctness | acked synthetic IDs reconciled downstream | unexplained missing events |
| DR topology | destination network/auth, replication filters | destination unready |
| RPO/RTO | measured lag and recovery time | invented or undefined objectives |
| Failover/failback | single-writer fencing and offset plan | split writes/unknown replay |
| Change control | approval, cost, abort and recovery plan | unsafe/irreversible rollback |
| Independent review | SRE/platform/security signoff | unsigned acceptance |

A green MSK `ACTIVE` state does not prove that Kafka clients can authenticate, produce, consume or preserve event correctness.

## 4. Versioned read-only baseline

```bash
export AWS_PROFILE=YOUR_APPROVED_PROFILE
export AWS_REGION=YOUR_REGION
export MSK_ARN='arn:aws:kafka:REGION:ACCOUNT:cluster/NAME/UUID'
aws sts get-caller-identity
aws kafka describe-cluster-v2 --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
aws kafka get-bootstrap-brokers --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
aws kafka list-cluster-operations-v2 --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
aws cloudwatch list-metrics --namespace AWS/Kafka --region "$AWS_REGION"
kubectl config current-context
kubectl -n kafka-clients get pods,serviceaccount,networkpolicy -o wide
```

Some broker-node APIs and metrics are only applicable to supported provisioned cluster modes. Record exact API errors; never treat a denied or unsupported call as passing evidence. Sanitize ARNs, endpoints and identity details before sharing.

## 5. Kafka durability and capacity model

For each critical topic record partition count, replication factor, min.insync.replicas, leader/replica distribution, current ISR, retention, compaction and expected client acknowledgments. Review broker CPU/network/storage and recovery headroom for a single broker or AZ outage.

**Decision rule:** stop rolling maintenance or scaling if minISR/ISR, client SLO or disk recovery headroom is unsafe. Adding brokers does not automatically redistribute hot partition keys or replicas.

## 6. EKS-to-MSK authenticated client acceptance

Synthetic test design:
1. Select approved EKS namespace, dedicated service account and IAM/SCRAM mechanism.
2. Verify DNS for bootstrap **and advertised brokers**, private routes, SG/NACL and TLS trust.
3. Produce unique synthetic event IDs, await Kafka acknowledgments and record topic/partition/offset/UTC.
4. Consume with approved group, measure freshness, lag, retries and application processing.
5. Reconcile expected acknowledged IDs against observed outputs; record duplicates and missing events.
6. Run negative authorization tests only in approved nonproduction scope.
7. Preserve sanitized results and independent reviewer signoff.

## 7. Monitoring and SLO design

Define business SLOs for producer acknowledged success, P95/P99 latency, consumer freshness, event correctness and recovery. Correlate MSK CloudWatch broker metrics (CPU, network, storage, under-replicated/offline partitions, leader skew) with EKS client telemetry (retries, errors, group lag, processing time).

Metrics vary by MSK type/monitoring level; confirm actual names, dimensions, period and publication delay. Design alerts for impact plus cause, assign on-call and runbook links, and record alert delivery test evidence separately from a dashboard screenshot.

## 8. Regional DR engineering

**Multi-AZ is not regional DR.** For regional recovery, choose a supported replication tool such as MSK Replicator or MirrorMaker 2 after validating deployment type, account/region eligibility, topic/config/ACL/offset support and costs.

- **RPO:** compare acknowledged source event IDs and destination observation at cutover.
- **RTO:** measure from declared incident to restored authenticated client processing.
- **Consumer offsets:** do not assume offset translation or synchronization is automatic.
- **Single writer:** fence the old write path before destination producers become authoritative.
- **Duplicates:** use idempotent processing and explicit reconciliation.
- **Failback:** choose source of truth, resolve divergence, validate offsets and re-enable only one writer.
- **Backup:** Kafka replication is not immutable backup; test independent restore where required.

## 9. Change and incident lifecycle

**Pre-change:** approved ticket, cost, version matrix, IAM/TLS, network, RF/minISR, capacity, client SLO, replication lag, RPO/RTO, rollback feasibility and communication plan.

**During:** observe AWS MSK operation state, Kafka ISR, CloudWatch, EKS clients, event IDs and security signals; stop on critical regression.

**Post-change:** reconcile event IDs, producer acknowledgments, consumer lag, replication, capacity and alerts; attach sanitized UTC evidence and signoff.

**Incident:** establish severity from customer impact, preserve data/identity evidence, coordinate AWS support when needed, execute least-risk recovery, measure RTO/RPO and produce RCA.

## 10. Twenty integrated MSK/EKS capstone labs

### Lab 01 — Approve enterprise capstone charter

**Procedure:** Define business criticality, tenant scope, RACI, AWS accounts/regions, SLO, RPO/RTO and budget.

**Acceptance evidence:** AWS account alias/region, MSK type/Kafka version, EKS context, UTC time, approved role, expected/observed state, Kafka ISR/minISR, security positive/negative result, synthetic event IDs, SLO/RPO/RTO, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Faults and regional cutover are **Tabletop** without explicitly approved isolated infrastructure.

### Lab 02 — Pin service and client versions

**Procedure:** Capture MSK type/Kafka version, EKS, AWS CLI, IAM auth plugin and replication tool versions.

**Acceptance evidence:** AWS account alias/region, MSK type/Kafka version, EKS context, UTC time, approved role, expected/observed state, Kafka ISR/minISR, security positive/negative result, synthetic event IDs, SLO/RPO/RTO, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Faults and regional cutover are **Tabletop** without explicitly approved isolated infrastructure.

### Lab 03 — Map EKS-to-MSK topology

**Procedure:** Diagram Pod identity, VPC/AZ, routing, SG, DNS and every advertised broker endpoint.

**Acceptance evidence:** AWS account alias/region, MSK type/Kafka version, EKS context, UTC time, approved role, expected/observed state, Kafka ISR/minISR, security positive/negative result, synthetic event IDs, SLO/RPO/RTO, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Faults and regional cutover are **Tabletop** without explicitly approved isolated infrastructure.

### Lab 04 — Validate broker and partition durability

**Procedure:** Review RF/minISR, leaders, under-replicated/offline partitions and failure-domain capacity.

**Acceptance evidence:** AWS account alias/region, MSK type/Kafka version, EKS context, UTC time, approved role, expected/observed state, Kafka ISR/minISR, security positive/negative result, synthetic event IDs, SLO/RPO/RTO, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Faults and regional cutover are **Tabletop** without explicitly approved isolated infrastructure.

### Lab 05 — Review IAM least privilege

**Procedure:** Audit cluster/topic/group resource ARNs, role trust and separation of administrative rights.

**Acceptance evidence:** AWS account alias/region, MSK type/Kafka version, EKS context, UTC time, approved role, expected/observed state, Kafka ISR/minISR, security positive/negative result, synthetic event IDs, SLO/RPO/RTO, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Faults and regional cutover are **Tabletop** without explicitly approved isolated infrastructure.

### Lab 06 — Review TLS/SCRAM and KMS

**Procedure:** Assess listener encryption, certificate verification, secret lifecycle and key grants.

**Acceptance evidence:** AWS account alias/region, MSK type/Kafka version, EKS context, UTC time, approved role, expected/observed state, Kafka ISR/minISR, security positive/negative result, synthetic event IDs, SLO/RPO/RTO, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Faults and regional cutover are **Tabletop** without explicitly approved isolated infrastructure.

### Lab 07 — Review tenant isolation

**Procedure:** Design positive/negative IAM/ACL/network tests without printing credentials.

**Acceptance evidence:** AWS account alias/region, MSK type/Kafka version, EKS context, UTC time, approved role, expected/observed state, Kafka ISR/minISR, security positive/negative result, synthetic event IDs, SLO/RPO/RTO, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Faults and regional cutover are **Tabletop** without explicitly approved isolated infrastructure.

### Lab 08 — Inspect cluster operations and change history

**Procedure:** Collect cluster state, configuration revisions, scaling/upgrade operations and CloudTrail.

**Acceptance evidence:** AWS account alias/region, MSK type/Kafka version, EKS context, UTC time, approved role, expected/observed state, Kafka ISR/minISR, security positive/negative result, synthetic event IDs, SLO/RPO/RTO, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Faults and regional cutover are **Tabletop** without explicitly approved isolated infrastructure.

### Lab 09 — Review storage and broker capacity

**Procedure:** Model CPU/network, partition skew, disk retention, scaling and recovery headroom.

**Acceptance evidence:** AWS account alias/region, MSK type/Kafka version, EKS context, UTC time, approved role, expected/observed state, Kafka ISR/minISR, security positive/negative result, synthetic event IDs, SLO/RPO/RTO, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Faults and regional cutover are **Tabletop** without explicitly approved isolated infrastructure.

### Lab 10 — Validate CloudWatch and EKS observability

**Procedure:** Review metric dimensions, client lag, retries, event correctness, alert owners and dashboards.

**Acceptance evidence:** AWS account alias/region, MSK type/Kafka version, EKS context, UTC time, approved role, expected/observed state, Kafka ISR/minISR, security positive/negative result, synthetic event IDs, SLO/RPO/RTO, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Faults and regional cutover are **Tabletop** without explicitly approved isolated infrastructure.

### Lab 11 — Validate authenticated client smoke

**Procedure:** Plan synthetic producer ack, consumer processing, unique event IDs and end-to-end latency.

**Acceptance evidence:** AWS account alias/region, MSK type/Kafka version, EKS context, UTC time, approved role, expected/observed state, Kafka ISR/minISR, security positive/negative result, synthetic event IDs, SLO/RPO/RTO, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Faults and regional cutover are **Tabletop** without explicitly approved isolated infrastructure.

### Lab 12 — Review DR destination readiness

**Procedure:** Confirm destination region/cluster, network, IAM/TLS, topics and consumer deployment.

**Acceptance evidence:** AWS account alias/region, MSK type/Kafka version, EKS context, UTC time, approved role, expected/observed state, Kafka ISR/minISR, security positive/negative result, synthetic event IDs, SLO/RPO/RTO, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Faults and regional cutover are **Tabletop** without explicitly approved isolated infrastructure.

### Lab 13 — Review replication correctness

**Procedure:** Assess MSK Replicator/MM2 support, filters, lag, offsets, duplicate and ordering behavior.

**Acceptance evidence:** AWS account alias/region, MSK type/Kafka version, EKS context, UTC time, approved role, expected/observed state, Kafka ISR/minISR, security positive/negative result, synthetic event IDs, SLO/RPO/RTO, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Faults and regional cutover are **Tabletop** without explicitly approved isolated infrastructure.

### Lab 14 — Measure RPO in a test plan

**Procedure:** Specify source acknowledged IDs, destination observation and last missing event.

**Acceptance evidence:** AWS account alias/region, MSK type/Kafka version, EKS context, UTC time, approved role, expected/observed state, Kafka ISR/minISR, security positive/negative result, synthetic event IDs, SLO/RPO/RTO, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Faults and regional cutover are **Tabletop** without explicitly approved isolated infrastructure.

### Lab 15 — Measure RTO in a test plan

**Procedure:** Specify start/end timestamps from incident declaration to recovered client processing.

**Acceptance evidence:** AWS account alias/region, MSK type/Kafka version, EKS context, UTC time, approved role, expected/observed state, Kafka ISR/minISR, security positive/negative result, synthetic event IDs, SLO/RPO/RTO, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Faults and regional cutover are **Tabletop** without explicitly approved isolated infrastructure.

### Lab 16 — Rehearse broker/AZ incident

**Procedure:** Tabletop broker loss, ISR, producer retries, lag and safe maintenance stop.

**Acceptance evidence:** AWS account alias/region, MSK type/Kafka version, EKS context, UTC time, approved role, expected/observed state, Kafka ISR/minISR, security positive/negative result, synthetic event IDs, SLO/RPO/RTO, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Faults and regional cutover are **Tabletop** without explicitly approved isolated infrastructure.

### Lab 17 — Rehearse regional failover

**Procedure:** Tabletop fencing, destination identity, producer/consumer cutover, offsets and communications.

**Acceptance evidence:** AWS account alias/region, MSK type/Kafka version, EKS context, UTC time, approved role, expected/observed state, Kafka ISR/minISR, security positive/negative result, synthetic event IDs, SLO/RPO/RTO, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Faults and regional cutover are **Tabletop** without explicitly approved isolated infrastructure.

### Lab 18 — Rehearse regional failback

**Procedure:** Tabletop divergent records, source-of-truth choice, offset reconciliation and split-write prevention.

**Acceptance evidence:** AWS account alias/region, MSK type/Kafka version, EKS context, UTC time, approved role, expected/observed state, Kafka ISR/minISR, security positive/negative result, synthetic event IDs, SLO/RPO/RTO, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Faults and regional cutover are **Tabletop** without explicitly approved isolated infrastructure.

### Lab 19 — Review security and change incidents

**Procedure:** Rehearse credential compromise, network exposure, rollback and RCA evidence.

**Acceptance evidence:** AWS account alias/region, MSK type/Kafka version, EKS context, UTC time, approved role, expected/observed state, Kafka ISR/minISR, security positive/negative result, synthetic event IDs, SLO/RPO/RTO, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Faults and regional cutover are **Tabletop** without explicitly approved isolated infrastructure.

### Lab 20 — Independent enterprise acceptance

**Procedure:** Score critical gates, attach sanitized evidence, track remediation and obtain SRE/security signoff.

**Acceptance evidence:** AWS account alias/region, MSK type/Kafka version, EKS context, UTC time, approved role, expected/observed state, Kafka ISR/minISR, security positive/negative result, synthetic event IDs, SLO/RPO/RTO, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Faults and regional cutover are **Tabletop** without explicitly approved isolated infrastructure.

## 11. Read-only capstone verification script

Save as `verify-ch75.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${AWS_PROFILE:?Set approved AWS_PROFILE}"
: "${AWS_REGION:?Set AWS_REGION}"
: "${MSK_ARN:?Set approved MSK cluster ARN}"
NS="${EKS_NS:-kafka-clients}"
echo '[1/11] Identity'; aws sts get-caller-identity
echo '[2/11] MSK cluster'; aws kafka describe-cluster-v2 --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
echo '[3/11] Bootstrap'; aws kafka get-bootstrap-brokers --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
echo '[4/11] Operations'; aws kafka list-cluster-operations-v2 --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
echo '[5/11] Metrics'; aws cloudwatch list-metrics --namespace AWS/Kafka --region "$AWS_REGION"
echo '[6/11] Alarms'; aws cloudwatch describe-alarms --region "$AWS_REGION"
echo '[7/11] Logs'; aws logs describe-log-groups --region "$AWS_REGION"
echo '[8/11] EKS context'; kubectl config current-context
echo '[9/11] Pods'; kubectl -n "$NS" get pods -o wide
echo '[10/11] Identities and network'; kubectl -n "$NS" get serviceaccount,networkpolicy
echo '[11/11] Events'; kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo 'PASS: read-only inventory only.'
echo 'NOT PROVEN: Kafka RF/minISR, client correctness, security negative tests, DR RPO/RTO or independent acceptance.'
```

Run only in an approved account/context; sanitize output. This script does not inspect actual Kafka topic metadata, trigger alerts or execute failover.

## 12. Twelve integrated failure scenarios

### Scenario 1 — MSK ACTIVE but client events fail

**Diagnosis:** Trace EKS identity, TLS/IAM, DNS, broker metadata and event-ID ledger. Correlate MSK state/operations, CloudWatch, IAM/TLS/SCRAM, EKS network, Kafka ISR/minISR, replication lag, consumer offsets and synthetic event IDs. **Response:** Freeze unsafe changes, contain security exposure, protect single-writer authority and preserve sanitized evidence. **Exit:** Restored SLO, measured or explicitly tabletop RPO/RTO, RCA and independent reviewer.

### Scenario 2 — Broker ISR degrades during maintenance

**Diagnosis:** Freeze updates, check RF/minISR, storage/network, client SLO and broker operations. Correlate MSK state/operations, CloudWatch, IAM/TLS/SCRAM, EKS network, Kafka ISR/minISR, replication lag, consumer offsets and synthetic event IDs. **Response:** Freeze unsafe changes, contain security exposure, protect single-writer authority and preserve sanitized evidence. **Exit:** Restored SLO, measured or explicitly tabletop RPO/RTO, RCA and independent reviewer.

### Scenario 3 — Cross-VPC bootstrap works but brokers time out

**Diagnosis:** Inspect advertised broker DNS, routes, SG/NACL and listener type. Correlate MSK state/operations, CloudWatch, IAM/TLS/SCRAM, EKS network, Kafka ISR/minISR, replication lag, consumer offsets and synthetic event IDs. **Response:** Freeze unsafe changes, contain security exposure, protect single-writer authority and preserve sanitized evidence. **Exit:** Restored SLO, measured or explicitly tabletop RPO/RTO, RCA and independent reviewer.

### Scenario 4 — IAM role trust breaks after deployment

**Diagnosis:** Check EKS service account association, role trust, resource ARN and SDK. Correlate MSK state/operations, CloudWatch, IAM/TLS/SCRAM, EKS network, Kafka ISR/minISR, replication lag, consumer offsets and synthetic event IDs. **Response:** Freeze unsafe changes, contain security exposure, protect single-writer authority and preserve sanitized evidence. **Exit:** Restored SLO, measured or explicitly tabletop RPO/RTO, RCA and independent reviewer.

### Scenario 5 — SCRAM/TLS rotation breaks clients

**Diagnosis:** Inspect Secrets Manager, CA trust, hostname verification and staged rollout. Correlate MSK state/operations, CloudWatch, IAM/TLS/SCRAM, EKS network, Kafka ISR/minISR, replication lag, consumer offsets and synthetic event IDs. **Response:** Freeze unsafe changes, contain security exposure, protect single-writer authority and preserve sanitized evidence. **Exit:** Restored SLO, measured or explicitly tabletop RPO/RTO, RCA and independent reviewer.

### Scenario 6 — Disk growth exceeds recovery reserve

**Diagnosis:** Check retention, partition skew, autoscaling eligibility, cost and expansion. Correlate MSK state/operations, CloudWatch, IAM/TLS/SCRAM, EKS network, Kafka ISR/minISR, replication lag, consumer offsets and synthetic event IDs. **Response:** Freeze unsafe changes, contain security exposure, protect single-writer authority and preserve sanitized evidence. **Exit:** Restored SLO, measured or explicitly tabletop RPO/RTO, RCA and independent reviewer.

### Scenario 7 — CloudWatch alarm missing during incident

**Diagnosis:** Check metric tier/dimension, period, ingestion delay, alarm routing and EKS telemetry. Correlate MSK state/operations, CloudWatch, IAM/TLS/SCRAM, EKS network, Kafka ISR/minISR, replication lag, consumer offsets and synthetic event IDs. **Response:** Freeze unsafe changes, contain security exposure, protect single-writer authority and preserve sanitized evidence. **Exit:** Restored SLO, measured or explicitly tabletop RPO/RTO, RCA and independent reviewer.

### Scenario 8 — Cross-region replication lags behind RPO

**Diagnosis:** Inspect throughput, topic filters, connector health, offsets and event ledger. Correlate MSK state/operations, CloudWatch, IAM/TLS/SCRAM, EKS network, Kafka ISR/minISR, replication lag, consumer offsets and synthetic event IDs. **Response:** Freeze unsafe changes, contain security exposure, protect single-writer authority and preserve sanitized evidence. **Exit:** Restored SLO, measured or explicitly tabletop RPO/RTO, RCA and independent reviewer.

### Scenario 9 — Regional failover creates split writers

**Diagnosis:** Fence old producer path and establish authoritative writer before cutover. Correlate MSK state/operations, CloudWatch, IAM/TLS/SCRAM, EKS network, Kafka ISR/minISR, replication lag, consumer offsets and synthetic event IDs. **Response:** Freeze unsafe changes, contain security exposure, protect single-writer authority and preserve sanitized evidence. **Exit:** Restored SLO, measured or explicitly tabletop RPO/RTO, RCA and independent reviewer.

### Scenario 10 — Consumer offsets diverge after cutover

**Diagnosis:** Check translation/synchronization, replay semantics and duplicate handling. Correlate MSK state/operations, CloudWatch, IAM/TLS/SCRAM, EKS network, Kafka ISR/minISR, replication lag, consumer offsets and synthetic event IDs. **Response:** Freeze unsafe changes, contain security exposure, protect single-writer authority and preserve sanitized evidence. **Exit:** Restored SLO, measured or explicitly tabletop RPO/RTO, RCA and independent reviewer.

### Scenario 11 — Failback misses events

**Diagnosis:** Reconcile acknowledged IDs and source-of-truth state before redirecting clients. Correlate MSK state/operations, CloudWatch, IAM/TLS/SCRAM, EKS network, Kafka ISR/minISR, replication lag, consumer offsets and synthetic event IDs. **Response:** Freeze unsafe changes, contain security exposure, protect single-writer authority and preserve sanitized evidence. **Exit:** Restored SLO, measured or explicitly tabletop RPO/RTO, RCA and independent reviewer.

### Scenario 12 — Change rollback restores manifests but not data

**Diagnosis:** Classify irreversible Kafka state, invoke approved recovery and verify correctness. Correlate MSK state/operations, CloudWatch, IAM/TLS/SCRAM, EKS network, Kafka ISR/minISR, replication lag, consumer offsets and synthetic event IDs. **Response:** Freeze unsafe changes, contain security exposure, protect single-writer authority and preserve sanitized evidence. **Exit:** Restored SLO, measured or explicitly tabletop RPO/RTO, RCA and independent reviewer.

## 13. Eight production runbooks

### Runbook A — Enterprise MSK incident command

**Trigger/response:** Declare severity, establish timeline, preserve evidence, communicate and assign owners. **No-go:** lost Kafka durability, credential leak, public exposure, unknown replication lag, split writers, unapproved cost/change or unsupported rollback. **Exit:** Stable MSK, least-privilege EKS client path, reconciled event IDs, documented RPO/RTO, restored SLO and signoff.

### Runbook B — Broker durability and client SLO

**Trigger/response:** Check ISR/minISR, leader state, CloudWatch, EKS retries and safe mitigation. **No-go:** lost Kafka durability, credential leak, public exposure, unknown replication lag, split writers, unapproved cost/change or unsupported rollback. **Exit:** Stable MSK, least-privilege EKS client path, reconciled event IDs, documented RPO/RTO, restored SLO and signoff.

### Runbook C — EKS-to-MSK network/auth outage

**Trigger/response:** Trace service-account identity, routing, broker DNS, TLS/SCRAM/IAM and ACL. **No-go:** lost Kafka durability, credential leak, public exposure, unknown replication lag, split writers, unapproved cost/change or unsupported rollback. **Exit:** Stable MSK, least-privilege EKS client path, reconciled event IDs, documented RPO/RTO, restored SLO and signoff.

### Runbook D — Capacity/storage escalation

**Trigger/response:** Review partition skew, broker CPU/network/disk, autoscaling and approved change. **No-go:** lost Kafka durability, credential leak, public exposure, unknown replication lag, split writers, unapproved cost/change or unsupported rollback. **Exit:** Stable MSK, least-privilege EKS client path, reconciled event IDs, documented RPO/RTO, restored SLO and signoff.

### Runbook E — Cross-region replication and RPO breach

**Trigger/response:** Inspect replication health, lag, filters, offsets, event correctness and escalation. **No-go:** lost Kafka durability, credential leak, public exposure, unknown replication lag, split writers, unapproved cost/change or unsupported rollback. **Exit:** Stable MSK, least-privilege EKS client path, reconciled event IDs, documented RPO/RTO, restored SLO and signoff.

### Runbook F — Regional failover/failback

**Trigger/response:** Require fencing, destination auth, measured RPO/RTO, client smoke and controlled reversal. **No-go:** lost Kafka durability, credential leak, public exposure, unknown replication lag, split writers, unapproved cost/change or unsupported rollback. **Exit:** Stable MSK, least-privilege EKS client path, reconciled event IDs, documented RPO/RTO, restored SLO and signoff.

### Runbook G — Credential compromise/security exposure

**Trigger/response:** Contain IAM/Secrets/SG access, rotate, preserve audit and security escalation. **No-go:** lost Kafka durability, credential leak, public exposure, unknown replication lag, split writers, unapproved cost/change or unsupported rollback. **Exit:** Stable MSK, least-privilege EKS client path, reconciled event IDs, documented RPO/RTO, restored SLO and signoff.

### Runbook H — Independent readiness and RCA

**Trigger/response:** Validate all gates, evidence, change approvals, recovery outcomes and signoff. **No-go:** lost Kafka durability, credential leak, public exposure, unknown replication lag, split writers, unapproved cost/change or unsupported rollback. **Exit:** Stable MSK, least-privilege EKS client path, reconciled event IDs, documented RPO/RTO, restored SLO and signoff.

## 14. Evidence package

```text
evidence-ch75/
  charter-raci-slo-rpo-rto.md
  pinned-versions.md
  eks-msk-topology.md
  kafka-rf-minisr-isr.md
  iam-authorization-review.md
  tls-scram-kms-review.md
  tenant-negative-tests.md
  msk-operations-change-history.md
  broker-storage-capacity.md
  cloudwatch-eks-alerting.md
  synthetic-client-event-ledger.csv
  dr-destination-readiness.md
  replication-offset-review.md
  rpo-measurement.md
  rto-measurement.md
  broker-az-incident-tabletop.md
  regional-failover-tabletop.md
  regional-failback-tabletop.md
  security-change-incident-tabletop.md
  independent-sre-platform-security-signoff.md
  scorecard.md
```

Every evidence artifact requires UTC time, AWS region/account scope, exact service/client versions, expected/observed result, **Live** vs **Tabletop**, sanitized data, owner, abort/rollback and independent reviewer.

## 15. 100-point enterprise SRE acceptance assessment

| Domain | Points | Critical |
|---|---:|---|
| Architecture, networking, identity and change provenance | 15 | Yes |
| Kafka durability, capacity and broker operations | 15 | Yes |
| IAM/TLS/SCRAM and tenant isolation | 15 | Yes |
| CloudWatch, EKS client SLO and event correctness | 15 | Yes |
| DR replication, consumer offsets and RPO/RTO | 20 | Yes |
| Failover/failback and incident response | 15 | Yes |
| Independent technical/security acceptance | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 **and** every critical gate independently evidenced, including representative live tests. **Automatic Fail:** fabricated live results, unreviewed public access, credential exposure, lost ISR without response, split writes, unexplained missing events, invented RPO/RTO or missing independent review.

**Current readiness: Pending / Not Ready.** Publishing the capstone is not evidence of executed EKS-to-MSK tests, live DR recovery or security approval.

## 16. References and transition

**References:** [Amazon MSK Developer Guide](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html), [MSK Monitoring](https://docs.aws.amazon.com/msk/latest/developerguide/monitoring.html), [MSK Replicator](https://docs.aws.amazon.com/msk/latest/developerguide/msk-replicator.html), [Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html), [Apache Kafka](https://kafka.apache.org/documentation/).

**Part 15 — Amazon MSK and AWS Kafka Operations is fully published (071–075).**

**Next:** Chapter 076 — Kafka Infrastructure as Code with Terraform, GitOps and CI/CD Automation, beginning Part 16 — Automation, Terraform and CI/CD.

---

**Verification boundary:** Publication proves document availability only. Live MSK/EKS smoke, RPO/RTO measurement, failover/failback, negative security tests and independent technical/security review remain Pending.
