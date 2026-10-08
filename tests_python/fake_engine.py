"""Executable protocol fixture: launched as a real subprocess by controller tests."""
import argparse
import json
from pathlib import Path
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument("--param", required=True)
parser.add_argument("--result", required=True)
parser.add_argument("--events", action="store_true")
parser.add_argument("--seed", type=int, default=123)
parser.add_argument("--threads")
parser.add_argument("--backend", choices=("auto", "cpu", "gpu"), default="auto")
args = parser.parse_args()
parameters = json.loads(Path(args.param).read_text(encoding="utf-8"))
behavior = parameters.get("_test_behavior", "success")


def emit(kind, **values):
    print(json.dumps(dict(protocol_version=1, run_id="fixture-run", type=kind, **values)), flush=True)


if behavior == "crash":
    print("A useful crash diagnostic", file=sys.stderr, flush=True)
    sys.exit(7)
if behavior == "invalid_json":
    print("this is not a JSON event", flush=True)
    time.sleep(30)
if behavior == "wrong_version":
    print('{"protocol_version":2,"type":"started","run_id":"fixture-run"}', flush=True)
    sys.exit(0)
backend = "gpu" if args.backend == "gpu" else "cpu"
selection = dict(backend=backend, requested_backend=args.backend,
                 device="Fixture FP64 GPU" if backend == "gpu" else None,
                 backend_reason="No supported GPU is available." if args.backend == "auto" else "Explicit selection.")
if behavior == "gpu_unavailable":
    emit("error", message="GPU-assisted computation requires a supported double-precision GPU.")
    sys.exit(1)
emit("started", seed=args.seed, **selection)
if behavior == "stderr_flood":
    for i in range(2000):
        print("diagnostic " + str(i), file=sys.stderr)
    sys.stderr.flush()
emit("progress", repeat=1, cycle=1, total_repeats=1, total_cycles=1, phase="development")
if behavior in ("cancel", "ignore_cancel"):
    if behavior == "ignore_cancel":
        time.sleep(30)
    else:
        command = json.loads(sys.stdin.readline())
        if command == {"command": "cancel"}:
            emit("cancelled")
            sys.exit(130)
if behavior == "error":
    emit("error", message="A useful simulation error")
    sys.exit(1)
if behavior == "missing_completion":
    sys.exit(0)
if behavior == "stale_id":
    print('{"protocol_version":1,"type":"progress","run_id":"stale","repeat":1,"cycle":1,"total_repeats":1,"total_cycles":1,"phase":"growth"}', flush=True)
    sys.exit(0)
result = {"parameters": parameters, "sex_cycle_list": [], "x_axis_values": [0, 1]}
for key in ("mean_ch", "ch_ci", "mean_res", "res_ci", "mean_wild", "wild_ci",
            "mean_mt1", "mt1_ci", "mean_mt2", "mt2_ci", "mean_mt3", "mt3_ci",
            "graph_mean_ch_eff", "ch_eff_ci", "graph_mean_res_eff", "res_eff_ci"):
    result[key] = [float("nan"), float("nan")] if key.endswith("ci") else [0.0, 0.25]
for key in ("average_tracker_dict", "ci_tracker_dict"):
    result[key] = {"gene_pair0": [[0, 1], [0, 1], [0, 1]]}
result_path = Path(args.result)
metadata_path = Path(args.result + ".run.json")
if behavior == "invalid_result":
    result = {"no": "result"}
if behavior == "incomplete_parameters":
    result["parameters"] = {"i_macrocyst": [0]}
result_path.write_text(json.dumps(result), encoding="utf-8")
metadata_path.write_text(json.dumps({"seed": args.seed, **selection}), encoding="utf-8")
emit("completed", result_path=str(result_path), metadata_path=str(metadata_path), seed=args.seed, **selection)
