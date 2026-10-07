# Independent review, round 1: core state and population transitions

Reviewed 7 October 2026. This review independently compared `rust-sim/specs/02-state-initialization-growth.md` and `rust-sim/specs/03-development-and-sex.md` with the executable statements in `DictySimulator/dicty_sim_test_env.py`, `locus.py`, `locus_tracker.py`, and the separately defined `cell.py`. Source comments were not treated as executable requirements. The review did not use the existing verification program or its results as evidence.

## Verdict

No material mismatch was found in the documented ordinary-input transition rules, formulas, selection order, ownership, or examples. Two low-severity wording corrections remain for negative configured values. These are literal overstatements in unconditional sentences, rather than missing ordinary simulation algorithms.

## Findings

### R1-CORE-001 — P3: Negative slug-loop bounds mean zero iterations

**Document:** `rust-sim/specs/03-development-and-sex.md:11`, DEV-001 says the loop runs “exactly `math.floor(variables["n"] / variables["sl"])` times.”

**Source:** `DictySimulator/dicty_sim_test_env.py:461` executes `range(0, math.floor(...))`. A negative result produces an empty range, rather than a negative iteration count or a rejection of the loop bound. The function then proceeds to the empty-fruiting-body measurements at lines 524–587.

**Reproduction:** With one valid input cell, `n=-1`, `sl=2`, and `gene_pairs=1`, an isolated execution of the original function made no random calls, left the input list length at one, and raised `ZeroDivisionError` at frequency normalization. `floor(n/sl)` is -1 in this case. DEV-009 already describes the downstream empty-body failure, so only the count statement needs correction.

**Suggested wording:** “Evaluate `math.floor(variables["n"] / variables["sl"])` once as the stop value for `range(0, stop)`. When this arithmetic succeeds, the loop executes `max(0, stop)` iterations unless a loop body raises. The configured `n`, rather than the current list length, determines this stop value.”

### R1-CORE-002 — P3: Recombination draw count needs a nonnegative-length/completion qualifier

**Document:** `rust-sim/specs/03-development-and-sex.md:179`, SEX-005 unconditionally gives `2 * gene_pairs + 1` NumPy integer draws for the recombination branch.

**Source:** `DictySimulator/dicty_sim_test_env.py:630–632` constructs blank loci with `range(0, gene_pairs)`. Lines 667–669 draw twice per actual blank locus, and line 671 makes one further mating-type draw. A negative integer `gene_pairs` creates zero blank loci. In addition, incompatible parental shape can raise while evaluating a `fifty_fifty` argument, before all the claimed calls occur; SEX-009 already acknowledges the indexing failure.

**Reproduction:** With `gene_pairs=-1`, one founder and one eligible partner, and a scripted draw selecting recombination, the original function made two Python `sample` calls, one Python `uniform` call, and exactly one NumPy `randint(0,2)` call. It then raised `ZeroDivisionError` in progeny fitness computation. The stated formula would give -1 NumPy draws.

**Suggested wording:** “If the recombination branch completes, it consumes `2 * len(blank_list) + 1` NumPy integer draws after the Python uniform draw. For a nonnegative integer `gene_pairs`, this is `2 * gene_pairs + 1`; negative integers create no blank loci, so only the mating-type draw occurs before the later zero-locus fitness failure. Earlier indexing/type errors can interrupt this sequence.”

## Verified coverage

- **STATE-001–012:** Active versus standalone cell classes; constructor list retention; cell keys and equality/hash behavior; fresh lists/loci on cloning; raw allele sums and zero-slot counting; sum-equals-two `both()`; the exact effectiveness arithmetic; every one-locus binary exploitability pair at both 0/1 effectiveness multipliers; nonbinary branch rules and short-circuiting; tracker storage; random-stream portability limitations. The binary table also matched source executions at multiplier 0.5, including the all-zero exploitability result when either relevant gate is not 0 or 1.
- **INIT-001–010:** Construction and RNG call order; independent mating-type draws; `round` versus `int`; the sequential overlap at the last cheater index; uniform allele assignment across loci; tally and denominator distinctions; tracker snapshot order; append-only histories and partial failure; negative/zero locus counts; all numerical initialization examples.
- **VEG-001–011:** Input-list aliasing and delayed deletion; one germination pass even with zero generations; strict germination comparison; exact asymmetric fitness grouping and use of raw counts; weighted replacement sampling; clone order; cell-then-locus, cheater-then-resistor mutations; inclusive zero-rate mutation boundary; stale final fitness; error-state side effects and high-level RNG call counts.
- **DEV-001–010:** Configured versus actual population size; sampling, clone, and deletion order; mode gates; independent prestalk selection; complete prestalk-list construction before attempts; the two set symmetric differences and unsorted candidate iteration; retry absence; duplicate stalk deletion; leftover ownership; measurement timing and GUI gate; all four examples. In particular, a scripted `[0,0]` stalk list for the documented three-cell slug left only its third cell, as specified.
- **SEX-001–010:** Founder sampling and equality-based filtering; unchanged caller list; ordered eligible partners and partner removal; one temporary progeny per founder; identity-based locus-list comparison; no-recombination parent/mating-type coupling; exact recombination draw and allele order; reused blank-locus objects; immediate deep-clone isolation; exact progeny fitness; output grouping and key consumption; failure and zero-descendant behavior; all four examples by direct tracing, with focused scripted executions for identity, recombination, and ownership.

## Probe method and limits

The probes parsed the actual source with Python's `ast`, executed its original selected function/class nodes without editing them, and supplied scripted `random`/NumPy API stubs. This avoids importing the GUI and permits precise boundary outcomes and RNG-call inspection. Ordinary `Locus`, `LocusTracker`, and default variables were loaded from the source files themselves. The installed interpreter identified by the shell was `C:\Python314\python.exe`; it printed a launcher-location warning but executed the probes successfully.

Seven grouped assertions passed for initialization examples, initialization object independence, exact-zero mutation, strict germination, returned/input-list ownership, stored-fitness lag, repeated-parent independence, sexual recombination order, repeated-founder blank storage, offspring keys, and identity-equality bypass. Separate executions confirmed the complete documented binary exploitability table, duplicate stalk deletion, and both edge findings above. These are source-behavior checks, not a claim of full GUI execution or seeded Python/NumPy compatibility with Rust.

One optional clarification is useful but is **not an additional error**: configured `gene_pairs=0` does not force the final progeny to have zero loci in every direct call. Equal-list and no-recombination branches replace the blank loci with parental loci. A direct-call probe with nonempty parents, zero configured gene pairs, and no recombination successfully returned one-locus offspring. The algorithms already specify this correctly; SEX-009's “Zero loci” should continue to mean the actual progeny locus list, rather than being rewritten as an unconditional failure for `gene_pairs=0`.

No source or specification files were modified. No commit or branch was created.
