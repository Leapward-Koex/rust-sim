# Implementation release verification

Date: 2026-10-07. Engine version: 0.1.0. Behavior baseline: `python-test-env-62d707e-v1`.

The Windows application is in `dist/DictySimulator`; the distributable archive is `dist/DictySimulator-windows-x64.zip`. The source, captured baseline, build instructions, and validation evidence remain in this project folder.

## Completed checks

| Check | Result / evidence |
| --- | --- |
| Original behavior checker | 31 passed; `results.json`; checker source retained unchanged |
| Scripted source differential fixtures | 148 passed; `differential-results.json`; actual pinned SciPy, complete source `main()` and phase functions |
| Rust unit and sampling tests | 11 passed; includes negative-weight cumulative selection, fixed-seed sampling checks, confidence values, JSON preservation, and cancellation |
| CLI contract tests | 12 passed; `qa/test_cli.py`; includes Windows read-only failures in both result/metadata replacement directions |
| GUI/controller/plot tests | 20 passed, none skipped; `tests_python/test_gui.py`; actual Tk controls and TkAgg plots included |
| Original and snapshot integrity | All 205 recorded original files and 80 snapshot files unchanged; `source-integrity.json`; original Git status clean |
| Requirement traceability | All 115 numbered requirements classified; `COVERAGE.md` and `coverage-map.json` |
| Full workload and worker reproducibility | 500 cycles × 10 repeats completed; single-/multi-worker legacy result bytes identical; `full-workload.json` |
| Performance | 45–74× measured single-worker improvement; `PERFORMANCE.md` |
| Packaged application | Final frozen GUI and sidecar pass isolated integration; `package-smoke.json` |

The final packaged engine and tested release engine have the same SHA-256: `582505ce2115637d39012bf75d8401e1cd20a97855d408f92533ae78848909bc`. The archive SHA-256 is `0b2eb3f4f5886d3df14edc23fffe2baf99f203d9bb1fe34cd976050edc2041b8`.

## Independent implementation reviews

Two rounds used three fresh reviewers each, separate from the implementation authors. These are additional to the earlier independent reviews of the source specifications.

| Finding | Resolution and regression evidence |
| --- | --- |
| Eager conversion rejected valid unused phase parameters | Cache conversions and return errors only at actual phase use; real-source successful/failing differential cases and CLI checks |
| serde private-number keys corrupted unknown JSON objects | Escape and restore original object keys; nested/reserved/Unicode/nonfinite round-trip probes |
| Malformed completed parameters replaced valid prior results | Validate required result parameters before accepting completion; real subprocess failure test retains the prior result |
| Failed paired export left result/metadata inconsistent | Stage both files, preserve backups, roll back committed replacements on ordinary I/O failure; GUI injected failure and both Windows CLI read-only directions tested |
| Absolute export depended on the default Documents directory | Create the default base only for relative paths; actual Tk regression with unavailable default base |

Round-one findings are preserved in `implementation-review1-core.md`, `implementation-review1-data.md`, and `implementation-review1-ui.md`. Their historical open status is superseded by the fixes and second-round reports: `implementation-review2-core.md`, `implementation-review2-data.md`, and `implementation-review2-ui.md`, which have no remaining actionable findings.

Independent additional checks included 387 parameter-type probes, 60 missing-field probes, 27 key/Unicode probes, 65 further JSON round trips, 8 malformed-input cases, and 40 real-SciPy numerical comparisons. These strengthen the evidence but are not a claim of exhaustive correctness.

## Packaging boundary and limits

The final application was copied into a path containing spaces and Unicode and launched from an unrelated working directory. PATH contained only Windows System32; Python/Rust were absent from that PATH and Python/Tk overrides were removed. The frozen app loaded NumPy, Matplotlib, and Tkinter from its own folder, launched its bundled Rust engine, completed a simulation with saving disabled, and rendered an embedded plot while processing UI timers. The Rust sidecar imports only Windows system DLLs; the C runtime is statically linked. No separate Python/Rust installation is required by this distribution.

This was performed on the development Windows machine. **A separate clean Windows installation was not available and has not been tested.** The test explicitly records that distinction; source portability is not a claim that macOS/Linux packages have been built or validated.

Paired-file rollback covers ordinary I/O failures, not atomic recovery from power loss between two filesystem replacements. If rollback itself fails, the application retains recovery backups and reports their paths. RNG replay is guaranteed only within the stated Rust engine/version/platform boundary, not against Python's generators.

No branches or commits were created. The original simulation and captured reference remain unchanged.
