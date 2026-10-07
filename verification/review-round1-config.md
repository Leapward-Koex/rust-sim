# Independent source review: configuration, entrypoints, legacy, and tools

Reviewed on 7 October 2026. Scope: `specs/01-configuration-and-entrypoints.md`, `specs/05-legacy-and-supporting-tools.md`, and the source-authority claims in `specs/00-scope-and-source-authority.md`, against the original `DictySimulator` files. No simulator or specification files were changed by this review.

## Findings requiring correction

### R1-C01 — The recombination table describes genotype equality where the code uses locus-object identity

**Document:** [01-configuration-and-entrypoints.md:34](<C:/Dev/Dicty sim/rust-sim/specs/01-configuration-and-entrypoints.md:34>), CONFIG-001 `recomb_chance` row: “After the identical-genotype special case”.

**Source:** [dicty_sim_test_env.py:648](<C:/Dev/Dicty sim/DictySimulator/dicty_sim_test_env.py:648>) compares `cell.loci == partner_cell.loci`; [locus.py:1](<C:/Dev/Dicty sim/DictySimulator/locus.py:1>) defines no equality method. The nonempty lists therefore compare corresponding locus objects by identity. Cells independently created with identical allele values normally fail this shortcut and consume the recombination decision draw. This wording could cause a Rust implementation to add a genotype-value shortcut and change random consumption and mating-type inheritance. The detailed SEX-003 section already correctly explains the distinction.

**Concrete replacement:** “After the loci-list equality special case (corresponding locus-object identity, not allele-value equality; see SEX-003), take the intact loci and mating type of one randomly chosen parent when a uniform draw is `< 1-recomb_chance`; otherwise recombine.”

### R1-C02 — Two entrypoint/lifecycle statements invent elapsed-time output

**Document:** [01-configuration-and-entrypoints.md:63](<C:/Dev/Dicty sim/rust-sim/specs/01-configuration-and-entrypoints.md:63>), RUN-001 item 6 says “printing progress/timing”; [01-configuration-and-entrypoints.md:102](<C:/Dev/Dicty sim/rust-sim/specs/01-configuration-and-entrypoints.md:102>), RUN-003 item 5 says “print elapsed time”.

**Source:** [dicty_sim_test_env.py:684](<C:/Dev/Dicty sim/DictySimulator/dicty_sim_test_env.py:684>) assigns `start = timer()`, but there is no second timer call, elapsed-time calculation, or elapsed-time print anywhere in the active file. The active main ends after [dicty_sim_test_env.py:1006](<C:/Dev/Dicty sim/DictySimulator/dicty_sim_test_env.py:1006>). In contrast, the excluded legacy implementation does print elapsed time at [dicty_sim_v0.6.py:1017](<C:/Dev/Dicty sim/DictySimulator/dicty_sim_v0.6.py:1017>) and line 1027. DISPLAY-001 in specification 04 already states the active behavior correctly.

**Concrete replacements:** Change RUN-001 item 6 to “runs and discards local aggregate results after printing simulation progress”. Change RUN-003 item 5 to “After all repeats, calculate averages and intervals, optionally serialize, and optionally plot. `start = timer()` is captured but never used, and no elapsed-time message is printed. `main()` has no explicit return value.”

### R1-C03 — The legacy comparison says every cheater samples a candidate

**Document:** [05-legacy-and-supporting-tools.md:16](<C:/Dev/Dicty sim/rust-sim/specs/05-legacy-and-supporting-tools.md:16>), LEGACY-001 discrete passive development row says “each cheater samples one candidate”.

**Source:** [dicty_sim_test_env.py:499](<C:/Dev/Dicty sim/DictySimulator/dicty_sim_test_env.py:499>) iterates only `pre_stalk_list`; line 500 tests raw positive cheater count, and line 508 samples a candidate. Cheaters not selected as prestalk never run this sampling step. Candidate sampling can also fail for an empty candidate set, rather than every qualifying cell necessarily completing a sample. The detailed development specification correctly scopes the loop.

**Concrete replacement:** “Draws all pre-stalk cells first; each pre-stalk cell with positive raw cheater count attempts to sample one candidate built with symmetric differences and checks pairwise `exploitable`, lines 490–515.”

## Meaningful supporting-tool clarification

### R1-C04 — State the actual legacy output incompatibility, which affects all four plotting helpers

**Document:** [05-legacy-and-supporting-tools.md:21](<C:/Dev/Dicty sim/rust-sim/specs/05-legacy-and-supporting-tools.md:21>) currently cautions only about the different per-locus aggregation structure and “current per-locus graph consumers”. The file explicitly excludes a complete legacy specification, which is appropriate, but a short schema-boundary statement would remove a misleadingly narrow compatibility impression.

