# Chapter 074 — Amazon MSK Security, Multi-VPC Connectivity, Disaster Recovery and Production Change Management

**Curriculum:** Apache Kafka Administration, SRE & Platform Engineering  
**Part:** 15 — Amazon MSK and AWS Kafka Operations (4/5)  
**Primary client runtime:** Amazon EKS / Kubernetes  
**Kafka platform:** Amazon MSK, with feature differences by provisioned/serverless mode  
**Prerequisites:** Chapters 001–073, AWS IAM/VPC/EKS, Kafka replication and incident response  
**Publication:** Published · **Live labs:** Pending · **Independent technical/security review:** Pending

> **Safety:** Use approved nonproduction AWS accounts and synthetic events. Do not enable public access, change IAM/cluster policies, create cross-VPC connectivity, rotate production Secrets, provision paid replication, cut over clients, fence producers or run DR failover without a formal change. A Kafka replica is not a point-in-time backup. Failover/failback can duplicate or lose events unless measured and engineered.

## 1. Mission and learning objectives

Secure Amazon MSK across VPCs and AWS accounts, design EKS workload identity and private Kafka connectivity, plan regional disaster recovery, protect event correctness during failover, and govern production changes with auditable RPO/RTO acceptance.

By completion, learners can build an MSK trust-boundary diagram, distinguish AWS IAM from Kafka ACL authorization, review supported multi-VPC options, design cross-region replication and consumer offset strategies, and lead a security-aware DR incident.

## 2. Architecture and threat boundaries

```text
 EKS Account A / VPC A                         EKS Account B / VPC B
 client SA -> IAM role                          client SA -> IAM role
         \                                             /
          \   approved routing / MSK connectivity      /
           \              + DNS + SG                 /
            +------------ Amazon MSK ----------------+
                            |
                 TLS + IAM or SCRAM/mTLS
                            |
                   topics / groups / ACL
                            |
                   replication connector
                            |
                DR MSK in second AWS region
                            |
              fenced cutover + event-ID ledger
                            |
                  on-call + audit + RCA
```

**Boundary 1:** AWS IAM trust and cluster policy control AWS-authorized Kafka access where supported. **Boundary 2:** Kafka ACLs apply to Kafka authorization models where configured. **Boundary 3:** VPC/SG/NACL and EKS NetworkPolicy constrain network reachability, not topic permissions. **Boundary 4:** Cross-region replication copies selected Kafka data, not automatically all identity, application configuration, consumer state or backups.

## 3. Authentication and authorization

| Mechanism | Operational responsibility | Common failure |
|---|---|---|
| MSK IAM/SASL | IAM actions/resources, role trust, supported client plugin | wrong principal or resource ARN |
| SASL/SCRAM | Secrets Manager, KMS, Kafka ACLs | stale/invalid secret or ACL |
| mTLS where supported | certificate issuance/trust, identity mapping and ACL | expired cert or SAN mismatch |
| TLS encryption | broker listener, CA verification, client trust | plaintext or disabled hostname check |

Do not assume all mechanisms are supported by every MSK type or listener. Avoid shared superuser identities. Use EKS IRSA or Pod Identity with dedicated service accounts and roles where supported.

## 4. Read-only AWS security inventory

```bash
export AWS_PROFILE=YOUR_APPROVED_PROFILE
export AWS_REGION=YOUR_REGION
export MSK_ARN='arn:aws:kafka:REGION:ACCOUNT:cluster/NAME/UUID'
aws sts get-caller-identity
aws kafka describe-cluster-v2 --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
aws kafka get-bootstrap-brokers --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
aws kafka get-cluster-policy --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
aws kafka list-scram-secrets --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
kubectl config current-context
kubectl -n kafka-clients get serviceaccount,networkpolicy
```

**Interpretation:** Some APIs require provisioned cluster type or specific features; `get-cluster-policy` may return no policy, which is not proof of a security failure. Do not dump Secrets Manager secret values or IAM tokens. Sanitize endpoint/ARN details in shared evidence.

