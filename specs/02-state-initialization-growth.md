# State, population initialization, and vegetative growth

This is an **as-implemented behavioral specification**, not a corrected biological model. Its primary implementation is the inline `Cell` class and functions in `DictySimulator/dicty_sim_test_env.py`. All source references below are repository-relative and refer to the source snapshot recorded by this specification set. Statements about normal genotype behavior assume allele values are binary integers; explicitly identified edge behavior follows the actual comparisons and arithmetic instead. A future implementation must not silently substitute intended behavior described by Python comments for the operations below.

## 1. Cell and locus state

**STATE-001 — Active class.** The test-environment simulation defines and uses its own inline `Cell`; its `from cell import Cell` line is commented out. `DictySimulator/cell.py` contains a separate class with equivalent method bodies and its own class counter, but is not the active cell class in this entry point. Source: `DictySimulator/dicty_sim_test_env.py:16-18,111-225`; `DictySimulator/cell.py:1-119`.

**STATE-002 — Ordered, mutable records.** A cell stores `loci`, `positionX`, `positionY`, `fitness`, `mating_type`, and `spore_chance` directly from its constructor arguments. The constructor retains the exact supplied loci-list object; it does not copy that list, validate values, or enforce a locus count. A locus stores `cheater_allele` and `resistor_allele` directly, without validation or conversion. List order identifies which loci correspond between cells. Source: `DictySimulator/dicty_sim_test_env.py:114-120`; `DictySimulator/locus.py:1-4`.

**STATE-003 — Identity.** The active `Cell._id_counter` starts at zero when the class is defined. Construction assigns the current counter as `key`, then increments the counter by one. Neither population initialization nor the run loop resets this counter. Both string conversion and representation return the decimal string of `key`. Two instances of this active class compare equal exactly when their keys compare equal; comparisons with other types return false. Hashing uses `hash(key)`. Consequently equal genotypes are not equal cells, while repeated references to the same cell compare equal and collapse in sets. IDs continue across repeat runs and repeated calls to `main()` within the same loaded module. Source: `DictySimulator/dicty_sim_test_env.py:111-142,256-395,683-903`.

**STATE-004 — Clone.** `cell.clone()` constructs, in locus order, a fresh `Locus` from each old locus's two allele values, then constructs a fresh `Cell`. The clone receives a new key and a new list containing new locus objects. It copies position, fitness, mating type, and spore chance as stored at clone time. Clones of a single selected parent are therefore independently mutable. `Locus.clone()` similarly constructs a new locus holding its current two values. These operations copy the ordinary numeric allele values; there is no generic recursive copy of arbitrarily typed constructor inputs. Source: `DictySimulator/dicty_sim_test_env.py:135-139`; `DictySimulator/locus.py:9-10`.

**STATE-005 — Allele counts.** For a cell with ordered loci `l[0] ... l[L-1]`:

- `cheater_value()` starts at integer zero and sequentially adds each `cheater_allele`.
- `resistor_value()` starts at integer zero and sequentially adds each `resistor_allele`.
- `wild_value()` adds one separately for each cheater allele equal to zero and each resistor allele equal to zero. For binary inputs it counts zero-valued allele slots, not entirely wild loci or entirely wild cells.
- `locus.both()` returns `int(cheater_allele + resistor_allele == 2)`. This is a **sum-equals-two** test, not a general conjunction that both values are nonzero. For ordinary binary alleles it is one only for `(1,1)`; a supplied `(2,0)` also yields one.

Source: `DictySimulator/dicty_sim_test_env.py:144-163`; `DictySimulator/locus.py:6-7`.

**STATE-006 — Effectiveness.** Each call reads current allele values and the current global `variables` dictionary. There is no cached effectiveness. Let `C = cheater_value()`, `R = resistor_value()`, `B = sum(locus.both())`, `L = len(cell.loci)`, and `q = 1/L`. The actual expressions, with their multiplication and addition order retained, are:

```text
ch_eff  = ((C - B) * q) + ((B * variables["ch_eff_rc"])  * q)
res_eff = ((R - B) * q) + ((B * variables["res_eff_rc"]) * q)
```

