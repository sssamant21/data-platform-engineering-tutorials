#!/usr/bin/env python3
"""Inventory Kubernetes manifest candidates in Kafka Markdown fences.

Read-only; no kubectl apply. YAML parse requires PyYAML.
Classifies incomplete/template examples as REVIEW, and reports K8s API versions/kinds.
"""
from __future__ import annotations
import argparse
import json
import sys
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
    p.add_argument("--output", type=Path, default=Path("kafka/qa/evidence/kubernetes-manifest-audit.json"))
    args = p.parse_args()
    if yaml is None:
        print("PyYAML required: python -m pip install PyYAML", file=sys.stderr)
        return 2
    records = []
    for file in sorted(args.root.rglob("*.md")):
        rel = file.relative_to(args.root).as_posix()
        for start, end, language, body, unclosed in extract(file.read_text(encoding="utf-8-sig")):
            if language not in ("yaml", "yml"):
                continue
            item = {"path": rel, "start_line": start, "end_line": end, "resources": []}
            if unclosed:
                item.update(status="FAIL", detail="Unclosed fence")
            elif PLACEHOLDER.search(body):
                item.update(status="REVIEW", detail="Template placeholders; cannot validate as complete manifest")
            else:
                try:
                    documents = list(yaml.safe_load_all(body))
                    resources = [d for d in documents if isinstance(d, dict) and "apiVersion" in d and "kind" in d]
                    item["resources"] = [{"apiVersion": str(d["apiVersion"]), "kind": str(d["kind"]),
                                          "name": str((d.get("metadata") or {}).get("name", ""))}
                                         for d in resources]
                    if resources and len(resources) == len([d for d in documents if d is not None]):
                        item.update(status="CANDIDATE", detail="Parsed Kubernetes resources; schema not yet checked")
                    else:
                        item.update(status="REVIEW", detail="Not a complete Kubernetes resource collection")
                except (yaml.YAMLError, AttributeError) as exc:
                    item.update(status="FAIL", detail=str(exc).splitlines()[0])
            records.append(item)
    counts = dict(Counter(x["status"] for x in records))
    output = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "YAML parsing and Kubernetes resource identification only; no API schema or cluster validation.",
              "summary": counts, "blocks": records}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Kubernetes YAML inventory: {len(records)} blocks, {counts}")
    print(f"Evidence: {args.output}")
    return 1 if counts.get("FAIL") else 0


if __name__ == "__main__":
    raise SystemExit(main())
