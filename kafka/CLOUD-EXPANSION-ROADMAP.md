# Kafka Multi-Cloud Expansion Roadmap — Chapters 101–120

**Original curriculum:** 001–100 published. **Expanded target:** 120. **Cloud expansion status:** planned, not published unless explicitly listed in STATUS.md. **Live labs/security review:** pending.

## Part 21 — Microsoft Azure Kafka Engineering & SRE (101–110)

- 101 — Azure Kafka Architecture: AKS + Strimzi vs Azure Event Hubs Kafka Endpoint
- 102 — Provision AKS, Networking, Storage and Strimzi KRaft
- 103 — Azure Kafka Identity, Entra ID, TLS, SASL, ACL and Secrets
- 104 — Azure Event Hubs Kafka Compatibility, Limits and Client Migration
- 105 — Azure Kafka Producers, Consumers, Topics and Data Pipelines
- 106 — Azure Kafka Observability, Azure Monitor, Prometheus and SLOs
- 107 — Azure Kafka Performance, Capacity, Disk and FinOps
- 108 — Azure Kafka HA, Availability Zones, Backup and DR
- 109 — Azure Kafka Incident Response, Security and Upgrade Operations
- 110 — Azure Kafka Enterprise Production Capstone and Acceptance

## Part 22 — Google Cloud Kafka Engineering & SRE (111–120)

- 111 — Google Cloud Kafka Architecture: GKE + Strimzi vs Managed Service for Apache Kafka
- 112 — Provision GKE, Networking, Storage and Strimzi KRaft
- 113 — Google Cloud Kafka IAM, TLS, Authentication, ACL and Secrets
- 114 — Google Cloud Managed Service for Apache Kafka Operations and Compatibility
- 115 — Google Cloud Kafka Producers, Consumers, Topics and Data Pipelines
- 116 — Google Cloud Kafka Observability, Cloud Monitoring, Prometheus and SLOs
- 117 — Google Cloud Kafka Performance, Capacity, Storage and FinOps
- 118 — Google Cloud Kafka HA, Zones, Backup and DR
- 119 — Google Cloud Kafka Incident Response, Security and Upgrade Operations
- 120 — Google Cloud Kafka Enterprise Production Capstone and Acceptance

## Architecture choices

Azure track compares **Apache Kafka on AKS with Strimzi KRaft** and **Azure Event Hubs Kafka-compatible endpoint**. Event Hubs is a managed event streaming service, not a full drop-in Kafka broker; verify supported Kafka APIs, feature limitations, client authentication, retention, partitions, transactions, tooling and migration behavior against current Microsoft documentation.

Google Cloud track compares **Apache Kafka on GKE with Strimzi KRaft** and **Google Cloud Managed Service for Apache Kafka**. Verify supported features, Kafka versions, regional availability, identity, networking, quotas, backups, operational boundaries and service documentation before designing production labs.

## Chapter quality and validation

Every chapter must contain: architecture and decision criteria; cloud-specific prerequisites and IaC/GitOps; Kubernetes-first Strimzi KRaft lab plus managed-service comparison where applicable; commands and manifest samples; synthetic producer/consumer/Connect or CDC scenario; metrics and alerts; 10+ hands-on labs; failure scenarios; SRE runbooks; 100-point acceptance; evidence format; security, FinOps and HA/DR controls. Do not claim a live lab, provider feature or independent review without evidence.

**Publication ≠ runtime certification.** Chapter status must separately track published, live lab executed, and independently reviewed.
