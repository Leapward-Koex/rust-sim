# Measurements and output

## Measurement population and timing

**MEASURE-001.** Initialization records one measurement before any sexual, vegetative, or developmental cycle. Every successful `developmental_cycle` records one measurement of `fruiting_body`, after stalk deletion and before return. No separate measurements occur inside `vegetative_growth` or `sexual_cycle`. Normally each repeat supplies `n_dev + 1` points. Sources: `dicty_sim_test_env.py:313–393,524–608,757–786`.

**MEASURE-002.** For a measured population `P`, define `N = len(P)`, configured gene-pair count `L = variables["gene_pairs"]`, `C_i = cell.cheater_value()`, `R_i = cell.resistor_value()`, and `W_i = cell.wild_value()`. The denominator for allele frequencies is the configured `L * N`, not a sum of actual list lengths. Under ordinary operation all cells have `L` loci. Sources: `dicty_sim_test_env.py:342–379,544–589`.

| Per-repeat series | Exact recorded value |
| --- | --- |
| `cheater_allele_counts` | `sum(C_i) / (L * N)` |
| `resistor_allele_counts` | `sum(R_i) / (L * N)` |
| `wild_counts` | `sum(W_i) / (2 * L * N)` |
| `mt1_ratios` | Count of cells with `mating_type == 1`, divided by `N` |
| `mt2_ratios` | Count of cells with `mating_type == 2`, divided by `N` |
| `mt3_ratios` | Count of cells with `mating_type == 3`, divided by `N` |
| `mean_ch_eff` | Sum of `ch_eff()` over cells where `C_i > 0`, divided by the number of such cells; integer `0` if none |
| `mean_res_eff` | Sum of `res_eff()` over cells where `R_i > 0`, divided by the number of such cells; integer `0` if none |

**MEASURE-003.** Wild frequency means absent allele slots, not the fraction of cells lacking both alleles. A locus with neither allele contributes two wild slots, a locus with one allele contributes one, and a locus with both contributes zero. For normal binary state, `wild = 1 - (cheater_frequency + resistor_frequency) / 2`. Cheater and resistor frequencies can overlap and need not sum to one. Sources: `dicty_sim_test_env.py:144–163,375–379,587–589`.

**MEASURE-004.** Effectiveness means condition on the presence of raw allele counts, not positive effectiveness. A cell with a cheater allele whose effectiveness is fully suppressed still contributes to the cheater-effectiveness denominator. Mating type comparisons use an `if/elif/elif` chain; other values contribute to none of the three numerators but remain in the population denominator. Sources: `dicty_sim_test_env.py:356–368,558–570`.

**MEASURE-005.** Each measured locus has a `LocusTracker` containing `ch_count`, `res_count`, and `both_count`. At each cell's locus: if `locus.both() == 0`, add the raw cheater/resistor values to the first two counters; otherwise increment `both_count` by one, adding nothing to the first two. For binary state the first two counters are cheater-only and resistor-only counts; the third is the both-alleles count. Neither-allele counts are not separately stored. These are cell counts, not normalized frequencies. Source: `dicty_sim_test_env.py:267–270,347–354,524–529,549–556`; `locus_tracker.py:1–9`.

**MEASURE-006.** Trackers use names `Locus0`, `Locus1`, etc. A deep-enough snapshot is appended to global `locus_plot`: a fresh list of fresh tracker objects containing their scalar counts. At initialization that snapshot is appended before frequency division; after development it is appended after frequency division. Thus empty populations or zero gene pairs can leave different partial tracker state on failure. There is no rollback or empty-population guard before allele-frequency division. Sources: `dicty_sim_test_env.py:370–379,572–594`.

## A concrete measurement example

**MEASURE-007.** For one gene pair and four cells with loci `(0,0)`, `(1,0)`, `(0,1)`, `(1,1)`, allele frequencies are `cheater=0.5`, `resistor=0.5`, and `wild=0.5`. Locus counts are `[1,1,1]`, excluding the neither-allele cell. With `ch_eff_rc=res_eff_rc=0`, each effectiveness mean is `0.5`, because the two carriers have effectiveness one and zero. With `ch_eff_rc=res_eff_rc=1`, each is `1.0`. This example follows `MEASURE-002` through `MEASURE-005`; it is not a different model rule.

## Aggregation over repeats

**AGG-001.** `main()` allocates fresh local aggregate lists and dictionaries. For each locus index `z`, all three dictionaries use the exact key `"gene_pair" + str(z)` and a list of three independent lists. At the end of the first repeat, each point becomes a singleton list of that repeat's observed value. Later repeats append to that point's list. This applies to the eight scalar series and the three counts per locus. Sources: `dicty_sim_test_env.py:696–741,788–841`.

