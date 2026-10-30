#!/usr/bin/env python3
"""V02-D Chapters 011-020: safety contracts and deterministic retry unit tests.

All tests are static/local; no PostgreSQL, shell lifecycle or network activity.
"""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
IDS = [f"{n:03}" for n in range(11, 21)]
REQUIRED = {
    "011": ["011-provision-lab.sql", "011-role-access-inspection.sql",
            "011-runtime-acceptance.sql", "011-cleanup-lab.sql"],
    "012": ["012-hba-lab.py", "012-authentication-inspection.sql"],
    "013": ["013-generate-lab-certificates.sh", "013-tls-inspection.sql",
            "013-tls-peer-probe.py"],
    "014": ["014-provision-lab.sql", "014-account-lifecycle-inspection.sql",
            "014-service-access-check.sql", "014-cleanup-lab.sql"],
    "015": ["015-security-acceptance-inspection.sql"],
    "016": ["016-provision-mvcc-lab.sql", "016-mvcc-inspection.sql"],
    "017": ["017-provision-isolation-lab.sql", "017-reset-isolation-lab.sql",
            "017-isolation-inspection.sql", "017-transaction-retry-pattern.py"],
    "018": ["018-provision-lock-lab.sql", "018-reset-lock-lab.sql",
            "018-lock-chain-inspection.sql"],
    "019": ["019-transaction-age-inspection.sql"],
    "020": ["020-concurrency-incident-snapshot.sql", "020-reviewed-session-signal.sql"],
}


