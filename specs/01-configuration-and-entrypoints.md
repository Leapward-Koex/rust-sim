# Configuration, entrypoints, and run orchestration

This is an **as-implemented** contract for `DictySimulator/dicty_sim_test_env.py`. Requirements describe the existing executable behavior, including inconsistencies and failure paths; they are not corrections or inferred biological intent. Source line references apply to the source snapshot recorded by this specification set. `S` below means [dicty_sim_test_env.py](<C:/Dev/Dicty sim/rust-sim/reference-source/dicty_sim_test_env.py>); `G` means [global_variables.py](<C:/Dev/Dicty sim/rust-sim/reference-source/global_variables.py>); `T` means [import_template.json](<C:/Dev/Dicty sim/rust-sim/reference-source/import_template.json>).

## CONFIG-001 — Parameter sources and representations

There are exactly **31** entries in `G.variables` and the supplied import template. The module imports the dictionary from `global_variables` at S:19. There is no configuration class, schema, merging function, or range validator.

The table preserves the literal module defaults and JSON template defaults. `int` and `float` in the GUI column mean the Python conversions used by `submit_form`, not validated input types. JSON values are used as parsed: a JSON `1.0` remains a floating-point number, `1` an integer, and `true` a boolean. Python comparisons may accept numerically equal values, but `range`, indexing, sampling, and arithmetic retain their normal type restrictions. Sources: G:1–33, T:1–31, S:82–104 and 1013–1021.