**AGG-002.** The global nine tracker lists are rebound to empty lists after each repeat's values have been collected. They are not explicitly cleared at `main()` entry. Normal successful preceding runs leave them empty; calling individual functions or a failed previous run may leave stale observations. Local aggregation does not detect mismatched lengths. `Cell._id_counter` and both random-generator states are not reset between repeats. Sources: `dicty_sim_test_env.py:23–34,111–123,683–695,843–852`.

**AGG-003.** After all repeats, `x_axis_values = list(range(0, n_dev + 1))`. At each point, `np.mean` is applied across repeat observations. Ratios are averaged equally per repeat, not pooled over different survivor population sizes. Each effectiveness output is a mean of the per-repeat conditional means, including zero from a repeat with no carriers. Locus outputs are means of absolute per-repeat counts. Sources: `dicty_sim_test_env.py:864–904`.

**AGG-004.** Confidence values are half-widths, not full intervals, calculated by this exact function:

```python
def mean_confidence_interval(data, confidence=variables["confidence_interval"]):
    a = 1.0 * np.array(data)
    n = len(a)
    m, se = np.mean(a), st.sem(a)
    h = se * st.t.ppf((1 + confidence) / 2., n-1)
    return h
```

The intermediate mean `m` is unused. `st.sem` receives no options; for ordinary finite one-dimensional data with at least two values its default sample standard error uses `ddof=1`. The quantile uses `n-1` degrees of freedom. No clipping to `[0,1]`, bootstrap, multiple-comparison correction, or population-size weighting occurs. Source: `dicty_sim_test_env.py:248–253`.

**AGG-005.** The function's default confidence is bound when its definition executes, using the imported default dictionary value `0.95`. All calls in `main()` omit the second argument. Replacing the module's dictionary with CLI JSON or changing its `confidence_interval` field through the GUI therefore does not change the confidence calculation. The configured value is still saved in output, which can disagree with the actual confidence used. Explicit direct calls with a second argument do use it. Sources: `global_variables.py:32`; `dicty_sim_test_env.py:82–104,248,876–878,886–904,1019`.

**AGG-006.** A one-repeat run normally produces `NaN` confidence half-widths through SciPy's sample-size behavior. Warnings and floating-point details depend on the library versions. There is no fallback to zero. Zero repeats with nonnegative `n_dev` reaches indexing of empty aggregate lists and fails. Negative or malformed counts are not normalized. Sources: `dicty_sim_test_env.py:757,865–904`.

**AGG-007.** Locus aggregation is computed first, point by point, and for each locus the three means precede the three confidence calculations. Scalar aggregation follows in point order: cheater/resistor/wild means then their confidence values; mating-type means then their confidence values; effectiveness means then their confidence values. Within repeat measurement, population and locus list iteration order determine floating-point accumulation. Source: `dicty_sim_test_env.py:869–904`.

## Result JSON schema

**OUTPUT-001.** When `variables["output_filepath"] != ""`, the output path is formed by string addition of `".json"`. A configured filename already ending in `.json` receives another `.json`. Relative paths resolve against the process working directory. No directory is created. The file is opened in text write mode, overwriting an existing file, then `json.dump(value_dict, outfile)` is called with default options. File or serialization errors propagate; there is no atomic write or recovery. Empty string suppresses saving even in CLI mode. Sources: `dicty_sim_test_env.py:907–934`.

**OUTPUT-002.** The top-level object has exactly the following 21 keys in this insertion order. Extra configuration fields, if present, survive inside `parameters`; they are not extra top-level result keys.

| Order | JSON key | Value |
| --- | --- | --- |
| 1 | `parameters` | The current `variables` object, with no added provenance or seed |
| 2 | `sex_cycle_list` | Interval-triggered cycle numbers accumulated across all repeats |
| 3 | `x_axis_values` | Integers `0` through `n_dev`, inclusive, in the normal nonnegative case |
| 4 | `mean_ch` | Across-repeat mean cheater frequency |
| 5 | `ch_ci` | Cheater-frequency confidence half-width |
| 6 | `mean_res` | Across-repeat mean resistor frequency |
| 7 | `res_ci` | Resistor-frequency confidence half-width |
| 8 | `mean_wild` | Across-repeat mean absent-slot frequency |
| 9 | `wild_ci` | Absent-slot frequency confidence half-width |
| 10 | `mean_mt1` | Across-repeat mean mating-type-1 fraction |
| 11 | `mt1_ci` | Mating-type-1 confidence half-width |
| 12 | `mean_mt2` | Across-repeat mean mating-type-2 fraction |
| 13 | `mt2_ci` | Mating-type-2 confidence half-width |
| 14 | `mean_mt3` | Across-repeat mean mating-type-3 fraction |
| 15 | `mt3_ci` | Mating-type-3 confidence half-width |
| 16 | `graph_mean_ch_eff` | Across-repeat mean conditional cheater effectiveness |
| 17 | `ch_eff_ci` | Cheater-effectiveness confidence half-width |
| 18 | `graph_mean_res_eff` | Across-repeat mean conditional resistor effectiveness |
| 19 | `res_eff_ci` | Resistor-effectiveness confidence half-width |
| 20 | `average_tracker_dict` | Per-locus arrays of mean absolute counts |
| 21 | `ci_tracker_dict` | Per-locus arrays of count confidence half-widths |

