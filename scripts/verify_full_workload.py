"""Run the full repository workload serially and in parallel, comparing bytes."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import time

from benchmark import measure

ROOT = Path(__file__).resolve().parents[1]


def main():
    work = ROOT / "build" / "full-workload" / str(time.time_ns())
    work.mkdir(parents=True)
    config = json.loads((ROOT / "reference-source" / "import_template.json").read_text())
    config["output_filepath"] = ""
    parameters = work / "parameters.json"
    parameters.write_text(json.dumps(config), encoding="utf-8")
    engine = ROOT / "target" / "release" / ("dicty-sim.exe" if os.name == "nt" else "dicty-sim")
    workers = min(config["n_runs"], max(1, (os.cpu_count() or 1) - 1))
    report = {"parameters": config, "seed": 20261007,
              "engine_sha256": hashlib.sha256(engine.read_bytes()).hexdigest(), "runs": []}
    result_hashes = []
    for mode, count in (("serial", 1), ("parallel", workers)):
        result_path = work / (mode + ".json")
        command = [str(engine), "--param", str(parameters), "--result", str(result_path),
                   "--seed", str(report["seed"]), "--threads", str(count)]
        print(f"Full workload {mode}: 10000 cells, 500 cycles, 10 repeats, {count} workers", flush=True)
        measurement = measure(command, work / (mode + ".log"), 600)
        payload = result_path.read_bytes()
        data = json.loads(payload)
        assert len(data) == 21 and len(data["x_axis_values"]) == 501
        digest = hashlib.sha256(payload).hexdigest()
        result_hashes.append(digest)
        report["runs"].append(dict(measurement, mode=mode, workers=count, result_sha256=digest,
                                   result_bytes=len(payload), result_points=len(data["x_axis_values"])))
        print(f"  {measurement['seconds']:.3f}s, {measurement['peak_working_set_bytes']/1048576:.1f} MiB", flush=True)
    report["identical_result_bytes"] = result_hashes[0] == result_hashes[1]
    (ROOT / "verification" / "full-workload.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    assert report["identical_result_bytes"], "Worker count changed the full-workload result"
    print("Full results are byte-identical across worker counts.")


if __name__ == "__main__":
    main()
