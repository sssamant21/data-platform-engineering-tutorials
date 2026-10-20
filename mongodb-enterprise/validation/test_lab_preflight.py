#!/usr/bin/env python3
"""Offline fail-closed input checks for Chapter 01–04 preflight."""
import unittest
from lab_preflight import validate_inputs


class PilotPreflightTests(unittest.TestCase):
    def test_approved_exact_host_and_chapter(self):
        self.assertEqual(
            validate_inputs("mongodb://127.0.0.1:27017", "127.0.0.1", 1, "run_12345678"),
            "mongodb_enterprise_tutorial_ch01",
        )

    def test_reject_wrong_host(self):
        with self.assertRaises(ValueError):
            validate_inputs("mongodb://prod.internal:27017", "lab.internal", 1, "run_12345678")

    def test_reject_multi_host(self):
        with self.assertRaises(ValueError):
            validate_inputs("mongodb://lab.internal:27017,other.internal:27017", "lab.internal", 2, "run_12345678")

    def test_reject_embedded_credentials(self):
        with self.assertRaises(ValueError):
            validate_inputs("mongodb://user:password@lab.internal:27017", "lab.internal", 3, "run_12345678")

    def test_reject_unsupported_chapter(self):
        with self.assertRaises(ValueError):
            validate_inputs("mongodb://lab.internal:27017", "lab.internal", 5, "run_12345678")

    def test_reject_unsafe_run_id(self):
        with self.assertRaises(ValueError):
            validate_inputs("mongodb://lab.internal:27017", "lab.internal", 4, "../unsafe")

    def test_reject_remote_endpoint_even_if_allowlisted(self):
        with self.assertRaises(ValueError):
            validate_inputs("mongodb://lab.internal:27017", "lab.internal", 1, "run_12345678")

    def test_reject_uri_query_override(self):
        with self.assertRaises(ValueError):
            validate_inputs("mongodb://127.0.0.1:27017/?tls=false", "127.0.0.1", 1, "run_12345678")

    def test_reject_database_path(self):
        with self.assertRaises(ValueError):
            validate_inputs("mongodb://127.0.0.1:27017/admin", "127.0.0.1", 1, "run_12345678")



    def test_reject_missing_explicit_port(self):
        with self.assertRaises(ValueError):
            validate_inputs("mongodb://127.0.0.1", "127.0.0.1", 1, "run_12345678")

    def test_reject_invalid_port(self):
        for uri in ("mongodb://127.0.0.1:abc", "mongodb://127.0.0.1:65536",
                    "mongodb://127.0.0.1:0"):
            with self.subTest(uri=uri), self.assertRaises(ValueError):
                validate_inputs(uri, "127.0.0.1", 1, "run_12345678")

    def test_reject_empty_userinfo(self):
        with self.assertRaises(ValueError):
            validate_inputs("mongodb://@127.0.0.1:27017", "127.0.0.1", 1, "run_12345678")

    def test_reject_noncanonical_port(self):
        with self.assertRaises(ValueError):
            validate_inputs("mongodb://127.0.0.1:027017", "127.0.0.1", 1, "run_12345678")

if __name__ == "__main__":
    unittest.main()
