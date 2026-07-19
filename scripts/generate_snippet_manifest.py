#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "examples/snippets/manifest-source.json"
SCHEMA_PATH = ROOT / "schemas/snippet-manifest.schema.json"
VERSION_PATH = ROOT / "oilpriceapi/version.py"
FORBIDDEN = (
    re.compile(r"(?i)(api[_-]?key|token)\s*[:=]\s*['\"][A-Za-z0-9_-]{20,}"),
    re.compile(r"your_api_key_here", re.IGNORECASE),
)


def package_version() -> str:
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', VERSION_PATH.read_text(), re.MULTILINE)
    if not match:
        raise ValueError("Unable to read package version")
    return match.group(1)


def default_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def build_manifest(source_commit: str) -> Dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("source commit must be a full lowercase Git SHA")

    source = json.loads(SOURCE_PATH.read_text())
    examples = []
    seen_ids = set()
    for metadata in source["examples"]:
        if metadata["id"] in seen_ids:
            raise ValueError(f"duplicate example id: {metadata['id']}")
        seen_ids.add(metadata["id"])

        path = ROOT / metadata["path"]
        code = path.read_text()
        for pattern in FORBIDDEN:
            if pattern.search(code):
                raise ValueError(f"forbidden secret-like content in {metadata['path']}")

        example = dict(metadata)
        example["code"] = code
        example["sha256"] = hashlib.sha256(code.encode("utf-8")).hexdigest()
        examples.append(example)

    manifest = {
        "schema_version": source["schema_version"],
        "package": {**source["package"], "version": package_version()},
        "source_commit": source_commit,
        "examples": examples,
    }
    schema = json.loads(SCHEMA_PATH.read_text())
    Draft202012Validator(schema).validate(manifest)
    return manifest


def write_manifest(output: Path, source_commit: str) -> None:
    manifest = build_manifest(source_commit)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output.write_bytes(payload)
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{hashlib.sha256(payload).hexdigest()}  {output.name}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the versioned SDK snippet manifest")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-commit", default=default_commit())
    args = parser.parse_args()
    write_manifest(args.output, args.source_commit)


if __name__ == "__main__":
    main()
