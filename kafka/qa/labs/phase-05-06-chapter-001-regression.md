# Phase 5.6 — Chapter 001 Recovery Regression Gate

**Status:** automated regression checks published; GitHub Actions result pending.

The Chapter 001 single-broker, three-node and six-Pod recovery tests require a replacement Pod with a **different Kubernetes UID** and a ready Kafka container before reporting recovery. Kafka CR `Ready` alone is insufficient because it may temporarily remain true while deletion/recreation is in flight.

The [regression workflow](../../../.github/workflows/kafka-chapter-001-regression.yml) runs automatically when recovery scripts or this test change, and also supports manual execution. It performs Python syntax and source-level safety invariant checks. It does **not** start Kubernetes or prove recovery functionality. The dedicated runtime workflows must still pass and provide their own JSON artifacts.

## Run

Open Actions → **Kafka Chapter 001 Recovery Regression** → **Run workflow**. Review the job output. A passing result is a static guard only, not Chapter 001 certification.