These are not capped to `[0,1]`; fractional, negative, or greater-than-one multipliers flow through arithmetic if supplied. The methods do not branch on `discrete_res`, `resistance_type`, or `ch_self_cheat`. An empty loci list fails with division by zero before the allele sum is used. Source: `DictySimulator/dicty_sim_test_env.py:165-190`.

**STATE-007 — Direction of exploitability.** `self.exploitable(other)` answers whether `self` can exploit `other`. It returns integer one as soon as a qualifying same-index locus is found, otherwise integer zero. The following binary-genotype table is exhaustive for one locus. `W=(0,0)`, `C=(1,0)`, `R=(0,1)`, and `B=(1,1)`. Each row lists every positive ordered pair `(self, other)`; all unlisted pairs return zero.

| `ch_eff_rc` | `res_eff_rc` | Positive one-locus pairs |
|---|---|---|
| `0` | `0` | `(C,W)`, `(C,B)` |
| `0` | `1` | `(C,W)` |
| `1` | `0` | `(C,W)`, `(B,W)` |
| `1` | `1` | `(C,W)`, `(B,W)` |
| neither `0` nor `1` | any | none |
| `0` or `1` | neither `0` nor `1` | none |

For equal-length, ordinary binary multilocus cells the result is the logical OR of the corresponding per-locus results. In particular, a cheater at one locus can be exploited at another locus where it qualifies as a target. `ch_self_cheat`, `discrete_res`, and `resistance_type` do not change this method. Equality comparisons also accept numerically equal values such as `0.0` and `1.0`; these are not strict integer-type checks. Source: `DictySimulator/dicty_sim_test_env.py:192-225`.

**STATE-008 — Exact exploitability branch rules, including nonbinary inputs.** The binary table must not replace the following rules for arbitrary values. Process loci in increasing index order and preserve comparison short-circuiting:

1. If `ch_eff_rc == 0`, skip a locus when `self.both() == 1` **or** `self.cheater_allele == 0`.
   - If `res_eff_rc == 0`: skip when `other.cheater_allele == 1` **and** `other.both() == 0`; otherwise return one when `other.both() == 1` **or** `other.resistor_allele == 0`.
   - Else if `res_eff_rc == 1`: skip when `other.cheater_allele == 1` **and** `other.both() == 0`; otherwise return one when `other.resistor_allele == 0`.
   - For any other resistance multiplier, this locus yields no success.
2. Else if `ch_eff_rc == 1`, skip a locus when `self.cheater_allele == 0`.
   - If `res_eff_rc == 0`: skip when `other.cheater_allele == 1`; otherwise return one when `other.both() == 1` **or** `other.resistor_allele == 0`.
   - Else if `res_eff_rc == 1`: skip when `other.cheater_allele == 1`; otherwise return one when `other.resistor_allele == 0`.
   - For any other resistance multiplier, this locus yields no success.
3. Return zero after processing, or immediately without entering a loop when the cheater multiplier equals neither zero nor one.

Here each `self`/`other` allele or `both()` reference concerns the current locus. The loop length is **self's** loci length. Extra target loci are ignored. A shorter target list can raise `IndexError` when an executed branch accesses a missing index; skipped source loci or a prior successful locus may avoid that access. An empty source loci list returns zero. Source: `DictySimulator/dicty_sim_test_env.py:192-225`.

**STATE-009 — Tracker records.** `LocusTracker` directly stores `name`, `ch_count`, `res_count`, and `both_count`; `clone()` constructs a fresh tracker with the four stored values. There is no counter normalization or validation inside this class. Source: `DictySimulator/locus_tracker.py:1-9`.

**STATE-010 — Hand-checkable state examples.** For loci `[(1,0),(1,1),(0,0)]`, `C=2`, `R=1`, `wild_value=3`, and `B=1`. With `ch_eff_rc=0.5` and `res_eff_rc=0`, the respective effectiveness values are `0.5` and `0`; nevertheless exploitability is zero because the cheater multiplier equals neither zero nor one. Cloning this cell creates three new loci and a new cell key; changing a clone's first allele must leave its parent and any sibling clones unchanged. These examples follow STATE-004 through STATE-008 and do not prescribe a different numerical calculation order.

