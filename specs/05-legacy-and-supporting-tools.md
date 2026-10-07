# Legacy variant and supporting tools

The behavioral baseline for the other specifications is the README-directed `dicty_sim_test_env.py`, not every historical implementation merged together. This file identifies alternate code and the exact existing helper workflows so that a future port does not accidentally combine incompatible models. Source references refer to the snapshot recorded by this specification set.

## LEGACY-001 — Two runnable simulator files exist

[README.md](<C:/Dev/Dicty sim/rust-sim/reference-source/README.md:4>) names `dicty_sim_test_env.py` for GUI and CLI use. [directory_run.py](<C:/Dev/Dicty sim/rust-sim/reference-source/directory_run.py:14>) also targets that script. The separate [dicty_sim_v0.6.py](<C:/Dev/Dicty sim/rust-sim/reference-source/dicty_sim_v0.6.py>) is a different implementation, not an alias. It has its own initialization, development, growth, sex, main, and GUI code. Its behavior is excluded from the primary baseline unless the user later chooses that version explicitly.

This is not a complete specification for reproducing the old executable. The following differences are sufficient to establish the version boundary and important incompatibilities:

The existing VS Code `Sim` launch configuration actively selects this legacy file, using `${workspaceFolder}/venv/Scripts/python.exe` and no command arguments. It therefore starts the legacy GUI rather than the README-directed entry point. This alternate launch path is preserved in `reference-source/.vscode/launch.json` and detailed in RUN-004. Source: `.vscode/launch.json:5–10`.

| Area | Active `dicty_sim_test_env.py` | Separate `dicty_sim_v0.6.py` |
|---|---|---|
| Cell implementation | Inline `Cell` at lines 111–225; `from cell import Cell` is commented out at line 16. | Imports `Cell` from `cell.py` at line 16. |
| Mutation comparison | Uniform draw `<=` configured rate, lines 437 and 443. | Strict `<` at lines 313 and 319. |
| Resistance back-mutation | Sets `locus.resistor_allele = 0`, line 445. | Writes misspelled `locus.ressitor_allele = 0`, line 321, so it leaves the real resistance allele unchanged. |
| Discrete passive development | Draws all pre-stalk cells first; each pre-stalk cell with positive raw cheater count attempts to sample one candidate built with symmetric differences and checks pairwise `exploitable`, lines 490–515. | Builds per-locus exploitable-index lists, then processes cells sequentially; successful cheating samples from a combined list whose duplicates intentionally weight candidates, lines 367–434. |
| `ch_self_cheat` | No active read in engine. | Switches construction of the per-locus exploitable lists, lines 375–396. |
| Additive passive mode | `discrete_res != 1` has no fate-selection body; selected slug cells all survive, lines 485–522. | Contains an additive mode at lines 435–458; its comparisons are literally `res_eff() > uniform` for entry into the exploitable list and `ch_eff() < uniform` for access to that list. |
| Other resistance modes | No branches after passive mode, lines 485–522. | Contains policing and counter-cheating branches, lines 469–590, but these use obsolete `cell.locus` attributes absent from the imported Cell. They also refer to `ch_eff`/`res_eff` configuration keys absent from the supplied defaults. They are not usable alternative active modes. |
| CLI schedule representation | Leaves JSON value untouched, lines 1018–1021; usable normal input is an integer array. | Calls `.split(',')` on `variables['i_macrocyst']` after JSON load, lines 1047–1053; expects a comma-separated string, and fails on the active template's array. |
| Per-locus result data | Builds per-locus trackers and aggregate output, lines 729–741, 788–801, 867–878. | Uses different top-level keys and sample-index dictionaries instead of the active arrays (lines 919–938). It lacks `x_axis_values`, `mean_ch`/`mean_res`, `sex_cycle_list`, and per-locus result dictionaries; none of the four supplied plotting helpers accepts an untouched legacy result. |

## LEGACY-002 — `cell.py` import and configuration trap

[cell.py](<C:/Dev/Dicty sim/rust-sim/reference-source/cell.py:1>) imports `variables` from **`dicty_sim_test_env`**, then defines its own `Cell`. Its methods implement the same record fields, ID counter, cloning, counts, effectiveness, and exploitation logic as the inline active class (cell.py:5–119 versus active:111–225). They are distinct Python classes with independent class-level ID counters and class-sensitive equality checks.

