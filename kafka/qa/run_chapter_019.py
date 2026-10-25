#!/usr/bin/env python3
"""Chapter 019 Kubernetes-run transaction acceptance; no production certification."""
import subprocess
import sys
from runtime_acceptance import Lab

CHECKS = ['topics_rf3_isr3_minisr2', 'commit_abort_isolation',
          'open_transaction_blocks_read_committed', 'abort_releases_last_stable_offset',
          'old_producer_fenced_new_owner_commits', 'six_durable_input_events',
          'aborted_output_and_offsets_unchanged', 'atomic_output_and_offsets_committed',
          'exact_output_id_reconciliation', 'restart_resumes_transactional_offsets', 'final_full_isr']
LIMITATIONS = ['Kafka-to-Kafka transaction guarantees only; no external database/API exactly-once claim.',
               'No broker failure, multi-zone recovery or production latency/RTO certification.',
               'Disposable plaintext listener; TLS/SASL/ACL, application review and independent security signoff pending.']


def main():
    lab = Lab('019', LIMITATIONS)
    error = None
    try:
        lab.prepare()
        source, output = lab.topic('input'), lab.topic('output')
        lab.run_job('TransactionAcceptance', [source, output, lab.tag + '-group', lab.tag], CHECKS)
        lab.result['status'] = 'PASS'
        lab.result['runtime_scope'] = 'SUPPORTED_ACCEPTANCE_PASS'
    except (RuntimeError, OSError, subprocess.SubprocessError, KeyError, ValueError) as exc:
        error = exc
        print(str(exc), file=sys.stderr)
    return lab.finish(error)


if __name__ == '__main__':
    sys.exit(main())
