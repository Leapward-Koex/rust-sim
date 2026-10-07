"""Black-box contract tests for the release CLI. No simulation reimplementation."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import queue
import subprocess
import stat
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "target" / "release" / ("dicty-sim.exe" if os.name == "nt" else "dicty-sim")
KEYS = ["parameters", "sex_cycle_list", "x_axis_values", "mean_ch", "ch_ci", "mean_res", "res_ci",
        "mean_wild", "wild_ci", "mean_mt1", "mt1_ci", "mean_mt2", "mt2_ci", "mean_mt3", "mt3_ci",
        "graph_mean_ch_eff", "ch_eff_ci", "graph_mean_res_eff", "res_eff_ci", "average_tracker_dict", "ci_tracker_dict"]


class CliContract(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="Dicty CLI ü ")
        self.addCleanup(self.directory.cleanup)
        self.work = Path(self.directory.name)
        self.config = json.loads((ROOT / "reference-source" / "import_template.json").read_text())
        self.config.update(n=48, sl=8, n_dev=4, n_runs=3, vg=2, mc_count=3, mc_germ_count=16, output_filepath="")

    def run_engine(self, config=None, extra=(), transport=True, seed=739, threads=1):
        parameters = self.work / "parameters.json"
        parameters.write_text(json.dumps(config if config is not None else self.config), encoding="utf-8")
        command = [str(ENGINE), "--param", str(parameters), "--seed", str(seed), "--threads", str(threads), "--events", *extra]
        result = self.work / "private-result.json"
        if transport:
            command.extend(["--result", str(result)])
        process = subprocess.run(command, cwd=self.work, text=True, encoding="utf-8", capture_output=True, timeout=30)
        events = [json.loads(line, parse_constant=lambda s: self.fail(f"Non-strict protocol token {s}")) for line in process.stdout.splitlines()]
        self.assertTrue(events, process.stderr)
        for event in events:
            self.assertEqual(event["protocol_version"], 1)
            self.assertIsInstance(event["run_id"], str)
        return process, events, result

    def test_complete_shape_and_private_output_with_saving_disabled(self):
        process, events, result = self.run_engine()
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(events[0]["type"], "started")
        self.assertEqual(events[-1]["type"], "completed")
        data = json.loads(result.read_text())
        self.assertEqual(list(data), KEYS)
        self.assertEqual(data["parameters"]["output_filepath"], "")
        self.assertEqual(data["x_axis_values"], [0, 1, 2, 3, 4])
        self.assertTrue(Path(events[-1]["metadata_path"]).is_file())
        self.assertEqual(Path(events[-1]["result_path"]), result)

    def test_worker_count_does_not_change_result_bytes(self):
        _, _, result = self.run_engine(threads=1)
        first = result.read_bytes()
        process, _, result = self.run_engine(threads=3)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(first, result.read_bytes())

    def test_one_repeat_retains_nan_confidence_and_parameter_extras(self):
        self.config.update(n_runs=1, extra={"label": "NaN Infinity -Infinity", "number": float("nan"), "fraction": 1.0})
        process, _, result = self.run_engine()
        self.assertEqual(process.returncode, 0, process.stderr)
        data = json.loads(result.read_text())
        self.assertTrue(all(math.isnan(x) for x in data["ch_ci"]))
        self.assertEqual(data["parameters"]["extra"]["label"], "NaN Infinity -Infinity")
        self.assertTrue(math.isnan(data["parameters"]["extra"]["number"]))
        self.assertIsInstance(data["parameters"]["extra"]["fraction"], float)

    def test_private_serde_names_are_ordinary_parameter_extras(self):
        extra = {"$serde_json::private::Number": "7", "nested": {"$serde_json::private::Number": "hello"}}
        self.config["extra"] = extra
        process, _, result = self.run_engine()
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(result.read_text())["parameters"]["extra"], extra)

    def test_unused_phase_parameter_types_do_not_reject_valid_runs(self):
        for changes in ({"n_dev": 0, "mc_count": 1.5, "vg": None, "sp": None},
                        {"n_dev": 1, "i_macrocyst": [], "mc_germ_count": 1.5, "recomb_chance": None}):
            with self.subTest(changes=changes):
                process, _, _ = self.run_engine(dict(self.config, **changes))
                self.assertEqual(process.returncode, 0, process.stderr)

    @unittest.skipUnless(os.name == "nt", "Windows read-only replacement semantics")
    def test_failed_result_replacement_restores_previous_metadata(self):
        process, _, result = self.run_engine(seed=111)
        self.assertEqual(process.returncode, 0, process.stderr)
        metadata = Path(str(result) + ".run.json")
        original = result.read_bytes(), metadata.read_bytes()
        os.chmod(result, stat.S_IREAD)
        try:
            process, events, _ = self.run_engine(seed=222)
            self.assertNotEqual(process.returncode, 0)
            self.assertEqual(events[-1]["type"], "error")
            self.assertEqual((result.read_bytes(), metadata.read_bytes()), original)
        finally:
            os.chmod(result, stat.S_IWRITE | stat.S_IREAD)

    @unittest.skipUnless(os.name == "nt", "Windows read-only replacement semantics")
    def test_failed_metadata_replacement_restores_or_removes_result(self):
        for had_result in (True, False):
            with self.subTest(had_result=had_result):
                process, _, result = self.run_engine(seed=111)
                self.assertEqual(process.returncode, 0, process.stderr)
                metadata = Path(str(result) + ".run.json")
                original_result, original_metadata = result.read_bytes(), metadata.read_bytes()
                if not had_result:
                    result.unlink()
                os.chmod(metadata, stat.S_IREAD)
                try:
                    process, events, _ = self.run_engine(seed=222)
                    self.assertNotEqual(process.returncode, 0)
                    self.assertEqual(events[-1]["type"], "error")
                    self.assertEqual(metadata.read_bytes(), original_metadata)
                    if had_result:
                        self.assertEqual(result.read_bytes(), original_result)
                    else:
                        self.assertFalse(result.exists())
                finally:
                    os.chmod(metadata, stat.S_IWRITE | stat.S_IREAD)

    def test_literal_suffix_and_empty_output_suppression(self):
        self.config["output_filepath"] = "already.json"
        process, _, _ = self.run_engine(transport=False)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue((self.work / "already.json.json").is_file())
        self.config["output_filepath"] = ""
        process, events, _ = self.run_engine(transport=False)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIsNone(events[-1].get("result_path"))

    def test_empty_schedule_without_interval_works(self):
        self.config["i_macrocyst"] = []
        process, _, _ = self.run_engine()
        self.assertEqual(process.returncode, 0, process.stderr)

    def test_invalid_parameters_fail_without_result(self):
        for changes in ({"n": 0}, {"gene_pairs": 0}, {"resistance_type": 2}, {"i_macrocyst": [], "sex_cycle_interval": 1}):
            with self.subTest(changes=changes):
                config = dict(self.config, **changes)
                process, events, result = self.run_engine(config)
                self.assertNotEqual(process.returncode, 0)
                self.assertEqual(events[-1]["type"], "error")
                self.assertFalse(result.exists())

    def test_interval_events_are_duplicated_across_repeats(self):
        # One sex event per repeat avoids subsequent mating-type extinction in
        # this tiny stochastic population; full repeated-sex parity is scripted.
        self.config.update(sex_cycle_interval=2, n_dev=2)
        process, _, result = self.run_engine()
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(result.read_text())["sex_cycle_list"], [2] * 3)

    def test_cancellation_is_cooperative_and_no_result_is_saved(self):
        self.config.update(n=10000, sl=1000, n_dev=500, n_runs=10)
        path = self.work / "cancel.json"
        path.write_text(json.dumps(self.config))
        result = self.work / "cancel-result.json"
        process = subprocess.Popen([str(ENGINE), "--param", str(path), "--seed", "71", "--threads", "1", "--result", str(result), "--events"],
                                   cwd=self.work, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        self.addCleanup(lambda: process.kill() if process.poll() is None else None)
        events = queue.Queue()
        def read():
            for line in process.stdout:
                events.put(json.loads(line))
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        self.assertEqual(events.get(timeout=10)["type"], "started")
        started = time.monotonic()
        process.stdin.write('{"command":"cancel"}\n')
        process.stdin.flush()
        self.assertEqual(process.wait(timeout=5), 130)
        self.assertLess(time.monotonic() - started, 3)
        reader.join(timeout=2)
        types = []
        while not events.empty():
            types.append(events.get_nowait()["type"])
        self.assertIn("cancelled", types)
        self.assertFalse(result.exists())
        process.stdin.close()
        process.stdout.close()
        process.stderr.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