When the legacy CLI loads a JSON file, it rebinds **its own** `variables` name (v0.6:1044), but `cell.py` still references the dictionary imported through the active module, initially the one from `global_variables`. Thus legacy engine functions can use CLI values while legacy Cell effectiveness/exploitation methods use module defaults. The legacy GUI mutates the originally shared dictionary in place, which is a different configuration path. Source: cell.py:1, 59–119; active:19; legacy:19, 83–105, 1044.

The Rust baseline must use the active inline Cell behavior tied to the active script's current `variables`, not copy this cross-module configuration binding.

## TOOL-001 — Directory runner

[directory_run.py](<C:/Dev/Dicty sim/rust-sim/reference-source/directory_run.py:1>) is a top-level batch helper:

1. `argparse` requires a single positional string argument `directory` (lines 5–9).
2. It hardcodes the simulator checkout as `c:/Users/tehch/OneDrive/Documents/GitHub/DictySimulator`, the Python executable as its `.conda/python.exe`, and the script as its `dicty_sim_test_env.py` (lines 12–14). These paths are not derived from the runner's own directory and are not supplied by the argument.
3. Iterate `os.listdir(args.directory)` without sorting or recursion. For each returned name ending with case-sensitive `.json`, join it to the input directory and run a quoted command of the form `"python_exe" "script" --param "json_file"` with `subprocess.run(..., shell=True)` (lines 17–23).
4. Runs are sequential because each `subprocess.run` blocks. It does not set a subprocess working directory, so subprocess output paths are relative to the caller's working directory. It does not use `check=True`, inspect the return code, select an output filename, distinguish parameter JSON from result JSON, or reject a directory whose name ends with `.json`.

This runner is not a parallel-execution engine or a parameter-sweep generator.

## TOOL-002 — Shared plotting-helper behavior

`grapher.py`, `figure_maker.py`, `custom_figure_maker.py`, and `same_graph.py` execute at import/top level. Each creates and hides a Tk root, opens a JSON file dialog initially located at `os.getcwd()`, reads a selected file with `json.load`, creates Matplotlib figures, and eventually calls `plt.show()`. They consume the **result** object, not the bare parameter object. There is no schema negotiation, missing-key fallback, cancellation handling, file export, or automatic parameter-label generation. Cancelling passes an empty path to `open` and fails. None re-simulates or recomputes confidence intervals; they plot saved means and saved interval half-widths.

Sources: [grapher.py](<C:/Dev/Dicty sim/rust-sim/reference-source/grapher.py:13>) lines 13–24 and 117; [figure_maker.py](<C:/Dev/Dicty sim/rust-sim/reference-source/figure_maker.py:13>) lines 13–24 and 132; [custom_figure_maker.py](<C:/Dev/Dicty sim/rust-sim/reference-source/custom_figure_maker.py:12>) lines 12–23 and 89; [same_graph.py](<C:/Dev/Dicty sim/rust-sim/reference-source/same_graph.py:12>) lines 12–23 and 80.

Confidence bands are simply `mean - ci` through `mean + ci`, with alpha `0.1`, without clipping to `[0,1]` before drawing. Axis limits can hide the out-of-range portion. Where sexual-cycle markers exist, the rule is `parameters.i_macrocyst[0] != 0`: use each configured explicit entry; otherwise use every saved `sex_cycle_list` entry. This includes duplicate saved interval entries across repeats and configured entries outside the executed cycle range. Sources: grapher:45–64, 74–82, 104–114; figure_maker:44–119; custom_figure_maker:45–56.

## TOOL-003 — `grapher.py`

The first figure has two vertically stacked axes (line 27):

- Top: `mean_ch` in red with `ch_ci` band; `mean_res` in blue with `res_ci` band; y range `[0,1]`; y label `Percentage of possible alleles`; title literally `Mating type frequency over time` despite the plotted allele data. Wild series and bands are commented out. Legend labels are `Cheater alleles` and `Resistor alleles`. Lines 30–51.
- Bottom: `mean_mt1` red and `mean_mt2` blue with their bands, plus a green `mt3_ci` band around `mean_mt3` even though the mating-type-3 line and legend entry are commented out. Y label `Ratio`, range `[0,1]`; legend Type 1/Type 2. Lines 53–65.
- Both x labels read `Development cycles`; add sex markers to both axes; spacing `hspace=0.5`. Lines 68–82.