## 5. Multi-VPC and cross-account networking

**Kafka connectivity is more than bootstrap:** clients fetch metadata then connect to broker-advertised endpoints. Verify each broker DNS name resolves and each endpoint is reachable using the correct listener.

| Option | Use case | Review |
|---|---|---|
| Same-VPC | EKS clients and MSK in one VPC | private subnets, SG, DNS |
| VPC peering | supported private routing between VPCs | CIDR overlap, route tables, DNS |
| Transit Gateway | multi-VPC hub-and-spoke | attachments, routes, costs |
| MSK managed multi-VPC private connectivity | supported cluster/client/account combinations | MSK mode, auth, policy, endpoint/DNS and region |
| VPN/Direct Connect | hybrid connectivity | route propagation, latency, failure domains |

MSK-managed connectivity eligibility and support change by service type/region. Do not invent endpoint types or assume VPC peering is automatically permitted.

## 6. Kubernetes-first client network validation

```bash
kubectl -n kafka-clients get pods -o wide
kubectl -n kafka-clients get serviceaccount
kubectl -n kafka-clients get networkpolicy
kubectl -n kafka-clients get events --sort-by=.metadata.creationTimestamp
```

From a pre-approved debug Pod:

```bash
kubectl -n kafka-clients exec POD_NAME -- getent hosts BROKER_DNS
kubectl -n kafka-clients exec POD_NAME -- openssl s_client -connect BROKER_DNS:PORT -servername BROKER_DNS -verify_return_error
```

Use the actual MSK TLS listener/port. TLS connection success does not prove IAM/SCRAM authorization or all advertised broker paths. Do not disable TLS verification.

## 7. Regional DR patterns

| Pattern | Benefit | Limitation |
|---|---|---|
| Multi-AZ single-region MSK | tolerates supported AZ/broker failures | not a regional DR solution |
| Cross-region replication | warm destination topics and lower potential RTO | asynchronous lag, cost, data divergence |
| MSK Replicator where supported | managed replication workflow | validate feature, topic/offset support and eligibility |
| MirrorMaker 2 on approved compute | flexible Kafka replication | connectors, offset translation, monitoring and maintenance |
| Immutable archival/backup | recovery beyond retained topic replicas | separate tooling, restore testing and RPO |

**Never equate replication with backup:** accidental deletes, corrupt records or retention policy mistakes can propagate. A backup strategy requires independent retention and a tested restore path.

## 8. RPO/RTO engineering and event correctness

- **RPO:** quantify last acknowledged source event absent at destination at failover; record source/destination offsets and event IDs. Do not claim zero without proof.
- **RTO:** measure from incident declaration or agreed start to successful authenticated destination produce/consume and application recovery.
- **Consumer groups:** offset synchronization/translation support varies by replication tool and topology. Validate before cutover; avoid blind offset reuse.
- **Producers:** use single-writer fencing/cutover design to prevent simultaneous active writes across regions.
- **Event semantics:** duplicate delivery and reordering are possible. Use idempotent consumers, unique event IDs and reconciliation.
- **Failback:** assess data divergence, client identity, DNS, replication direction, consumer offsets and the designated source of truth.

## 9. Illustrative DR event ledger

```text
test_run_id, event_id, source_topic, source_partition, source_offset,
source_ack_utc, destination_topic, destination_partition,
destination_observed_utc, consumer_group, processing_status
```

A pass requires the expected set of acknowledged event IDs to appear at the destination under the approved RPO, and downstream processing to satisfy the agreed semantics. Document duplicates explicitly; do not silently deduplicate evidence.

## 10. Production change management

Every network, IAM, authentication, replication or DR change must include: owner, security approval, AWS region/account, exact cluster mode, current/desired config, change window, cost, RPO/RTO, client SLO, data correctness, abort triggers, rollback/failback and communications.

**No-go conditions:** unknown Kafka ISR/partition state, missing destination security, unmeasured replication lag, unresolved offset strategy, active split writers, missing recovery plan or incomplete incident escalation.