## 2. Initial population and its initial observation

**INIT-001 — Setup and construction order.** `initialise_pop()` creates a new population list, a fixed ordered mating-type list `[1,2,3]`, and weights `[mt1_start,mt2_start,mt3_start]`. For each index in `range(0, gene_pairs)` it adds `Locus(0,0)` to a temporary template list and `LocusTracker("Locus" + str(index),0,0,0)` to the tracker list. It prints `length of loci: ` followed by the template-list length. Source: `DictySimulator/dicty_sim_test_env.py:256-272`.

**INIT-002 — Initial cells and random mating types.** For each index in `range(0, int(n))`, in order:

1. Execute `random.choices([1,2,3], k=1, weights=[mt1_start,mt2_start,mt3_start])[0]`.
2. Clone each template locus into a new list, then pass a shallow copy of that new list to a new `Cell(0,0,1,chosen_mt,0,...)`.
3. Append the cell to the population.

Thus position starts at `(0,0)`, fitness at `1`, and spore chance at `0`. Initial cells have distinct locus objects and distinct cell keys. Mating-type counts are stochastic weighted draws; the code does not assign exact quotas and does not itself require the three weights to sum to one. All mating-type selection calls occur **before** either initial allele-selection call. No even-number rounding is performed inside this function. Source: `DictySimulator/dicty_sim_test_env.py:275-283`.

**INIT-003 — Random allele distribution mode.** Exactly when `ch_res_dist == 1`, execute these two calls, in this order:

```text
cheater_index_list  = random.sample(list(range(n)), round(ch_start  * n))
resistor_index_list = random.sample(list(range(n)), round(res_start * n))
```

Each sample is without replacement within itself, but the two samples are independent and may overlap. These are sample sizes for **cells**, not independent draws for every locus. Python's `round` is used, including ties to even (for example `round(2.5)==2`, `round(3.5)==4`), subject to the input's actual binary floating-point product. No overlap exclusion or shuffle of the population follows these calls. The calls are still made when their requested sample sizes are zero. Source: `DictySimulator/dicty_sim_test_env.py:285-288`.

**INIT-004 — All other distribution values use the sequential branch.** Every value of `ch_res_dist` unequal to one selects this branch, including negative numbers and values other than zero. The exact algorithm is:

```text
cheater_index_list = []
resistor_index_list = []
ch_end = int(ch_start * n)
last_index = 0
for i in range(0, ch_end):
    cheater_index_list.append(i)
    last_index = i
res_end = int(last_index + (res_start * n))
for i in range(last_index, res_end):
    resistor_index_list.append(i)
```

`int` truncates toward zero. With a positive `ch_end`, resistance begins at the **last cheater index**, not the next index. If both index lists are nonempty, that index has both alleles. With `ch_end <= 0`, `last_index` remains zero. There are no random draws in this branch. No clipping to available population indices, exclusion of overlap, or check of the sum of the start frequencies occurs here. Source: `DictySimulator/dicty_sim_test_env.py:289-300`.

**INIT-005 — Assignment.** Traverse `cheater_index_list` in its stored order and set the cheater allele to one at **every locus** of each selected cell. Then traverse `resistor_index_list` and set the resistor allele to one at every locus of each selected cell. Other alleles remain zero. Starting multilocus cells therefore have only uniform states across all their loci: all `(0,0)`, all `(1,0)`, all `(0,1)`, or all `(1,1)`. The two allele assignments do not change mating types. The local variable `check = len(cheater_index_list)` has no later use. Source: `DictySimulator/dicty_sim_test_env.py:302-310`.

**INIT-006 — Initial tally pass.** After allele assignment, traverse cells in population-list order. Accumulate raw cheater, resistor, and wild values using STATE-005. For each locus index:

- If `locus.both() == 0`, add its cheater value to that tracker's `ch_count` and its resistor value to `res_count`.
- Otherwise increment only `both_count` by one.

For binary inputs, tracker `ch_count` and `res_count` count **exclusive** cheater-only and resistor-only loci; co-occurring alleles are represented only by `both_count`. In contrast, global raw cheater/resistor allele totals include co-occurring alleles. Source: `DictySimulator/dicty_sim_test_env.py:323-354`.