| Parameter | Module default | Template default | GUI conversion | Executed meaning / limits |
|---|---|---|---|---|
| `n_runs` | `10` | `10` | `int` | Repeat count: `range(0, n_runs)`. Each repeat initializes a new population. S:757–759. |
| `n_dev` | `500` | `500` | `int` | Number of development iterations after initial sample, cycles `1..n_dev` inclusive. S:762. |
| `i_macrocyst` | string `"0"` | array `[0]` | comma-separated integer list | Explicit sexual-cycle membership list; first item also controls interval selection. See RUN-002. |
| `sex_cycle_interval` | `0` | `0` | `int` | Use interval scheduling only if nonzero and `i_macrocyst[0] == 0`; otherwise ignored by the scheduling branch. S:765–785. |
| `vg` | `10` | `10` | `int` | Vegetative reproduction/mutation generations per call to `vegetative_growth`, which is called once in every development iteration. Germination filtering occurs before this loop even when `vg == 0`. S:398–447. |
| `n` | `10000` | `10000` | `int` | Initial target population and offspring count per vegetative generation; also determines number of slugs through `floor(n/sl)`. No even-number rounding is implemented. S:276, 287–299, 427, 461. |
| `sl` | `1000` | `1000` | `int` | Number of cells sampled for each slug. S:461–466. |
| `sp` | `0.8` | `0.8` | `float` | A cell enters the pre-stalk list when a uniform draw is `< 1-sp`, in discrete passive mode only. It does not prescribe an exact number of spores. S:485–497. |
| `m_ch` | `0.001` | `0.001` | `float` | For every offspring locus per vegetative generation, toggle cheater allele when uniform draw `<= m_ch`. S:435–441. |
| `m_re` | `0.001` | `0.001` | `float` | Separate draw `<= m_re` toggles resistance allele. S:443–447. |
| `c_ch` | `0.01` | `0.01` | `float` | Cost times raw cheater-allele count in vegetative fitness; times `ch_eff()` in sexual progeny fitness. S:420, 674. |
| `c_res` | `0.01` | `0.01` | `float` | Cost times raw resistance-allele count in vegetative fitness; times `res_eff()` in sexual progeny fitness. S:420, 674. |
| `ch_germ` | `0` | `0.0` | `float` | Germination filter for cells with positive raw cheater count: remove when `1-ch_germ*ch_eff() < uniform(0,1)`. S:403–412. |
| `c_ch_res` | `0` | `0.0` | `float` | **Unused by the active engine.** It is editable and serialized; no combined cost term is calculated. |
| `ch_start` | `0` | `0.0` | `float` | Select initial cells whose **every locus** receives cheater allele; random/sequential branch rounding differs; the sequential branch can overlap. S:285–306. |
| `res_start` | `0` | `0.0` | `float` | Select initial cells whose **every locus** receives resistance allele. S:285–310. |
| `ch_res_dist` | `1` | `1` | `int` | Exactly `1`: independently sample cheater and resistance index sets. Every other value: construct contiguous index ranges, including the overlap behavior specified in the population specification. S:286–300. |
| `ch_eff_rc` | `0` | `0.0` | `int` | Both-allele multiplier in `ch_eff`; discrete exploitation only branches on exact `0` or `1`. Fractional values from JSON affect effectiveness but cannot activate an exploitation branch. S:165–177, 195–225. |
| `res_eff_rc` | `0` | `0.0` | `int` | Both-allele multiplier in `res_eff`; exploitation only branches on exact `0` or `1`. S:179–225. |
| `mc_count` | `100` | `100` | `int` | Number of first parents sampled without replacement per sexual call. S:620. |
| `mc_germ_count` | `100` | `100` | `int` | Clones emitted for each macrocyst's single computed progeny genotype. S:676–678. |
| `recomb_chance` | `1` | `1.0` | `float` | After the loci-list equality special case (locus-object identity, not allele-value equality; SEX-003), take the intact loci and mating type of one randomly chosen parent when a uniform draw is `< 1-recomb_chance`; otherwise recombine. S:647–670. |
| `mt1_start` | `0.5` | `0.5` | `float` | Weight for mating type `1` in initial `random.choices`. S:260–278. |
| `mt2_start` | `0.5` | `0.5` | `float` | Weight for mating type `2`. Weights are not checked to sum to one. S:260–278. |
| `mt3_start` | `0` | `0.0` | `float` | Weight for mating type `3`; type 3 receives no special compatibility rule. S:260–278, 636–641. |
| `output_filepath` | `"default_out"` | `"default_10Sex"` | `str` | If not empty, append literal `.json` and write results there; empty suppresses file output. The template filename does not enable sex: its schedule values disable sex. S:907–944. |
| `resistance_type` | `1` | `1.0` | `float` | Exactly `1`: passive branch. All other values have no branch and contribute no spores; later empty-population measurement fails. S:485–522, 572–589. |
| `gene_pairs` | `3` | `3` | `int` | Number of ordered two-allele loci per cell and tracker positions. S:267–270, 526–528, 734–741. |
| `discrete_res` | `1` | `1.0` | `float` | Exactly `1`: pre-stalk and exploitation logic. Every other value, with passive resistance, leaves the stalk list empty and returns all selected slug cells as spores. There is no active additive development algorithm. S:485–522. |
| `ch_self_cheat` | `0` | `0` | `int` | **Unused by the active engine.** The active `Cell.exploitable` logic does not read it. |
| `confidence_interval` | `0.95` | `0.95` | `float` | Serialized, but the function default is captured from the module dictionary at definition time, before GUI or CLI overrides. Normal calls use that captured `0.95`, so editing this parameter does not change computed intervals. S:248–253, 876–904. |

## CONFIG-002 — No parameter validation or correction

1. No bounds checks constrain probabilities, population sizes, frequencies, costs, locus counts, or mating weights. No check enforces the tooltip rule that mating weights sum to one, or mutual exclusion between an explicit sex list and interval. Python/library operations and the actual branch comparisons decide behavior. S:82–108, 255–395, 398–681, 1013–1021.
2. No adjustment makes `n` even. No adjustment makes `n` divisible by `sl`. Development forms `floor(n/sl)` slugs, leaving unsampled cells outside the returned population. S:461–473.
3. `resistance_type` and `discrete_res` are numeric comparisons, not enums. In particular JSON `1.0` and GUI `1.0` compare equal to `1`. `ch_res_dist` similarly uses equality with `1`, and the effectiveness switches use equality with `0` and `1`. S:195–225, 286, 485–490.
4. Nonzero interval does not necessarily activate interval scheduling: the first list element must be integer/numerically equal `0`. List order matters to this mode selection even though explicit-cycle membership does not depend on order. S:765–778.
5. The model has no parameter for random seed, maximum population, generation time, spatial geometry, carrying-capacity dynamics, or per-run output files. Extra JSON keys are retained in the dictionary and serialized under `parameters` but do not acquire behavior. S:910–911, 1019.
6. The tooltip descriptions are not the executable contract. In addition to the mismatches above, GUI `i_macrocyst` accepts comma-separated values rather than Python list syntax, `output_filepath` produces `.json` rather than `.txt`, and `vg` is run every development cycle rather than only when sex occurs. S:37–69, 82–104, 765–785, 908.

