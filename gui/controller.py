"""Nonblocking process lifecycle. No Tk objects are touched by worker threads."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid

from .parameters import ParameterError, validate_parameters


SCALAR_KEYS = (
    "mean_ch", "ch_ci", "mean_res", "res_ci", "mean_wild", "wild_ci",
    "mean_mt1", "mt1_ci", "mean_mt2", "mt2_ci", "mean_mt3", "mt3_ci",
    "graph_mean_ch_eff", "ch_eff_ci", "graph_mean_res_eff", "res_eff_ci",
)
RESULT_KEYS = ("parameters", "sex_cycle_list", "x_axis_values", *SCALAR_KEYS,
               "average_tracker_dict", "ci_tracker_dict")


class ProtocolError(ValueError):
    pass


def resolve_engine(override: str | None = None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    filename = "dicty-sim.exe" if os.name == "nt" else "dicty-sim"
    if getattr(sys, "frozen", False):
        beside = Path(sys.executable).resolve().parent / filename
        bundled = Path(getattr(sys, "_MEIPASS", beside.parent)) / filename
        return beside if beside.is_file() else bundled
    return Path(__file__).resolve().parents[1] / "target" / "release" / filename


def validate_result(data: object) -> dict:
    if not isinstance(data, dict) or set(data) != set(RESULT_KEYS):
        raise ProtocolError("The engine result does not contain the expected 21 fields.")
    try:
        validate_parameters(data["parameters"])
    except ParameterError as exc:
        raise ProtocolError(f"Invalid result parameters: {exc}") from exc
    x = data["x_axis_values"]
    if not isinstance(x, list) or any(type(v) not in (int, float) for v in x):
        raise ProtocolError("The result x-axis is not a numeric array.")
    if not isinstance(data["sex_cycle_list"], list):
        raise ProtocolError("The result sex-cycle history is not an array.")
    for key in SCALAR_KEYS:
        values = data[key]
        if not isinstance(values, list) or len(values) != len(x):
            raise ProtocolError(f"Result series {key} has an invalid length.")
        if any(type(v) not in (int, float) for v in values):
            raise ProtocolError(f"Result series {key} is not numeric.")
    for key in ("average_tracker_dict", "ci_tracker_dict"):
        if not isinstance(data[key], dict):
            raise ProtocolError(f"Result {key} is not an object.")
        for name, series in data[key].items():
            if not isinstance(series, list) or len(series) != 3:
                raise ProtocolError(f"Result {name} must contain three locus series.")
            for values in series:
                if (not isinstance(values, list) or len(values) != len(x)
                        or any(type(v) not in (int, float) for v in values)):
                    raise ProtocolError(f"Result {name} has an invalid locus series.")
    return data


def strict_event(line: str) -> dict:
    def reject(value: str):
        raise ProtocolError(f"Nonfinite value {value} in the strict event protocol.")
    try:
        value = json.loads(line, parse_constant=reject)
    except ValueError as exc:
        raise ProtocolError(f"Invalid JSON progress event: {exc}") from exc
    if (not isinstance(value, dict) or type(value.get("protocol_version")) is not int
            or value["protocol_version"] != 1):
        raise ProtocolError("The engine and GUI event protocol versions do not match.")
    if value.get("type") not in ("started", "progress", "completed", "cancelled", "error"):
        raise ProtocolError("The engine emitted an unknown progress event.")
    if not isinstance(value.get("run_id"), str) or not value["run_id"]:
        raise ProtocolError("The engine event has no run identifier.")
    return value


@dataclass
class CompletedRun:
    result: dict
    result_bytes: bytes
    metadata: dict
    metadata_bytes: bytes
    directory: tempfile.TemporaryDirectory

    def export(self, destination: Path) -> None:
        """Stage exact bytes and roll back both files if either replacement fails.

        Two file replacements cannot be crash-atomic, but ordinary I/O errors
        must not leave new data paired with old metadata or destroy old results.
        """
        paths = [Path(str(destination) + ".run.json"), destination]
        payloads = [self.metadata_bytes, self.result_bytes]
        token = uuid.uuid4().hex
        staged = [p.with_name(p.name + f".{token}.tmp") for p in paths]
        backups = [p.with_name(p.name + f".{token}.backup") for p in paths]
        existed = [p.exists() for p in paths]
        committed = []
        preserve_backups = False
        try:
            # Discover inaccessible targets before replacing either file.
            for path, payload, temp, backup, exists in zip(paths, payloads, staged, backups, existed):
                if exists:
                    if not path.is_file():
                        raise OSError(f"Export destination is not a file: {path}")
                    shutil.copyfile(path, backup)
                with temp.open("xb") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
            for index, (temp, path) in enumerate(zip(staged, paths)):
                os.replace(temp, path)
                committed.append(index)
        except OSError as original:
            failures = []
            for index in reversed(committed):
                try:
                    if existed[index]:
                        os.replace(backups[index], paths[index])
                    else:
                        paths[index].unlink(missing_ok=True)
                except OSError as exc:
                    failures.append(str(exc))
            if failures:
                preserve_backups = True
                raise OSError(f"Export failed: {original}. Restoration also failed: {'; '.join(failures)}. "
                              f"Recovery backups: {', '.join(str(p) for p in backups if p.exists())}") from original
            raise
        finally:
            for path in staged + ([] if preserve_backups else backups):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass

    def cleanup(self) -> None:
        self.directory.cleanup()


@dataclass
class _Job:
    token: str
    process: subprocess.Popen
    directory: tempfile.TemporaryDirectory
    result_path: Path
    metadata_path: Path
    messages: queue.Queue
    engine_run_id: str | None = None
    completion: dict | None = None
    error: str | None = None
    terminal_seen: bool = False
    cancelled_event: bool = False
    cancel_requested: bool = False
    cancel_deadline: float | None = None
    terminated_at: float | None = None
    stderr_tail: deque = field(default_factory=lambda: deque(maxlen=40))


class RunController:
    def __init__(self, engine: Path, prefix: tuple[str, ...] = ()):
        # prefix is an injection seam for executable protocol fixtures.
        self.engine = engine.resolve()
        self.prefix = prefix
        self.job: _Job | None = None
        self.last_result: CompletedRun | None = None

    @property
    def active(self) -> bool:
        return self.job is not None

    def start(self, parameters: dict, seed: int | None = None, threads: int | None = None,
              backend: str = "auto") -> str:
        if self.active:
            raise RuntimeError("A simulation is already running.")
        if backend not in ("auto", "cpu", "gpu"):
            raise ValueError("Computation must be Automatic, CPU, or GPU-assisted.")
        if not self.engine.is_file():
            raise FileNotFoundError(f"Rust simulation executable not found: {self.engine}")
        directory = tempfile.TemporaryDirectory(prefix="dicty-run-")
        location = Path(directory.name)
        parameter_path = location / "parameters.json"
        result_path = location / "result.json"
        metadata_path = Path(str(result_path) + ".run.json")
        try:
            parameter_path.write_text(json.dumps(parameters, ensure_ascii=False), encoding="utf-8")
            arguments = [str(self.engine), *self.prefix, "--param", str(parameter_path),
                         "--result", str(result_path), "--events", "--backend", backend]
            if seed is not None:
                arguments += ["--seed", str(seed)]
            if threads is not None:
                arguments += ["--threads", str(threads)]
            process = subprocess.Popen(
                arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
                cwd=location, shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except Exception:
            directory.cleanup()
            raise
        job = _Job(uuid.uuid4().hex, process, directory, result_path, metadata_path, queue.Queue())
        self.job = job

        def read(stream, kind: str):
            try:
                with stream:
                    with (location / (kind + ".log")).open("w", encoding="utf-8") as log:
                        for line in stream:
                            log.write(line)
                            log.flush()
                            job.messages.put((job.token, kind, line.rstrip("\r\n")))
            except Exception as exc:
                job.messages.put((job.token, "reader_error", str(exc)))

        readers = [threading.Thread(target=read, args=(process.stdout, "stdout"), daemon=True),
                   threading.Thread(target=read, args=(process.stderr, "stderr"), daemon=True)]
        for reader in readers:
            reader.start()

        def finish():
            code = process.wait()
            for reader in readers:
                reader.join()
            if process.stdin:
                try:
                    process.stdin.close()
                except OSError:
                    pass
            job.messages.put((job.token, "exit", code))

        threading.Thread(target=finish, daemon=True).start()
        return job.token

    def cancel(self) -> None:
        job = self.job
        if job is None or job.cancel_requested:
            return
        job.cancel_requested = True
        job.cancel_deadline = time.monotonic() + 2.0
        try:
            job.process.stdin.write('{"command":"cancel"}\n')
            job.process.stdin.flush()
        except (OSError, ValueError):
            pass

    def _stop_failed_protocol(self, message: str) -> None:
        job = self.job
        if job.error is None:
            job.error = message
        if job.process.poll() is None:
            job.process.terminate()
            job.terminated_at = time.monotonic()

    def poll(self) -> list[dict]:
        """Call from Tk's main thread. Always returns promptly."""
        job = self.job
        if job is None:
            return []
        now = time.monotonic()
        if job.process.poll() is None:
            if job.cancel_deadline is not None and now >= job.cancel_deadline and job.terminated_at is None:
                job.process.terminate()
                job.terminated_at = now
            elif job.terminated_at is not None and now - job.terminated_at >= 2:
                job.process.kill()
        events = []
        for _ in range(2000):
            try:
                token, kind, value = job.messages.get_nowait()
            except queue.Empty:
                break
            if token != job.token:
                continue
            if kind == "stderr":
                job.stderr_tail.append(value)
            elif kind == "reader_error":
                self._stop_failed_protocol("Cannot read engine output: " + value)
            elif kind == "stdout" and job.error is None:
                try:
                    event = strict_event(value)
                    event_type = event["type"]
                    if job.terminal_seen:
                        raise ProtocolError("The engine emitted an event after its terminal event.")
                    if job.engine_run_id is None:
                        if event_type not in ("started", "error", "cancelled"):
                            raise ProtocolError("The first engine event was not started.")
                        job.engine_run_id = event["run_id"]
                    elif event["run_id"] != job.engine_run_id or event_type == "started":
                        raise ProtocolError("The engine changed run identifiers or started twice.")
                    if event_type == "completed":
                        if Path(event.get("result_path", "")).resolve() != job.result_path.resolve():
                            raise ProtocolError("The engine reported an unexpected result path.")
                        if Path(event.get("metadata_path", "")).resolve() != job.metadata_path.resolve():
                            raise ProtocolError("The engine reported an unexpected metadata path.")
                        job.completion = event
                        job.terminal_seen = True
                    elif event_type == "error":
                        job.error = str(event.get("message", "Simulation failed."))
                        job.terminal_seen = True
                    elif event_type == "cancelled":
                        job.cancelled_event = True
                        job.terminal_seen = True
                    elif event_type == "progress":
                        if (not isinstance(event.get("phase"), str)
                                or any(type(event.get(k)) is not int for k in
                                       ("repeat", "cycle", "total_repeats", "total_cycles"))):
                            raise ProtocolError("The progress event is missing phase or cycle counts.")
                    events.append(event)
                except (ValueError, TypeError) as exc:
                    self._stop_failed_protocol(str(exc))
            elif kind == "exit":
                events.append(self._finish(job, value))
                self.job = None
                break
        return events

    def _finish(self, job: _Job, exit_code: int) -> dict:
        if job.error:
            outcome = {"type": "failed", "message": job.error}
        elif job.cancel_requested or job.cancelled_event or exit_code == 130:
            outcome = {"type": "finished_cancelled"}
        elif exit_code != 0:
            detail = "\n".join(job.stderr_tail)
            outcome = {"type": "failed", "message": f"Engine exited with code {exit_code}.\n{detail}"}
        elif job.completion is None:
            outcome = {"type": "failed", "message": "Engine exited without a completion event."}
        else:
            try:
                payload = job.result_path.read_bytes()
                result = validate_result(json.loads(payload))
                metadata_bytes = job.metadata_path.read_bytes()
                metadata = json.loads(metadata_bytes)
                if not isinstance(metadata, dict):
                    raise ProtocolError("Run metadata is not an object.")
                completed = CompletedRun(result, payload, metadata, metadata_bytes, job.directory)
                if self.last_result:
                    self.last_result.cleanup()
                self.last_result = completed
                return {"type": "succeeded", "run": completed, "seed": job.completion.get("seed")}
            except (OSError, ValueError) as exc:
                outcome = {"type": "failed", "message": f"Cannot read the completed result: {exc}"}
        job.directory.cleanup()
        outcome["exit_code"] = exit_code
        return outcome

    def cleanup(self) -> None:
        if self.active:
            raise RuntimeError("Cancel and reap the active simulation before cleanup.")
        if self.last_result:
            self.last_result.cleanup()
            self.last_result = None
