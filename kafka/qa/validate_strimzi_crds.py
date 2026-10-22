#!/usr/bin/env python3
"""Validate complete Strimzi YAML examples against pinned upstream CRD OpenAPI schemas.

Read-only: no kubectl, no cluster changes. Uses GitHub API to download version-pinned
CRDs, caches them, and validates with jsonschema. Never treats unavailable schemas as PASS.
Dependencies: PyYAML, jsonschema.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from validate_code_blocks import extract, PLACEHOLDER

try:
    import yaml
    from jsonschema import Draft4Validator
except ImportError:
    print("Missing dependencies: python -m pip install PyYAML jsonschema", file=sys.stderr)
    raise SystemExit(2)

API = "https://api.github.com/repos/strimzi/strimzi-kafka-operator"
GROUP = "kafka.strimzi.io"


def fetch(url: str):
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                                    "User-Agent": "kafka-curriculum-qa"})
    with urllib.request.urlopen(request, timeout=35) as response:
        return response.read()


def load_schemas(version: str, cache: Path, offline: bool):
    cache.mkdir(parents=True, exist_ok=True)
    saved = cache / f"strimzi-{version}-crd-schemas.json"
    if saved.exists():
        return json.loads(saved.read_text(encoding="utf-8"))
    if offline:
        raise RuntimeError(f"No cached schemas at {saved}; run once without --offline")
    # A release tag pins the exact upstream tree; no floating main branch.
    tree = json.loads(fetch(f"{API}/git/trees/{version}?recursive=1"))
    if tree.get("truncated"):
        raise RuntimeError("Upstream Git tree truncated; cannot establish complete CRD inventory")
    paths = [x["path"] for x in tree.get("tree", [])
             if x.get("type") == "blob"
             and x["path"].startswith("packaging/install/cluster-operator/")
             and "-Crd-" in x["path"] and x["path"].endswith((".yaml", ".yml"))]
    if not paths:
        raise RuntimeError(f"No CRDs found in pinned Strimzi tag {version}")
    schemas = {}
    for path in paths:
        raw = fetch(f"https://raw.githubusercontent.com/strimzi/strimzi-kafka-operator/{version}/{path}")
        for crd in yaml.safe_load_all(raw):
            if not isinstance(crd, dict) or crd.get("kind") != "CustomResourceDefinition":
                continue
            spec = crd.get("spec", {})
            names = spec.get("names", {})
            group = spec.get("group")
            for entry in spec.get("versions", []):
                schema = (entry.get("schema") or {}).get("openAPIV3Schema")
                if schema:
                    schemas[f"{group}/{entry['name']}/{names.get('kind')}"] = schema
    if not schemas:
        raise RuntimeError("CRDs were found but none exposed versioned OpenAPI schemas")
    saved.write_text(json.dumps(schemas, indent=2) + "\n", encoding="utf-8")
    return schemas


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path("kafka"))
    p.add_argument("--output", type=Path, default=Path("kafka/qa/evidence/strimzi-schema-audit.json"))
    p.add_argument("--cache", type=Path, default=Path("kafka/qa/evidence/schema-cache"))
    p.add_argument("--version", default="0.47.0", help="Pinned Strimzi release tag")
    p.add_argument("--offline", action="store_true", help="Use cached schemas only")
    args = p.parse_args()
    try:
        schemas = load_schemas(args.version, args.cache, args.offline)
    except Exception as exc:
        print(f"BLOCKED: could not obtain pinned Strimzi CRD schemas: {exc}", file=sys.stderr)
        return 2
    records = []
    for file in sorted(args.root.rglob("*.md")):
        rel = file.relative_to(args.root).as_posix()
        for start, end, language, body, unclosed in extract(file.read_text(encoding="utf-8-sig")):
            if language not in ("yaml", "yml"):
                continue
            item = {"path": rel, "start_line": start}
            if unclosed or PLACEHOLDER.search(body):
                continue
            try:
                docs = [d for d in yaml.safe_load_all(body) if d is not None]
            except yaml.YAMLError:
                continue  # Other YAML gate owns syntax errors
            resources = [d for d in docs if isinstance(d, dict)
                         and str(d.get("apiVersion", "")).startswith(GROUP + "/")]
            if not resources:
                continue
            if len(resources) != len(docs):
                item.update(status="REVIEW", reason="Mixed or incomplete YAML documents")
            else:
                issues = []
                missing = []
                for resource in resources:
                    version = resource["apiVersion"].split("/", 1)[1]
                    key = f"{GROUP}/{version}/{resource.get('kind')}"
                    schema = schemas.get(key)
                    if schema is None:
                        missing.append(key)
                        continue
                    for error in Draft4Validator(schema).iter_errors(resource):
                        issues.append({"resource": key, "path": "/".join(map(str, error.absolute_path)),
                                       "message": error.message[:500]})
                if missing:
                    item.update(status="REVIEW", reason="No matching pinned CRD schema", missing=missing)
                elif issues:
                    item.update(status="FAIL", issues=issues[:30])
                else:
                    item.update(status="PASS", resources=len(resources))
            records.append(item)
    counts = dict(Counter(x["status"] for x in records))
    report = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "strimzi_version": args.version, "schemas_loaded": sorted(schemas),
              "scope": "Static CRD OpenAPI validation only; no cluster execution.",
              "summary": counts, "blocks": records}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Strimzi CRD schema: {len(records)} candidate blocks, {counts}")
    print(f"Evidence: {args.output}")
    return 1 if counts.get("FAIL") else 0


if __name__ == "__main__":
    raise SystemExit(main())