## 11. Twenty Kubernetes-first MSK security and DR labs

### Lab 01 — Define MSK security and DR charter

**Procedure:** Record tenants, AWS accounts, regions, RPO/RTO, data classification, owners and approval.

**Evidence and acceptance:** Capture approved AWS account alias/region, MSK type/version, EKS context, UTC time, principal/network/replication scope, expected and observed positive/negative result, synthetic event IDs, RPO/RTO definition, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Cross-account denial tests, regional cutover and failback remain **Tabletop** without authorized disposable infrastructure.

### Lab 02 — Inventory cluster security posture

**Procedure:** Review encryption in transit/at rest, authentication, public access, monitoring and tags.

**Evidence and acceptance:** Capture approved AWS account alias/region, MSK type/version, EKS context, UTC time, principal/network/replication scope, expected and observed positive/negative result, synthetic event IDs, RPO/RTO definition, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Cross-account denial tests, regional cutover and failback remain **Tabletop** without authorized disposable infrastructure.

### Lab 03 — Review IAM authorization matrix

**Procedure:** Map cluster/topic/group actions, principal trust and explicit deny boundaries.

**Evidence and acceptance:** Capture approved AWS account alias/region, MSK type/version, EKS context, UTC time, principal/network/replication scope, expected and observed positive/negative result, synthetic event IDs, RPO/RTO definition, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Cross-account denial tests, regional cutover and failback remain **Tabletop** without authorized disposable infrastructure.

### Lab 04 — Review EKS workload identity

**Procedure:** Validate IRSA/Pod Identity associations and least-privilege per client namespace.

**Evidence and acceptance:** Capture approved AWS account alias/region, MSK type/version, EKS context, UTC time, principal/network/replication scope, expected and observed positive/negative result, synthetic event IDs, RPO/RTO definition, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Cross-account denial tests, regional cutover and failback remain **Tabletop** without authorized disposable infrastructure.

### Lab 05 — Review SCRAM/TLS lifecycle

**Procedure:** Check Secrets Manager association, KMS permissions, TLS chain, rotation and revocation.

**Evidence and acceptance:** Capture approved AWS account alias/region, MSK type/version, EKS context, UTC time, principal/network/replication scope, expected and observed positive/negative result, synthetic event IDs, RPO/RTO definition, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Cross-account denial tests, regional cutover and failback remain **Tabletop** without authorized disposable infrastructure.

### Lab 06 — Review VPC security groups

**Procedure:** Inventory broker ENI SGs, approved client sources and denied paths.

**Evidence and acceptance:** Capture approved AWS account alias/region, MSK type/version, EKS context, UTC time, principal/network/replication scope, expected and observed positive/negative result, synthetic event IDs, RPO/RTO definition, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Cross-account denial tests, regional cutover and failback remain **Tabletop** without authorized disposable infrastructure.

### Lab 07 — Review DNS and advertised brokers

**Procedure:** Capture bootstrap and all broker DNS endpoints for client metadata connections.

**Evidence and acceptance:** Capture approved AWS account alias/region, MSK type/version, EKS context, UTC time, principal/network/replication scope, expected and observed positive/negative result, synthetic event IDs, RPO/RTO definition, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Cross-account denial tests, regional cutover and failback remain **Tabletop** without authorized disposable infrastructure.

### Lab 08 — Review cross-VPC architecture

**Procedure:** Compare supported managed multi-VPC connectivity, peering and Transit Gateway.

**Evidence and acceptance:** Capture approved AWS account alias/region, MSK type/version, EKS context, UTC time, principal/network/replication scope, expected and observed positive/negative result, synthetic event IDs, RPO/RTO definition, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Cross-account denial tests, regional cutover and failback remain **Tabletop** without authorized disposable infrastructure.

### Lab 09 — Review cross-account permissions

**Procedure:** Check MSK cluster policy, IAM principals, connectivity type and account ownership.

