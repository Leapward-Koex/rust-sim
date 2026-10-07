# Implementation review round 1 — desktop UI and delivery

Reviewed independently on 2026-10-07. Scope: `gui/`, `tests_python/`, `packaging/launcher.py`, `scripts/build_windows.py`, the current Rust event/output boundary, and the captured source/specifications. No implementation or reference-source files were edited by this reviewer. Findings describe the code as initially reviewed; the author owns remediation.

## Findings requiring correction

### UI-R1-001 — P2: malformed result parameters are accepted as a successful run

Locations: `gui/controller.py:46-49`, `gui/controller.py:297-303`, and `gui/app.py:230` at review time.

`validate_result()` checks only that `parameters` is an object containing `i_macrocyst`. A result with otherwise valid arrays and `parameters={"i_macrocyst":[0]}` passes validation. The controller then replaces and cleans up the previous completed result. `Application._completed()` subsequently reads `output_filepath` through `export_destination()` outside its error handler and raises `KeyError`. Wrongly typed output paths have a similar path to an uncaught exception. This breaks the requirement that malformed results fail clearly while retaining the previous completed result.

Executed reproduction using `.venv-build/Scripts/python.exe`:

```python
from pathlib import Path
from gui.controller import validate_result
from gui.parameters import export_destination
from tests_python.test_gui import sample_result
r = sample_result()
r["parameters"] = {"i_macrocyst": [0]}
assert validate_result(r) is r
export_destination(r["parameters"], Path.cwd())  # KeyError: 'output_filepath'
```

Required fix: validate the full parameter object before accepting a completed result or cleaning up the previous one. Add an end-to-end controller regression proving malformed nested parameters retain the preceding successful result; guard export preparation errors in the GUI as well.

### UI-R1-002 — P2: export failure can overwrite a prior saved result without its metadata

Location: `gui/controller.py:99-102` at review time.

`CompletedRun.export()` writes the destination result directly and then writes the metadata. If the second write fails, the UI reports export failure but the prior result file has already been replaced. Any pre-existing metadata can now describe the wrong simulation/seed. Failure partway through the first write can also leave a truncated destination. These are user files, so retaining the in-memory result alone is insufficient recovery.

Executed reproduction: create `existing.json` containing `b"old completed result"`, create a directory named `existing.json.run.json`, then call `CompletedRun(..., result_bytes=b"new completed result", metadata_bytes=b"{}", ...).export(existing_path)`. Export raises `PermissionError`, while `existing.json` now contains `b"new completed result"`.

Required fix: stage both files before replacing either, and restore the prior pair if replacement of the second file fails. Do not leave an existing result paired with unrelated metadata. Add failure-injection coverage for both staging and replacement failures.

The equivalent issue is present in the CLI output boundary in `src/main.rs`: metadata is atomically replaced before the result is atomically replaced. Independently reproduced with an existing Windows read-only result file, metadata containing seed 111, and a new zero-development-cycle run with seed 222. The engine exited 1 with `Cannot replace ... Access is denied`, the old result remained, and its metadata now contained seed 222. Pair consistency must cover both the GUI exporter and CLI writer.

## Executed checks

- `python -m unittest discover -s tests_python -v`: all 17 tests passed, including real subprocess fixtures and Tk tests; none skipped. `TMP` and `TEMP` were set to the workspace `build/tmp` directory.
- Real release-engine/controller integration: 48 cells, slug size 8, three development cycles, two repeats, one vegetative generation, seed 12345, two workers, saving disabled. Completed successfully with the expected 21 result fields and versioned started/progress/completed events.
- Real release-engine cancellation: started the 10,000-cell, 500-cycle, 10-repeat workload with two workers, cancelled after approximately 100 ms, and received `finished_cancelled` with the process reaped approximately 32 ms after cancellation.
- Both findings above were independently reproduced using executable Python probes.
- The CLI variant of the paired-file consistency finding was reproduced with the actual release executable and a read-only result file in the workspace test directory; test file attributes were restored before cleanup.

## Source-reviewed conclusions and limits

- The 31 parameter defaults/order, seven-row grouping, parameter preservation, list handling, and deliberate fractional-input improvements agree with the approved plan. The two-panel figure's series, colors, labels, limits, confidence fills, and sex-marker behavior agree with the source/specification, with the approved empty-list plotting fix.
- The controller uses absolute executable paths, separate pipe readers, a Tk-polled queue, per-job tokens, strict versioned events, and a private result path. The real engine's current event field names and file paths match this contract. Cooperative and forced cancellation are covered by tests.
- The packaging script uses the intended onedir/windowed launcher and places the Rust sidecar where the frozen resolver expects it. At the time of this review, there was no completed distribution artifact to inspect. This review therefore does not claim clean-machine or packaged-application acceptance.
- No additional blocking source-level finding was identified in these areas. Release readiness requires correction and regression verification of the two findings above, plus the planned packaged-artifact checks.
