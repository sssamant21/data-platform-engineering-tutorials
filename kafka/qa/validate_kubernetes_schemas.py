#!/usr/bin/env python3
"""Kubernetes schema gate for extracted Kafka tutorial YAML.

Requires PyYAML and kubeconform executable. Never applies resources to a cluster.
Strimzi custom resources without pinned CRD schemas are REVIEW, not PASS.
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from validate_code_blocks import extract, PLACEHOLDER

try:
    import yaml
except ImportError:
    yaml = None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path("kafka"))
    p.add_argument("--output", type=Path, default=Path("kafka/qa/evidence/kubernetes-schema-audit.json"))
    p.add_argument("--kubernetes-version", default="1.31.0")
    p.add_argument("--docker", action="store_true", help="Run kubeconform in Docker instead of local binary")
    args = p.parse_args()
    if yaml is None:
        print("PyYAML required", file=sys.stderr)
        return 2
    if not shutil.which("docker" if args.docker else "kubeconform"):
        print("Required Docker or kubeconform executable not found. No schemas were checked.", file=sys.stderr)
        return 2
    results = []
    with tempfile.TemporaryDirectory(prefix="kafka-k8s-schema-") as temp:
        for file in sorted(args.root.rglob("*.md")):
            relative = file.relative_to(args.root).as_posix()
            for start, end, lang, body, unclosed in extract(file.read_text(encoding="utf-8-sig")):
                if lang not in ("yaml", "yml"):
                    continue
                entry = {"path": relative, "start_line": start, "status": "REVIEW"}
                if unclosed or PLACEHOLDER.search(body):
                    entry["reason"] = "Unclosed or templated YAML"
                else:
                    try:
                        docs = [x for x in yaml.safe_load_all(body) if x is not None]
                        if not docs or any(not isinstance(x, dict) or not x.get("apiVersion") or not x.get("kind") for x in docs):
                            entry["reason"] = "Not a complete Kubernetes manifest collection"
                        elif any("/" in str(x["apiVersion"]) and str(x["apiVersion"]).split("/")[0] not in
                                 {"apps", "batch", "rbac.authorization.k8s.io", "networking.k8s.io",
                                  "policy", "storage.k8s.io", "autoscaling", "apiextensions.k8s.io",
                                  "admissionregistration.k8s.io", "coordination.k8s.io",
                                  "discovery.k8s.io", "scheduling.k8s.io", "certificates.k8s.io",
                                  "authentication.k8s.io", "authorization.k8s.io",
                                  "events.k8s.io", "node.k8s.io", "flowcontrol.apiserver.k8s.io"} for x in docs):
                            entry["reason"] = "Custom resource: needs version-pinned CRD schema"
                        else:
                            candidate = Path(temp) / f"candidate-{len(results):04d}.yaml"
                            candidate.write_text(body + "\n", encoding="utf-8")
                            command = (["docker", "run", "--rm", "--network", "none", "--read-only",
                                        "--mount", f"type=bind,source={candidate},target=/manifest.yaml,readonly",
                                        "ghcr.io/yannh/kubeconform:latest", "-strict", "-summary", "-output", "json",
                                        "-kubernetes-version", args.kubernetes_version, "/manifest.yaml"]
                                       if args.docker else
                                       ["kubeconform", "-strict", "-summary", "-output", "json",
                                        "-kubernetes-version", args.kubernetes_version, str(candidate)])
                            proc = subprocess.run(
                                command,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=45)
                            entry["status"] = "PASS" if proc.returncode == 0 else "FAIL"
                            entry["detail"] = (proc.stdout + proc.stderr)[-3000:]
                    except (yaml.YAMLError, subprocess.TimeoutExpired, OSError, ValueError) as exc:
                        entry.update(status="ERROR", reason=str(exc)[:1000])
                results.append(entry)
    counts = dict(Counter(x["status"] for x in results))
    report = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "kubernetes_version": args.kubernetes_version,
              "scope": "Offline kubeconform validation of supported built-in Kubernetes manifests. CRDs are REVIEW; no cluster execution.",
              "summary": counts, "blocks": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Kubernetes schema: {len(results)} YAML blocks, {counts}")
    print(f"Evidence: {args.output}")
    return 2 if counts.get("ERROR") else 1 if counts.get("FAIL") else 0


if __name__ == "__main__":
    raise SystemExit(main())