**INIT-007 — Effectiveness and mating tallies.** Add `cell.ch_eff()` and increment its averaging denominator only when `cell.cheater_value() > 0`; likewise use `cell.res_eff()` only when `cell.resistor_value() > 0`. A genotype with a present but completely suppressed allele is still in that denominator. Count mating types with the ordered chain `==1`, else `==2`, else `==3`. The locals `test1 = ch_eff_rc` and `test2 = res_eff_rc` are read but unused. Source: `DictySimulator/dicty_sim_test_env.py:339-368`.

**INIT-008 — Appended initial observation.** Make fresh clones of all trackers and append that list to the global `locus_plot`. Let `P = len(pop_list)` and `T = variables["gene_pairs"] * P`. Then append, in this order:

1. Raw cheater allele total divided by `T`, to `cheater_allele_counts`.
2. Raw resistor allele total divided by `T`, to `resistor_allele_counts`.
3. Raw wild count divided by `2*T`, to `wild_counts`.
4. Cheater effectiveness total divided by the number of cells with positive cheater value, or integer zero if that count is zero, to `mean_ch_eff`.
5. Resistor effectiveness total divided by the number of cells with positive resistor value, or integer zero if that count is zero, to `mean_res_eff`.
6. Mating-type counts divided by `P`, to `mt1_ratios`, then `mt2_ratios`, then `mt3_ratios`.

Return the newly created population list. Initialization **appends** to these global histories; it does not clear them itself. The per-locus tracker snapshot is raw counts, not fractions. Source: `DictySimulator/dicty_sim_test_env.py:370-395`.

**INIT-009 — Deterministic distribution examples.** For `n=10`, `gene_pairs=1`, `ch_res_dist=0`, `ch_start=0.4`, and `res_start=0.3`, the cheater indices are `[0,1,2,3]` and resistor indices `[3,4,5]`. The resulting counts are three `C`, one `B`, two `R`, and four `W`; the initial allele frequencies are `0.4`, `0.3`, and wild-slot fraction `0.65`. With both effectiveness multipliers zero, the carrier-conditional mean effectiveness values are `0.75` and `2/3`. With both start frequencies `0.15`, the sequential branch selects only index zero for both traits, so each allele frequency is `0.1`. In random mode, with the same `n=10` and frequencies `0.15`, each sample has size `round(1.5)=2`, so each allele frequency is `0.2` regardless of overlap. Source: INIT-003 through INIT-008.

**INIT-010 — Failure and unusual-input behavior.** Initialization supplies no local validation or exception handling. In particular:

- `gene_pairs` is passed directly to `range` and must support Python's integer indexing protocol. A float such as `3.0` is not accepted by `range`.
- Although cell construction uses `int(n)`, random distribution later uses `range(n)` directly, and growth also uses `n` directly. This is not a general conversion of the configured `n` to an integer.
- Negative `gene_pairs` yields no loci or trackers. With a nonempty population, `T` is negative rather than zero, so this function can append signed-zero allele fractions and return empty-locus cells. `gene_pairs == 0` instead causes division by zero at the first frequency append.
- A zero/negative constructed population size reaches division by zero in the initial observations if an earlier sampling or index operation has not already failed. `locus_plot` is appended before that division, so failure may leave partial history.
- A sample size outside `[0,n]` raises the `random.sample` library error. Sequential indices outside the actual population raise `IndexError` while assigning alleles. Parameters are not clamped.
- Mating weights are delegated to `random.choices`. They are not normalized or individually validated by simulation code. Invalid totals and incompatible types can raise library errors; a future replacement must not infer an existing user-facing validation layer from this function.

Source: `DictySimulator/dicty_sim_test_env.py:267-310,370-395`.

## 3. Vegetative growth

**VEG-001 — Input aliasing and one germination pass.** `vegetative_growth(pop_list)` begins with `pop_copy = pop_list`, retaining the original list object. Before any generation, iterate all current list indices in increasing order. For a cell with `cheater_value() > 0`, evaluate:

```text
(1 - (variables["ch_germ"] * cell.ch_eff())) < random.uniform(0, 1)
```

