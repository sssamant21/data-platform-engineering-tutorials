#!/usr/bin/env python3
"""No live commands: synthetic V04-C staging rehearsal preflight regression."""
from __future__ import annotations

from datetime import timedelta
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_v04_staging_readiness import NOW, synthetic_complete
from test_v04_independent_review import review_complete
import v04c_rehearsal_preflight as gate
import v04_independent_review as v04b

def utc(m: int) -> str:
    return (NOW + timedelta(minutes=m)).isoformat()

def fixture():
    staging = synthetic_complete()
    review = review_complete(staging)
    packet = {
        "schema": gate.SCHEMA,
        "mode": "offline_preflight_only",
        "requested_decision": "request_manual_authorization",
        "environment": "staging",
        "environment_id": staging["environment_id"],
        "change_ticket": staging["change_ticket"],
        "system_identifier": staging["cluster"]["system_identifier"],
        "window_start_utc": staging["window_start_utc"],
        "window_end_utc": staging["window_end_utc"],
        "staging_manifest_sha256": v04b.digest(staging),
        "independent_review_sha256": v04b.digest(review),
        "prepared_at_utc": utc(-4),
        "authorities": {
            key: {
                "name": name, "disposition": "ready_for_independent_decision",
                "attested_at_utc": utc(-2),
                "attestation_ref": f"evidence://synthetic/{key}",
            }
            for key, name in (
                ("change_authority", "Independent-Change-Authority"),
                ("incident_commander", "Independent-Incident-Commander"),
            )
        },
        "fresh_observations": {
            key: {
                "reported_safe": True, "observed_at_utc": utc(-1),
                "evidence_ref": f"evidence://synthetic/{key}",
                "evidence_sha256": "abcdef1234567890" * 4,
            }
            for key in gate.REQUIRED_FRESH
        },
    }
    return staging, review, packet