**Evidence and acceptance:** Capture approved AWS account alias/region, MSK type/version, EKS context, UTC time, principal/network/replication scope, expected and observed positive/negative result, synthetic event IDs, RPO/RTO definition, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Cross-account denial tests, regional cutover and failback remain **Tabletop** without authorized disposable infrastructure.

### Lab 10 — Review EKS NetworkPolicy

**Procedure:** Check Pod ingress/egress, DNS, NAT/endpoint access and CNI enforcement.

**Evidence and acceptance:** Capture approved AWS account alias/region, MSK type/version, EKS context, UTC time, principal/network/replication scope, expected and observed positive/negative result, synthetic event IDs, RPO/RTO definition, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Cross-account denial tests, regional cutover and failback remain **Tabletop** without authorized disposable infrastructure.

### Lab 11 — Define DR topology

**Procedure:** Compare same-region AZ resilience, cross-region replication and recovery clusters.

**Evidence and acceptance:** Capture approved AWS account alias/region, MSK type/version, EKS context, UTC time, principal/network/replication scope, expected and observed positive/negative result, synthetic event IDs, RPO/RTO definition, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Cross-account denial tests, regional cutover and failback remain **Tabletop** without authorized disposable infrastructure.

### Lab 12 — Design replication approach

**Procedure:** Assess MSK Replicator or MirrorMaker 2 support, topic filters, ACL/config replication and costs.

**Evidence and acceptance:** Capture approved AWS account alias/region, MSK type/version, EKS context, UTC time, principal/network/replication scope, expected and observed positive/negative result, synthetic event IDs, RPO/RTO definition, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Cross-account denial tests, regional cutover and failback remain **Tabletop** without authorized disposable infrastructure.

### Lab 13 — Review offset and failover strategy

**Procedure:** Document consumer group offsets, producer cutover, DNS/config changes and replay semantics.

**Evidence and acceptance:** Capture approved AWS account alias/region, MSK type/version, EKS context, UTC time, principal/network/replication scope, expected and observed positive/negative result, synthetic event IDs, RPO/RTO definition, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Cross-account denial tests, regional cutover and failback remain **Tabletop** without authorized disposable infrastructure.

### Lab 14 — Review data correctness ledger

**Procedure:** Plan unique event IDs, duplicate handling, ordering limits and reconciliation.

**Evidence and acceptance:** Capture approved AWS account alias/region, MSK type/version, EKS context, UTC time, principal/network/replication scope, expected and observed positive/negative result, synthetic event IDs, RPO/RTO definition, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Cross-account denial tests, regional cutover and failback remain **Tabletop** without authorized disposable infrastructure.

### Lab 15 — Review recovery point measurement

**Procedure:** Define timestamp/offset lag and actual RPO observation without invented metrics.

**Evidence and acceptance:** Capture approved AWS account alias/region, MSK type/version, EKS context, UTC time, principal/network/replication scope, expected and observed positive/negative result, synthetic event IDs, RPO/RTO definition, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Cross-account denial tests, regional cutover and failback remain **Tabletop** without authorized disposable infrastructure.

### Lab 16 — Review recovery time measurement

**Procedure:** Define RTO from incident detection to restored authenticated client processing.

**Evidence and acceptance:** Capture approved AWS account alias/region, MSK type/version, EKS context, UTC time, principal/network/replication scope, expected and observed positive/negative result, synthetic event IDs, RPO/RTO definition, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Cross-account denial tests, regional cutover and failback remain **Tabletop** without authorized disposable infrastructure.

### Lab 17 — Review backup and retention

**Procedure:** Assess Kafka replication versus true backups, retention, immutable copies and restore test.

**Evidence and acceptance:** Capture approved AWS account alias/region, MSK type/version, EKS context, UTC time, principal/network/replication scope, expected and observed positive/negative result, synthetic event IDs, RPO/RTO definition, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Cross-account denial tests, regional cutover and failback remain **Tabletop** without authorized disposable infrastructure.

