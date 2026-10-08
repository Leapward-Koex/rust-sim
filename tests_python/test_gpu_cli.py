"""Opt-in hardware integration: DICTY_TEST_GPU=1 requires a working FP64 GPU.

Run after cargo build --release --locked --bins. These tests deliberately fail,
rather than skip, if GPU execution is requested but unavailable. The ordinary
test suite remains usable on machines without OpenCL hardware or drivers.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import queue
import subprocess
import tempfile
import threading
import time
import unittest

from gui.parameters import DEFAULTS


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "target" / "release" / ("dicty-sim.exe" if os.name == "nt" else "dicty-sim")


@unittest.skipUnless(os.environ.get("DICTY_TEST_GPU") == "1", "Set DICTY_TEST_GPU=1 to test real GPU execution")
class GpuCliIntegration(unittest.TestCase):
    def setUp(self):
        self.assertTrue(ENGINE.is_file(), "Build the release engine before GPU integration tests")
        self.directory = tempfile.TemporaryDirectory(prefix="Dicty GPU integration ü ")
        self.addCleanup(self.directory.cleanup)
        self.work = Path(self.directory.name)
        self.config = copy.deepcopy(DEFAULTS)
        self.config.update(n=192, sl=24, n_dev=3, n_runs=5, vg=4,
                           mc_count=8, mc_germ_count=24, output_filepath="")

    def test_automatic_selects_gpu_for_eligible_workload(self):
        self.config.update(n=2048, sl=256, n_runs=64, n_dev=1, vg=2)
        command, result = self.command(self.config, 'auto', threads=2)
        process = subprocess.run(command, capture_output=True, text=True, timeout=30,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.assertEqual(process.returncode, 0, process.stderr)
        first = self.parse_event(process.stdout.splitlines()[0])
        self.assertEqual(first['backend'], 'gpu')
        self.assertEqual(first['requested_backend'], 'auto')
        self.assertTrue(first['device'])
        actual = result.read_bytes()
        expected, _events, _metadata = self.run_engine(self.config, 'cpu', threads=2)
        self.assertEqual(actual, expected)

    def command(self, parameters, backend, threads=1, batch_size=3):
        path = self.work / "parameters.json"
        path.write_text(json.dumps(parameters), encoding="utf-8")
        result = self.work / "result.json"
        command = [str(ENGINE), "--param", str(path), "--result", str(result),
                   "--backend", backend, "--gpu-batch-size", str(batch_size),
                   "--threads", str(threads), "--seed", "739", "--events"]
        return command, result

    def parse_event(self, line):
        def reject(value):
            self.fail(f"Progress protocol contained nonfinite token {value}")
        event = json.loads(line, parse_constant=reject)
        self.assertEqual(event["protocol_version"], 1)
        self.assertIsInstance(event["run_id"], str)
        return event

    def run_engine(self, parameters, backend, threads=1, batch_size=3):
        command, result = self.command(parameters, backend, threads, batch_size)
        process = subprocess.run(command, cwd=self.work, capture_output=True, text=True,
                                 encoding="utf-8", timeout=45,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        self.assertEqual(process.returncode, 0, process.stderr + "\n" + process.stdout)
        events = [self.parse_event(line) for line in process.stdout.splitlines()]
        self.assertEqual(events[0]["type"], "started")
        self.assertEqual(events[-1]["type"], "completed")
        self.assertEqual({event["run_id"] for event in events}, {events[0]["run_id"]})
        metadata = json.loads(Path(str(result) + ".run.json").read_text(encoding="utf-8"))
        for record in (events[0], events[-1], metadata):
            self.assertEqual(record["backend"], backend)
            self.assertEqual(record["seed"], 739)
            if backend == "gpu":
                self.assertIsInstance(record["device"], str)
                self.assertTrue(record["device"])
            else:
                self.assertIsNone(record["device"])
        for record in (events[0], metadata):
            self.assertEqual(record["requested_backend"], backend)
            self.assertEqual(record["gpu_batch_size"], batch_size)
            self.assertEqual(record["threads"], threads)
            self.assertIsInstance(record["backend_reason"], str)
        counts = [event["completed_cycles"] for event in events if event["type"] == "progress"]
        self.assertEqual(counts, sorted(counts), "Completed-cycle progress went backwards")
        self.assertEqual(counts[-1], parameters["n_runs"] * parameters["n_dev"])
        return result.read_bytes(), events, metadata

    def test_complete_runs_match_cpu_bytes_across_workers_batches_and_model_branches(self):
        cases = {
            "default_small": {},
            "mixed_germination": {"ch_start": 0.4, "res_start": 0.3, "ch_germ": 0.2,
                                   "m_ch": 0.08, "m_re": 0.04},
            "sequential_distribution": {"ch_res_dist": 0, "ch_start": 0.4, "res_start": 0.3,
                                        "ch_eff_rc": 1, "res_eff_rc": 1},
            "interval_sex": {"sex_cycle_interval": 2, "n_dev": 2, "ch_start": 0.25,
                             "res_start": 0.25, "mt3_start": 0.25},
            "explicit_sex": {"i_macrocyst": [2, 2], "sex_cycle_interval": 1,
                             "recomb_chance": 0.4, "ch_start": 0.3, "res_start": 0.2},
            "fractional_epistasis": {"ch_eff_rc": 0.3, "res_eff_rc": 0.7,
                                     "ch_start": 0.45, "res_start": 0.4, "discrete_res": 0},
            "mutation_cheater_boundary": {"m_ch": 1, "m_re": 0, "res_start": 0.5},
            "mutation_resistor_boundary": {"m_ch": 0, "m_re": 1, "ch_start": 0.3},
            "high_loci": {"gene_pairs": 97, "c_ch": 0.001, "c_res": 0.002,
                          "ch_start": 0.3, "res_start": 0.25, "m_ch": 0.02, "m_re": 0.01},
            "single_repeat_nonfinite": {"n_runs": 1, "extra": {"value": float("nan"),
                                                               "text": "NaN Infinity"}},
        }
        for name, changes in cases.items():
            parameters = dict(self.config, **changes)
            with self.subTest(case=name, backend="cpu"):
                expected, _, _ = self.run_engine(parameters, "cpu")
            for workers, batch_size in ((1, 1), (2, 3), (4, 8)):
                with self.subTest(case=name, workers=workers, batch_size=batch_size):
                    actual, _, _ = self.run_engine(parameters, "gpu", workers, batch_size)
                    self.assertEqual(actual, expected, "GPU and CPU encoded legacy results differ")

    def test_throttled_progress_counts_every_cycle(self):
        parameters = dict(self.config, n_runs=65, n=64, sl=8, n_dev=2, vg=2)
        expected, _, _ = self.run_engine(parameters, "cpu", threads=3)
        actual, events, _ = self.run_engine(parameters, "gpu", threads=3, batch_size=16)
        self.assertEqual(actual, expected)
        self.assertEqual([e for e in events if e["type"] == "progress"][-1]["completed_cycles"], 130)

    def launch_long_job(self):
        parameters = dict(self.config, n=4096, sl=256, n_dev=500, n_runs=64, vg=8)
        command, result = self.command(parameters, "gpu", threads=2, batch_size=16)
        result.write_bytes(b"previous successful result")
        metadata = Path(str(result) + ".run.json")
        metadata.write_bytes(b"previous successful metadata")
        process = subprocess.Popen(command, cwd=self.work, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        messages = queue.Queue()
        diagnostics = []

        def read_events():
            for line in process.stdout:
                try:
                    messages.put(json.loads(line))
                except ValueError as exc:
                    messages.put({"type": "invalid", "message": str(exc)})

        def read_errors():
            diagnostics.extend(process.stderr)

        readers = [threading.Thread(target=read_events, daemon=True),
                   threading.Thread(target=read_errors, daemon=True)]
        for reader in readers:
            reader.start()

        def cleanup():
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            for reader in readers:
                reader.join(timeout=3)
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()
        self.addCleanup(cleanup)
        received = []
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                event = messages.get(timeout=0.1)
            except queue.Empty:
                self.assertIsNone(process.poll(), "Engine exited before GPU cycle: " + "".join(diagnostics))
                continue
            received.append(event)
            self.assertNotIn(event["type"], ("error", "invalid", "completed"), str(event))
            if event["type"] == "started":
                self.assertEqual(event["backend"], "gpu")
            if event.get("completed_cycles", 0) > 0:
                break
        else:
            self.fail("GPU job never completed its first cycle: " + "".join(diagnostics))
        return process, messages, readers, result, metadata, received

    def test_gpu_cancellation_is_cooperative_and_preserves_previous_files(self):
        process, messages, readers, result, metadata, received = self.launch_long_job()
        started = time.monotonic()
        process.stdin.write('{"command":"cancel"}\n')
        process.stdin.flush()
        self.assertEqual(process.wait(timeout=10), 130)
        self.assertLess(time.monotonic() - started, 5)
        for reader in readers:
            reader.join(timeout=3)
        while not messages.empty():
            received.append(messages.get_nowait())
        self.assertEqual(received[-1]["type"], "cancelled")
        self.assertNotIn("completed", [event["type"] for event in received])
        self.assertEqual(result.read_bytes(), b"previous successful result")
        self.assertEqual(metadata.read_bytes(), b"previous successful metadata")

    def test_forced_gpu_termination_reaps_process_and_preserves_previous_files(self):
        process, _, _, result, metadata, _ = self.launch_long_job()
        process.terminate()
        self.assertNotEqual(process.wait(timeout=10), 0)
        self.assertIsNotNone(process.poll())
        self.assertEqual(result.read_bytes(), b"previous successful result")
        self.assertEqual(metadata.read_bytes(), b"previous successful metadata")


if __name__ == "__main__":
    unittest.main(verbosity=2)
