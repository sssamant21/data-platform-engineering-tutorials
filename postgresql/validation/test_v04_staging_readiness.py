#!/usr/bin/env python3
"""V04 offline evidence gate regression; all inputs are SYNTHETIC.

Tests never contact databases or cloud/HA systems and never exercise fencing.
An evidence-complete fixture is not a certified staging environment.
"""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import v04_staging_readiness as gate

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)


def utc(delta: timedelta = timedelta()) -> str:
    return (NOW + delta).isoformat()


def attestation(name: str) -> dict:
    return {"name": name, "approved_at_utc": utc(timedelta(hours=-1)),
            "evidence_ref": f"evidence://synthetic/approval-{name.lower()}"}


def synthetic_complete() -> dict:
    """Synthetic metadata fixture only; never reuse as staging authorization."""
    return {
        "schema": gate.SCHEMA, "mode": "evidence_review_only",
        "environment": "staging", "environment_id": "synthetic-staging-fixture",
        "change_ticket": "SYNTHETIC-TEST-ONLY",
        "change_ticket_ref": "evidence://synthetic/change",
        "window_start_utc": utc(timedelta(hours=-1)),
        "window_end_utc": utc(timedelta(hours=1)),
        "cluster": {
            "postgres_major": 18, "system_identifier": "1234567890123456789",
            "old_primary": {"node_id": "old-A", "endpoint": "127.0.0.1:55432",
                            "pgdata": "/tmp/synthetic-old", "role": "primary"},
            "candidate": {"node_id": "standby-B", "endpoint": "127.0.0.1:55433",
                          "pgdata": "/tmp/synthetic-standby", "role": "standby"},
            "topology_evidence_ref": "evidence://synthetic/topology",
        },
        "approvals": {
            "dbre": attestation("Reviewer-A"),
            "application_owner": attestation("Reviewer-B"),
            "fencing_owner": attestation("Reviewer-C"),
            "change_manager": attestation("Reviewer-D"),
        },
        "approved_objectives": {
            # These numbers are SYNTHETIC TEST VALUES, not suggested SLOs.
            "ha_rpo_seconds": 1, "ha_rto_seconds": 30,
            "pitr_rpo_seconds": 60, "pitr_rto_seconds": 300,
            "approval_evidence_ref": "evidence://synthetic/objectives",
        },
        "baseline": {
            "observed_at_utc": utc(timedelta(minutes=-5)),
            "healthy": True, "evidence_ref": "evidence://synthetic/baseline",
            "candidate_marker_replayed": True,
            "candidate_replay_evidence_ref": "evidence://synthetic/replay",
            "replay_gap_bytes": 0,
        },
        "fencing": {
            "mechanism": "synthetic-independent-mechanism",
            "evidence_ref": "evidence://synthetic/fence",
            "verified_at_utc": utc(timedelta(minutes=-5)),
            "observer": "Independent-Observer",
            "direct_write_denied": True,
            "old_primary_restart_denied": True,
            "orchestrator_restart_denied": True,
            "routing_bypass_denied": True,
            "storage_exclusion_verified": True,
            "independent_observation_confirmed": True,
        },
        "backup": {
            "base_backup_verified": True, "wal_archive_verified": True,
            "isolated_restore_verified": True,
            "evidence_ref": "evidence://synthetic/recovery",
        },
        "application": {
            "routing_smoke_plan_verified": True,
            "rollback_route_verified": True,
            "evidence_ref": "evidence://synthetic/application",
        },
        "rollback": {
            "rejoin_or_rebuild_plan_verified": True,
            "incident_owner_assigned": True,
            "evidence_ref": "evidence://synthetic/rollback",
        },
    }


def inspect(document) -> dict:
    return gate.screen(document, now=NOW)


