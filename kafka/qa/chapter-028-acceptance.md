# Chapter 028 SASL_SSL, SCRAM credentials and Kubernetes identity acceptance

Run `python kafka/qa/run_chapter_028.py` against the independent persistent
Kafka 4.0.0/KRaft/Strimzi 0.47.0 fixture. Its parallel internal scramlab listener
uses TLS and SCRAM-SHA-512, retaining the mTLS listener and simple authorizer.
RF3/minISR2 remains mandatory. No application superuser or anonymous grants exist.

## Supported live acceptance

- Discover SASL bootstrap from listener status and verify served v1beta2 APIs,
  broker readiness and an immutable client image digest from a running broker.
- Create a scoped KafkaUser through the operator, literal topic/group ACLs,
  a dedicated token-free ServiceAccount and two owned immutable random password
  source Secrets. Record only Secret identities, versions and key names.
- Verify get/list/watch Secret API denial through authorized impersonation;
  mount only CA certificate and password as read-only 0440 files in non-root Jobs.
  Passwords enter neither shell arguments nor files on the Actions runner.
- Authenticate SASL_SSL through every advertised broker with hostname verification.
  Classify wrong-password and wrong-username SASL failures separately from
  wrong-CA TLS failure and authenticated unauthorized-topic rejection.
- Verify the actual SCRAM Kafka principal independently from native broker
  authorizer denial records matching the exact identity and denied topic.
- Produce and consume six deterministic acks=all records per successful Job,
  check RF3/full ISR and exact committed offsets, then resume after credential
  replacement with six more records under the same principal.
- Rotate via the supported KafkaUser password Secret reference, require Ready
  for the current observedGeneration and a changed generated Secret version,
  reconnect a fresh Job using the new generated credential, and reject the old
  credential mounted from the retained old source Secret. No operator-managed
  Secret is patched or deleted. ACLs remain identical across the change.

The pinned [Strimzi deployment guide](https://strimzi.io/docs/operators/0.47.0/deploying)
defines custom SCRAM password Secret references. The tagged
[User Operator implementation](https://github.com/strimzi/strimzi-kafka-operator/blob/0.47.0/user-operator/src/main/java/io/strimzi/operator/user/operator/KafkaUserOperator.java)
reconciles desired passwords to Kafka and generated user Secrets.

## Evidence and limits

JSON includes listener/identity metadata, per-stage outcomes, native principal
evidence and measured rotation completion time. This interval includes harness
work and deliberate negatives; it is not a production recovery SLO. Independent
Jobs do not establish uninterrupted traffic or overlapping credential validity.
Private-value redaction, including generated credential values and their base64
forms in memory, fails the run closed. The final sanitizer also scans diagnostics
before upload. Bounded API/client/Job/workflow deadlines constrain failures.
Cleanup touches only owned test resources before disposable kind teardown.

No reviewed supported external IdP is supplied. OAuth/OIDC/JWKS, issuer/audience
and token-expiry rejection, refresh, signing-key rotation and federated workload
identity remain NOT_EXECUTED. There is no invented security review or OAuth
success from SCRAM results. Production migration availability, alert routing,
namespace admission policy, encryption at rest, CNI/multi-zone resilience and
independent IAM assessment remain unvalidated. Publication, supported runtime
acceptance and enterprise certification are separate: certification is NOT_CERTIFIED.