### Lab 18 — Review production change gate

**Procedure:** Validate IAM/TLS, network, replication health, DR, cost, rollout and abort.

**Evidence and acceptance:** Capture approved AWS account alias/region, MSK type/version, EKS context, UTC time, principal/network/replication scope, expected and observed positive/negative result, synthetic event IDs, RPO/RTO definition, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Cross-account denial tests, regional cutover and failback remain **Tabletop** without authorized disposable infrastructure.

### Lab 19 — Rehearse DR incident tabletop

**Procedure:** Walk through source region outage, failover, security, lag, rollback/failback and communications.

**Evidence and acceptance:** Capture approved AWS account alias/region, MSK type/version, EKS context, UTC time, principal/network/replication scope, expected and observed positive/negative result, synthetic event IDs, RPO/RTO definition, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Cross-account denial tests, regional cutover and failback remain **Tabletop** without authorized disposable infrastructure.

### Lab 20 — Independent security/DR acceptance

**Procedure:** Score positive/negative access tests, RPO/RTO evidence, remediation and signoff.

**Evidence and acceptance:** Capture approved AWS account alias/region, MSK type/version, EKS context, UTC time, principal/network/replication scope, expected and observed positive/negative result, synthetic event IDs, RPO/RTO definition, cost, abort/rollback, owner and independent reviewer. Mark **Pending** until executed. Cross-account denial tests, regional cutover and failback remain **Tabletop** without authorized disposable infrastructure.

## 12. Read-only security/DR inventory script

Save as `verify-ch74.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${AWS_PROFILE:?Set approved AWS_PROFILE}"
: "${AWS_REGION:?Set AWS_REGION}"
: "${MSK_ARN:?Set approved MSK ARN}"
NS="${EKS_NS:-kafka-clients}"
echo '[1/9] AWS identity'; aws sts get-caller-identity
echo '[2/9] MSK cluster'; aws kafka describe-cluster-v2 --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
echo '[3/9] Bootstrap'; aws kafka get-bootstrap-brokers --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
echo '[4/9] Cluster policy (may be absent)'
aws kafka get-cluster-policy --cluster-arn "$MSK_ARN" --region "$AWS_REGION" || echo 'Policy unavailable/absent: investigate'
echo '[5/9] SCRAM associations (may be unsupported)'
aws kafka list-scram-secrets --cluster-arn "$MSK_ARN" --region "$AWS_REGION" || echo 'SCRAM API unavailable: investigate'
echo '[6/9] MSK operations'; aws kafka list-cluster-operations-v2 --cluster-arn "$MSK_ARN" --region "$AWS_REGION"
echo '[7/9] EKS context'; kubectl config current-context
echo '[8/9] EKS identity/policy'; kubectl -n "$NS" get serviceaccount,networkpolicy
echo '[9/9] EKS events'; kubectl -n "$NS" get events --sort-by=.metadata.creationTimestamp
echo 'PASS: read-only AWS/EKS inventory only.'
echo 'NOT PROVEN: private connectivity, IAM denial, replication, RPO/RTO or independent review.'
```

An API error is **not** a security pass. Follow up on denied or unsupported API calls; sanitize output. This script does not create DR infrastructure or validate cross-region event correctness.

## 13. Twelve security and DR failure scenarios

### Scenario 1 — Cross-VPC bootstrap times out

**Diagnosis:** Check connectivity mode, VPC routing, SG/NACL, DNS and supported cluster type. Correlate AWS cluster policy/IAM, VPC route/SG/DNS, Kafka TLS/SASL, replication tool state, source/destination offsets, EKS client logs and event-ID ledger. **Response:** Contain exposure, stop split writes, protect data, escalate security/SRE and apply approved recovery. **Exit:** Measured or explicitly tabletop RPO/RTO, restored authenticated clients, reconciled event IDs, RCA and independent approval.

### Scenario 2 — Bootstrap works but broker metadata fails