def module_from_file(stem, filename):
    spec = importlib.util.spec_from_file_location(stem, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RETRY = module_from_file("chapter017_retry", "017-transaction-retry-pattern.py")
HBA = module_from_file("chapter012_hba", "012-hba-lab.py")


class RetryError(Exception):
    def __init__(self, sqlstate):
        self.sqlstate = sqlstate


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def execute(self, statement):
        self.connection.sql.append(statement)


class FakeConnection:
    def __init__(self, *, commit_error=None, autocommit=False, rollback_error=None):
        self.autocommit = autocommit
        self.commit_error = commit_error
        self.rollback_error = rollback_error
        self.sql = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False
    def cursor(self):
        return FakeCursor(self)
    def commit(self):
        self.commits += 1
        if self.commit_error:
            raise self.commit_error
    def rollback(self):
        self.rollbacks += 1
        if self.rollback_error:
            raise self.rollback_error
    def close(self):
        self.closed = True


class SemanticReview011020(unittest.TestCase):
    def test_exactly_ten_chapters_and_labs_with_sources(self):
        for ident in IDS:
            chapters = list((ROOT / "chapters").glob(ident + "-*.md"))
            labs = list((ROOT / "labs").glob(ident + "-*-lab.md"))
            with self.subTest(chapter=ident):
                self.assertEqual(len(chapters), 1)
                self.assertEqual(len(labs), 1)
                self.assertIn(f"../labs/{labs[0].name}", chapters[0].read_text())
                for script in REQUIRED[ident]:
                    self.assertTrue((SCRIPTS / script).is_file(), script)
                    self.assertIn(script, labs[0].read_text(), script)

    def test_database_role_cleanup_requires_lab_identity(self):
        for ident in ("011", "014"):
            source = (SCRIPTS / f"{ident}-cleanup-lab.sql").read_text()
            lab = next((ROOT / "labs").glob(f"{ident}-*-lab.md")).read_text()
            with self.subTest(chapter=ident):
                for required in (
                    r"\if :{?expected_system_id}", r"\if :{?confirm_cleanup}",
                    "pg_control_system()", "'lab_admin'", "inet_server_port()=55432",
                    "current_setting('data_directory')", "pg_is_in_recovery()",
                    "current_setting('server_version_num')",
                    f"'{ident}-DROP-ROLES-DB'", r"\if :cleanup_permitted", r"\quit 3",
                ):
                    self.assertIn(required, source, required)
                self.assertIn(f"-v confirm_cleanup={ident}-DROP-ROLES-DB", lab)
                self.assertNotIn("lab_sql <<'SQL'\nDO $guard$\n", lab)

    def test_session_signals_require_exact_cluster_and_actor(self):
        helper = (SCRIPTS / "020-reviewed-session-signal.sql").read_text()
        lab = next((ROOT / "labs").glob("020-*-lab.md")).read_text()
        for value in ("expected_system_id", "pg_control_system()",
                      "inet_server_port() = 55432", "current_user = 'lab_admin'",
                      "pg_is_in_recovery()", "data_directory",
                      "target_start", "target_query_start", "target_state",
                      "target_app", "a.backend_type = 'client backend'",
                      "a.usename = 'lab_app'", "pg_cancel_backend",
                      "pg_terminate_backend"):
            with self.subTest(control=value):
                self.assertIn(value, helper)
        self.assertIn('-v expected_system_id="$PG_LAB_SYSTEM_ID_020"', lab)
        self.assertIn("a_system_id", lab)
        self.assertIn("pg_control_system()", lab)

    def test_hba_states_exact_and_unknown_rejected(self):
        for state, content in HBA.STATES.items():
            with self.subTest(state=state):
                self.assertEqual(HBA.current_state(content), state)
        with self.assertRaisesRegex(ValueError, "differs"):
            HBA.current_state(HBA.BASELINE + b"host all all 0.0.0.0/0 trust\n")
        self.assertNotIn(b" trust", b"".join(HBA.STATES.values()))
        self.assertIn(b"scram-sha-256", HBA.BASELINE)

    def test_retry_commit_conflict_retries_fresh_connection(self):
        connections = [FakeConnection(commit_error=RetryError("40001")), FakeConnection()]
        attempts = []
        pauses = []
        def connect():
            return connections[len(attempts)]
        def work(cursor):
            attempts.append(len(attempts) + 1)
            return "committed"
        result = RETRY.run_serializable(connect, work, max_attempts=2,
                                         sleep=pauses.append, random_value=lambda: 0.5)
        self.assertEqual(result, "committed")
        self.assertEqual(attempts, [1, 2])
        self.assertEqual(pauses, [0.025])
        self.assertEqual([x.commits for x in connections], [1, 1])
        self.assertEqual([x.rollbacks for x in connections], [1, 0])
        self.assertTrue(all(x.closed for x in connections))
        self.assertTrue(all("SERIALIZABLE" in " ".join(x.sql) for x in connections))

    def test_retry_deadlock_and_exhaustion(self):
        connections = [FakeConnection(), FakeConnection()]
        attempts = []
        def connect():
            return connections[len(attempts)]
        def work(_cursor):
            attempts.append(1)
            raise RetryError("40P01")
        with self.assertRaises(RetryError) as ctx:
            RETRY.run_serializable(connect, work, max_attempts=2,
                                    sleep=lambda _: None, random_value=lambda: 0)
        self.assertEqual(ctx.exception.sqlstate, "40P01")
        self.assertEqual(len(attempts), 2)
        self.assertEqual([c.rollbacks for c in connections], [1, 1])
        self.assertTrue(all(c.closed for c in connections))

    def test_nonretryable_error_stops_without_second_connection(self):
        connections = [FakeConnection()]
        attempts = []
        def connect():
            attempts.append(1)
            return connections[0]
        def fail(_):
            raise RetryError("42501")
        with self.assertRaises(RetryError):
            RETRY.run_serializable(connect, fail, max_attempts=3)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(connections[0].rollbacks, 1)
        self.assertTrue(connections[0].closed)

    def test_rollback_failure_is_not_silently_retried(self):
        connection = FakeConnection(rollback_error=RuntimeError("rollback refused"))
        def fail(_):
            raise RetryError("40001")
        with self.assertRaisesRegex(RuntimeError, "Rollback failed"):
            RETRY.run_serializable(lambda: connection, fail, max_attempts=2)
        self.assertTrue(connection.closed)

    def test_autocommit_and_invalid_retry_limits_are_rejected(self):
        conn = FakeConnection(autocommit=True)
        with self.assertRaisesRegex(ValueError, "autocommit=False"):
            RETRY.run_serializable(lambda: conn, lambda _: 1)
        self.assertTrue(conn.closed)
        for attempts in (0, 11, True, 1.5):
            with self.subTest(attempts=attempts), self.assertRaises(ValueError):
                RETRY.run_serializable(lambda: FakeConnection(), lambda _: None,
                                       max_attempts=attempts)

    def test_bad_jitter_rejected_after_rollback_and_close(self):
        connections = [FakeConnection()]
        def fail(_):
            raise RetryError("40001")
        with self.assertRaisesRegex(ValueError, "Jitter"):
            RETRY.run_serializable(lambda: connections[0], fail,
                                    max_attempts=2, random_value=lambda: 1.5)
        self.assertTrue(connections[0].closed)
        self.assertEqual(connections[0].rollbacks, 1)


if __name__ == "__main__":
    unittest.main()