If true, record that index for deletion. Cells whose cheater value is zero or negative consume no germination random draw. A positive raw cheater value always consumes one draw, including when `ch_germ==0` or its effectiveness is zero. This pass happens once per function call, not once per vegetative generation, and happens even when `vg` is zero or negative. It also applies to initialized cells and to sexual offspring when the main loop sends them into this function; the cell does not carry a checked spore-only state. Source: `DictySimulator/dicty_sim_test_env.py:398-408,757-785`.

**VEG-002 — Germination boundary and deletions.** Evaluate the strict comparison exactly as written: a draw equal to the survival threshold survives. There is no clamp on threshold, cost, or effectiveness. After all draws, delete recorded indices from the aliased input list in descending numerical order; survivors retain their original order. This changes the caller's original list in place. For binary alleles with effectiveness in `[0,1]` and ordinary parameter range, the threshold is `1 - ch_germ*ch_eff`; the actual rule is the comparison, not a separately normalized probability. Thus threshold zero still retains an exact zero draw. Source: `DictySimulator/dicty_sim_test_env.py:403-412`.

**VEG-003 — Generation count.** Execute `range(0, variables["vg"])`. A zero or negative integer performs no generations and returns the same original, possibly shortened list after germination. Non-integer values rejected by `range` fail after the germination deletions have already occurred. Source: `DictySimulator/dicty_sim_test_env.py:410-415,451`.

**VEG-004 — Fitness assignment.** At the start of every generation, traverse current cells in list order and mutate their stored `fitness` to this exact expression:

```text
((1 - (c_ch * cell.cheater_value())))
    + (1 - (c_res * cell.resistor_value())) / 2
```

Algebraically this is `1.5 - c_ch*C - 0.5*c_res*R`, but use the expression above to preserve floating-point operation order. It is **not** `(cheater component + resistor component)/2`. It uses raw allele sums, not `ch_eff()` or `res_eff()`, and is not divided by the number of loci. Consequently increasing the number of affected loci increases the cost. `c_ch_res`, both effectiveness multipliers, `resistance_type`, and `discrete_res` are not read for this fitness calculation. There is no cap or nonnegative floor. Source: `DictySimulator/dicty_sim_test_env.py:415-424`.

**VEG-005 — Weighted replacement sampling.** Construct `fitness_values` in current population-list order, then make exactly one call:

```text
random.choices(range(len(pop_copy)), k=variables["n"], weights=fitness_values)
```

This is sampling with replacement and returns ordered parent indices. With ordinary nonnegative weights and a positive total, selection is proportional to stored fitness. There is no explicit survivor quota, pairwise reproduction, reproduction without replacement, or population doubling. The requested next-generation length is `n`, independently of the number of germination survivors. Source: `DictySimulator/dicty_sim_test_env.py:423-427`.

**VEG-006 — New generation and aliases.** Clone selected parents in sampled-index order using STATE-004, producing a new population list; then rebind the function-local `pop_copy` to that list. All parent selections happen before any clones, and all clones are created before mutation begins. Each offspring copies its parent's mating type, position, spore chance, and just-computed fitness. If a parent is chosen more than once, its offspring remain distinct. For the first generation, caller-visible survivor objects have already had their fitness changed by VEG-004; cloning does not otherwise mutate them. The caller's original list is not overwritten with the offspring list; receiving the function's return value is necessary to use the new generation. Source: `DictySimulator/dicty_sim_test_env.py:418-431`.

**VEG-007 — Mutations and exact random-call order.** After cloning the entire generation, traverse offspring in their new list order and their loci in locus order. For **every** locus:

1. Draw `random.uniform(0,1)` and compare with `<= m_ch`. If true, set cheater allele to zero when its existing value equals one; otherwise set it to one.
2. Draw a second `random.uniform(0,1)` and compare with `<= m_re`. If true, set resistor allele to zero when its existing value equals one; otherwise set it to one.

