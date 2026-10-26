# Chapter 029 multi-tenant authorization acceptance

`python kafka/qa/run_chapter_029.py` independently provisions owned synthetic
identities/topics/groups against the persistent Kafka 4.0.0/KRaft/Strimzi 0.47.0
SCRAM fixture. Its separate kind workflow destroys the complete disposable cluster.
No application superusers, wildcard resource grants, ACL deletion or production
resources are involved. Chapter 028 shares the Java client and is regressed.

## Live measurable acceptance

- Verify all three brokers' actual StandardAuthorizer configuration with a fixed
  read-only properties whitelist. Reject default-open behavior and application
  superusers. Missing allow.everyone.if.no.acl.found uses Kafka 4.0's documented
  false default, supplemented by live denial on a topic with no matching ACL.
- Create two distinct SCRAM principals, topics, groups and transactional IDs with
  exact literal ACLs. Tenant cluster permission is only IdempotentWrite. A separate
  diagnostic principal has Cluster Describe solely for read-only effective ACL
  inventory; it cannot mutate ACLs and has no application topic grants.
- Compare native effective ACLs against the exact desired operations, resources,
  principal, literal pattern, ALLOW and host. Reject extra/cross-tenant grants and
  any prefix/wildcard ACL matching the no-ACL probe topic.
- For BOTH directions A-to-B and B-to-A, require explicit authorization exceptions
  for foreign-topic describe, produce and consume, foreign-group access on the
  tenant's OWN allowed topic, and a resource with no matching ACL. Network/TLS/SASL
  failures and timeouts cannot satisfy an authorization assertion.
- Before and after negatives, reconcile six deterministic acks=all records and
  exact committed offsets under the tenant's own group. Verify RF3/full ISR.
  Commit an owned transaction and consume its acknowledged record with
  read_committed; reject initialization of the foreign transactional ID.
- Independently bind each authenticated principal to exact foreign-topic denial
  records from native broker authorizer logs. Secret names alone are not identity
  evidence. Log identities and payloads are synthetic and disposable.
- Dedicated non-root client Jobs mount only their own read-only password plus
  public CA; no API token. Authorized RBAC reviews must deny get/list/watch Secrets
  and patching Kafka/KafkaUser/KafkaTopic CRs. Impersonation errors do not count.

Kafka's [4.0 ACL documentation](https://kafka.apache.org/40/security/authorization-and-acls/)
defines the StandardAuthorizer default and resource semantics. Strimzi's pinned
[configuration reference](https://strimzi.io/docs/operators/0.47.0/configuring)
defines the simple authorizer and KafkaUser resource/operation types.

## Evidence and assessment boundaries

JSON records exact effective grants, before/after positive outcomes, each classified
negative, principal records, RBAC denials, safe authorizer metadata and pending gates.
Kubernetes diagnostics and secret-safe client logs are captured under bounded
API/Job/workflow deadlines. The sanitizer fails closed on private material before
artifact upload. Cleanup touches owned resources, then kind teardown discards the lab.

This single-namespace, single-host lab does not prove namespace/admission isolation,
CNI-enforced NetworkPolicy, external firewalls or multi-zone resilience. No broad
NetworkPolicy is applied to broker/controller paths. OAuth mapping, signed GitOps
approval, break-glass governance, production alerts and independent assessor signoff
remain pending. The observed desired/effective drift comparison covers owned users,
not production-wide recertification. Publication and supported runtime acceptance
are distinct from the manuscript's full critical-gate assessment. No numeric security
score or enterprise certification is awarded; certification remains NOT_CERTIFIED.
