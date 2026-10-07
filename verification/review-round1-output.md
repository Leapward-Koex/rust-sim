# Fresh review: measurements, output, and verification harness

Reviewed independently on 2026-10-07 against the live `DictySimulator/dicty_sim_test_env.py`, `global_variables.py`, `locus.py`, and `locus_tracker.py`. The live copies, snapshot copies, and manifest hashes match for these four files. This review excludes specification 06.

## Findings requiring correction or completion

1. **Cross-file contradiction: specification 01 invents elapsed-time output.** `01-configuration-and-entrypoints.md:63` says "printing progress/timing", and line 102 says "print elapsed time". The source captures `start = timer()` at line 684 but never reads `start` or prints an elapsed duration. Specification 04's DISPLAY-001 is correct. Remove the timing claims from specification 01. This finding was also sent to the coordinating reviewer.

2. **DISPLAY-003 omits the exact legend strings.** "Legends use the matching patch labels" does not tell an implementer what those labels are. Source lines 943-945 and 948-950 define the first legend as `Cheater alleles`, `Resistor alleles`, `Wild-type alleles`, and the second as `Type 1`, `Type 2`, `Type 3`. Add those labels in order. A probe running the unchanged `main` body with plotting-call spies confirmed the legend handles and labels. This is a completeness gap, not a wrong formula or plotting color.

3. **Exact GUI console strings should be preserved somewhere.** Specification 01 already describes the parsed-list and process-ID prints, so their omission from specification 04 is not a missing behavior across the document set. However, it does not preserve the exact startup typo: source line 1076 prints `Proccess ID: {os.getpid()}`. Source line 99 prints the parsed Python list before storing it in `variables`. Add the exact startup spelling and cross-reference these GUI-only messages from DISPLAY-001 if that section is intended as the complete console-output catalog.

## Verification harness review

The harness really parses the snapshot with `ast.parse`, selects the named original `FunctionDef` and `ClassDef` nodes, and compiles those unchanged nodes (lines 50-65). It executes complete helper files for the defaults, locus, and tracker classes. It does not import and run the GUI module. Defaults are applied after function definition, correctly preserving captured CI default behavior. The local random generator replacement, forced CLI guard, configuration overrides, SciPy spy, and orchestration stage spies are visible in the implementation and accurately disclosed in the report scope.

All **28 checks passed** when independently invoked via `runpy.run_path(..., run_name='review_only')` using bundled Python 3.12.14 and NumPy 2.3.5. This invocation did not rewrite `results.json`. The ordinary `C:\Python314\python.exe` lacks NumPy; the successful runtime was `C:\Users\ScottM\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.

No false numerical SciPy-validation claim or harmful filesystem mutation was found in the retained checks. `orchestrated` captures the source `open` call in memory, including doubled `.json` and write mode. `json_nonfinite_defaults` tests the standard-library serializer directly; it should continue to be described that narrowly. SciPy is absent from the available bundled runtime, so this review does not newly establish its numerical outputs or warning text. The harness also does not test the installed application's real Tk/Matplotlib rendering or import requirements.

Useful coverage improvements, distinct from demonstrated harness bugs:

- `empty_init_errors` checks the exception type but not the partial snapshot state described by MEASURE-006. Add assertions for tracker lengths after failure.
- `stale_measurements_at_main_entry` uses zero repeats and a negative development count. It proves no entry reset, but does not demonstrate contamination of a subsequent actual run. Add a failed-scheduler followed by a successful-run example.
- All eight scalar inputs in `orchestrated.record` receive the same values. This cannot detect cross-wiring between scalar output series. Use distinct series/repeat/point values and verify every output series if these checks are extended.
- `confidence_bound_default` confirms quantile arguments and the product under a spy, but no retained check covers one-repeat SciPy `NaN`, real t quantiles, exact console strings, or plotting calls. The scope statement currently avoids claiming otherwise; retain that distinction.

## Additional independent source-body probes

These probes used unchanged extracted source bodies and in-memory output. They were not added to the retained harness.

| Probe | Observed result |
| --- | --- |
| `initialise_pop` with `n=0` | `ZeroDivisionError`; `locus_plot` length 1, all eight scalar trackers length 0. |
| `initialise_pop` with `gene_pairs=0`, `n=2` | Same tracker lengths and exception; stored snapshot is an empty tracker list. |
| One wild cell, `n=sl=1`, `sp=0`, development | Input list consumed; `ZeroDivisionError`; all nine trackers remain empty; printed `Len: 0, cheater: 0, resistor: 0, wild: 0 , total stalks: 1`. |
| Four-state measurement example with both effectiveness multipliers 1 | Both conditional effectiveness means exactly `1.0`. The retained four-state test already covers multipliers 0. |
| `main` fails scheduling with `i_macrocyst=[]`, interval 1 after initial `ch_start=0` population | All nine global tracker lists retain one observation. |
| Same environment then runs with `n_dev=0`, `ch_start=1` | Saved parameters report `ch_start=1`, but saved `mean_ch` is `[0.0]`: stale time-zero observation is used and extra current observations are not emitted. |
| GUI plotting branch with `n_dev=0`, then empty explicit schedule | JSON already exists in memory with all 21 keys before plotting raises `IndexError`. |

The first two observations make MEASURE-006 more precise; the two stale-run observations give a concrete consequence of AGG-002. Consider adding these details, but existing wording is not contradicted.

## Verified specification areas

- Measurement denominators, absent-slot wild counts, carrier-conditioned effectiveness, raw locus counters, the four-state example, and snapshot timing match source lines 342-393 and 524-608.
- Repeat accumulation and equal weighting, dictionary shape, nine global tracker resets, aggregation order, and non-reset cell IDs/RNG states match lines 683-904.
- The literal CI function and definition-time default `0.95` match lines 248-253; later CLI replacement and GUI edits do not affect omitted-argument calls.
- All 21 top-level JSON keys and their insertion order match lines 910-932. Filename concatenation, default `json.dump`, optional saving, absence of an explicit main return, and the incomplete interval-only sexual-cycle list match source.
- Printed simulation templates, summary-before-division timing, reset-before-run-completion messages, progress calls, plot colors, alpha values, dimensions, labels, title, and marker rules match the source, subject to the exact-label completeness findings above.

No incorrect measurement formula, JSON key/order, CI wiring, or claimed failure ordering was found in specification 04.