## RUN-001 — CLI entrypoint

The documented active entrypoint is `python dicty_sim_test_env.py`, with optional literal `--param path`. The README explicitly names this file, despite its `test_env` name. See [README.md](<C:/Dev/Dicty sim/rust-sim/reference-source/README.md:4>).

1. Imports and definitions execute before the `__main__` block; even CLI execution imports Tkinter, Matplotlib, NumPy, and SciPy. S:1–21.
2. The executable checks whether the exact string `--param` occurs anywhere in `sys.argv`. It takes the token immediately after the **first** occurrence as the file path. There is no `argparse`, help flag, other supported option, or `--param=path` parsing. Unrecognized arguments do not prevent GUI startup if no literal `--param` is present. S:1013–1024.
3. It opens that file in default text read mode, calls `json.load`, **rebinds the entire module variable** `variables` to the decoded result, closes the file, then calls `main`. It does not fill missing keys from defaults or convert input values. S:1018–1021.
4. Missing next token, unreadable file, invalid JSON, missing accessed keys, wrong types, and downstream simulation errors are uncaught by the script. A JSON object is the usable input shape; it is not validated up front. S:1013–1021 and key reads throughout the engine.
5. A CLI configuration should represent `i_macrocyst` as an integer array, such as `[0]` or `[10,20]`. The active CLI does **not** parse the string representation used by the module GUI defaults. With positive development cycles, string `"0"` eventually encounters integer membership testing against a string and fails; the code does not translate it to `[0]`. S:765–778.
6. Presence of `--param` also suppresses progress-widget access and built-in plotting. CLI output-file creation is nevertheless optional in implementation: `output_filepath == ""` runs and discards in-memory results after printing simulation progress. The README's statement that a file “must” be specified is usage guidance, not an enforced check. S:610–613, 858–862, 907–944, 946–1006.
7. Paths are used as given, relative to the process working directory when relative. No working-directory change or automatic output directory creation occurs in the entrypoint. S:1018, 908–944.

## RUN-002 — Scheduling and cycle order

For every repeat `j` in `range(0,n_runs)`:

1. Call `initialise_pop()` once. This creates population and initial measurements at sample index/cycle **0**. It does not execute a development or sexual phase for cycle 0. S:757–759; initial measurement S:342–393.
2. For each integer `i` from **1** through `n_dev`, execute exactly one `vegetative_growth` call and exactly one `developmental_cycle` call, in that order. Before those calls, optionally execute `sexual_cycle` according to the following decision. S:762–786.

```text
if sex_cycle_interval != 0 AND i_macrocyst[0] == 0:
    if i % sex_cycle_interval == 0:
        pop = sexual_cycle(pop)
        pop = vegetative_growth(pop)
        pop = developmental_cycle(pop)
        sex_cycle_list.append(i)
    else:
        pop = vegetative_growth(pop)
        pop = developmental_cycle(pop)
else:
    if i in i_macrocyst:
        pop = sexual_cycle(pop)
    pop = vegetative_growth(pop)
    pop = developmental_cycle(pop)
```

