#!/usr/bin/env python3
"""Real PG18 role/RLS fixture QA in one isolated disposable CI Docker container.

No external network, credentials or data. No HA/DR actions. Not certification.
"""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "labs" / "sql"
REPORT = ROOT / "validation" / "evidence-v03-ch076078-security.json"
DATA = "/tmp/postgresql-dbre-lab.V03SEC18/primary"
PORT = "55432"
NAME = "pg18-security-%s-%s" % (os.environ.get("GITHUB_RUN_ID", ""), os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
checks = []
def cmd(args, input_text=None, seconds=20):
    return subprocess.run(args, input=input_text, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=seconds, check=False)
def docker(*args, input_text=None):
    return cmd(["docker", *args], input_text=input_text)
def pg(user, db, sql=None, fixture=None, params=None):
    args = ["docker", "exec", "-i", NAME, "psql", "-X", "-w",
            "-v", "ON_ERROR_STOP=1", "-v", "VERBOSITY=verbose",
            "-A", "-t", "-h", "127.0.0.1", "-p", PORT, "-U", user, "-d", db]
    for key, value in (params or {}).items():
        args += ["-v", "%s=%s" % (key, value)]
    if fixture:
        return cmd(args + ["-f", "-"], fixture)
    return cmd(args + ["-c", sql])
def record(name, passed, diagnostic=""):
    checks.append({"name":name, "passed":bool(passed)})
    print(("PASS " if passed else "FAIL ") + name, flush=True)
    if not passed and diagnostic:
        print(diagnostic[-900:], file=sys.stderr, flush=True)
def success(name, user, db, sql):
    p=pg(user,db,sql=sql)
    record(name, p.returncode==0, p.stderr)
    return p.stdout.strip()
def equal(name, user, db, sql, expected):
    p=pg(user,db,sql=sql)
    record(name, p.returncode==0 and p.stdout.strip()==str(expected),
           p.stderr or ("Expected %s got %r" %(expected,p.stdout.strip())))
def denied(name, user, db, sql, code="42501"):
    p=pg(user,db,sql=sql)
    err=p.stderr.lower()
    record(name,p.returncode!=0 and (code in p.stderr if code else True)
           and "syntax error" not in err and "invalid command" not in err, p.stderr)
def fixture(n, mode, system_id):
    name="076-security-role-fixture.sql" if n=="076" else "078-rls-fixture.sql"
    args={"expected_system_id":system_id,
          "expected_lab_pgdata":DATA, "confirm_stage":n+"-CREATE-LAB-FIXTURE"}
    role="lab_admin"; database="postgres"
    if mode=="bad_sid": args["expected_system_id"]="0"
    if mode=="missing_sid": del args["expected_system_id"]
    if mode=="bad_pgdata": args["expected_lab_pgdata"]="/tmp/other"
    if mode=="bad_stage": args["confirm_stage"]="INVALID"
    if mode=="missing_stage": del args["confirm_stage"]
    if mode=="wrong_db": database="template1"
    if mode=="wrong_role": role="ch_v03_guest"
    return pg(role,database,fixture=(SQL/name).read_text(encoding="utf-8"),params=args)
def safe_refusal(n,mode,sid):
    p=fixture(n,mode,sid)
    record(n+"-"+mode+"-refused",p.returncode!=0
           and "syntax error" not in p.stderr.lower()
           and "invalid command" not in p.stderr.lower(),p.stderr)
def main():
    if os.environ.get("GITHUB_ACTIONS")!="true" or not os.environ.get("GITHUB_RUN_ID"):
        raise RuntimeError("REFUSED: GitHub Actions disposable CI only")
    result=cmd(["docker","pull","postgres:18"],seconds=120)
    if result.returncode: raise RuntimeError("Image pull failed: "+result.stderr[-500:])
    args=["docker","run","-d","--name",NAME,"--network","none",
          "--tmpfs","/tmp:rw,size=768m,mode=1777","--memory","1g",
          "--cpus","2","--pids-limit","256",
          "-e","POSTGRES_HOST_AUTH_METHOD=trust","-e","POSTGRES_USER=lab_admin",
          "-e","POSTGRES_DB=postgres","-e","PGDATA="+DATA,
          "postgres:18","-c","listen_addresses=127.0.0.1",
          "-c","port="+PORT,"-c","statement_timeout=7000"]
    result=cmd(args)
    if result.returncode: raise RuntimeError("Container launch failed: "+result.stderr[-500:])
    try:
        mode=docker("inspect","-f","{{.HostConfig.NetworkMode}}",NAME)
        ports=docker("port",NAME)
        if mode.stdout.strip()!="none" or ports.stdout.strip():
            raise RuntimeError("REFUSED: container not isolated")
        for _ in range(75):
            r=docker("exec",NAME,"pg_isready","-h","127.0.0.1","-p",PORT,
                     "-U","lab_admin","-d","postgres")
            if r.returncode==0: break
            time.sleep(1)
        else: raise RuntimeError("Disposable database did not start")
        v=pg("lab_admin","postgres","SHOW server_version_num")
        path=pg("lab_admin","postgres","SHOW data_directory")
        sid=pg("lab_admin","postgres","SELECT system_identifier::text FROM pg_control_system()")
        if v.returncode or path.returncode or sid.returncode: raise RuntimeError("Identity queries failed")
        record("major-version-18",180000 <= int(v.stdout.strip()) < 190000)
        record("exact-ephemeral-PGDATA",path.stdout.strip()==DATA)
        system_id=sid.stdout.strip()
        if not system_id.isdigit(): raise RuntimeError("Bad system identifier")
        success("create-disposable-guest","lab_admin","postgres","CREATE ROLE ch_v03_guest LOGIN")
        for n in ("076","078"):
            for case in ("missing_sid","missing_stage","bad_sid","bad_pgdata",
                         "bad_stage","wrong_db","wrong_role"):
                safe_refusal(n,case,system_id)
            equal(n+"-no-role-before-setup","lab_admin","postgres",
                  "SELECT count(*) FROM pg_roles WHERE left(rolname,6)='ch%s_'" % n,"0")
            equal(n+"-no-database-before-setup","lab_admin","postgres",
                  "SELECT count(*) FROM pg_database WHERE datname='ch%s_lab'" % n,"0")
            p=fixture(n,"correct",system_id)
            record(n+"-actual-one-time-fixture-executes",p.returncode==0,p.stderr)
            if p.returncode: raise RuntimeError(n+" fixture failed; see case result")
            equal(n+"-database-created","lab_admin","postgres",
                  "SELECT count(*) FROM pg_database WHERE datname='ch%s_lab'" % n,"1")
            safe_refusal(n,"correct",system_id)  # repeated fixture must fail
        # Distinct real LOGIN connections; trust authentication only inside this container.
        equal("076-app-login","ch076_app_login","ch076_lab","SELECT current_user","ch076_app_login")
        equal("076-analyst-login","ch076_analyst_login","ch076_lab","SELECT current_user","ch076_analyst_login")
        equal("076-owner-NOLOGIN","lab_admin","postgres",
              "SELECT rolcanlogin FROM pg_roles WHERE rolname='ch076_owner'","f")
        equal("076-app-can-insert","lab_admin","ch076_lab",
              "SELECT has_table_privilege('ch076_app_login','app.orders','INSERT')","t")
        success("076-app-insert","ch076_app_login","ch076_lab",
                "INSERT INTO app.orders(customer_ref) VALUES ('lab-001')")
        equal("076-app-read","ch076_app_login","ch076_lab",
              "SELECT count(*) FROM app.orders WHERE customer_ref='lab-001'","1")
        success("076-app-update","ch076_app_login","ch076_lab",
                "UPDATE app.orders SET customer_ref='lab-002' WHERE customer_ref='lab-001'")
        equal("076-analyst-read","ch076_analyst_login","ch076_lab",
              "SELECT count(*) FROM app.orders","1")
        denied("076-analyst-insert-denied","ch076_analyst_login","ch076_lab",
               "INSERT INTO app.orders(customer_ref) VALUES ('forbidden')")
        denied("076-analyst-update-denied","ch076_analyst_login","ch076_lab",
               "UPDATE app.orders SET customer_ref='forbidden'")
        denied("076-app-create-denied","ch076_app_login","ch076_lab",
               "CREATE TABLE app.unapproved(id integer)")
        denied("076-app-SET-ROLE-denied","ch076_app_login","ch076_lab","SET ROLE ch076_app_rw")
        denied("076-analyst-SET-ROLE-denied","ch076_analyst_login","ch076_lab","SET ROLE ch076_readonly")
        denied("076-monitor-write-denied","ch076_monitor_login","ch076_lab",
               "INSERT INTO app.orders(customer_ref) VALUES ('forbidden')")
        equal("076-monitor-observes","ch076_monitor_login","ch076_lab",
              "SELECT count(*) > 0 FROM pg_stat_activity","t")
        success("076-app-delete","ch076_app_login","ch076_lab",
                "DELETE FROM app.orders WHERE customer_ref='lab-002'")
        equal("076-app-deleted","ch076_app_login","ch076_lab","SELECT count(*) FROM app.orders","0")
        success("076-owner-create-future-table","lab_admin","ch076_lab",
                "SET ROLE ch076_owner; CREATE TABLE app.future_orders(id integer); RESET ROLE")
        equal("076-default-privilege-app","lab_admin","ch076_lab",
              "SELECT has_table_privilege('ch076_app_login','app.future_orders','INSERT')","t")
        equal("076-default-privilege-analyst","lab_admin","ch076_lab",
              "SELECT has_table_privilege('ch076_analyst_login','app.future_orders','SELECT')","t")
        success("076-admin-table-not-owner","lab_admin","ch076_lab","CREATE TABLE app.admin_created(id integer)")
        equal("076-other-creator-does-not-inherit-defaults","lab_admin","ch076_lab",
              "SELECT has_table_privilege('ch076_app_login','app.admin_created','SELECT')","f")
        # Actual unprivileged RLS / column grants.
        equal("078-RLS-force-enabled","lab_admin","ch078_lab",
              "SELECT relrowsecurity AND relforcerowsecurity FROM pg_class WHERE oid='app.tenant_orders'::regclass","t")
        for n in ("a","b"):
            role="ch078_tenant_"+n
            equal("078-"+n+"-no-bypass","lab_admin","postgres",
                  "SELECT rolbypassrls FROM pg_roles WHERE rolname='%s'"%role,"f")
            equal("078-"+n+"-sees-one","ch078_tenant_"+n,"ch078_lab",
                  "SELECT count(*) FROM app.tenant_orders","1")
            denied("078-"+n+"-cannot-read-sensitive-column",role,"ch078_lab",
                   "SELECT secret_note FROM app.tenant_orders")
        equal("078-a-cannot-see-b","ch078_tenant_a","ch078_lab",
              "SELECT count(*) FROM app.tenant_orders WHERE tenant_role='ch078_tenant_b'","0")
        equal("078-b-cannot-see-a","ch078_tenant_b","ch078_lab",
              "SELECT count(*) FROM app.tenant_orders WHERE tenant_role='ch078_tenant_a'","0")
        success("078-a-own-insert","ch078_tenant_a","ch078_lab",
                "INSERT INTO app.tenant_orders(tenant_role,order_ref) VALUES ('ch078_tenant_a','a-002')")
        equal("078-a-insert-seen","ch078_tenant_a","ch078_lab",
              "SELECT count(*) FROM app.tenant_orders","2")
        denied("078-a-cross-insert-denied","ch078_tenant_a","ch078_lab",
               "INSERT INTO app.tenant_orders(tenant_role,order_ref) VALUES ('ch078_tenant_b','evil')")
        denied("078-b-cross-insert-denied","ch078_tenant_b","ch078_lab",
               "INSERT INTO app.tenant_orders(tenant_role,order_ref) VALUES ('ch078_tenant_a','evil')")
        denied("078-a-cross-update-denied","ch078_tenant_a","ch078_lab",
               "UPDATE app.tenant_orders SET tenant_role='ch078_tenant_b' WHERE order_ref='a-002'")
        denied("078-a-SET-ROLE-denied","ch078_tenant_a","ch078_lab","SET ROLE ch078_owner")
        success("078-a-attempt-delete-b","ch078_tenant_a","ch078_lab",
                "DELETE FROM app.tenant_orders WHERE tenant_role='ch078_tenant_b'")
        equal("078-b-row-preserved","ch078_tenant_b","ch078_lab",
              "SELECT count(*) FROM app.tenant_orders","1")
        success("078-a-delete-own","ch078_tenant_a","ch078_lab",
                "DELETE FROM app.tenant_orders WHERE order_ref='a-002'")
        equal("078-a-only-original-remains","ch078_tenant_a","ch078_lab",
              "SELECT count(*) FROM app.tenant_orders","1")
        equal("078-admin-sees-both-originals","lab_admin","ch078_lab",
              "SELECT count(*) FROM app.tenant_orders","2")
    finally:
        docker("rm","-f",NAME)
    report={
      "scope":"single disposable PostgreSQL 18, Docker network none and loopback TCP",
      "real_postgresql_executed":True,"case_count":len(checks),
      "passed":sum(x["passed"] for x in checks),
      "failed":sum(not x["passed"] for x in checks),
      "cases":checks,
      "password_authentication_tested":False,
      "tls_tested":False,"pgaudit_tested":False,
      "external_security_signoff":False,"ha_fencing_tested":False,
      "staging_or_production_touched":False,
      "enterprise_certification":"NOT_CERTIFIED",
      "timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
    REPORT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("DISPOSABLE PG18 SECURITY:",report["passed"],"/",report["case_count"],flush=True)
    if report["failed"]: raise SystemExit(1)
if __name__=="__main__":
    main()
