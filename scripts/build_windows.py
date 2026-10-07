"""Build the Windows application folder and ZIP with the current Python env.

Run using .venv-build/Scripts/python.exe after installing requirements-build.lock.
The original simulation and captured reference are never modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-rust", action="store_true", help="Package an already-built release engine")
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("This script builds the Windows application on Windows.")
    if not args.skip_rust:
        cargo = shutil.which("cargo") or str(Path.home() / ".cargo" / "bin" / "cargo.exe")
        subprocess.run([cargo, "build", "--release", "--locked", "--bin", "dicty-sim"], cwd=ROOT, check=True)
    engine = ROOT / "target" / "release" / "dicty-sim.exe"
    if not engine.is_file():
        raise SystemExit(f"Release engine missing: {engine}")
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
         "--windowed", "--name", "DictySimulator", "--paths", str(ROOT),
         "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build" / "pyinstaller"),
         "--specpath", str(ROOT / "build"), "--collect-all", "matplotlib",
         str(ROOT / "packaging" / "launcher.py")],
        cwd=ROOT, check=True,
    )
    folder = ROOT / "dist" / "DictySimulator"
    shutil.copy2(engine, folder / "dicty-sim.exe")
    for source, target in [(ROOT / "USER_GUIDE.md", folder / "USER_GUIDE.md"),
                           (ROOT / "reference-source" / "import_template.json", folder / "example-parameters.json")]:
        if source.is_file():
            shutil.copy2(source, target)
    manifest = {
        "format_version": 1,
        "platform": "windows-x86_64",
        "python": sys.version,
        "engine_sha256": hashlib.sha256(engine.read_bytes()).hexdigest(),
        "reference_commit": json.loads((ROOT / "source-manifest.json").read_text())["git_commit"],
    }
    (folder / "build-info.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    archive = ROOT / "dist" / "DictySimulator-windows-x64.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as package:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                package.write(path, path.relative_to(folder.parent))
    print(f"Application: {folder / 'DictySimulator.exe'}")
    print(f"Archive: {archive}")
    print(f"Archive SHA256: {hashlib.sha256(archive.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
