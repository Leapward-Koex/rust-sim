# Compatibility and verification

## What exact compatibility means here

**COMPAT-001.** The source is a stochastic program with observable mutable state, not only a collection of biological equations. Preserve the specified order of phases, conditionals, selection, cloning, mutation, measurements, aggregation, and serialization when interpreting this baseline. An optimization that preserves an idealized probability distribution but changes an implemented bug is not equivalent to this baseline.

**COMPAT-002.** There are three distinct comparison levels:

| Level | What can be compared | What it does not establish |
| --- | --- | --- |
| Scripted choices | Identical state transitions when the named random API calls return specified results | Equality of RNG implementations or library samplers |
| Distributional behavior | Outcome distributions under the same rules and random-choice distributions | Identical trajectories, IDs, set ordering, or output bytes |
| Exact execution replay | Same runtime/library algorithms, initial generator states, selection ordering, floating-point operations, and output conventions | Portability of that trajectory to other runtimes without emulation |

The source itself exposes no seed or replay interface. This specification does not silently select a weaker level for the Rust remake; it records the operational behavior and explicitly identifies dependencies that must be resolved before claiming exact replay.

**COMPAT-003.** The two module-level RNG families must be distinguished. Python `random` handles initial mating-type weighted choices, initial allele samples, germination draws, parent weighted choices, mutation draws, slug samples, prestalk draws, sexual founder/partner samples, and the recombination gate. NumPy `np.random` handles developmental candidate integer selection and every `fifty_fifty` allele/genome/mating-type choice. Both persist across repeats, and neither is seeded or serialized by this code. Source: `dicty_sim_test_env.py:2,7,242–246,278–288,403–447,466–508,620–671`.

**COMPAT-004.** Preserve the literal comparisons and API conventions: mutation uses `<=`; prestalk uses `<`; germination removes when `threshold < draw`; no-recombination uses `<`; `fifty_fifty` selects its first argument on integer `1`. Samples are from the actual ordered lists given in the source. Sampling API calls can consume a variable number of internal RNG values, so counting explicit calls is not a count of underlying random bits. An implementation replacing `random.uniform(0,1)` with another draw or replacing `random.sample` with a shuffle must not claim stream equivalence without establishing it.

**COMPAT-005.** Python set-to-list ordering in developmental target selection, Python's ties-to-even `round` for random initial frequencies, truncation by `int` in the sequential branch, numeric equality of integer/float/boolean parameters, and object identity in locus-list equality are part of the reference semantics. Floating-point evaluation order is recorded where expressions matter. No Rust enum restrictions, probability clamps, fixed-width overflow behavior, alternative rounding, or genotype-value equality may be inferred from Python comments.

**COMPAT-006.** `requirements.txt` pins NumPy 1.26.4, SciPy 1.13.0, and Matplotlib 3.8.4; `mac_reqs.txt` pins different versions. Neither pins Python or Tcl/Tk. The exact historical interpreter and initial RNG states are absent. Therefore this package provides a source baseline and targeted executable checks, not a historical run reconstruction or a guarantee of byte-for-byte agreement with every saved result file.

## Source coverage map

This is a specification coverage map, not instrumented line-coverage data. `dicty_sim_test_env.py` is abbreviated as the active source below.

| Source area | Source lines | Specification |
| --- | --- | --- |
| Imports, globals, tooltip descriptions | Active 1–69 | 00, CONFIG-001/002, RUN-003, UI-002, TOOL dependency section |
| GUI tooltip binding and form parsing | Active 73–108 | UI-001/002 |
| Cell state, cloning, counts, effectiveness, exploitability | Active 111–225; `locus.py` | STATE-001 through STATE-010 |
| Parameter dialog and numeric validation | Active 227–239 | UI-001 |
| Binary parent-choice helper | Active 242–246 | SEX-006 |
| Confidence half-width function | Active 248–253 | AGG-004/005 |
| Initial population and measurement | Active 256–395 | INIT-001 through INIT-010; MEASURE-001 through MEASURE-007 |
| Germination, growth, selection, mutation | Active 398–451 | VEG-001 through VEG-011 |
| Slugs, prestalk, exploitation, deletion | Active 453–522 | DEV-001 through DEV-010 |
| Post-development measurements and progress | Active 524–615 | MEASURE-001 through MEASURE-007; DISPLAY-001/002 |
| Sexual reproduction | Active 617–681 | SEX-001 through SEX-010 |
| Main local state, scheduling, collecting repeats, resets | Active 683–862 | RUN-002/003; AGG-001/002; OUTPUT-004 |
| Across-repeat means and confidence values | Active 864–904 | AGG-003 through AGG-007 |
| JSON saving | Active 907–934 | OUTPUT-001 through OUTPUT-005 |
| Built-in plots | Active 937–1006 | DISPLAY-003/004 |
| CLI and GUI startup | Active 1013–1079; `.vscode/launch.json` | RUN-001/004; UI-001; LEGACY-001 |
| Locus tracker class | `locus_tracker.py:1–9` | STATE-009; MEASURE-005/006 |
| Legacy engine and external Cell binding | `dicty_sim_v0.6.py`; `cell.py` | 05 legacy sections; expressly not the active model |
| Standalone figures, batch runner, tooltip implementation, test scratch file, dependency lists | Other captured Python/text files | 01 tooltips and 05 supporting tools |