3. Sex is therefore **additional work before growth and development**, not a replacement for either phase, and occurs on the preceding cycle's spore population (or the initial population for cycle 1). The germination filter in vegetative growth also runs on the fresh sexual offspring when sex has occurred. S:767–769, 779–781, 398–415.
4. `sex_cycle_list` is allocated once per `main()` before the repeat loop. It receives entries only for interval-triggered cycles, after development succeeds. The explicit-list branch never appends to it. It is not reset between repeats, so two repeats with interval 2 and `n_dev=4` produce `[2,4,2,4]`. S:743–744, 757–785.
5. In explicit mode, duplicates in the configured list cause only one sexual call per matching cycle. Zero, negative, or out-of-range entries are never executed by the positive cycle loop. `[0]` with zero interval disables sex. `[0,2]` with nonzero interval selects interval mode and ignores membership of the later `2`; with zero interval it uses membership and executes sex at 2. S:762–785.
6. A negative nonzero interval is not rejected and follows Python modulo equality with zero. A zero interval bypasses `[0]` indexing because of short-circuit evaluation; an empty list can therefore run in explicit mode with no sexual cycles, but GUI plotting later indexes `[0]` and can fail. An empty list with nonzero interval fails at scheduling. S:765, 778, 996.
7. No sex occurs after the final development sample. There are no measurements between sexual reproduction and vegetative growth, or between individual vegetative generations. Only initialization and development append sample measurements. S:255–395, 398–451, 453–615, 617–681.

## RUN-003 — Repeat state and lifecycle

1. The repeat loop is sequential, with no process/thread pool. Each new repeat discards the previous `pop` by assigning `initialise_pop()`'s result. Statistical accumulators in `main` combine corresponding sample indices from repeats. S:683–741, 757–841.
2. At module import, nine history arrays are initialized: cheater, resistance, wild, mean cheater effectiveness, mean resistance effectiveness, the three mating-type histories, and `locus_plot`. After each successful repeat is copied into aggregate structures, all nine global histories are replaced by empty lists. They are **not cleared at the start of `main` or `initialise_pop`**. S:23–34, 255–258, 683–695, 843–852.
3. No seed is set at startup or per repeat, and no RNG state is saved in the output. Python `random` and NumPy `np.random` are both used. `Cell._id_counter` starts at class definition and is never reset between repeats or GUI submissions. S:112–123, 242–246, 278, 437–443, 508, 620–670, 843–852.
4. A normal subsequent GUI run creates fresh local aggregate lists and starts with histories that the preceding completed run cleared. A run that fails before its reset may leave partial global histories. There is no cleanup handler or rollback; a subsequent GUI submission in that process can consequently consume old partial histories. S:683–852, `submit_form` S:82–108.
5. After each repeat, print a separator, `Run {j+1} of {n_runs} completed`, and a separator; in GUI mode reset progress to 0 and call `root.update()`. After all repeats, calculate averages and intervals, optionally serialize, and optionally plot. `start = timer()` is captured but never used; no elapsed-time message is printed. `main()` has no explicit return value. S:854–1006.
6. Zero/negative run counts execute no initialization but do not trigger a special empty-results return. For ordinary nonnegative `n_dev`, the aggregation code then indexes unpopulated containers and fails. Negative `n_dev` executes no development and creates an empty x-axis; no normalization to zero is performed. Behavior depends on the exact combination, not a general “invalid-input” check. S:757, 762, 865–904.

## RUN-004 — Existing VS Code launch path

The shipped `.vscode/launch.json` defines one configuration named `Sim`, using `type="debugpy"`, `request="launch"`, interpreter `${workspaceFolder}/venv/Scripts/python.exe`, program `${workspaceFolder}/dicty_sim_v0.6.py`, and `console="integratedTerminal"`. It specifies no arguments, so that legacy script takes its GUI branch when launched this way. This is a Windows-shaped local interpreter path and a different simulator entry point from the README and `directory_run.py`. It does not select the inline active engine specified here. Source: `.vscode/launch.json:1–12`; see LEGACY-001.

## UI-001 — GUI construction and entry handling

