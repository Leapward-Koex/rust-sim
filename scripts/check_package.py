"""Exercise the frozen GUI and Rust worker from an isolated application copy.

This checks bundled dependencies with no Python/Rust on PATH. It does not claim
to replace a separate test on a clean Windows installation.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, default=ROOT / "dist" / "DictySimulator")
    parser.add_argument("--report", type=Path, default=ROOT / "verification" / "package-smoke.json")
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("The current package test targets Windows.")
    work = ROOT / "build" / f"package-smoke-{uuid.uuid4().hex[:8]}"
    application = work / "Unicode ü app with spaces"
    unrelated = work / "unrelated working directory"
    temporary = work / "temp"
    unrelated.mkdir(parents=True)
    temporary.mkdir()
    shutil.copytree(args.folder.resolve(), application)
    env = os.environ.copy()
    env["PATH"] = str(Path(env.get("SystemRoot", r"C:\Windows")) / "System32")
    for key in ("PYTHONPATH", "PYTHONHOME", "TCL_LIBRARY", "TK_LIBRARY", "VIRTUAL_ENV"):
        env.pop(key, None)
    env.update(TEMP=str(temporary), TMP=str(temporary), MPLCONFIGDIR=str(temporary / "matplotlib"))
    args.report = args.report.resolve()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    command = [str(application / "DictySimulator.exe"), "--smoke-test", str(args.report)]
    process = subprocess.run(command, cwd=unrelated, env=env, timeout=45, capture_output=True,
                             creationflags=subprocess.CREATE_NO_WINDOW)
    if not args.report.exists():
        raise SystemExit(f"Frozen application exited {process.returncode} without a report: {process.stderr!r}")
    report = json.loads(args.report.read_text(encoding="utf-8"))
    report["isolated_test"] = {
        "application_copy": str(application), "path": env["PATH"],
        "python_on_path": shutil.which("python.exe", path=env["PATH"]),
        "rustc_on_path": shutil.which("rustc.exe", path=env["PATH"]),
        "exit_code": process.returncode,
        "fresh_windows_installation": False,
    }
    errors = report.setdefault("errors", [])
    if process.returncode:
        errors.append(f"Frozen application exit code: {process.returncode}")
    if not report.get("frozen"):
        errors.append("The process was not a frozen application.")
    for name, module in report.get("modules", {}).items():
        if not Path(module["path"]).resolve().is_relative_to(application.resolve()):
            errors.append(f"{name} loaded outside the application folder: {module['path']}")
    if not Path(report["engine_path"]).resolve().is_relative_to(application.resolve()):
        errors.append("Engine loaded outside the application folder.")
    report["ok"] = report.get("ok", False) and not errors
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "report": str(args.report), "errors": errors}, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
