import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import time
import tkinter as tk
import unittest
from unittest import mock

from gui.controller import RunController, RESULT_KEYS, strict_event, validate_result
from gui.parameters import (DEFAULTS, ParameterError, export_destination, field_text,
                            load_parameters, parameters_from_fields, save_parameters)
from gui.plotting import make_figure, sex_markers


def config(**changes):
    value = copy.deepcopy(DEFAULTS)
    value.update(changes)
    return value


def sample_result():
    result = {"parameters": config(), "sex_cycle_list": [1, 1], "x_axis_values": [0, 1]}
    for key in RESULT_KEYS[3:-2]:
        result[key] = [float("nan"), float("nan")] if key.endswith("ci") else [0.25, 0.5]
    result["average_tracker_dict"] = {"gene_pair0": [[1, 2], [3, 4], [5, 6]]}
    result["ci_tracker_dict"] = {"gene_pair0": [[0, 0], [0, 0], [0, 0]]}
    return result


class ParameterTests(unittest.TestCase):
    def test_defaults_match_original_effective_gui_values_and_order(self):
        import ast
        source = Path(__file__).resolve().parents[1] / "reference-source" / "global_variables.py"
        original = ast.literal_eval(ast.parse(source.read_text()).body[0].value)
        original["i_macrocyst"] = [0]
        self.assertEqual(list(DEFAULTS), list(original))
        self.assertEqual(DEFAULTS, original)

    def test_roundtrip_preserves_extras_and_numeric_types(self):
        original = config(ch_eff_rc=0.35, i_macrocyst=[3, 1, 3], extra={"flag": True, "number": 1.0})
        fields = {k: field_text(k, v) for k, v in original.items() if k in DEFAULTS}
        result = parameters_from_fields(original, fields)
        self.assertEqual(original, result)
        self.assertIs(type(result["extra"]["number"]), float)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "parameters.json"
            save_parameters(path, result)
            self.assertEqual(load_parameters(path), original)

    def test_no_defaults_merge(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "partial.json"
            path.write_text('{"n": 10}')
            with self.assertRaisesRegex(ParameterError, "Missing parameters"):
                load_parameters(path)

    def test_transactional_parse_and_fractional_switch(self):
        original = config()
        fields = {k: field_text(k, v) for k, v in original.items()}
        fields["n"] = "200"
        fields["m_re"] = "broken"
        with self.assertRaises(ParameterError):
            parameters_from_fields(original, fields)
        self.assertEqual(original["n"], 10000)
        fields["m_re"] = "0.2"
        fields["ch_eff_rc"] = "0.3"
        self.assertEqual(parameters_from_fields(original, fields)["ch_eff_rc"], 0.3)

    def test_empty_and_comma_schedules_and_legacy_string(self):
        original = config()
        fields = {k: field_text(k, v) for k, v in original.items()}
        for text, expected in (("[]", []), ("", []), ("1, 3, 1", [1, 3, 1]), ("0", [0])):
            fields["i_macrocyst"] = text
            self.assertEqual(parameters_from_fields(original, fields)["i_macrocyst"], expected)
        original["i_macrocyst"] = "0"
        fields["i_macrocyst"] = '"0"'
        self.assertEqual(parameters_from_fields(original, fields)["i_macrocyst"], "0")

    def test_output_filename_quirks(self):
        base = Path(tempfile.gettempdir()) / "Dicty Simulator"
        self.assertIsNone(export_destination(config(output_filepath=""), base))
        self.assertEqual(export_destination(config(output_filepath="demo.json"), base), base / "demo.json.json")
        absolute = base / "absolute"
        self.assertEqual(export_destination(config(output_filepath=str(absolute)), base), Path(str(absolute) + ".json"))

    def test_imported_boolean_numbers_and_mixed_schedule_are_not_coerced(self):
        original = config(n_runs=True, ch_eff_rc=False, i_macrocyst=[0, True, "ignored", {"extra": 2}])
        fields = {k: field_text(k, v) for k, v in original.items()}
        parsed = parameters_from_fields(original, fields)
        self.assertIs(parsed["n_runs"], True)
        self.assertIs(parsed["ch_eff_rc"], False)
        self.assertEqual(parsed["i_macrocyst"], original["i_macrocyst"])

    def test_unused_phase_values_survive_parameter_roundtrip(self):
        original = config(n_dev=0, mc_count="unused", vg=None, sp={"unused": True})
        fields = {k: field_text(k, v) for k, v in original.items()}
        self.assertEqual(parameters_from_fields(original, fields), original)


class PlotTests(unittest.TestCase):
    def test_legacy_artist_properties_and_nan(self):
        result = sample_result()
        figure = make_figure(result)
        self.assertEqual(tuple(figure.get_size_inches()), (12, 8))
        self.assertEqual(len(figure.axes), 2)
        self.assertEqual(figure.axes[0].get_title(), "Allele frequency over time")
        self.assertEqual(figure.axes[1].get_title(), "")
        for axis, colors, labels in zip(figure.axes, (("red", "blue", "black"), ("red", "blue", "green")),
                                       (("Cheater alleles", "Resistor alleles", "Wild-type alleles"), ("Type 1", "Type 2", "Type 3"))):
            self.assertEqual(axis.get_ylim(), (0, 1))
            self.assertEqual(axis.get_xlabel(), "Development cycles")
            self.assertEqual(axis.get_ylabel(), "Ratio")
            self.assertEqual([line.get_color() for line in axis.lines[:3]], list(colors))
            self.assertEqual([text.get_text() for text in axis.get_legend().get_texts()], list(labels))
            self.assertEqual(len(axis.collections), 3)
            self.assertTrue(all(collection.get_alpha() == 0.1 for collection in axis.collections))
            self.assertEqual(len(axis.lines), 5)
            self.assertTrue(all(line.get_alpha() == 0.05 and line.get_linestyle() == "--" for line in axis.lines[3:]))
        figure.clear()

    def test_explicit_markers_preserve_order_duplicates_and_empty(self):
        result = sample_result()
        result["parameters"]["i_macrocyst"] = [2, 1, 2, 999]
        self.assertEqual(sex_markers(result), [2, 1, 2, 999])
        result["parameters"]["i_macrocyst"] = []
        self.assertEqual(sex_markers(result), [])
        self.assertEqual(len(make_figure(result).axes[0].lines), 3)


class ControllerTests(unittest.TestCase):
    def setUp(self):
        fixture = Path(__file__).with_name("fake_engine.py").resolve()
        self.controller = RunController(Path(sys.executable), (str(fixture),))

    def tearDown(self):
        if self.controller.active:
            self.controller.cancel()
            self.await_finish()
        self.controller.cleanup()

    def await_finish(self, timeout=8):
        deadline = time.monotonic() + timeout
        events = []
        while self.controller.active and time.monotonic() < deadline:
            events.extend(self.controller.poll())
            time.sleep(0.01)
        self.assertFalse(self.controller.active, "Engine was not reaped before timeout")
        return events

    def test_success_with_disabled_saving_nan_and_byte_export(self):
        self.controller.start(config(output_filepath=""), seed=456, threads=1)
        events = self.await_finish()
        self.assertEqual(events[-1]["type"], "succeeded")
        result = self.controller.last_result
        self.assertEqual(result.metadata["seed"], 456)
        self.assertTrue(math.isnan(result.result["ch_ci"][0]))
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "results ü.json"
            result.export(target)
            self.assertEqual(target.read_bytes(), result.result_bytes)
            self.assertEqual(Path(str(target) + ".run.json").read_bytes(), result.metadata_bytes)
        with self.assertRaises(OSError):
            result.export(Path(result.directory.name) / "missing" / "result.json")
        self.assertIs(self.controller.last_result, result)

    def test_error_protocol_and_exit_failures_preserve_prior_result(self):
        self.controller.start(config())
        self.await_finish()
        previous = self.controller.last_result
        for behavior in ("crash", "invalid_json", "wrong_version", "error", "missing_completion", "stale_id", "invalid_result", "incomplete_parameters"):
            with self.subTest(behavior=behavior):
                self.controller.start(config(_test_behavior=behavior))
                events = self.await_finish()
                self.assertEqual(events[-1]["type"], "failed")
                self.assertIs(self.controller.last_result, previous)

    def test_failed_paired_export_preserves_both_previous_files(self):
        import os
        self.controller.start(config())
        self.await_finish()
        completed = self.controller.last_result
        with tempfile.TemporaryDirectory() as temp:
            result = Path(temp) / "saved.json"
            metadata = Path(str(result) + ".run.json")
            result.write_bytes(b"previous result")
            metadata.mkdir()
            with self.assertRaises(OSError):
                completed.export(result)
            self.assertEqual(result.read_bytes(), b"previous result")
            metadata.rmdir()
            metadata.write_bytes(b"previous metadata")
            original_replace = os.replace

            def fail_result(source, destination):
                if Path(destination) == result and str(source).endswith(".tmp"):
                    raise PermissionError("Injected second replacement failure")
                return original_replace(source, destination)

            with mock.patch("gui.controller.os.replace", side_effect=fail_result):
                with self.assertRaises(PermissionError):
                    completed.export(result)
            self.assertEqual(result.read_bytes(), b"previous result")
            self.assertEqual(metadata.read_bytes(), b"previous metadata")
            self.assertEqual(sorted(p.name for p in Path(temp).iterdir()), ["saved.json", "saved.json.run.json"])

    def test_cancel_and_forced_termination_reap_process(self):
        for behavior in ("cancel", "ignore_cancel"):
            with self.subTest(behavior=behavior):
                self.controller.start(config(_test_behavior=behavior))
                process = self.controller.job.process
                time.sleep(0.15)
                self.controller.cancel()
                self.controller.cancel()
                events = self.await_finish()
                self.assertEqual(events[-1]["type"], "finished_cancelled")
                self.assertIsNotNone(process.poll())

    def test_stderr_is_drained_and_stale_queue_messages_ignored(self):
        self.controller.start(config(_test_behavior="stderr_flood"))
        self.controller.job.messages.put(("old-job", "stdout", "not JSON"))
        self.assertEqual(self.await_finish()[-1]["type"], "succeeded")

    def test_missing_executable_does_not_start(self):
        self.controller.engine = Path(tempfile.gettempdir()) / "does-not-exist-dicty.exe"
        with self.assertRaises(FileNotFoundError):
            self.controller.start(config())
        self.assertFalse(self.controller.active)

    def test_strict_event_rejects_nonfinite_and_bool_version(self):
        for line in ('{"protocol_version":1,"type":"started","run_id":"a","seed":NaN}',
                     '{"protocol_version":true,"type":"started","run_id":"a"}'):
            with self.assertRaises(ValueError):
                strict_event(line)


class TkTests(unittest.TestCase):
    def setUp(self):
        from gui.app import Application
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(str(exc))
        self.root.withdraw()
        self.app = Application(self.root)
        self.app.controller = RunController(Path(sys.executable), (str(Path(__file__).with_name("fake_engine.py").resolve()),))
        self.dialogs = mock.patch("gui.app.messagebox.showerror")
        self.errors = self.dialogs.start()

    def tearDown(self):
        self.dialogs.stop()
        if not self.app.closing:
            self.app.close()
        deadline = time.monotonic() + 8
        while self.app.controller.active and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.assertFalse(self.app.controller.active)

    def pump(self):
        deadline = time.monotonic() + 8
        while self.app.controller.active and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.root.update_idletasks()
        self.assertFalse(self.app.controller.active)

    def test_absolute_export_does_not_require_default_documents_directory(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            inaccessible = base / "not-a-directory"
            inaccessible.write_text("occupied")
            self.app.base_directory = inaccessible
            data = sample_result()
            data["parameters"]["output_filepath"] = str(base / "absolute-output")
            completed = SimpleNamespace(result=data, metadata={"seed": 7},
                                        export=lambda p: p.write_bytes(b"completed result"))
            with mock.patch.object(self.app, "show_plot"):
                self.app._completed({"run": completed, "seed": 7})
            self.assertEqual((base / "absolute-output.json").read_bytes(), b"completed result")
            self.errors.assert_not_called()

    def test_layout_import_failure_transaction_and_responsive_run(self):
        self.assertEqual(len(self.app.entries), 31)
        self.assertEqual(int(self.app.entries["sp"].grid_info()["row"]), 0)
        self.assertEqual(int(self.app.entries["sp"].grid_info()["column"]), 3)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text('{"n": 17}')
            with mock.patch("gui.app.filedialog.askopenfilename", return_value=str(path)):
                self.app.import_parameters()
        self.assertEqual(self.app.parameters["n"], 10000)
        self.errors.assert_called_once()
        self.app.fields["output_filepath"].set("")
        heartbeat = []
        self.root.after(1, lambda: heartbeat.append(True))
        self.app.run()
        self.assertEqual(str(self.app.run_button["state"]), "disabled")
        self.pump()
        self.assertTrue(heartbeat)
        self.assertEqual(len(self.app.plot_windows), 1)
        self.assertEqual(str(self.app.run_button["state"]), "normal")
        self.assertEqual(self.app.progress.get(), 100)

    def test_close_active_job_reaps_before_destroy(self):
        self.app.parameters["_test_behavior"] = "cancel"
        self.app.run()
        process = self.app.controller.job.process
        self.app.close()
        deadline = time.monotonic() + 8
        while self.app.controller.active and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.assertFalse(self.app.controller.active)
        self.assertIsNotNone(process.poll())


if __name__ == "__main__":
    unittest.main()