**Diagnosis:** Check all advertised broker endpoints, network paths and client listener type. Correlate AWS cluster policy/IAM, VPC route/SG/DNS, Kafka TLS/SASL, replication tool state, source/destination offsets, EKS client logs and event-ID ledger. **Response:** Contain exposure, stop split writes, protect data, escalate security/SRE and apply approved recovery. **Exit:** Measured or explicitly tabletop RPO/RTO, restored authenticated clients, reconciled event IDs, RCA and independent approval.

### Scenario 3 — IAM authentication denied across accounts

**Diagnosis:** Check cluster policy, caller role, resource ARNs, trust and client mechanism. Correlate AWS cluster policy/IAM, VPC route/SG/DNS, Kafka TLS/SASL, replication tool state, source/destination offsets, EKS client logs and event-ID ledger. **Response:** Contain exposure, stop split writes, protect data, escalate security/SRE and apply approved recovery. **Exit:** Measured or explicitly tabletop RPO/RTO, restored authenticated clients, reconciled event IDs, RCA and independent approval.

### Scenario 4 — SCRAM secret association rejected

**Diagnosis:** Check Secrets Manager secret format/name, KMS key, region and cluster support. Correlate AWS cluster policy/IAM, VPC route/SG/DNS, Kafka TLS/SASL, replication tool state, source/destination offsets, EKS client logs and event-ID ledger. **Response:** Contain exposure, stop split writes, protect data, escalate security/SRE and apply approved recovery. **Exit:** Measured or explicitly tabletop RPO/RTO, restored authenticated clients, reconciled event IDs, RCA and independent approval.

### Scenario 5 — TLS fails after CA/credential rotation

**Diagnosis:** Check trust chain, hostname verification, client restart and staged rollover. Correlate AWS cluster policy/IAM, VPC route/SG/DNS, Kafka TLS/SASL, replication tool state, source/destination offsets, EKS client logs and event-ID ledger. **Response:** Contain exposure, stop split writes, protect data, escalate security/SRE and apply approved recovery. **Exit:** Measured or explicitly tabletop RPO/RTO, restored authenticated clients, reconciled event IDs, RCA and independent approval.

### Scenario 6 — NetworkPolicy unexpectedly blocks Kafka

**Diagnosis:** Inspect EKS CNI policy enforcement, egress DNS and broker ports. Correlate AWS cluster policy/IAM, VPC route/SG/DNS, Kafka TLS/SASL, replication tool state, source/destination offsets, EKS client logs and event-ID ledger. **Response:** Contain exposure, stop split writes, protect data, escalate security/SRE and apply approved recovery. **Exit:** Measured or explicitly tabletop RPO/RTO, restored authenticated clients, reconciled event IDs, RCA and independent approval.

### Scenario 7 — Replication lag exceeds RPO

**Diagnosis:** Inspect source/destination throughput, topic filters, partition skew and network. Correlate AWS cluster policy/IAM, VPC route/SG/DNS, Kafka TLS/SASL, replication tool state, source/destination offsets, EKS client logs and event-ID ledger. **Response:** Contain exposure, stop split writes, protect data, escalate security/SRE and apply approved recovery. **Exit:** Measured or explicitly tabletop RPO/RTO, restored authenticated clients, reconciled event IDs, RCA and independent approval.

### Scenario 8 — DR consumer offsets diverge

**Diagnosis:** Inspect translation/sync support, replay, duplicate risk and group restart plan. Correlate AWS cluster policy/IAM, VPC route/SG/DNS, Kafka TLS/SASL, replication tool state, source/destination offsets, EKS client logs and event-ID ledger. **Response:** Contain exposure, stop split writes, protect data, escalate security/SRE and apply approved recovery. **Exit:** Measured or explicitly tabletop RPO/RTO, restored authenticated clients, reconciled event IDs, RCA and independent approval.

### Scenario 9 — Failover loses authentication

