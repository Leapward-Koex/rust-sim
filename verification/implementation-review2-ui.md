# Implementation review round 2 — integrated desktop UI

Reviewed independently on 2026-10-07 by a fresh reviewer who did not author the implementation or round-one review. Scope: `gui/`, `tests_python/`, the actual release-engine process boundary, and the approved UI requirements. Only this review and its evidence files were written by the reviewer; implementation fixes were made by the coordinating author. The original simulation and reference snapshot were not modified.

## Findings and resolution

### UI-R2-001 — P2: absolute exports unnecessarily depend on the default Documents directory — resolved

Initially, `Application._completed()` always created `self.base_directory` before exporting, even when `output_filepath` was absolute. An inaccessible, unavailable, or file-occupied Documents/Dicty Simulator location therefore prevented saving to an otherwise writable absolute destination.

Independent reproduction used a temporary file as `app.base_directory`, another writable absolute temporary output basename, and a completed result. The GUI reported WinError 183, and the requested result file was not written. This is a workflow problem because the unrelated default directory should not govern a user-selected absolute destination.

The author changed `gui/app.py:233` to create the default directory only for relative configured paths. The added `test_absolute_export_does_not_require_default_documents_directory` passed in the reviewer's full regression run. Resolved; no outstanding UI finding from this round.

### Round-one regression verification

- **UI-R1-001:** `validate_result()` now checks all required parameter keys and a string output path before replacing the previous completed result. The subprocess regression for incomplete nested parameters passed and retained the previous result.
- **UI-R1-002:** `CompletedRun.export()` now stages both payloads, backs up previous files, and rolls back committed replacements after ordinary I/O failure. Tests passed for a metadata destination occupied by a directory and for an injected failure replacing the second file. Both previous files and directory cleanliness were preserved.
- Unused parameter values remain ordinary JSON values during import/edit/save; the engine decides which parameters are accessed by a run. Round-trip tests cover null/object/string phase values, boolean numeric values, fractional switches, mixed schedules, and unknown fields.

## Executed verification

Commands used `.venv-build/Scripts/python.exe`, with `TEMP` and `TMP` pointing to the workspace `build/tmp` directory.

1. `python -m unittest discover -s tests_python -v` after the fix: **20 tests passed, none skipped**. This includes actual Tk widgets, graph artists, actual subprocess fixtures, malformed protocol/results, stderr draining, stale queue messages, forced termination, export failures, transactional parameters, and close-while-running.
2. `python -m gui --smoke-test verification/ui-source-review2-smoke.json`: **passed** using the real release Rust executable. A 48-cell, three-cycle, two-repeat run produced 21 fields, four result points, one plotted Tk window, and four timer heartbeats. Persistent saving was disabled, and the plot still appeared. The report records the module versions and paths.
3. Additional real-engine cancellation probes targeted **growth, development, and sex** separately, waiting for each corresponding progress event before sending cancellation. Each used 100,000 cells, 16 loci, one worker, and seed 1234; sexual runs scheduled cycle 1 with 2,000 founders and 50 clones per founder. All three processes exited 130, were reaped, and retained the preceding successful result. Observed completion was within the local monotonic clock's measurement resolution; the `0.0` values in `ui-review2-real-cancellation.json` must not be interpreted as a measured zero-cost operation.
4. Independently reproduced the absolute-export finding before remediation, then verified the added regression after remediation.

## Source-review conclusions and limits

- The main Tk thread owns UI and plot changes. Separate background readers drain both pipes into queues, and polling uses job tokens, run identifiers, expected private output paths, and terminal-event ordering. Success requires a completion event, a zero exit, readable metadata, and a validated result.
- The graph implementation retains the source's two panels, series, colors, confidence fills, limits, labels, and sex markers, with the approved empty-schedule improvement. A plot error leaves data available for export.
- The UI runs an absolute engine path without a shell, passes its parameters through a private snapshot, and preserves byte-for-byte legacy result payloads on export. Closing and cancellation share process cleanup, and previous completed plots/results survive failed or cancelled runs.
- The adjacent CLI variant of paired output replacement was relayed to the coordinator and is being handled by the separate engine/output review. This UI report does not attest to that Rust writer fix.
- At this review checkpoint, no packaged distribution existed. The source smoke test does not establish frozen-app, clean-machine, or isolated-package acceptance. Those checks remain a release validation step; the report can be supplemented after packaging.

**Outcome:** the integrated UI passes this fresh review after the documented fix. Packaged-artifact validation remains separate.