1. When literal `--param` is absent, create a Tk root titled `Dicty Simulator v0.6 - Stalk first determination, multiloci`, a Tk `IntVar` for progress, and one entry per item in `variables`, in dictionary insertion order. Labels are exact parameter names. Entries start with `str(default_value)`. S:1025–1056.
2. Numeric entries use key validation that returns true for empty text or any string accepted by Python `float()`. It does not distinguish integer fields, constrain signs/ranges, or reject non-finite float strings accepted by `float()`. `i_macrocyst` and output path bypass this numeric validation. S:232–239, 1039–1047.
3. On submission, visit all entry widgets in order. The integer fields are exactly `n_runs`, `n_dev`, `vg`, `n`, `sl`, `ch_res_dist`, `mc_count`, `mc_germ_count`, `gene_pairs`, `ch_self_cheat`, `sex_cycle_interval`, `ch_eff_rc`, `res_eff_rc`. All remaining fields except the list and path are converted using `float`. Mutations to the shared configuration happen one field at a time; conversion failure does not revert earlier fields. S:82–104.
4. A string such as `"0.5"` or `"1.0"` passes numeric key validation but fails `int(value)` for any integer field. In contrast `resistance_type` and `discrete_res` are intentionally in the float conversion branch as implemented. S:85–91, 232–239.
5. The list field splits the entry on literal commas, calls `character.strip()` without saving its result, and applies `int` to every original split token. Python `int` itself tolerates surrounding whitespace. `"0"` becomes `[0]`, and `"1, 5"` becomes `[1,5]`; `"[1,5]"`, empty text, or a trailing comma fails. Print the parsed list, then store it. S:93–100.
6. The path entry is converted with `str`, without trimming or path validation. A whitespace-only path is not the empty-string suppression case. S:102–104, 907–908.
7. After conversions, create a new `ttk.Progressbar(variable=progress)` and place it at row 15, column 3, spanning three columns. Call `main()` synchronously in the submit callback. No submit-button disablement, worker process, or re-entrancy guard exists. `root.update()` is called inside simulation progress handling, so GUI event processing can occur during a run. S:105–108, 610–613, 858–862.
8. The development handler adds `100/n_dev` to `progress.get()` and stores it in the Tk `IntVar` once per completed development cycle. The actual display/readback follows Tk integer-variable behavior; the Python code itself does not round or separately track a precise floating-point percentage. S:610–613, 1028.
9. The “Run simulation” button calls `submit_form`. “Import parameters” is disabled; its target function only updates the root, opens a file dialog, stores a local filename, and updates the root again—it never reads or applies parameters. “Run test suite” is disabled and is bound to `submit_form`, not a test suite. S:227–230, 1058–1070.
10. Entries occupy seven rows per two-column group, starting at row 2: after insertion increment the row; if `row_num+2 >= 11`, advance two columns and reset row to 2. The title label reads “Parameters”; startup prints the process ID, then enters `root.mainloop()`. S:1031–1056, 1072–1079.

## UI-002 — Tooltips

Each entry's enter/leave events immediately show/hide its tooltip using `variables_tooltips[var_name]`. There is no delay timer. The 31 tooltip strings live in S:37–69; they are explanatory strings and do not validate input. `CreateToolTip` is S:73–80. The helper [GUI/tooltip.py](<C:/Dev/Dicty sim/rust-sim/reference-source/GUI/tooltip.py:11>) creates a borderless `Toplevel`, positions it at `x = bbox_x + winfo_rootx() + 57` and `y = bbox_y + bbox_height + winfo_rooty() + 27` using the entry insertion box, and displays left-aligned Tahoma 8 text on `#ffffe0` with a solid one-pixel border. An existing window or empty text suppresses creation; leaving destroys the existing window. Source: tooltip.py:11–31.

## CONFIG-003 — Reimplementation boundary

This file records current accepted representations and accidental behavior. A future Rust engine may expose a safer configuration layer, add validation, or separate GUI and CLI concerns only as an explicitly approved behavior change. In particular, it must not silently infer additive resistance, combined-cost effects, self-cheating control, a working import button, or a user-selected confidence level from parameter names and tooltip text alone.
