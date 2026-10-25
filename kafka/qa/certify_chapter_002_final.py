#!/usr/bin/env python3
"""Strict Chapter 002 certification gate. Requires fresh workflow evidence."""
import json
import os
import pathlib
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(os.environ.get("EVIDENCE_ROOT", "kafka/qa/evidence/chapter-002-final"))
OUTPUT = pathlib.Path("kafka/qa/evidence/chapter-002-final-certification.json")
REQUIRED = {
    "partition-ordering": {
        "file": "chapter-002-certification.json",
        "checks": ["three_partitions_three_replicas", "keyed_produce_acks_all",
                   "same_key_same_partition", "partition_order_and_offsets"],
    },
    "offset-recovery": {
        "file": "chapter-002-offset-recovery.json",
        "checks": ["baseline_produced", "explicit_commit_sync",
                   "committed_offsets_visible", "resume_after_restart",
                   "fresh_group_replay"],
    },
    "consumer-rebalance": {
        "file": "chapter-002-rebalance-result.json",
        "checks": ["three_partition_topic", "single_consumer_three_partitions",
                   "balanced_group_assignment", "survivor_reassigned_three_partitions",
                   "replacement_consumer_rebalance"],
    },
    "consumer-lag": {
        "file": "chapter-002-lag-result.json",
        "checks": ["five_new_records", "initial_offset_commit",
                   "lag_before_consumption", "commit_after_consumption",
                   "lag_zero_after_commit", "restart_at_committed_end",
                   "explicit_seek_replay", "replay_does_not_change_commit"],
    },
}

def main():
    result = {
        "chapter": "002",
        "status": "NOT_CERTIFIED",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "labs": {},
        "rule": "All four latest workflow runs must succeed and all required evidence checks must PASS.",
    }
    for lab, spec in REQUIRED.items():
        entry = {"status": "FAIL", "errors": []}
        result["labs"][lab] = entry
        manifest_path = ROOT / lab / "run.json"
        evidence_path = ROOT / lab / spec["file"]
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            entry["run_id"] = manifest.get("databaseId")
            entry["head_sha"] = manifest.get("headSha")
            entry["conclusion"] = manifest.get("conclusion")
            entry["workflow"] = manifest.get("workflowName")
            if manifest.get("conclusion") != "success":
                entry["errors"].append("Latest workflow run did not succeed")
            if not isinstance(manifest.get("databaseId"), int) or not manifest.get("headSha"):
                entry["errors"].append("Missing run provenance")
            if evidence.get("chapter") != "002" or evidence.get("status") != "PASS":
                entry["errors"].append("Evidence is not a Chapter 002 PASS result")
            checks = evidence.get("checks", {})
            for check in spec["checks"]:
                if checks.get(check) != "PASS":
                    entry["errors"].append("Missing PASS: " + check)
            if not entry["errors"]:
                entry["status"] = "PASS"
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
            entry["errors"].append("Missing or invalid artifact: " + str(exc))
    if all(x["status"] == "PASS" for x in result["labs"].values()):
        result["status"] = "CERTIFIED"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "CERTIFIED" else 1

if __name__ == "__main__":
    sys.exit(main())
