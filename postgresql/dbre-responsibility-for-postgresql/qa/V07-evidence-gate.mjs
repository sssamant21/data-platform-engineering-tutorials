#!/usr/bin/env node
/**
 * PostgreSQL V07 — offline evidence gate (NOT a certification authority).
 * node V07-evidence-gate.mjs V07-evidence-template.json
 * node V07-evidence-gate.mjs --self-test
 * Requires Node 18+, standard library only. No network/database/cloud access.
 * READY_FOR_INDEPENDENT_REVIEW is a dossier-completeness result, not approval.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
export const assessEvidence = function assessEvidence(data) {
  const errors=[];
  const warnings=["This gate checks supplied fields only; it cannot authenticate proof URLs, DB execution or reviewer signatures.","READY_FOR_INDEPENDENT_REVIEW is not a production certification or authorization for failover."];
  const isObject=x=>x!==null&&typeof x==="object"&&!Array.isArray(x);
  const blank=x=>typeof x!=="string"||!x.trim()||/^(TBD|PENDING|UNKNOWN|NOT_RUN|N\/A)$/i.test(x.trim());
  const okUrl=u=>typeof u==="string"&&/^https:\/\/[A-Za-z0-9][A-Za-z0-9.-]+(?::\d{2,5})?(?:[/?#][^\s]*)?$/.test(u);
  const utc=(s,key)=>{
    if(typeof s!=="string"||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(s)){errors.push(`${key}: canonical UTC YYYY-MM-DDTHH:MM:SSZ required`);return null;}
    const t=Date.parse(s);
    if(!Number.isFinite(t)||new Date(t).toISOString().slice(0,19)+"Z"!==s){errors.push(`${key}: invalid UTC timestamp`);return null;}
    return t;
  };
  if(!isObject(data))return {status:"BLOCKED",errors:["Evidence must be a JSON object"],warnings};
  if(data.schema_version!=="1.0")errors.push("schema_version must be 1.0");
  const ctx=isObject(data.context)?data.context:{};
  for(const key of ["environment_id","source_instance_id","target_instance_id","provider","postgresql_version","executor_id","change_ticket","repository_commit"])
    if(blank(ctx[key]))errors.push(`context.${key} is required`);
  if(!blank(ctx.source_instance_id)&&ctx.source_instance_id===ctx.target_instance_id)errors.push("source and target instance identity must differ");
  if(!["ha-failover","pitr-only"].includes(ctx.recovery_mode))errors.push("context.recovery_mode must be ha-failover or pitr-only");
  if(!["self-managed","rds-postgresql","aurora-postgresql","azure-flexible","cloud-sql"].includes(ctx.provider))errors.push("unknown deployment provider");
  if(typeof ctx.postgresql_version==="string"&&!/^\d+\.\d+(?:\.\d+)?$/.test(ctx.postgresql_version))errors.push("postgresql_version must include deployed major.minor");
  if(typeof ctx.repository_commit!=="string"||!/^[a-f0-9]{40}$/i.test(ctx.repository_commit))errors.push("repository_commit must be full 40-character SHA");
  if(!okUrl(ctx.change_ticket))errors.push("context.change_ticket must be valid HTTPS approval link");
  if(ctx.isolated_test_environment!==true)errors.push("test environment must be explicitly isolated");
  const required=["V01_STRUCTURE","V02_SQL","V03_ALERTING","V04_INCIDENT_SAFETY","V05_CAPACITY_FINOPS","V06_PITR","V06_APP_ACCEPTANCE","V07_SECURITY"];
  if(ctx.recovery_mode==="ha-failover")required.push("V06_FENCING");
  const tests=Array.isArray(data.tests)?data.tests:[];
  const seen=new Set();
  for(const t of tests){
    if(!isObject(t)||blank(t.id)){errors.push("test entry needs id and object");continue;}
    if(seen.has(t.id))errors.push(`duplicate test ${t.id}`);
    seen.add(t.id);
    if(!required.includes(t.id))errors.push(`unexpected test ${t.id} for declared recovery scope`);
    if(t.status!=="STAGING_PASS")errors.push(`${t.id} must have STAGING_PASS, not tabletop or pending`);
    if(!okUrl(t.proof_url))errors.push(`${t.id} requires HTTPS proof_url`);
    utc(t.executed_at_utc,`${t.id}.executed_at_utc`);
    if(blank(t.executor_id))errors.push(`${t.id} executor_id required`);
  }
  for(const id of required)if(!seen.has(id))errors.push(`missing required ${id}`);
  const rec=isObject(data.recovery)?data.recovery:{};
  for(const key of ["backup_id","wal_or_provider_restore_point","business_watermark_id"])if(blank(rec[key]))errors.push(`recovery.${key} required`);
  for(const key of ["restore_target_isolated","wal_chain_or_provider_point_proven","app_read_write_verified","data_reconciled"])if(rec[key]!==true)errors.push(`recovery.${key} requires true backed by proof`);
  if(!okUrl(rec.proof_url))errors.push("recovery.proof_url required");
  if(ctx.recovery_mode==="ha-failover"){
    const f=isObject(data.fencing)?data.fencing:{};
    if(f.old_primary_fenced!==true)errors.push("independent fencing proof required");
    if(f.single_writer_verified!==true)errors.push("single-writer proof required");
    if(!okUrl(f.proof_url))errors.push("fencing.proof_url required");
  }
  const obj=isObject(data.objectives)?data.objectives:{};
  for(const key of ["rpo_target_seconds","rto_target_seconds"])
    if(!Number.isInteger(obj[key])||obj[key]<=0)errors.push(`objectives.${key} needs positive integer`);
  const failure=utc(obj.failure_at_utc,"objectives.failure_at_utc");
  const marker=utc(obj.last_recoverable_commit_at_utc,"objectives.last_recoverable_commit_at_utc");
  const accepted=utc(obj.service_accepted_at_utc,"objectives.service_accepted_at_utc");
  let rpo=null,rto=null;
  if(failure!==null&&marker!==null){
    rpo=(failure-marker)/1000;
    if(rpo<0)errors.push("recoverable watermark after incident start");
    if(Number.isInteger(obj.rpo_target_seconds)&&rpo>obj.rpo_target_seconds)errors.push("observed RPO window exceeds approved target");
  }
  if(failure!==null&&accepted!==null){
    rto=(accepted-failure)/1000;
    if(rto<0)errors.push("service accepted before incident");
    if(Number.isInteger(obj.rto_target_seconds)&&rto>obj.rto_target_seconds)errors.push("observed RTO exceeds approved target");
  }
  const reviewers=isObject(data.reviewers)?data.reviewers:{};
  const roles=["DBRE","APP","DATA","PLT","SEC","SM"],reviewerIds=[];
  for(const role of roles){
    const x=isObject(reviewers[role])?reviewers[role]:{};
    if(blank(x.reviewer_id))errors.push(`${role} reviewer_id missing`);
    else {reviewerIds.push(x.reviewer_id);if(x.reviewer_id===ctx.executor_id)errors.push(`${role} reviewer cannot be technical executor`);}
    if(x.decision!=="APPROVED")errors.push(`${role} independent approval missing`);
    if(!okUrl(x.proof_url))errors.push(`${role} approval proof_url missing`);
    utc(x.reviewed_at_utc,`${role}.reviewed_at_utc`);
  }
  if(new Set(reviewerIds).size!==reviewerIds.length)errors.push("independent reviewers must use distinct identities");
  return {status:errors.length?"BLOCKED":"READY_FOR_INDEPENDENT_REVIEW",errors,warnings,measured:{rpo_seconds:rpo,rto_seconds:rto},test_count:tests.length};
};

const syntheticFixture = {
  "schema_version": "1.0",
  "context": {
    "environment_id": "synthetic-lab",
    "source_instance_id": "lab-source",
    "target_instance_id": "isolated-test-target",
    "provider": "self-managed",
    "postgresql_version": "18.1",
    "executor_id": "synthetic-executor",
    "change_ticket": "https://synthetic.invalid/evidence",
    "repository_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "recovery_mode": "ha-failover",
    "isolated_test_environment": true
  },
  "tests": [
    {
      "id": "V01_STRUCTURE",
      "status": "STAGING_PASS",
      "proof_url": "https://synthetic.invalid/evidence",
      "executed_at_utc": "2026-11-01T10:00:00Z",
      "executor_id": "synthetic-executor"
    },
    {
      "id": "V02_SQL",
      "status": "STAGING_PASS",
      "proof_url": "https://synthetic.invalid/evidence",
      "executed_at_utc": "2026-11-01T10:00:00Z",
      "executor_id": "synthetic-executor"
    },
    {
      "id": "V03_ALERTING",
      "status": "STAGING_PASS",
      "proof_url": "https://synthetic.invalid/evidence",
      "executed_at_utc": "2026-11-01T10:00:00Z",
      "executor_id": "synthetic-executor"
    },
    {
      "id": "V04_INCIDENT_SAFETY",
      "status": "STAGING_PASS",
      "proof_url": "https://synthetic.invalid/evidence",
      "executed_at_utc": "2026-11-01T10:00:00Z",
      "executor_id": "synthetic-executor"
    },
    {
      "id": "V05_CAPACITY_FINOPS",
      "status": "STAGING_PASS",
      "proof_url": "https://synthetic.invalid/evidence",
      "executed_at_utc": "2026-11-01T10:00:00Z",
      "executor_id": "synthetic-executor"
    },
    {
      "id": "V06_PITR",
      "status": "STAGING_PASS",
      "proof_url": "https://synthetic.invalid/evidence",
      "executed_at_utc": "2026-11-01T10:00:00Z",
      "executor_id": "synthetic-executor"
    },
    {
      "id": "V06_APP_ACCEPTANCE",
      "status": "STAGING_PASS",
      "proof_url": "https://synthetic.invalid/evidence",
      "executed_at_utc": "2026-11-01T10:00:00Z",
      "executor_id": "synthetic-executor"
    },
    {
      "id": "V07_SECURITY",
      "status": "STAGING_PASS",
      "proof_url": "https://synthetic.invalid/evidence",
      "executed_at_utc": "2026-11-01T10:00:00Z",
      "executor_id": "synthetic-executor"
    },
    {
      "id": "V06_FENCING",
      "status": "STAGING_PASS",
      "proof_url": "https://synthetic.invalid/evidence",
      "executed_at_utc": "2026-11-01T10:00:00Z",
      "executor_id": "synthetic-executor"
    }
  ],
  "recovery": {
    "backup_id": "synthetic-base-backup",
    "wal_or_provider_restore_point": "synthetic-wal",
    "business_watermark_id": "synthetic-marker",
    "restore_target_isolated": true,
    "wal_chain_or_provider_point_proven": true,
    "app_read_write_verified": true,
    "data_reconciled": true,
    "proof_url": "https://synthetic.invalid/evidence"
  },
  "fencing": {
    "old_primary_fenced": true,
    "single_writer_verified": true,
    "proof_url": "https://synthetic.invalid/evidence"
  },
  "objectives": {
    "rpo_target_seconds": 1800,
    "rto_target_seconds": 7200,
    "failure_at_utc": "2026-11-01T10:00:00Z",
    "last_recoverable_commit_at_utc": "2026-11-01T09:55:00Z",
    "service_accepted_at_utc": "2026-11-01T11:10:00Z"
  },
  "reviewers": {
    "DBRE": {
      "reviewer_id": "synthetic-DBRE",
      "decision": "APPROVED",
      "proof_url": "https://synthetic.invalid/evidence",
      "reviewed_at_utc": "2026-11-01T12:00:00Z"
    },
    "APP": {
      "reviewer_id": "synthetic-APP",
      "decision": "APPROVED",
      "proof_url": "https://synthetic.invalid/evidence",
      "reviewed_at_utc": "2026-11-01T12:00:00Z"
    },
    "DATA": {
      "reviewer_id": "synthetic-DATA",
      "decision": "APPROVED",
      "proof_url": "https://synthetic.invalid/evidence",
      "reviewed_at_utc": "2026-11-01T12:00:00Z"
    },
    "PLT": {
      "reviewer_id": "synthetic-PLT",
      "decision": "APPROVED",
      "proof_url": "https://synthetic.invalid/evidence",
      "reviewed_at_utc": "2026-11-01T12:00:00Z"
    },
    "SEC": {
      "reviewer_id": "synthetic-SEC",
      "decision": "APPROVED",
      "proof_url": "https://synthetic.invalid/evidence",
      "reviewed_at_utc": "2026-11-01T12:00:00Z"
    },
    "SM": {
      "reviewer_id": "synthetic-SM",
      "decision": "APPROVED",
      "proof_url": "https://synthetic.invalid/evidence",
      "reviewed_at_utc": "2026-11-01T12:00:00Z"
    }
  }
};
function runSelfTest(){
 const cases = [
 ["complete synthetic HA",x=>{},"READY_FOR_INDEPENDENT_REVIEW"],
 ["backup proof absent",x=>{x.recovery.proof_url=""},"BLOCKED"],
 ["missing required PITR test",x=>{x.tests=x.tests.filter(t=>t.id!=="V06_PITR")},"BLOCKED"],
 ["tabletop not execution",x=>{x.tests.find(t=>t.id==="V06_FENCING").status="TABLETOP_PASS"},"BLOCKED"],
 ["RPO missed",x=>{x.objectives.rpo_target_seconds=100},"BLOCKED"],
 ["RTO missed",x=>{x.objectives.rto_target_seconds=200},"BLOCKED"],
 ["independent fence unproven",x=>{x.fencing.old_primary_fenced=false},"BLOCKED"],
 ["same source and destination",x=>{x.context.target_instance_id=x.context.source_instance_id},"BLOCKED"],
 ["reviewer is executor",x=>{x.reviewers.DBRE.reviewer_id=x.context.executor_id},"BLOCKED"],
 ["missing DATA approval",x=>{x.reviewers.DATA.decision="PENDING"},"BLOCKED"],
 ["duplicate evidence",x=>{x.tests.push({...x.tests[0]})},"BLOCKED"],
 ["non-UTC failure timestamp",x=>{x.objectives.failure_at_utc="2026-11-01T10:00:00-05:00"},"BLOCKED"],
 ["missing test proof URL",x=>{x.tests[0].proof_url=""},"BLOCKED"],
 ["scoped PITR-only package",x=>{x.context.recovery_mode="pitr-only";x.tests=x.tests.filter(t=>t.id!=="V06_FENCING")},"READY_FOR_INDEPENDENT_REVIEW"]
 ];
 for(const [label,mutate,want] of cases){
  const d=JSON.parse(JSON.stringify(syntheticFixture));mutate(d);
  const got=assessEvidence(d);
  if(got.status!==want)throw Error(label+": "+got.status+" instead of "+want);
  process.stdout.write("PASS: "+label+"\n");
 }
}
if(process.argv[1]&&fileURLToPath(import.meta.url)===path.resolve(process.argv[1])){
 try{
  if(process.argv.length!==3)throw Error("usage: node V07-evidence-gate.mjs <evidence.json|--self-test>");
  if(process.argv[2]==="--self-test")runSelfTest();
  else {
   const evidence=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));
   const out=assessEvidence(evidence);
   process.stdout.write(JSON.stringify(out,null,2)+"\n");
   if(out.status!=="READY_FOR_INDEPENDENT_REVIEW")process.exitCode=2;
  }
 }catch(err){process.stderr.write("BLOCKED: "+err.message+"\n");process.exitCode=2;}
}
