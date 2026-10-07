"""Measure unchanged reference Python and release Rust with the same parameters.

Uses a separate process for every sample, suppresses progress into retained logs,
and samples process-tree working-set memory. Run with the build Python (psutil).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

import psutil

ROOT = Path(__file__).resolve().parents[1]


def measure(command: list[str], log: Path, timeout: float) -> dict:
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE="1", MPLBACKEND="Agg", MPLCONFIGDIR=str(ROOT / ".cache" / "matplotlib"))
    started = time.perf_counter()
    peak = 0
    with log.open("wb") as output:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        watcher = psutil.Process(process.pid)
        try:
            while process.poll() is None:
                try:
                    members = [watcher, *watcher.children(recursive=True)]
                    memory = sum(max(p.memory_info().rss, getattr(p.memory_info(), "peak_wset", 0)) for p in members)
                    peak = max(peak, memory)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                if time.perf_counter() - started > timeout:
                    for child in watcher.children(recursive=True):
                        child.kill()
                    process.kill()
                    process.wait()
                    raise TimeoutError(f"Benchmark exceeded {timeout}s; log: {log}")
                time.sleep(0.01)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    elapsed = time.perf_counter() - started
    if process.returncode:
        raise RuntimeError(f"Exit {process.returncode}; log: {log}\n{log.read_text(errors='replace')[-2000:]}")
    return {"seconds": elapsed, "peak_working_set_bytes": peak, "log": str(log.relative_to(ROOT))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycles", type=int, default=50)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--cases", nargs="+", choices=["ordinary", "sex-heavy", "higher-locus"], default=["ordinary", "sex-heavy", "higher-locus"])
    parser.add_argument("--rust-only", action="store_true")
    parser.add_argument("--timeout", type=float, default=7200)
    parser.add_argument("--report", type=Path, default=ROOT / "verification" / "benchmark-results.json")
    args = parser.parse_args()
    output = ROOT / "build" / "benchmarks" / f"{time.time_ns()}"
    output.mkdir(parents=True)
    baseline = json.loads((ROOT / "reference-source" / "import_template.json").read_text())
    reference_python = ROOT / ".venv-reference" / "Scripts" / "python.exe"
    if os.name != "nt":
        reference_python = ROOT / ".venv-reference" / "bin" / "python"
    engine = ROOT / "target" / "release" / ("dicty-sim.exe" if os.name == "nt" else "dicty-sim")
    report = {"platform": platform.platform(), "processor": platform.processor(),
              "recorded_utc": datetime.now(timezone.utc).isoformat(),
              "engine_sha256": hashlib.sha256(engine.read_bytes()).hexdigest(),
              "source_sha256": hashlib.sha256((ROOT / "reference-source" / "dicty_sim_test_env.py").read_bytes()).hexdigest(),
              "logical_cpus": os.cpu_count(), "method": "Fresh process wall time; progress to log; peak process-tree working set sampled every 10ms. Includes process startup, imports, and aggregation. Python and Rust use different random generators.",
              "cycles": args.cycles, "repeats": args.repeats, "samples": args.samples, "workers": args.workers,
              "cases": {}}
    for case in args.cases:
        config = dict(baseline, n_dev=args.cycles, n_runs=args.repeats, output_filepath="")
        if case == "sex-heavy":
            config.update(sex_cycle_interval=2, ch_start=0.3, res_start=0.2)
        elif case == "higher-locus":
            config.update(gene_pairs=12, ch_start=0.3, res_start=0.2)
        parameter_path = output / f"{case}.json"
        parameter_path.write_text(json.dumps(config), encoding="utf-8")
        results = {"parameters": config, "rust": [], "python": []}
        report["cases"][case] = results
        for sample in range(args.samples):
            seed = 7241 + sample
            rust_command = [str(engine), "--param", str(parameter_path), "--seed", str(seed), "--threads", str(args.workers)]
            commands = [("rust", rust_command)]
            if not args.rust_only:
                # Seed both original RNG families before executing the unchanged source file.
                source = ROOT / "reference-source" / "dicty_sim_test_env.py"
                bootstrap = "import random,numpy,runpy,sys; random.seed(int(sys.argv[1])); numpy.random.seed(int(sys.argv[1])); p=sys.argv[2]; sys.path.insert(0,str(__import__('pathlib').Path(p).parent)); sys.argv=[p,'--param',sys.argv[3]]; runpy.run_path(p,run_name='__main__')"
                commands.append(("python", [str(reference_python), "-B", "-c", bootstrap, str(seed), str(source), str(parameter_path)]))
            for name, command in commands:
                print(f"{case} {name} sample {sample + 1}/{args.samples}", flush=True)
                result = measure(command, output / f"{case}-{name}-{sample}.log", args.timeout)
                results[name].append(result)
                print(f"  {result['seconds']:.3f}s, {result['peak_working_set_bytes']/1048576:.1f} MiB", flush=True)
                args.report.parent.mkdir(parents=True, exist_ok=True)
                args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
        for name in ("python", "rust"):
            if results[name]:
                results[f"{name}_median_seconds"] = statistics.median(r["seconds"] for r in results[name])
        if results["python"]:
            results["speedup"] = results["python_median_seconds"] / results["rust_median_seconds"]
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report: {args.report}")


if __name__ == "__main__":
    main()
