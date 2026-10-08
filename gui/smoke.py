"""Opt-in packaged-app integration check; never used during normal startup."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import time
import traceback


def run_smoke_test(report_path: Path, engine: Path, backend: str = "auto") -> int:
    started = time.monotonic()
    report = {"ok": False, "engine_path": str(engine), "python": sys.version,
              "executable": sys.executable, "frozen": bool(getattr(sys, "frozen", False)),
              "cwd": str(Path.cwd()), "errors": [], "heartbeats": 0,
              "requested_backend": backend}
    root = None
    app = None
    original_error = None
    try:
        import tkinter as tk
        from tkinter import messagebox
        import matplotlib
        import numpy
        from .app import Application
        from .parameters import DEFAULTS

        report["modules"] = {
            "numpy": {"version": numpy.__version__, "path": numpy.__file__},
            "matplotlib": {"version": matplotlib.__version__, "path": matplotlib.__file__},
            "tkinter": {"version": tk.TkVersion, "path": tk.__file__},
        }
        root = tk.Tk()
        root.withdraw()
        parameters = copy.deepcopy(DEFAULTS)
        parameters.update(n=48, sl=8, n_dev=3, n_runs=2, vg=1, output_filepath="")
        app = Application(root, engine, parameters, backend)
        app.seed.set("12345")
        app.threads.set("2")
        original_error = messagebox.showerror
        messagebox.showerror = lambda title, message, **_kwargs: report["errors"].append(f"{title}: {message}")
        original_plot = app.show_plot

        def plot(result):
            original_plot(result)
            for window in app.plot_windows:
                window.withdraw()

        app.show_plot = plot

        def exception_hook(error_type, value, tb):
            report["errors"].append("".join(traceback.format_exception(error_type, value, tb)))
            app.close()

        root.report_callback_exception = exception_hook

        def pulse():
            report["heartbeats"] += 1
            if not app.closing:
                root.after(10, pulse)

        def inspect():
            if app.controller.active:
                root.after(20, inspect)
                return
            result = app.controller.last_result
            if result:
                report["result_keys"] = list(result.result)
                report["result_points"] = len(result.result["x_axis_values"])
                report["seed"] = result.metadata.get("seed")
                report["backend"] = result.metadata.get("backend")
                report["device"] = result.metadata.get("device")
                report["backend_reason"] = result.metadata.get("backend_reason")
                report["plot_windows"] = len(app.plot_windows)
                report["ui_responsive"] = report["heartbeats"] >= 2
                report["ok"] = (not report["errors"] and len(result.result) == 21
                                and report["plot_windows"] == 1 and report["ui_responsive"]
                                and result.result["parameters"]["output_filepath"] == ""
                                and (backend == "auto" or report["backend"] == backend))
            else:
                report["errors"].append("No completed result was retained: " + app.status.get())
            app.close()

        def timeout():
            report["errors"].append("The packaged application test exceeded 30 seconds.")
            report["ok"] = False
            app.close()

        root.after(10, pulse)
        root.after(30_000, timeout)
        app.run()
        root.after(20, inspect)
        root.mainloop()
    except Exception:
        report["errors"].append(traceback.format_exc())
        if app and app.controller.active:
            app.controller.cancel()
            deadline = time.monotonic() + 6
            while app.controller.active and time.monotonic() < deadline:
                app.controller.poll()
                time.sleep(0.01)
        if root:
            try:
                root.destroy()
            except Exception:
                pass
    finally:
        if original_error:
            from tkinter import messagebox
            messagebox.showerror = original_error
        report["elapsed_seconds"] = time.monotonic() - started
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if report["ok"] else 1