**Diagnosis:** Check destination IAM/TLS/SCRAM, role ARNs, network and client config. Correlate AWS cluster policy/IAM, VPC route/SG/DNS, Kafka TLS/SASL, replication tool state, source/destination offsets, EKS client logs and event-ID ledger. **Response:** Contain exposure, stop split writes, protect data, escalate security/SRE and apply approved recovery. **Exit:** Measured or explicitly tabletop RPO/RTO, restored authenticated clients, reconciled event IDs, RCA and independent approval.

### Scenario 10 — Region outage causes split writes

**Diagnosis:** Apply fencing and single-writer policy; preserve audit and event ledger. Correlate AWS cluster policy/IAM, VPC route/SG/DNS, Kafka TLS/SASL, replication tool state, source/destination offsets, EKS client logs and event-ID ledger. **Response:** Contain exposure, stop split writes, protect data, escalate security/SRE and apply approved recovery. **Exit:** Measured or explicitly tabletop RPO/RTO, restored authenticated clients, reconciled event IDs, RCA and independent approval.

### Scenario 11 — Failback replays or skips events

**Diagnosis:** Review offset reconciliation, source of truth, idempotence and correctness. Correlate AWS cluster policy/IAM, VPC route/SG/DNS, Kafka TLS/SASL, replication tool state, source/destination offsets, EKS client logs and event-ID ledger. **Response:** Contain exposure, stop split writes, protect data, escalate security/SRE and apply approved recovery. **Exit:** Measured or explicitly tabletop RPO/RTO, restored authenticated clients, reconciled event IDs, RCA and independent approval.

### Scenario 12 — Change window ends with hidden data loss

**Diagnosis:** Compare event IDs, replication lag, acknowledgments and consumer outcomes. Correlate AWS cluster policy/IAM, VPC route/SG/DNS, Kafka TLS/SASL, replication tool state, source/destination offsets, EKS client logs and event-ID ledger. **Response:** Contain exposure, stop split writes, protect data, escalate security/SRE and apply approved recovery. **Exit:** Measured or explicitly tabletop RPO/RTO, restored authenticated clients, reconciled event IDs, RCA and independent approval.

## 14. Eight production runbooks

### Runbook A — MSK IAM/SCRAM/TLS security incident

**Trigger/response:** Contain principals, review role/secret/cert state, restore least privilege and preserve logs. **No-go:** unapproved public access, leaked credentials, split-brain writers, unknown replication lag, unsafe consumer offsets, missing rollback/failback or unsupported API. **Exit:** Least-privilege connectivity, single-writer state, event correctness, measured or explicitly tabletop RPO/RTO, audit and signoff.

### Runbook B — Cross-VPC and cross-account connectivity outage

**Trigger/response:** Trace broker DNS, SG/NACL, routes, IAM cluster policy and client endpoint. **No-go:** unapproved public access, leaked credentials, split-brain writers, unknown replication lag, unsafe consumer offsets, missing rollback/failback or unsupported API. **Exit:** Least-privilege connectivity, single-writer state, event correctness, measured or explicitly tabletop RPO/RTO, audit and signoff.

### Runbook C — Unapproved public access or secret exposure

**Trigger/response:** Isolate endpoint, revoke/rotate, assess tenant impact and escalate security. **No-go:** unapproved public access, leaked credentials, split-brain writers, unknown replication lag, unsafe consumer offsets, missing rollback/failback or unsupported API. **Exit:** Least-privilege connectivity, single-writer state, event correctness, measured or explicitly tabletop RPO/RTO, audit and signoff.

### Runbook D — Replication lag and DR RPO breach

**Trigger/response:** Assess source/destination health, network, filter/offset state and data integrity. **No-go:** unapproved public access, leaked credentials, split-brain writers, unknown replication lag, unsafe consumer offsets, missing rollback/failback or unsupported API. **Exit:** Least-privilege connectivity, single-writer state, event correctness, measured or explicitly tabletop RPO/RTO, audit and signoff.

### Runbook E — Regional failover