## Behavior checks included in this folder

**VERIFY-001.** `verification/check_source_behavior.py` compiles original AST function and class bodies from the captured source. It does not reimplement the simulation functions and does not rewrite their statements. It loads actual `Locus`, `LocusTracker`, and module defaults. Selected tests inject scripted RNG results to exercise otherwise rare or nondeterministic branches. Ordinary file imports requiring plotting/statistical dependencies are bypassed. The verification environment is not presented as the original installed application.

**VERIFY-002.** The executable checks cover:

- SHA-256 agreement for all 80 captured source/configuration files.
- Cell IDs, deep clone independence, and identity-based locus equality.
- All 64 binary one-locus actor/target/epistasis combinations, plus nonbinary switch fallthrough.
- A four-genotype measurement fixture, conditional effectiveness, raw locus counts, and mating fractions.
- The sequential initial-distribution overlap, ties-to-even sampling count, whole-genome starting assignments, and lack of even-population rounding.
- Literal vegetative fitness, germination equality boundary, inclusive mutation at a scripted zero draw, and mutation reversibility.
- Slug ordering/leftovers/input mutation, nondiscrete passive retention, unsupported resistance failure, empty candidate failure, and duplicate stalk-index deletion.
- Equal-valued versus shared-identity parental loci, no-recombination inheritance, within-locus independent assortment, sibling independence, and missing-partner failure.
- Definition-time confidence capture and exact SciPy call arguments using a statistical-call spy.
- Original `main` scheduling, aggregation, tracker reset, output key ordering, duplicated interval events, missing explicit-list events, and unconditional filename suffix, using stage spies and an in-memory output sink.
- Selected invalid inputs and GUI parsing mismatch, stale global history, and Python JSON nonfinite-token behavior.

**VERIFY-003.** Run from this folder using a Python interpreter with NumPy:

```text
python -B verification/check_source_behavior.py
```

The script writes `verification/results.json`, prints its results, and exits nonzero on any failed check. The `-B` option prevents bytecode-cache files. It writes no source files, launches no GUI, and creates no simulation result file outside its report. The results record the interpreter, NumPy version, and platform actually used.

**VERIFY-004.** Statistical spies return deliberately artificial `sem=2` and `ppf=3`; they verify the original confidence function's arguments, multiplication, and captured default. These numbers are not scientific confidence interval fixtures. Main-stage spies test orchestration and aggregation separately from the biological phase checks. The in-memory output sink checks the filename supplied to `open` and JSON serialization without proving filesystem error behavior.

**VERIFY-005.** The retained checks do not execute SciPy's numerical implementation, render the GUI/plots, exhaustively enumerate malformed parameters, measure performance, or compare a Rust engine. Matplotlib and SciPy are not installed in the bundled verification interpreter used here. Their calls and formulas were inspected against the captured source; runtime-dependent details are identified rather than represented as tested facts. NumPy used for these checks is 2.3.5, not either repository-pinned NumPy version.

## Behaviors that must not disappear during a remake

The following is an index into the specifications, not a corrected alternative contract.

| Easily missed behavior | Reference |
| --- | --- |
| CLI replaces defaults; GUI parses fields differently | CONFIG-001, RUN-001, UI-001 |
| Default module sex schedule is a string; template schedule is a list | CONFIG-001, RUN-001 |
| Nominal exclusive initial assignment can overlap | INIT-004/009 |
| Vegetative fitness is `A + B/2` and counts alleles; sexual fitness is `(A+B)/2` and uses effectiveness | VEG-004, SEX-008 |
| Mutations can remove alleles and use inclusive comparisons | VEG-007 |
| Stored offspring fitness can lag mutated genotype | VEG-008 |
| All prestalk draws happen before any target draws | DEV-004/005 |
| Target eligibility is symmetric difference, with repeated-index deletion | DEV-005/006 |
| Passive nondiscrete mode retains all slug cells; other resistance types fail downstream | DEV-003/009 |
| Same-valued cloned parental genomes do not pass identity-based equality | SEX-003 |
| One genotype is generated per pair and cloned for all descendants | SEX-002/008 |
| Wild is missing allele slots; locus counts are absolute exclusive categories | MEASURE-003/005 |
| Effectiveness means include suppressed carriers and then average repeats equally | MEASURE-004, AGG-003 |
| Configured confidence changes are saved but ignored by ordinary CI calls | AGG-005 |
| Interval sex events duplicate across repeats; explicit events absent from result event list | OUTPUT-004 |
| Nonfinite confidence values can serialize as `NaN` | AGG-006, OUTPUT-005 |
| Failed calls can leave changed input lists, IDs, RNG state, or histories | INIT-010, VEG-010, DEV-008/009, SEX-009, AGG-002 |
| Exposed `c_ch_res` and `ch_self_cheat` have no active engine effect | CONFIG-001 |

## Review record

The user requested repeated fresh review. The independent reports and the corrections applied from them are recorded in [the review record](../verification/REVIEW.md). Reviewer findings are evidence of review, not additional requirements; the reconciled specification files above define the documented baseline. Any report discussing an earlier wording should be read with its recorded resolution.