class V04GateTests(unittest.TestCase):
    def assert_blocks(self, document: dict, code: str):
        result = inspect(document)
        self.assertEqual("NO_GO", result["result"])
        self.assertIn(code, result["reason_codes"])
        self.assertEqual("NONE", result["authorization"])
        self.assertEqual("NEVER", result["execution"])

    def test_metadata_complete_still_does_not_authorize_action(self):
        result = inspect(synthetic_complete())
        self.assertEqual("EVIDENCE_COMPLETE_FOR_INDEPENDENT_REVIEW", result["result"])
        self.assertEqual([], result["reason_codes"])
        self.assertEqual("NONE", result["authorization"])
        self.assertEqual("NEVER", result["execution"])
        self.assertIn("does not authenticate", result["note"])

    def test_template_is_always_blocked(self):
        import json
        doc = json.loads((HERE / "v04_staging_evidence.template.json").read_text())
        result = inspect(doc)
        self.assertEqual("NO_GO", result["result"])
        self.assertGreaterEqual(len(result["reason_codes"]), 10)

    def test_production_or_unexpected_mode_is_never_accepted(self):
        for environment in ("production", "prod", "shared-staging", "", None):
            with self.subTest(environment=environment):
                doc = synthetic_complete()
                doc["environment"] = environment
                self.assert_blocks(doc, "non_staging_environment_refused")
        doc = synthetic_complete()
        doc["mode"] = "promote"
        self.assert_blocks(doc, "non_review_mode_refused")

    def test_time_and_staleness_are_hard_gates(self):
        for key, value, code in (
            ("window_start_utc", utc(timedelta(minutes=1)),
             "maintenance_window_not_current"),
            ("window_end_utc", utc(timedelta(hours=-2)),
             "maintenance_window_invalid"),
        ):
            with self.subTest(key=key):
                doc = synthetic_complete()
                doc[key] = value
                self.assert_blocks(doc, code)
        doc = synthetic_complete()
        doc["baseline"]["observed_at_utc"] = utc(timedelta(hours=-1))
        self.assert_blocks(doc, "healthy_fresh_baseline_missing")
        doc = synthetic_complete()
        doc["fencing"]["verified_at_utc"] = utc(timedelta(hours=-1))
        self.assert_blocks(doc, "independent_fencing_observation_stale")

    def test_incomplete_independent_fencing_fails_closed(self):
        for item in gate.REQUIRED_FENCE:
            with self.subTest(item=item):
                doc = synthetic_complete()
                doc["fencing"][item] = False
                self.assert_blocks(doc, f"fence_{item}_unproven")
        doc = synthetic_complete()
        doc["fencing"]["observer"] = doc["approvals"]["dbre"]["name"]
        self.assert_blocks(doc, "independent_fencing_observer_missing")

    def test_missing_and_duplicate_approvals(self):
        doc = synthetic_complete()
        del doc["approvals"]["fencing_owner"]
        self.assert_blocks(doc, "approval_fencing_owner_missing_or_stale")
        doc = synthetic_complete()
        doc["approvals"]["change_manager"]["name"] = doc["approvals"]["dbre"]["name"]
        self.assert_blocks(doc, "approvers_not_independent")
        doc = synthetic_complete()
        doc["approvals"]["dbre"] = []
        self.assert_blocks(doc, "approval_dbre_missing_or_stale")
        doc = synthetic_complete()
        doc["approvals"]["dbre"]["approved_at_utc"] = utc(timedelta(days=-15))
        self.assert_blocks(doc, "approval_dbre_missing_or_stale")

    def test_unapproved_thresholds_are_not_invented(self):
        for item in gate.METRICS:
            for value in (None, 0, -1, True, float("inf"), "10"):
                with self.subTest(item=item, value=value):
                    doc = synthetic_complete()
                    doc["approved_objectives"][item] = value
                    self.assert_blocks(doc, f"objective_{item}_missing")

    def test_replay_backup_routing_and_rebuild_are_mandatory(self):
        doc = synthetic_complete()
        doc["baseline"]["candidate_marker_replayed"] = False
        self.assert_blocks(doc, "candidate_replay_proof_missing")
        doc = synthetic_complete()
        doc["backup"]["wal_archive_verified"] = False
        self.assert_blocks(doc, "backup_wal_archive_verified_unproven")
        doc = synthetic_complete()
        doc["application"]["routing_smoke_plan_verified"] = False
        self.assert_blocks(doc, "application_routing_smoke_plan_verified_unproven")
        doc = synthetic_complete()
        doc["rollback"]["rejoin_or_rebuild_plan_verified"] = False
        self.assert_blocks(doc, "rollback_rejoin_or_rebuild_plan_verified_unproven")

    def test_identity_and_evidence_references_refused(self):
        doc = synthetic_complete()
        doc["cluster"]["candidate"]["pgdata"] = doc["cluster"]["old_primary"]["pgdata"]
        self.assert_blocks(doc, "same_node_pgdata")
        doc = synthetic_complete()
        doc["cluster"]["topology_evidence_ref"] = "<REPLACE-TOPOLOGY>"
        self.assert_blocks(doc, "topology_evidence_missing")
        doc = synthetic_complete()
        doc["cluster"]["postgres_major"] = 17
        self.assert_blocks(doc, "postgres18_identity_required")

    def test_password_fields_cannot_be_written_to_evidence(self):
        doc = synthetic_complete()
        doc["backup"]["password"] = "must-not-be-in-record"
        self.assert_blocks(doc, "sensitive_keys_not_allowed")

    def test_malformed_file_rejected_with_nonzero_exit(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "malformed.json"
            p.write_text("{invalid", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(HERE / "v04_staging_readiness.py"),
                 "--evidence", str(p)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(2, proc.returncode)
            self.assertIn('"result": "NO_GO"', proc.stdout)

    def test_template_cli_rejects_instead_of_reporting_success(self):
        proc = subprocess.run(
            [sys.executable, str(HERE / "v04_staging_readiness.py"),
             "--evidence", str(HERE / "v04_staging_evidence.template.json")],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(2, proc.returncode)
        self.assertIn('"result": "NO_GO"', proc.stdout)


if __name__ == "__main__":
    unittest.main()
