#!/usr/bin/env python3
"""Regression tests for the Snowflake accelerated-track static SQL guard.

No Snowflake connection is made. Tests use only Python's standard library.
"""
from __future__ import annotations
import unittest
import validate_courses as validator


class UnsafeSQLTest(unittest.TestCase):
    def assert_blocked(self, sql: str) -> None:
        self.assertTrue(validator.unsafe_sql_statements(sql), sql)

    def assert_allowed(self, sql: str) -> None:
        self.assertEqual([], validator.unsafe_sql_statements(sql), sql)

    def test_safe_queries_and_show(self):
        self.assert_allowed("SELECT CURRENT_USER(); SHOW WAREHOUSES; SHOW GRANTS;")

    def test_allowed_session_tag_operations(self):
        self.assert_allowed(
            "ALTER SESSION SET QUERY_TAG = 'snowflake_dbre_sre_l2_runtime_smoke';"
            "ALTER SESSION UNSET QUERY_TAG;"
        )

    def test_safe_temporary_table_and_training_insert(self):
        self.assert_allowed(
            "CREATE TEMP TABLE DBRE_SRE_L1_QA_20261030 (ID NUMBER);"
            "INSERT INTO DBRE_SRE_L1_QA_20261030 VALUES (1);"
        )

    def test_controlled_recovery_training_table(self):
        self.assert_allowed(
            "CREATE TABLE DBRE_SRE_L6_RECOVERY (ID NUMBER);"
            "INSERT INTO DBRE_SRE_L6_RECOVERY VALUES (1);"
        )

    def test_comments_not_executed(self):
        self.assert_allowed(
            "-- DROP TABLE PROD;\nSELECT 1; -- GRANT ROLE ACCOUNTADMIN TO USER X\n"
            "/* ALTER WAREHOUSE PROD SUSPEND; */ SHOW WAREHOUSES;"
        )

    def test_multiline_drop(self):
        self.assert_blocked("DROP\nTABLE PROD;")

    def test_multiline_warehouse_alter(self):
        self.assert_blocked("ALTER\nWAREHOUSE PROD SUSPEND;")

    def test_replace_variant(self):
        self.assert_blocked("CREATE OR\n REPLACE TABLE PROD (ID NUMBER);")

    def test_grant_after_select(self):
        self.assert_blocked("SELECT 1;\nGRANT ROLE ACCOUNTADMIN TO USER X;")

    def test_prohibited_insert_target(self):
        self.assert_blocked("INSERT INTO PROD.PATIENTS VALUES (1);")

    def test_prohibited_create_target(self):
        self.assert_blocked("CREATE TABLE PROD.PATIENTS (ID NUMBER);")

    def test_prohibited_privilege_escalation(self):
        self.assert_blocked("USE ROLE ACCOUNTADMIN;")

    def test_delete_in_cte(self):
        self.assert_blocked("WITH X AS (DELETE FROM PROD) SELECT * FROM X;")

    def test_semicolon_injection(self):
        self.assert_blocked("SELECT CURRENT_USER(); DROP TABLE PROD;")

    def test_invalid_session_change(self):
        self.assert_blocked("ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = 0;")


if __name__ == "__main__":
    unittest.main()
