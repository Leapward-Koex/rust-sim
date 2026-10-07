"""Verify every recorded original file and every captured reference file."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / "source-manifest.json").read_text())
    original = Path(manifest["source_directory"])
    failures = []
    counts = {"original": 0, "snapshot": 0}
    for entry in manifest["files"]:
        paths = [("original", original / entry["path"])]
        if entry["snapshot"]:
            paths.append(("snapshot", ROOT / "reference-source" / entry["path"]))
        for kind, path in paths:
            counts[kind] += 1
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
                failures.append(str(path))
    report = {"ok": not failures, "checked": counts, "failures": failures}
    (ROOT / "verification" / "source-integrity.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