Both draws are made even if the rates are zero, one, negative, or greater than one; neither test uses short-circuit gating on allele presence or the other mutation. Both alleles can mutate at one locus in one generation, in cheater-then-resistor order. For binary inputs mutations are reversible toggles, not only introductions. For arbitrary existing allele values, the rule is equality-to-one followed by assignment to zero/one, not arithmetic `1-value`. Mutation rate zero can still mutate on an exact zero draw because the comparison is inclusive. Source: `DictySimulator/dicty_sim_test_env.py:433-447`.

**VEG-008 — Stored fitness lag and return.** Mutation does not recalculate the offspring's fitness. Until the next generation's fitness assignment, each offspring stores the fitness its parent had before these mutations. After the final generation the function returns this population with potentially stale stored fitness. `cheater_value`, `resistor_value`, and effectiveness calculations still read the new loci directly. The function appends no population observations or tracker snapshots itself. Source: `DictySimulator/dicty_sim_test_env.py:420-451`.

**VEG-009 — Randomness summary.** With `P` input cells, `K` of them having positive raw cheater value, nonnegative integer `vg=G`, successful sampling to positive integer `n=N`, and uniform fixed locus count `L`, this function makes `K` germination `uniform` calls, followed for each of `G` generations by one `choices(...,k=N)` call and `2*N*L` mutation `uniform` calls. No germination call is repeated between generations. This is a count of high-level library calls; it does not claim all APIs consume the same number of underlying PRNG steps. `random` here is Python's standard-library module, not NumPy. No seeding occurs in this function. Source: `DictySimulator/dicty_sim_test_env.py:2,398-451`.

**VEG-010 — Failure behavior.** This function has no recovery logic. With positive `vg`, an empty survivor list reaches `random.choices` with empty weights and fails rather than reinitializing the population. A nonpositive or non-finite total fitness fails according to the Python `random.choices` implementation; negative individual weights are not explicitly rejected by the simulation and must not be described as an implemented fitness floor. Incompatible parameter types fail at the corresponding arithmetic, comparison, range, or library call. Any earlier germination deletions and fitness assignments remain observable when a later operation raises. A zero-generation call can return an empty list successfully; downstream behavior is specified separately. Source: `DictySimulator/dicty_sim_test_env.py:398-451`.

**VEG-011 — Deterministic acceptance examples.** These examples require controlling draw outcomes, rather than relying on a chosen seed across languages:

- For one locus, `c_ch=0.2`, `c_res=0.4`: the assigned vegetative fitness of `W`, `C`, `R`, and `B` is respectively `1.5`, `1.3`, `1.3`, and `1.1` (subject to ordinary floating-point representation).
- For a cheater with `ch_eff=0.5` and `ch_germ=0.4`, the threshold is `0.8`. A supplied germination draw of `0.8` retains it; `0.81` deletes it.
- Given a nonempty surviving population, `vg=0` returns the same list object and creates no new cell keys; `vg=1` with positive `n` returns a new list with `n` new cell keys.
- If controlled parent indices select the same parent twice, independently mutating the first offspring must not alter the second offspring or the parent.
- For starting locus `(1,0)` and successful cheater and resistor mutation comparisons, the resulting locus is `(0,1)`. A failed comparison leaves that allele unchanged.
- The final mutated offspring's stored fitness remains its parent's pre-mutation fitness; it is not silently recomputed on return.

Source: VEG-001 through VEG-008.

## 4. Compatibility limits that must remain visible

**STATE-011 — Exact behavior versus a portable random sequence.** The algorithms above specify API calls, their order, strict/inclusive comparisons, mutation ordering, data aliasing, and statistical weighting. An independently chosen Rust PRNG and weighted-sampling routine will not automatically reproduce a Python seed's trajectory. Exact seeded replay would additionally require fixing the original Python and NumPy versions, both RNG states, relevant set/list ordering, and the library algorithms. This specification does not present matching probability distributions as proof of identical trajectories. The repository's randomness and environment constraints are covered with the run-level specification.

**STATE-012 — No implicit correction authorization.** Keep the sequential initial overlap, sum-equals-two `both()` test, exact exploitability gates, unequal fitness averaging, conditional effectiveness denominators, inclusive zero-rate mutation comparison, and clone/list identity effects visible in any reconstruction or validation plan. A later explicitly chosen corrected mode can differ, but these are the behaviors of this source.
