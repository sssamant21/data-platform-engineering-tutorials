#!/usr/bin/env python3
"""V04-B synthetic independent-review gate regression; NEVER staging authorization."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import v04_independent_review as gate
from test_v04_staging_readiness import synthetic_complete, NOW

TS = lambda minutes: (NOW + timedelta(minutes=minutes)).isoformat()


def review_complete(staging):
    return {
        "schema": gate.SCHEMA,
        "mode": "independent_evidence_review_only",
        "decision": "submit_to_change_authority",
        "environment": staging["environment"],
        "environment_id": staging["environment_id"],
        "change_ticket": staging["change_ticket"],
        "system_identifier": staging["cluster"]["system_identifier"],
        "window_start_utc": staging["window_start_utc"],
        "window_end_utc": staging["window_end_utc"],
        "staging_manifest_sha256": gate.digest(staging),
        "prepared_by": "Packet-Preparer",
        "prepared_at_utc": TS(-6),
        "reviewers": {
            role: {
                "name": f"Independent-{role}",
                "reviewed_at_utc": TS(-1),
                "disposition": "verified",
                "attestation_ref": f"evidence://synthetic/reviewer/{role}",
            }
            for role in gate.REVIEW_ROLES
        },
        "claims": {
            claim: {
                "status": "verified",
                "reviewer_role": role,
                "observed_at_utc": TS(-2),
                "evidence_ref": f"evidence://synthetic/{claim}",
                "evidence_sha256": "1234567890abcdef" * 4,
                **({"observed_from_independent_control_plane": True}
                   if claim.startswith("independent_fence_") else {}),
            }
            for claim, role in gate.CLAIMS.items()
        }
    }


class ReviewGateTests(unittest.TestCase):
    def setUp(self):
        self.staging = synthetic_complete()
        self.review = review_complete(self.staging)

    def evaluate(self):
        return gate.screen(self.staging, self.review, now=NOW)

    def blocks(self, code):
        result = self.evaluate()
        self.assertEqual(result["result"], "NO_GO", result)
        self.assertIn(code, result["reason_codes"])
        self.assertEqual(result["authorization"], "NONE")
        self.assertEqual(result["execution"], "NEVER")

    def test_synthetic_metadata_complete_still_has_no_authorization(self):
        result = self.evaluate()
        self.assertEqual(result["result"], "REVIEW_PACKET_COMPLETE_UNAUTHENTICATED")
        self.assertEqual(result["reason_codes"], [])
        self.assertEqual(result["authorization"], "NONE")
        self.assertEqual(result["execution"], "NEVER")
        self.assertFalse(result["reviewed_real_staging"])

    def test_blank_public_templates_are_both_no_go(self):
        stage=json.loads((HERE/"v04_staging_evidence.template.json").read_text())
        review=json.loads((HERE/"v04_independent_review.template.json").read_text())
        result=gate.screen(stage,review,now=NOW)
        self.assertEqual(result["result"], "NO_GO")
        self.assertIn("v04a_staging_no_go", result["reason_codes"])
        self.assertIn("reviewer_dbre_attestation_missing", result["reason_codes"])

    def test_bad_v04a_cannot_be_overridden_by_review(self):
        self.staging["fencing"]["direct_write_denied"]=False
        self.review["staging_manifest_sha256"]=gate.digest(self.staging)
        self.blocks("v04a_fence_direct_write_denied_unproven")

    def test_review_cannot_switch_to_production_or_action(self):
        self.review["environment"]="production"
        self.blocks("review_non_staging_environment")
        self.review=review_complete(self.staging)
        self.review["decision"]="promote_now"
        self.blocks("attempted_operational_decision")
        self.review=review_complete(self.staging)
        self.review["mode"]="operational"
        self.blocks("review_mode_invalid")

    def test_change_environment_and_identity_binding(self):
        for key, value in (("environment_id","other-stage"),
                           ("change_ticket","other-change"),
                           ("system_identifier","0000000000000000000")):
            with self.subTest(key=key):
                self.review=review_complete(self.staging)
                self.review[key]=value
                self.blocks(f"review_{key}_mismatch")

    def test_window_and_digest_binding(self):
        self.review["window_start_utc"]=TS(-90)
        self.blocks("review_window_start_utc_mismatch")
        self.review=review_complete(self.staging)
        self.review["staging_manifest_sha256"]="abcdef0123456789"*4
        self.blocks("staging_manifest_digest_mismatch")
        self.review=review_complete(self.staging)
        self.staging["baseline"]["replay_gap_bytes"]=1
        self.blocks("staging_manifest_digest_mismatch")

    def test_reviewer_cannot_be_preparer_or_initial_approver(self):
        self.review["reviewers"]["dbre"]["name"]=self.review["prepared_by"]
        self.blocks("reviewer_not_independent")
        self.review=review_complete(self.staging)
        self.review["reviewers"]["dbre"]["name"]=self.staging["approvals"]["dbre"]["name"]
        self.blocks("reviewer_not_independent")
        self.review=review_complete(self.staging)
        self.review["reviewers"]["security_fencing"]["name"]=self.review["reviewers"]["dbre"]["name"]
        self.blocks("reviewer_not_independent")

    def test_reviews_are_named_fresh_verified_and_referenced(self):
        self.review["reviewers"]["dbre"]["disposition"]="pending"
        self.blocks("reviewer_dbre_attestation_missing")
        self.review=review_complete(self.staging)
        self.review["reviewers"]["dbre"]["attestation_ref"]="<UNVERIFIED>"
        self.blocks("reviewer_dbre_attestation_missing")
        self.review=review_complete(self.staging)
        self.review["reviewers"]["security_fencing"]["reviewed_at_utc"]=TS(-60*24*8)
        self.blocks("reviewer_security_fencing_timestamp_invalid")
        self.review=review_complete(self.staging)
        self.review["reviewers"]["dbre"]["reviewed_at_utc"]=TS(-7)
        self.blocks("reviewer_dbre_timestamp_invalid")

    def test_fencing_must_have_independent_observation_claim(self):
        fence=self.review["claims"]["independent_fence_write_restart_and_bypass"]
        fence["observed_from_independent_control_plane"]=False
        self.blocks("independent_control_plane_observation_missing")
        self.review=review_complete(self.staging)
        self.review["claims"]["independent_fence_write_restart_and_bypass"]["observed_at_utc"]=TS(-10)
        self.blocks("fence_review_predates_fence_evidence")

    def test_every_claim_requires_approved_review_role_and_evidence(self):
        for key, role in gate.CLAIMS.items():
            with self.subTest(key=key):
                self.review=review_complete(self.staging)
                self.review["claims"][key]["status"]="pending"
                self.blocks(f"claim_{key}_not_independently_verified")
                self.review=review_complete(self.staging)
                self.review["claims"][key]["evidence_sha256"]="0"*64
                self.blocks(f"claim_{key}_evidence_missing")
                self.review=review_complete(self.staging)
                self.review["claims"][key]["reviewer_role"]="other"
                self.blocks(f"claim_{key}_not_independently_verified")

    def test_missing_packet_or_observation_is_no_go(self):
        self.review.pop("claims")
        self.blocks("claim_cluster_and_scope_not_independently_verified")
        self.review=review_complete(self.staging)
        self.review["claims"]["backup_archive_restore"]["observed_at_utc"]="not-an-utc-time"
        self.blocks("claim_backup_archive_restore_timestamp_invalid")

    def test_stale_staging_fence_and_expired_window_are_no_go(self):
        self.staging["fencing"]["verified_at_utc"]=TS(-35)
        self.review["staging_manifest_sha256"]=gate.digest(self.staging)
        self.blocks("v04a_independent_fencing_observation_stale")
        self.staging=synthetic_complete()
        self.staging["window_end_utc"]=TS(-1)
        self.review=review_complete(self.staging)
        self.blocks("v04a_maintenance_window_not_current")

    def test_sensitive_keys_disallowed_in_review(self):
        self.review["reviewers"]["dbre"]["access_token"]="DO_NOT_STORE_SECRETS"
        self.blocks("secret_keys_in_review_packet")

    def test_malformed_json_nonzero_and_no_operational_actions(self):
        with tempfile.TemporaryDirectory() as path:
            a=Path(path)/"a.json"
            b=Path(path)/"b.json"
            a.write_text("{bad json",encoding="utf-8")
            b.write_text("{}",encoding="utf-8")
            output=subprocess.run([sys.executable,str(HERE/"v04_independent_review.py"),
                                   "--staging",str(a),"--review",str(b)],
                                  text=True,capture_output=True,check=False)
            self.assertEqual(output.returncode,2)
            self.assertIn('"authorization": "NONE"',output.stdout)
            self.assertIn('"result": "NO_GO"',output.stdout)

    def test_template_cli_is_no_go(self):
        output=subprocess.run([sys.executable,str(HERE/"v04_independent_review.py"),
                               "--staging",str(HERE/"v04_staging_evidence.template.json"),
                               "--review",str(HERE/"v04_independent_review.template.json")],
                              text=True,capture_output=True,check=False)
        self.assertEqual(output.returncode,2)
        self.assertIn('"result": "NO_GO"',output.stdout)


if __name__ == "__main__":
    unittest.main()
