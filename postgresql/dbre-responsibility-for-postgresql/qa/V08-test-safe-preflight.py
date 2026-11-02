#!/usr/bin/env python3
"""Offline V08 guardrail tests. All PostgreSQL calls are mocked; NO DB connection."""
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
RUNNER = HERE / 'V08-safe-preflight.py'
SQL = HERE / 'V08-readonly-staging-preflight.sql'
spec = importlib.util.spec_from_file_location('v08_preflight', RUNNER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class StagingPreflightSecurityTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        p = Path(self.temp.name)
        self.allow = p / 'targets.txt'
        self.allow.write_text('staging.example.internal|5432|testdb\n')
        self.allow.chmod(0o600)
        self.passfile = p / '.pgpass'
        self.passfile.write_text('staging.example.internal:5432:testdb:readonly:*\n')
        self.passfile.chmod(0o600)
        self.ca = p / 'root-ca.crt'
        self.ca.write_text('FICTIONAL CERTIFICATE; NO CONNECTION MADE\n')
        self.out = p / 'evidence'
        self.out.mkdir(mode=0o700)
        SQL.write_text('BEGIN READ ONLY;\nSELECT 1;\nCOMMIT;\n')
        self.env = {
            'V08_EXECUTION_APPROVED': 'YES',
            'V08_CHANGE_TICKET': 'https://change.example.invalid/approved',
            'V08_ALLOWLIST_FILE': str(self.allow),
            'V08_EXPECT_DATABASE': 'testdb',
            'V08_EXPECT_ROLE': 'readonly',
            'V08_EXPECT_SERVER_VERSION_NUM': '180001',
            'V08_EXPECT_IS_STANDBY': 'f',
            'V08_EXPECT_SQL_SHA256': hashlib.sha256(SQL.read_bytes()).hexdigest(),
            'V08_EVIDENCE_DIR': str(self.out),
            'PGHOST': 'staging.example.internal',
            'PGPORT': '5432',
            'PGDATABASE': 'testdb',
            'PGUSER': 'readonly',
            'PGSSLMODE': 'verify-full',
            'PGSSLROOTCERT': str(self.ca),
            'PGPASSFILE': str(self.passfile),
        }
        self.calls = []

    def fake_psql(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        if '-c' in cmd:
            return subprocess.CompletedProcess(cmd, 0, self.env['V08_EXPECT_DATABASE']+'|readonly|180001|f\n', '')
        if '-f' in cmd:
            return subprocess.CompletedProcess(cmd, 0, 'MOCK OUTPUT NO REAL DATABASE\n', '')
        raise AssertionError('unexpected command')

    def invoke(self, changes=None, sql=None, psql=True, responder=None):
        env = dict(self.env)
        for k,v in (changes or {}).items():
            if v is None:env.pop(k,None)
            else:env[k]=v
        if sql is not None: SQL.write_text(sql)
        with patch.dict(os.environ, env, clear=True), patch.object(module.shutil,'which',return_value='/fake/psql' if psql else None), patch.object(module.subprocess,'run', side_effect=responder or self.fake_psql):
            with redirect_stdout(io.StringIO()) as output:
                module.main()
            return output.getvalue()

    def blocked(self, changes=None, **kw):
        with self.assertRaisesRegex(RuntimeError, '^V08 BLOCKED:'):
            self.invoke(changes,**kw)
        self.assertEqual(len(self.calls),0,'Unsafe prerequisites must block before any psql invocation')

    def test_default_unapproved(self):self.blocked({'V08_EXECUTION_APPROVED': None})
    def test_unlisted_endpoint(self):self.blocked({'PGHOST': 'other.example.internal'})
    def test_uri_host(self):self.blocked({'PGHOST':'host,secondhost'})
    def test_socket_host(self):self.blocked({'PGHOST':'/tmp'})
    def test_conninfo_database(self):self.blocked({'PGDATABASE':'host=other dbname=testdb','V08_EXPECT_DATABASE':'host=other dbname=testdb'})
    def test_insecure_ssl(self):self.blocked({'PGSSLMODE':'prefer'})
    def test_password_environment(self):self.blocked({'PGPASSWORD':'DUMMY'})
    def test_service_override(self):self.blocked({'PGSERVICE':'override'})
    def test_hostaddr_override(self):self.blocked({'PGHOSTADDR':'127.0.0.1'})
    def test_wrong_role(self):self.blocked({'PGUSER':'admin'})
    def test_missing_expected_hash(self):self.blocked({'V08_EXPECT_SQL_SHA256':None})
    def test_wrong_sql_hash(self):self.blocked({'V08_EXPECT_SQL_SHA256':'0'*64})
    def test_modified_sql_rejected(self):self.blocked(sql='DROP TABLE x;\n')
    def test_open_allowlist(self):
        self.allow.chmod(0o644)
        self.blocked()
    def test_open_secret(self):
        self.passfile.chmod(0o644)
        self.blocked()
    def test_open_evidence_directory(self):
        self.out.chmod(0o755)
        self.blocked()
    def test_no_psql_binary(self):self.blocked(psql=False)

    def test_wrong_actual_identity(self):
        def wrong(cmd,**kwargs):
            self.calls.append((cmd,kwargs))
            return subprocess.CompletedProcess(cmd,0,'testdb|wronguser|180001|f\n','')
        with self.assertRaisesRegex(RuntimeError,'does not match approved target'):
            self.invoke(responder=wrong)
        self.assertEqual(len(self.calls),1,'Identity mismatch must block the actual SQL pack')

    def test_identity_connection_exception(self):
        def fails(cmd,**kwargs):
            self.calls.append((cmd,kwargs))
            raise subprocess.CalledProcessError(2,cmd)
        with self.assertRaisesRegex(RuntimeError,'identity query failed'):
            self.invoke(responder=fails)
        self.assertEqual(len(self.calls),1)

    def test_sql_execution_exception(self):
        def fails_second(cmd,**kwargs):
            self.calls.append((cmd,kwargs))
            if len(self.calls)==1: return subprocess.CompletedProcess(cmd,0,'testdb|readonly|180001|f\n','')
            raise subprocess.CalledProcessError(2,cmd)
        with self.assertRaisesRegex(RuntimeError,'read-only preflight failed'):
            self.invoke(responder=fails_second)
        self.assertEqual(len(self.calls),2)
        self.assertEqual(len(list(self.out.iterdir())),0)

    def test_mock_success_writes_private_noncertified_evidence(self):
        output=self.invoke()
        self.assertEqual(len(self.calls),2)
        for cmd,kwargs in self.calls:
            for flag,value in (('-h','staging.example.internal'),('-p','5432'),('-d','testdb'),('-U','readonly')):
                self.assertEqual(cmd[cmd.index(flag)+1],value)
            self.assertIn('-w',cmd)
            self.assertIn('default_transaction_read_only=on',kwargs['env']['PGOPTIONS'])
        self.assertIn('-f', self.calls[1][0]); self.assertEqual(self.calls[1][0][self.calls[1][0].index('-f')+1], '-')
        self.assertEqual(self.calls[1][1]['input'],SQL.read_text())
        written=list(self.out.iterdir())
        self.assertEqual(len(written),1)
        self.assertEqual(stat.S_IMODE(written[0].stat().st_mode),0o600)
        self.assertIn('MOCK OUTPUT', written[0].read_text())
        self.assertIn('NOT a PITR result',output)

    def test_chapter004_lab_exception_is_narrow(self):
        self.allow.write_text('127.0.0.1|55432|ops_lab\n')
        self.env.update(PGHOST='127.0.0.1',PGPORT='55432',PGDATABASE='ops_lab',V08_EXPECT_DATABASE='ops_lab',PGSSLMODE='disable',V08_LOCAL_CH004_LAB_ONLY='YES')
        self.invoke()
        self.assertEqual(len(self.calls),2)
        self.calls.clear()
        self.env['PGPORT']='55435'
        self.blocked()

if __name__ == '__main__':
    unittest.main(verbosity=2)