**Trigger/response:** Confirm incident declaration, fencing, lag/RPO, destination security and client cutover. **No-go:** unapproved public access, leaked credentials, split-brain writers, unknown replication lag, unsafe consumer offsets, missing rollback/failback or unsupported API. **Exit:** Least-privilege connectivity, single-writer state, event correctness, measured or explicitly tabletop RPO/RTO, audit and signoff.

### Runbook F — Regional failback

**Trigger/response:** Review divergence, offsets, duplicate protection, controlled single-writer transition. **No-go:** unapproved public access, leaked credentials, split-brain writers, unknown replication lag, unsafe consumer offsets, missing rollback/failback or unsupported API. **Exit:** Least-privilege connectivity, single-writer state, event correctness, measured or explicitly tabletop RPO/RTO, audit and signoff.

### Runbook G — Production network/auth change

**Trigger/response:** Require approved diff, EKS smoke, rollback and monitoring. **No-go:** unapproved public access, leaked credentials, split-brain writers, unknown replication lag, unsafe consumer offsets, missing rollback/failback or unsupported API. **Exit:** Least-privilege connectivity, single-writer state, event correctness, measured or explicitly tabletop RPO/RTO, audit and signoff.

### Runbook H — Independent DR/security acceptance

**Trigger/response:** Verify RTO/RPO, security negative tests, event ledger, RCA and signoff. **No-go:** unapproved public access, leaked credentials, split-brain writers, unknown replication lag, unsafe consumer offsets, missing rollback/failback or unsupported API. **Exit:** Least-privilege connectivity, single-writer state, event correctness, measured or explicitly tabletop RPO/RTO, audit and signoff.

## 15. Evidence package

```text
evidence-ch74/
  security-dr-charter.md
  cluster-security-inventory.md
  iam-authorization-matrix.md
  eks-workload-identity.md
  scram-tls-kms-lifecycle.md
  vpc-security-groups.md
  dns-broker-endpoints.md
  multi-vpc-architecture.md
  cross-account-policies.md
  eks-networkpolicy.md
  dr-topology.md
  replication-tool-review.md
  consumer-offset-cutover.md
  synthetic-event-ledger.csv
  rpo-measurement.md
  rto-measurement.md
  backup-retention-restore.md
  change-gates.md
  regional-outage-tabletop.md
  independent-security-dr-signoff.md
  scorecard.md
```

Each artifact requires exact versions, AWS region/account scope, UTC time, expected/observed result, **Live** vs **Tabletop**, sanitized evidence, RPO/RTO, owner, abort/rollback and independent reviewer.

## 16. 100-point MSK security and DR assessment

| Domain | Points | Critical |
|---|---:|---|
| IAM/TLS/SCRAM and tenant authorization | 20 | Yes |
| Multi-VPC, cross-account and EKS networking | 20 | Yes |
| Cross-region replication and DR architecture | 20 | Yes |
| Consumer offsets, event correctness, RPO/RTO | 20 | Yes |
| Change management, runbooks and security response | 15 | Yes |
| Independent technical/security review | 5 | Yes |
| **Total** | **100** | |

**Pass:** ≥85/100 with all critical gates independently evidenced. **Automatic Fail:** leaked credential, unapproved public listener, unauthorized tenant read, active split writers, fabricated live RPO/RTO, silent data loss or absent independent security review.

## 17. References and next chapter

**References:** [Amazon MSK Developer Guide](https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html), [MSK IAM Access Control](https://docs.aws.amazon.com/msk/latest/developerguide/iam-access-control.html), [Amazon MSK Replicator](https://docs.aws.amazon.com/msk/latest/developerguide/msk-replicator.html), [Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html), [Apache Kafka](https://kafka.apache.org/documentation/).

**Next:** Chapter 075 — Amazon MSK Enterprise SRE Operations, Disaster Recovery and Security Acceptance Capstone.

---

**Verification boundary:** Publication proves document availability only. Live multi-VPC reachability, IAM denial tests, replication, failover/failback RPO/RTO, event correctness and independent technical/security review remain Pending.