class StagingRehearsalGateTests(unittest.TestCase):
    def setUp(self):
        self.stage, self.review, self.packet = fixture()

    def evaluate(self):
        return gate.screen(self.stage, self.review, self.packet, now=NOW)

    def blocks(self, code):
        v = self.evaluate()
        self.assertEqual("NO_GO", v["result"], v)
        self.assertIn(code, v["reason_codes"])
        self.assertEqual("NONE", v["authorization"])
        self.assertEqual("NEVER", v["execution"])

    def test_all_synthetic_metadata_still_has_no_go_authorization(self):
        v = self.evaluate()
        self.assertEqual("REQUIRES_LIVE_CHANGE_AUTHORITY_GO", v["result"])
        self.assertEqual([], v["reason_codes"])
        self.assertEqual("NONE", v["authorization"])
        self.assertFalse(v["fencing_verified_by_tool"])
        self.assertEqual("NEVER", v["execution"])

    def test_both_public_templates_are_no_go(self):
        a=json.loads((HERE/"v04_staging_evidence.template.json").read_text())
        b=json.loads((HERE/"v04_independent_review.template.json").read_text())
        c=json.loads((HERE/"v04c_rehearsal_request.template.json").read_text())
        v=gate.screen(a,b,c,now=NOW)
        self.assertEqual("NO_GO",v["result"])
        self.assertIn("v04a_no_go",v["reason_codes"])
        self.assertIn("v04b_no_go",v["reason_codes"])
        self.assertIn("independent_fence_not_proven",v["reason_codes"])

    def test_v04a_and_v04b_cannot_be_overridden(self):
        self.stage["fencing"]["old_primary_restart_denied"]=False
        self.review["staging_manifest_sha256"]=v04b.digest(self.stage)
        self.packet["staging_manifest_sha256"]=v04b.digest(self.stage)
        self.packet["independent_review_sha256"]=v04b.digest(self.review)
        self.blocks("v04a_fence_old_primary_restart_denied_unproven")
        self.stage,self.review,self.packet=fixture()
        self.review["claims"]["rollback_and_abort_conditions"]["status"]="pending"
        self.packet["independent_review_sha256"]=v04b.digest(self.review)
        self.blocks("v04b_claim_rollback_and_abort_conditions_not_independently_verified")

    def test_expired_or_wrong_environment_denied(self):
        self.packet["environment"]="production"
        self.blocks("production_or_nonstaging_refused")
        self.stage,self.review,self.packet=fixture()
        self.packet["mode"]="promote"
        self.blocks("operational_mode_refused")
        self.stage,self.review,self.packet=fixture()
        self.packet["requested_decision"]="GO"
        self.blocks("automatic_go_refused")
        self.stage,self.review,self.packet=fixture()
        self.packet["operational_go"]=True
        self.blocks("embedded_operational_go_refused")

    def test_cross_packet_sha256_and_identity_bindings(self):
        for key,value,code in (
            ("staging_manifest_sha256","0"*64,"staging_digest_mismatch"),
            ("independent_review_sha256","1"*64,"independent_review_digest_mismatch"),
            ("change_ticket","OTHER","change_ticket_binding_invalid"),
            ("environment_id","OTHER","environment_id_binding_invalid"),
            ("window_start_utc",utc(-60),"window_start_utc_binding_invalid"),
            ("system_identifier","11111111111111111111","system_identifier_binding_invalid"),
        ):
            with self.subTest(key=key):
                self.stage,self.review,self.packet=fixture()
                self.packet[key]=value
                self.blocks(code)
        self.stage,self.review,self.packet=fixture()
        self.review["reviewers"]["dbre"]["name"]="altered-after-review"
        self.blocks("independent_review_digest_mismatch")

    def test_attestations_and_independence(self):
        self.packet["authorities"]["change_authority"]["disposition"]="pending"
        self.blocks("change_authority_attestation_missing")
        self.stage,self.review,self.packet=fixture()
        self.packet["authorities"]["incident_commander"]["name"]=self.review["reviewers"]["dbre"]["name"]
        self.blocks("authority_not_independent")
        self.stage,self.review,self.packet=fixture()
        self.packet["authorities"]["incident_commander"]["name"]=self.packet["authorities"]["change_authority"]["name"]
        self.blocks("authority_not_independent")
        self.stage,self.review,self.packet=fixture()
        self.packet["authorities"]["incident_commander"]["attested_at_utc"]=utc(-10)
        self.blocks("incident_commander_attestation_stale")

    def test_fresh_fence_and_observation_checks(self):
        for item in gate.REQUIRED_FRESH:
            with self.subTest(item=item):
                self.stage,self.review,self.packet=fixture()
                self.packet["fresh_observations"][item]["reported_safe"]=False
                self.blocks(f"{item}_not_proven")
                self.stage,self.review,self.packet=fixture()
                self.packet["fresh_observations"][item]["observed_at_utc"]=utc(-10)
                self.blocks(f"{item}_observation_stale")
                self.stage,self.review,self.packet=fixture()
                self.packet["fresh_observations"][item]["evidence_sha256"]="0"*64
                self.blocks(f"{item}_evidence_missing")
        self.stage,self.review,self.packet=fixture()
        self.packet["fresh_observations"]["independent_fence"]["observed_at_utc"]=utc(-5)
        self.blocks("independent_fence_observation_predates_request")

    def test_expired_request_and_changing_packet_denied(self):
        self.packet["prepared_at_utc"]=utc(-10)
        self.blocks("rehearsal_request_not_fresh")
        self.stage,self.review,self.packet=fixture()
        self.stage["baseline"]["replay_gap_bytes"]=100
        self.blocks("staging_digest_mismatch")
        self.stage,self.review,self.packet=fixture()
        self.stage["window_end_utc"]=utc(-1)
        self.blocks("v04a_maintenance_window_not_current")

    def test_missing_secrets_and_malformed(self):
        self.packet["authorities"]["change_authority"]["client_secret"]="secret"
        self.blocks("sensitive_keys_not_allowed")
        self.stage,self.review,self.packet=fixture()
        self.packet["authorities"]=None
        self.blocks("change_authority_attestation_missing")
        self.assertEqual("NO_GO",gate.screen(None,{},None,now=NOW)["result"])

    def test_cli_public_templates_refused_nonzero(self):
        p=subprocess.run([sys.executable,str(HERE/"v04c_rehearsal_preflight.py"),
            "--staging",str(HERE/"v04_staging_evidence.template.json"),
            "--review",str(HERE/"v04_independent_review.template.json"),
            "--request",str(HERE/"v04c_rehearsal_request.template.json")],
            text=True,capture_output=True,check=False)
        self.assertEqual(2,p.returncode)
        self.assertIn('"result": "NO_GO"',p.stdout)

    def test_cli_malformed_json_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"bad.json"
            p.write_text("{oops",encoding="utf-8")
            done=subprocess.run([sys.executable,str(HERE/"v04c_rehearsal_preflight.py"),
                "--staging",str(p),"--review",str(p),"--request",str(p)],
                text=True,capture_output=True,check=False)
            self.assertEqual(2,done.returncode)
            self.assertIn('"result": "NO_GO"',done.stdout)


if __name__ == "__main__":
    unittest.main()
