"""Tkinter parameter editor, process control, and Matplotlib result windows."""

from __future__ import annotations

import argparse
import copy
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .controller import RunController, resolve_engine
from .parameters import (DEFAULTS, TOOLTIPS, ParameterError, export_destination,
                         field_text, load_parameters, output_base_directory,
                         parameters_from_fields, save_parameters)


class ToolTip:
    def __init__(self, widget, text: str):
        self.widget, self.text, self.window = widget, text, None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)
        widget.bind("<ButtonPress>", self.hide, add=True)

    def show(self, _event=None):
        if self.window is not None:
            return
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        x = min(self.widget.winfo_rootx(), self.widget.winfo_screenwidth() - 440)
        self.window.wm_geometry(f"+{max(0, x)}+{self.widget.winfo_rooty() + self.widget.winfo_height() + 4}")
        tk.Label(self.window, text=self.text, justify="left", background="#ffffe0",
                 relief="solid", borderwidth=1, wraplength=420, padx=6, pady=4).pack()

    def hide(self, _event=None):
        if self.window is not None:
            self.window.destroy()
            self.window = None


class Application:
    def __init__(self, root: tk.Tk, engine: Path | None = None, parameters: dict | None = None):
        self.root = root
        self.parameters = copy.deepcopy(DEFAULTS if parameters is None else parameters)
        self.controller = RunController(engine or resolve_engine())
        self.base_directory = output_base_directory()
        self.closing = False
        self.repeat_cycles: dict[int, int] = {}
        self.poll_id = None
        self.plot_windows = []
        self.entries: dict[str, ttk.Entry] = {}
        self.fields: dict[str, tk.StringVar] = {}
        self.tooltips = []
        root.title("Dicty Simulator — Rust engine")
        root.protocol("WM_DELETE_WINDOW", self.close)
        outer = ttk.Frame(root, padding=12)
        outer.grid(sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        ttk.Label(outer, text="Parameters", font=("TkDefaultFont", 12, "bold")).grid(row=0, column=0, pady=(0, 12))
        parameter_grid = ttk.Frame(outer)
        parameter_grid.grid(row=1, column=0, sticky="ew")
        for index, name in enumerate(DEFAULTS):
            row, group = index % 7, index // 7
            column = group * 2
            ttk.Label(parameter_grid, text=name).grid(row=row, column=column, sticky="e", padx=(8, 4), pady=4)
            variable = tk.StringVar(value=field_text(name, self.parameters[name]))
            entry = ttk.Entry(parameter_grid, textvariable=variable, width=14)
            entry.grid(row=row, column=column + 1, sticky="ew", padx=(0, 10), pady=4)
            parameter_grid.columnconfigure(column + 1, weight=1)
            self.fields[name], self.entries[name] = variable, entry
            self.tooltips.append(ToolTip(entry, TOOLTIPS[name]))
        self.fields["output_filepath"].trace_add("write", self._update_destination)

        execution = ttk.Frame(outer)
        execution.grid(row=2, column=0, pady=(16, 4))
        ttk.Label(execution, text="Seed (blank generates one)").grid(row=0, column=0, padx=4)
        self.seed = tk.StringVar()
        self.seed_entry = ttk.Entry(execution, textvariable=self.seed, width=22)
        self.seed_entry.grid(row=0, column=1, padx=4)
        ttk.Label(execution, text="Workers (blank = automatic)").grid(row=0, column=2, padx=(16, 4))
        self.threads = tk.StringVar()
        self.threads_entry = ttk.Entry(execution, textvariable=self.threads, width=8)
        self.threads_entry.grid(row=0, column=3, padx=4)

        actions = ttk.Frame(outer)
        actions.grid(row=3, column=0, pady=10)
        self.import_button = ttk.Button(actions, text="Import parameters", command=self.import_parameters)
        self.save_button = ttk.Button(actions, text="Save parameters", command=self.save_parameters)
        self.run_button = ttk.Button(actions, text="Run simulation", command=self.run)
        self.cancel_button = ttk.Button(actions, text="Cancel", command=self.cancel, state="disabled")
        self.export_button = ttk.Button(actions, text="Save results as…", command=self.export_result, state="disabled")
        for column, button in enumerate((self.import_button, self.save_button, self.run_button,
                                         self.cancel_button, self.export_button)):
            button.grid(row=0, column=column, padx=5)

        self.progress = tk.DoubleVar(value=0)
        ttk.Progressbar(outer, variable=self.progress, maximum=100).grid(row=4, column=0, sticky="ew", pady=(3, 8))
        self.status = tk.StringVar(value="Ready. Simulation runs in a separate Rust process.")
        ttk.Label(outer, textvariable=self.status, wraplength=1120).grid(row=5, column=0, sticky="w", pady=4)
        self.destination = tk.StringVar()
        ttk.Label(outer, textvariable=self.destination, wraplength=1120).grid(row=6, column=0, sticky="w", pady=4)
        self._update_destination()
        root.update_idletasks()
        root.minsize(min(root.winfo_reqwidth(), root.winfo_screenwidth() - 60), root.winfo_reqheight())

    def _update_destination(self, *_args):
        if not hasattr(self, "destination"):
            return
        config = {"output_filepath": self.fields["output_filepath"].get()}
        path = export_destination(config, self.base_directory)
        self.destination.set(f"Output: {path}" if path else "Output saving disabled. Completed results will still be plotted.")

    def _parse_fields(self):
        return parameters_from_fields(self.parameters, {k: v.get() for k, v in self.fields.items()})

    def import_parameters(self):
        path = filedialog.askopenfilename(parent=self.root, title="Import simulation parameters",
                                          filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            loaded = load_parameters(Path(path))
        except (OSError, ValueError) as exc:
            messagebox.showerror("Cannot import parameters", str(exc), parent=self.root)
            return
        self.parameters = loaded
        for name, variable in self.fields.items():
            variable.set(field_text(name, loaded[name]))
        self.status.set(f"Imported {Path(path).name}. Extra JSON fields are retained.")

    def save_parameters(self):
        try:
            parsed = self._parse_fields()
        except ParameterError as exc:
            messagebox.showerror("Invalid parameter", str(exc), parent=self.root)
            return
        path = filedialog.asksaveasfilename(parent=self.root, title="Save simulation parameters",
                                           defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not path:
            return
        try:
            save_parameters(Path(path), parsed)
        except OSError as exc:
            messagebox.showerror("Cannot save parameters", str(exc), parent=self.root)
            return
        self.parameters = parsed
        self.status.set(f"Saved parameters to {path}.")

    def _set_running(self, running: bool):
        state = "disabled" if running else "normal"
        for widget in (*self.entries.values(), self.seed_entry, self.threads_entry,
                       self.import_button, self.save_button, self.run_button):
            widget.configure(state=state)
        self.cancel_button.configure(state="normal" if running else "disabled")

    def run(self):
        if self.controller.active:
            return
        try:
            parsed = self._parse_fields()
            seed = int(self.seed.get().strip()) if self.seed.get().strip() else None
            workers = int(self.threads.get().strip()) if self.threads.get().strip() else None
            if seed is not None and not 0 <= seed <= 2**64 - 1:
                raise ParameterError("Seed must be an integer from 0 through 18446744073709551615.")
            if workers is not None and workers < 1:
                raise ParameterError("Workers must be a positive integer or blank.")
            self.controller.start(parsed, seed, workers)
        except (OSError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Cannot start simulation", str(exc), parent=self.root)
            return
        self.parameters = parsed
        self.repeat_cycles.clear()
        self.progress.set(0)
        self.status.set("Starting Rust simulation…")
        self._set_running(True)
        self._schedule_poll()

    def _schedule_poll(self):
        if self.poll_id is None:
            self.poll_id = self.root.after(50, self._poll)

    def cancel(self):
        self.controller.cancel()
        self.cancel_button.configure(state="disabled")
        self.status.set("Cancelling simulation…")

    def _poll(self):
        self.poll_id = None
        for event in self.controller.poll():
            kind = event["type"]
            if kind == "started":
                actual_seed = event.get("seed")
                self.status.set(f"Simulation running. Seed: {actual_seed}")
            elif kind == "progress" and not self.closing:
                repeat, cycle = event["repeat"], event["cycle"]
                self.repeat_cycles[repeat] = max(cycle, self.repeat_cycles.get(repeat, 0))
                total = event["total_repeats"] * event["total_cycles"]
                if total > 0:
                    self.progress.set(min(99.9, 100 * sum(self.repeat_cycles.values()) / total))
                if not (self.controller.job and self.controller.job.cancel_requested):
                    self.status.set(f"Repeat {repeat}/{event['total_repeats']} · cycle {cycle}/{event['total_cycles']} · {event['phase']}")
            elif kind == "succeeded":
                self._set_running(False)
                if not self.closing:
                    self._completed(event)
            elif kind == "finished_cancelled":
                self._set_running(False)
                self.status.set("Cancelled. Previous completed results are retained.")
            elif kind == "failed":
                self._set_running(False)
                self.status.set("Simulation failed. Previous completed results are retained.")
                if not self.closing:
                    messagebox.showerror("Simulation failed", event["message"], parent=self.root)
        if self.controller.active:
            self._schedule_poll()
        elif self.closing:
            self._destroy()

    def _completed(self, event):
        completed = event["run"]
        self.progress.set(100)
        self.export_button.configure(state="normal")
        seed = event.get("seed", completed.metadata.get("seed"))
        self.status.set(f"Completed. Seed: {seed}")
        try:
            self.show_plot(completed.result)
        except Exception as exc:
            messagebox.showerror("Cannot display plot", f"Results are retained and can be saved.\n{exc}", parent=self.root)
        destination = export_destination(completed.result["parameters"], self.base_directory)
        if destination is not None:
            try:
                if not Path(completed.result["parameters"]["output_filepath"]).is_absolute():
                    self.base_directory.mkdir(parents=True, exist_ok=True)
                completed.export(destination)
                self.status.set(f"Completed. Seed: {seed}. Saved {destination}")
            except OSError as exc:
                self.status.set(f"Completed. Seed: {seed}. Export failed; use Save results as…")
                messagebox.showerror("Results could not be saved", f"The simulation succeeded and results are retained.\n{exc}", parent=self.root)

    def show_plot(self, result: dict):
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
        from .plotting import make_figure
        figure = make_figure(result)
        window = tk.Toplevel(self.root)
        window.title("Dicty Simulator — results")
        canvas = FigureCanvasTkAgg(figure, master=window)
        canvas.draw()
        toolbar = NavigationToolbar2Tk(canvas, window, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.plot_windows.append(window)

        def close_plot():
            self.plot_windows.remove(window)
            window.destroy()
            figure.clear()

        window.protocol("WM_DELETE_WINDOW", close_plot)

    def export_result(self):
        result = self.controller.last_result
        if result is None:
            return
        path = filedialog.asksaveasfilename(parent=self.root, title="Save completed simulation results",
                                           defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if path:
            try:
                result.export(Path(path))
                self.status.set(f"Saved results and run metadata to {path}.")
            except OSError as exc:
                messagebox.showerror("Cannot save results", str(exc), parent=self.root)

    def close(self):
        if self.closing:
            return
        self.closing = True
        if self.controller.active:
            self.cancel()
            self.status.set("Closing: waiting for the simulation process to stop…")
            self._schedule_poll()
        else:
            self._destroy()

    def _destroy(self):
        self.controller.cleanup()
        for tooltip in self.tooltips:
            tooltip.hide()
        if self.poll_id is not None:
            self.root.after_cancel(self.poll_id)
        self.root.destroy()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Dicty Simulator desktop interface")
    parser.add_argument("--engine", help="Path to the Rust simulation executable")
    parser.add_argument("--param", help="Parameter JSON to display on startup")
    parser.add_argument("--smoke-test", metavar="REPORT_PATH", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.smoke_test:
        from .smoke import run_smoke_test
        raise SystemExit(run_smoke_test(Path(args.smoke_test), resolve_engine(args.engine)))
    root = tk.Tk()
    try:
        parameters = load_parameters(Path(args.param)) if args.param else None
        Application(root, resolve_engine(args.engine), parameters)
    except Exception as exc:
        messagebox.showerror("Cannot open Dicty Simulator", str(exc), parent=root)
        root.destroy()
        return
    root.mainloop()
