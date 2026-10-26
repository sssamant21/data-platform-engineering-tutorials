# Chapter 027 TLS, mTLS and scoped authorization acceptance

Run `python kafka/qa/run_chapter_027.py` against the dedicated disposable
Kafka 4.0.0/KRaft/Strimzi 0.47.0 fixture. The fixture has three persistent
brokers, RF3/minISR2, a separate internal TLS listener with client-certificate
authentication, the User Operator and the simple authorizer. Anonymous access
is not granted. Existing earlier chapter fixtures are unchanged.

## Measurable runtime criteria

- Verify actual listener status, served Kafka/KafkaUser API versions, the simple
  authorizer and a pullable client image digest obtained from the running broker.
- Create a uniquely owned TLS KafkaUser with literal topic/group ACLs, plus
  Cluster Describe and IdempotentWrite for diagnostic metadata and idempotence.
  A different owned topic must reject that valid identity with an authorization
  error. No superuser or All permission is used.
- Mount only the public cluster CA and the client's PKCS12/password keys as
  read-only, non-world-readable projections in a non-root Job. Disable API token
  mounting; verify the dedicated ServiceAccount cannot get/list/watch Secrets.
  Secret inventory contains only object identity, resource version and key names.
- Verify valid client identity binding, certificate validity and public metadata;
  authenticate bootstrap and all advertised brokers using the cluster CA with
  hostname verification enabled. Wrong trust, wrong hostname and a missing
  client certificate must fail with classified TLS/authentication errors.
- Produce six deterministic acks=all records per fresh client Job, reconcile
  exact partition offsets and values, commit offsets and verify a second Job
  resumes with the same identity. Maintain RF3 and full ISR throughout the check.

JSON evidence records checks, public observations, image digest, safe Secret
metadata, scope and limitations. Kubernetes diagnostics and client logs are
sanitized before upload; discovered private credential material makes the run
fail. Jobs, API calls, TLS sockets and workflow execution have bounded timeouts.
Only uniquely owned synthetic resources are cleaned up before kind teardown.

## Explicit unexecuted gates

A reconnect using the same identity is not renewal or Secret rotation proof.
Expired-client rejection, on-demand client renewal, live CA renewal/key rotation,
trust overlap, revocation and production expiry alert pipelines are NOT_EXECUTED.
Strimzi 0.47.0 documents force renewal of CA certificates; the later user-level
force-renew feature cannot be assumed for this pinned version. The test does not
accelerate expiry by deleting Secrets, changing clocks or mutating a CA. A live
CA rotation needs its separate approved exercise and evidence.

The pinned [deployment guide](https://strimzi.io/docs/operators/0.47.0/deploying)
and [configuration reference](https://strimzi.io/docs/operators/0.47.0/configuring)
define the TLS listener, KafkaUser PKCS12 identity and simple authorization used
here. These successful lab checks provide no production PKI, network-isolation,
external-listener, multi-zone or independent security certification. Enterprise
certification remains NOT_CERTIFIED and independent signoff remains PENDING.