Source: `dicty_sim_test_env.py:910–932`.

**OUTPUT-003.** Each scalar series normally has `n_dev + 1` numbers. Each tracker dictionary maps `gene_pair0` through `gene_pair{L-1}` to exactly three time-series arrays, ordered `[cheater_only, resistor_only, both]`. The same ordering is used in `ci_tracker_dict`. Time zero is included. Counts are not divided by population size before saving. Sources: `dicty_sim_test_env.py:734–741,788–801,869–878`.

**OUTPUT-004.** `sex_cycle_list` is initialized once per `main()`, appended only in the interval branch, and never reset between repeats. For two repeats with `n_dev=4`, interval `2`, and `i_macrocyst=[0]`, it is `[2,4,2,4]`. Explicit-list-triggered sex is not appended at all. It is therefore not a complete unique event log. Source: `dicty_sim_test_env.py:744,765–781`.

**OUTPUT-005.** Default `json.dump` emits non-finite Python-compatible tokens such as `NaN` if present, rather than rejecting them or replacing them with `null`. It uses no indentation and retains dictionary insertion order. The output does not store individual cells, individual repeat trajectories, RNG state, seeds, timing, software versions, exception records, or total stalk counts. `main()` has no explicit return value. Sources: `dicty_sim_test_env.py:684,907–1006`.

## Console and GUI output

**DISPLAY-001.** Normal simulation messages use these exact source templates:

```text
length of loci: {loci_template_length}
Completed sexual cycle
Len: {survivor_count}, cheater: {cheater_count}, resistor: {resistor_count}, wild: {wild_count} , total stalks: {total_stalk}
Dev round {i} of {n_dev} completed.
------------------
Run {j+1} of {n_runs} completed
------------------
```

GUI startup additionally prints the exact misspelled prefix `Proccess ID: ` followed by `os.getpid()` (line 1076), and GUI submission prints the parsed integer sex-cycle list (line 99). `loci_template_length` is the actual number of constructed template loci, not the raw configured value when it is negative. The sex message occurs only after successful sexual reproduction. The survivor line uses raw allele counts and the accumulated length of stalk-index lists, including any duplicate indexes. It is printed before allele-frequency division. Initialization logs once per repeat; the three run-completion lines follow tracker resets. No final elapsed time is printed despite capturing `start = timer()`. Sources: `dicty_sim_test_env.py:272,574,680,684,774–786,843–856`.

**DISPLAY-002.** In GUI operation, after each development measurement `progress.set(progress.get() + (100 / n_dev))` is called, followed by `root.update()`. `progress` is a Tk `IntVar`, even though the increment may be fractional; no application-level rounding is added. Each repeat subsequently sets it to zero and updates the GUI. Behavior of reading fractional values through this Tk variable belongs to the Tcl/Tk runtime; these specs preserve the calls and variable type. Both GUI branches are guarded by absence of the literal `"--param"` in `sys.argv`, not by whether a window object exists. Sources: `dicty_sim_test_env.py:610–613,858–862,1028`.

**DISPLAY-003.** After saving JSON, if `"--param"` is absent, `main()` creates a two-row Matplotlib figure of size 12 by 8 inches. Both panels have y-label `Ratio`, y-limits `[0,1]`, x-label `Development cycles`, and a grid. The first title is `Allele frequency over time`; it draws cheater red, resistor blue, wild black, each with mean ± confidence fill at alpha `0.1`. The second draws mating types 1 red, 2 blue, 3 green with the same fill alpha. The first legend labels, in order, are `Cheater alleles`, `Resistor alleles`, `Wild-type alleles`; the second labels are `Type 1`, `Type 2`, `Type 3`. The mating-type title and effectiveness plots are commented out. Sources: `dicty_sim_test_env.py:937–993`.

**DISPLAY-004.** If `i_macrocyst[0] != 0`, vertical blue dashed lines with alpha `0.05` are drawn at every element of the configured list, including values outside simulated cycles and duplicates. Otherwise lines use `sex_cycle_list`, including repetitions across repeats. Both panels receive the lines, then `plt.show()` runs. The plotting step can fail after the JSON file has already been saved, for example on an empty `i_macrocyst` list. Sources: `dicty_sim_test_env.py:995–1006`.