The second figure calls `plt.subplots(gene_pairs)` and accesses each axis as `ax[x]` (lines 85–93). With `gene_pairs == 1`, Matplotlib returns a scalar axes object, so the unmodified indexing fails. For each normal multi-locus axis, plot `average_tracker_dict['gene_pair'+str(x)]` series 0/1/2 in red/blue/green and corresponding `ci_tracker_dict` bands. These are cheater-only/resistance-only/both counts, not total allele frequencies. Y range is hardcoded `[0,10000]` independently of input population size; y label `# of individuals`; x label `Developmental cycles`; title numbers the locus from **1** although keys are zero-based. Add sex markers and use `hspace=1.5`. Lines 89–115. This figure does not create a genotype legend.

## TOOL-004 — `figure_maker.py`

This helper asks for **four result files in order**, first top left, then top right, bottom left, bottom right, and creates a `2 x 2` figure sized 12 by 8 inches. Each subplot displays cheater and resistance means and bands with sex markers and y range `[0,1]`. A legend appears only on the top-right axis. Source: figure_maker.py:26–27, 43–123.

Labels are hardcoded: overall title `Mutation rates, no epistasis`; subplot titles `1%`, `0.1%`, `0.01%`, `0.001%`; title font size 16 for subplot titles and 18 for the figure/global labels. It does not verify that loaded files match those titles. Global labels read `Developmental Cycles` and `Proportion of possible alleles`; use `hspace=0.3`. Source: figure_maker.py:29–37, 125–132.

## TOOL-005 — `custom_figure_maker.py`

This helper asks for **three result files**, overlaid on one 12 by 8 inch axis:

1. First file: solid red cheater and solid blue resistance means and matching bands; sex markers come from this file only. Lines 25–56.
2. Second file: dashed `tab:blue` resistance mean and matching band. Its cheater plot is commented out. Lines 58–67.
3. Third file: dashed `tab:red` cheater mean and matching band. Lines 70–76.

Legend labels claim cheater/resistance alleles in the first file, “Resistor alleles without cheaters present” for the second, and “Cheater alleles without resistors present” for the third; no data check enforces those claims. Y range `[0,1]`, same global labels as TOOL-004, no active figure title. Source: custom_figure_maker.py:38–42, 78–89.

## TOOL-006 — `same_graph.py`

This helper asks for **four result files** and overlays only `mean_res` and `res_ci` for each on one 12 by 8 inch axis. The series colors in file-selection order are `lightseagreen`, `teal`, `tab:blue`, `blue`; **all** confidence bands use `blue`. Source: same_graph.py:25–68.

Legend title `Mutation rate`; descending legend labels `1%`, `0.1%`, `0.01%`, `0.001%`, mapped to file selections 4, 3, 2, 1 respectively. This is hardcoded and does not inspect mutation parameters. Y range `[0,1]`; same global axis labels as TOOL-004; no sexual-cycle markers and no active figure title. Source: same_graph.py:32–36, 70–80.

## TOOL-007 — `test.py` is a list-copy demonstration

[test.py](<C:/Dev/Dicty sim/rust-sim/reference-source/test.py:1>) constructs a list of ten one-element lists `[[1], [2], ..., [10]]`, using `list.copy()`, and prints it. It imports no simulator code and contains no assertions or test functions. The disabled GUI “Run test suite” button also calls `submit_form`, not this file. Sources: test.py:1–7; active:1067–1070. The repository's `test_params` directories contain input examples, not executable assertions that establish correctness.

## TOOL-008 — Runtime dependencies versus saved requirements

The active simulator directly imports the Python standard-library modules `os`, `random`, `math`, `json`, `sys`, `tkinter`, and `timeit`; third-party `matplotlib`, `numpy`, and `scipy.stats`; and the local `GUI.tooltip`, `locus`, `locus_tracker`, and `global_variables`. It does **not** import external `cell.py`. Imports are unconditional for both CLI and GUI. Source: active:1–21. Plotting helpers use Matplotlib/NumPy/Tkinter/JSON; the directory runner uses standard-library `os`, `subprocess`, `argparse`.

The saved [requirements.txt](<C:/Dev/Dicty sim/rust-sim/reference-source/requirements.txt>) pins NumPy 1.26.4, Matplotlib 3.8.4, and SciPy 1.13.0, alongside many packages not imported by any simulation/helper source, including network, database, cryptography, and typing tools. [mac_reqs.txt](<C:/Dev/Dicty sim/rust-sim/reference-source/mac_reqs.txt>) pins NumPy 1.25.2, Matplotlib 3.8.3, and SciPy 1.12.0, again with additional packages not imported by these sources. Neither file specifies a Python interpreter version or provides a lock for Python/Tk itself. These files record environments; their full package lists do not define simulation behavior or justify adding equivalent Rust dependencies.