**Source:** [dicty_sim_v0.6.py:919](<C:/Dev/Dicty sim/DictySimulator/dicty_sim_v0.6.py:919>) emits keys such as `mean cheater values` and `mean resistor values`, each containing an enumerated dictionary. It does not emit `x_axis_values`, `mean_ch`, `mean_res`, `sex_cycle_list`, or either per-locus result dictionary. The first plot in [grapher.py:45](<C:/Dev/Dicty sim/DictySimulator/grapher.py:45>), [figure_maker.py:44](<C:/Dev/Dicty sim/DictySimulator/figure_maker.py:44>), [custom_figure_maker.py:45](<C:/Dev/Dicty sim/DictySimulator/custom_figure_maker.py:45>), and [same_graph.py:39](<C:/Dev/Dicty sim/DictySimulator/same_graph.py:39>) already requires the active schema. All four therefore fail on an untouched legacy result before reaching any per-locus plotting.

**Concrete addition:** “Legacy JSON also uses different top-level keys and dictionaries keyed by sample index instead of the active result arrays. It lacks `x_axis_values`, `mean_ch`/`mean_res`, `sex_cycle_list`, and the per-locus result dictionaries. None of the four supplied plotting helpers accepts an untouched legacy result.”

## Small precision improvements

- **CONFIG-001 `ch_start` row:** [01:27](<C:/Dev/Dicty sim/rust-sim/specs/01-configuration-and-entrypoints.md:27>) calls the other initialization path “disjoint”, although [source:296](<C:/Dev/Dicty sim/DictySimulator/dicty_sim_test_env.py:296>) retains the last cheater index and line 299 starts resistor selection at that same index. Replace “random/disjoint branch rounding differs” with “random/sequential branch rounding differs; the sequential branch can overlap”. This agrees with the already-correct CONFIG-001 `ch_res_dist` row and the detailed population specification.
- **SCOPE-008:** [00:23](<C:/Dev/Dicty sim/rust-sim/specs/00-scope-and-source-authority.md:23>) broadly says “identity-based equality”. To prevent conflating locus and cell semantics, use “cell-key equality and locus-object identity comparisons”. [Cell.__eq__:131](<C:/Dev/Dicty sim/DictySimulator/dicty_sim_test_env.py:131>) compares keys on instances of the active Cell class; [Locus:1](<C:/Dev/Dicty sim/DictySimulator/locus.py:1>) has default object equality. This is a terminology refinement, not a claim that the surrounding scope statement is substantively wrong.
- **Tooltip positioning:** [01:120](<C:/Dev/Dicty sim/rust-sim/specs/01-configuration-and-entrypoints.md:120>) summarizes the position with offsets `(57,27)`. For an exact GUI remake, state `x = bbox_x + winfo_rootx() + 57` and `y = bbox_y + bbox_height + winfo_rooty() + 27`; the box height in [tooltip.py:16](<C:/Dev/Dicty sim/DictySimulator/GUI/tooltip.py:16>)–18 is part of the vertical position.
- **Snapshot links:** SCOPE-001 says citations refer to the captured source, but the explicit source links in specifications 01 and 05 point to the live original checkout. They currently agree byte-for-byte. For durable source authority, link these to `../reference-source/` or explicitly state that live links are conveniences and the manifest/snapshot remains authoritative after later source edits.

## Checks completed and limitations

- Read the complete configuration, scheduling, main-loop, GUI callback, tooltip, inline Cell, initialization, growth, development, and sexual source relevant to these claims. Compared every listed module default, template default, and GUI conversion. An independent Python AST/JSON check confirmed exact values and Python types for all **62 default cells across 31 parameter rows**.
- Reviewed all four plotting scripts, the directory runner, `test.py`, dependency files, external `cell.py`, and every legacy branch cited by specification 05. File counts, colors, confidence bands, marker selection, titles, legends, axes, disabled GUI buttons, batch-runner paths, CLI rebinding, and legacy configuration binding match the source except for the points above.
- Independently reproduced the `Locus` equality distinction with the original `locus.py` class and counted exactly one active `main` timer call, at line 684.
- Verified all **205 manifest file hashes** against the original checkout and all **79 copied snapshot file hashes** against the manifest, with zero mismatches. Independently confirmed original Git HEAD `62d707eee5f348320d6e50ab034b18a3a1a45b23`, branch `main`, and clean status.
- This review did not execute GUI windows, plotting backends, SciPy numerical routines, or a full simulation. Claims about those portions were checked against their exact calls, branch conditions, and arguments, rather than inferred from an installed runtime. No source, specification, branch, or commit mutations were made.
