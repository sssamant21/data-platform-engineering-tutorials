# Phase 5.2 — Chapter 001 Kubernetes Kafka Lab Certification

**Scope:** Chapter 001 — Kafka Architecture and Distributed Streaming Fundamentals.  
**Execution platform:** disposable GitHub-hosted kind cluster, Strimzi 0.47.0, Kafka 4.0.0 KRaft.  
**Status:** LAB DEFINED / RUNTIME NOT YET CERTIFIED.

## Objective

Demonstrate that the Strimzi operator reconciles a KRaft Kafka cluster, that a KafkaTopic exists, and that two events can be produced and consumed. This validates the Chapter 001 Kubernetes-first **basic architecture and messaging path**, not its six-pod HA architecture, failure recovery, or production durability claims.

## Prerequisites

Use the existing [Phase 4 runtime workflow](../../../.github/workflows/kafka-strimzi-runtime.yml) and [single-node fixture](../runtime/strimzi-single-node.yaml). The workflow creates its own `kind-kafka-qa` context and `kafka-qa` namespace. **Never run this against production or a shared Kubernetes cluster.**

## Automated execution

The [Chapter 001 acceptance script](../certify_chapter_001.py) is executed by the dedicated [Chapter 001 certification workflow](../../../.github/workflows/kafka-chapter-001-certification.yml), which provisions a fresh cluster, installs Strimzi, applies the same version-pinned fixture, and then runs this acceptance test.

1. Open **Actions → Kafka Chapter 001 Lab Certification**.
2. Select **Run workflow** on `main`.
3. Inspect the job result and download the uploaded `chapter-001-certification-<run-id>` artifact.
4. Check `chapter-001-result.json` for all four checks: `kafka_ready`, `topic_ready`, `produce`, `consume_verify`.
5. Record the GitHub Actions run URL and artifact identifier as chapter-level evidence.

## Acceptance criteria

| Check | Expected |
|---|---|
| Cluster isolation | Current Kubernetes context is exactly `kind-kafka-qa` |
| Operator reconciliation | `kafka/qa-kafka` Ready |
| Topic reconciliation | `kafkatopic/qa-smoke` Ready |
| End-to-end delivery | Exactly two unique Chapter 001 records produced and consumed |
| Evidence | JSON result and sanitized diagnostic files uploaded, including on failure |

A successful workflow certifies only the **basic messaging lab** of Chapter 001. The chapter's HA six-pod lab and broker failure/recovery exercise require separate tests. Do not change overall Chapter 001 certification to `CERTIFIED` until all mandatory chapter exercises are mapped and validated.

## Failure triage

Inspect the operator logs, `kubectl -n kafka-qa get kafka,kafkanodepools,kafkatopics,pods`, and namespace events in the artifact. Fix the test or fixture and rerun; do not attribute a shared Phase 4 smoke-test result to Chapter 001.

## Cleanup

The GitHub-hosted runner and its kind cluster are disposable. The workflow has no credentials or commands targeting external Kafka clusters. No laptop installation is required.
