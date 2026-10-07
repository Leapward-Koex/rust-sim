# Development and sexual reproduction: current implementation

This document specifies executable behavior in `DictySimulator/dicty_sim_test_env.py`, rather than a corrected biological model. Requirement IDs beginning `DEV` and `SEX` identify behavior to preserve or explicitly approve changing during a Rust rewrite. Source line ranges refer to the reviewed Python source. Comments are explanatory only when they agree with executable statements. The separately implemented legacy simulation is not the authority for this document.

## Developmental cycle

### DEV-001 — Entry state, ownership, and number of slugs

**Source:** `DictySimulator/dicty_sim_test_env.py:453–473`.

`developmental_cycle(dpop_list)` receives the current population list directly. It initializes a new empty `fruiting_body` list and integer `total_stalk = 0`. It executes `range(0, math.floor(variables["n"] / variables["sl"]))`, so the number of iterations is the floor when positive, and zero when the floor is zero or negative. It uses the configured population size `n`, not the actual current list length. The division is Python `/` followed by `math.floor`, not integer division written in the source.

The input list is mutated in place as slugs form. The output is a separate list containing cloned cells; the input is not replaced with the output inside this function. After all slugs are formed successfully, any cells left in `dpop_list` remain in that caller-visible list but do not enter `fruiting_body`. For ordinary valid sizes where the input contains exactly `n` cells, this leaves `n % sl` discarded cells. The code does not append these leftovers as spores or select a smaller final slug.

### DEV-002 — Ordered slug construction and removal

**Source:** `DictySimulator/dicty_sim_test_env.py:463–473`; cloning: `135–139`.

For each slug, perform these steps in order:

1. Create a fresh empty `slug` list.
2. Call Python `random.sample(list(range(len(dpop_list))), variables["sl"])` once. This samples distinct **indices**, without replacement, from the population remaining at this point.
3. In the order returned by that sample, clone each indexed input cell and append the clone to `slug`. Every clone receives a new cell key and fresh `Locus` objects, while copying the parent's position, stored fitness, mating type, spore chance, and allele values.
4. Sort the sampled indices in descending numeric order and delete those positions from `dpop_list` in that order.

Thus slug index order is the sample order, not the source population order. Slugs draw from disjoint input positions. All cloned cells are created before any of their original population positions are deleted. No mutation draw, fitness recomputation, germination draw, or spatial interaction occurs during slug construction.

### DEV-003 — Mode gates and their actual consequences

**Source:** `DictySimulator/dicty_sim_test_env.py:485–522`, failure in measurement: `572–589`.

Only `variables["resistance_type"] == 1` enters the fate-selection and fruiting-body accumulation block. There is no `else` implementation for any other resistance type. A slug is still sampled, cloned, and removed from the input in those other modes, but none of its cells are added to the fruiting body. If all configured slugs complete, measurement then encounters an empty fruiting body and divides by zero at the first allele-frequency append.

Inside resistance type 1, initialize `stalk_index_list = []` and `pre_stalk_list = []` independently for each slug. The prestalk/cheating algorithm runs only if `variables["discrete_res"] == 1`. If that comparison is false, the stalk list stays empty, all cells in each complete slug become spores, and `sp` has no effect. There is no additive-resistance selection algorithm in this function.

These are equality comparisons, not truthiness checks. Values such as numeric `1.0` compare equal to `1` in Python; arbitrary nonzero values do not automatically enable either mode.

### DEV-004 — Prestalk assignment

**Source:** `DictySimulator/dicty_sim_test_env.py:490–499`.

For the passive/discrete mode, first construct `slug_list = [0, 1, ..., len(slug)-1]`. Then visit every slug index in increasing order. Draw `random.uniform(0, 1)` separately for **every** cell, and append that index to `pre_stalk_list` exactly when the draw is strictly less than `1 - variables["sp"]`.

`sp` therefore controls independent initial prestalk selections, not a fixed quota of spores. There is no rounding to a fixed number of stalk cells and no guarantee of at least one spore. The whole prestalk list is constructed before any cheating attempt. It retains increasing index order and is never modified afterward. The strict comparison is part of the behavior, including exact boundary draws. The source does not clamp `sp` to `[0, 1]` here.

### DEV-005 — Prestalk processing and candidate-pool XOR

**Source:** `DictySimulator/dicty_sim_test_env.py:499–515`.

Process `pre_stalk_list` in its stored order. For each index `num`:

- If the comparison `slug[num].cheater_value() > 0` is false, append `num` to `stalk_index_list`, with no partner selection or NumPy draw.
- If the raw sum of its cheater allele values is greater than zero, compute the following **symmetric differences**, in this order:

  ```text
  A = set(stalk_index_list)
  U = set(slug_list)
  P = set(pre_stalk_list)
  result_set = A symmetric_difference U
  final_result_set = result_set symmetric_difference P
  result_list = list(final_result_set)
  other_cell_index = result_list[np.random.randint(0, len(result_list))]
  ```

- Call `slug[num].exploitable(slug[other_cell_index])` once. If its return value equals `1`, append `other_cell_index` to `stalk_index_list`; otherwise append `num`.

This is one attempted target per cheater prestalk cell. An unsuccessful attempt is not retried against another candidate. Attempt eligibility uses raw `cheater_value()`, even if the cell's cheating effectiveness is zero or its active alleles are suppressed. Such a cell still selects a candidate and consumes the NumPy draw before exploitation fails.

The code converts the set directly to a list; it does **not** sort it. Python set iteration order, including its dependence on the runtime and set construction, therefore participates in mapping a NumPy draw to a target. A Rust implementation that sorts these candidates must not be claimed to reproduce this exact draw-to-target mapping without a separately approved compatibility decision.

### DEV-006 — XOR consequences and duplicate stalk indices

**Source:** `DictySimulator/dicty_sim_test_env.py:501–520`.

The XOR expression is not set subtraction. Since `A` and `P` contain slug indices, the candidate set is equivalently:

```text
(U minus (A union P)) union (A intersection P)
```

This reintroduces prestalk indices already present in `stalk_index_list`. In particular, a cell earlier assigned to stalk can be selected again as a later cheater's target. The current prestalk index is excluded under ordinary distinct-index processing, because it is in `P` but has not yet been inserted in `A`. Non-prestalk targets already selected as stalk are excluded.

There is no deduplication when appending or deleting stalk indices. After all prestalk processing, add `len(stalk_index_list)` to `total_stalk`, sort the **list** in descending index order, and execute `del slug[index]` for every entry, including duplicate entries. Deletion uses positions in the progressively shrinking list. Consequently a repeated index can remove another cell shifted into that position; it does not merely attempt to delete the same original cell twice. Preserve this effect rather than implementing an intuitive unique set of stalk cells.

After deletion, extend `fruiting_body` with the remaining slug cells in their current order. The result is concatenated by slug formation order. No extra cloning happens during the `extend`.

### DEV-007 — Exploitation dependency

**Source:** `DictySimulator/dicty_sim_test_env.py:192–225`, invocation at `510`.

The actor is the prestalk cell and the argument is the sampled target. `Cell.exploitable` scans corresponding loci and returns either `1` on its first allowed cheating interaction or `0` after all checks fail. The exact per-locus branch table belongs to the cell/genotype specification. Development itself does not draw an exploitation probability, compare additive effectiveness values, inspect `ch_self_cheat`, or calculate a fitness-weighted target probability. Changing that helper changes developmental fates, so the Rust port must preserve the helper's current branches as well as this caller's sequence.

### DEV-008 — Completion and measurements

**Source:** `DictySimulator/dicty_sim_test_env.py:524–615`.

After all slugs, the function computes and appends the developmental measurements described in the measurement specification. They observe **only the final fruiting body**, after the deletion behavior above. `total_stalk` is the sum of stalk-list lengths, not a count of unique selected original identities. The function prints its count summary before appending the normalized observations. GUI progress and `root.update()` run after the measurement appends if `"--param"` is absent from `sys.argv`. Finally it returns `fruiting_body` without restoring population size.

There is no germination filtering of fruiting-body spores in this function. There is no growth back to `n` here. It does not return a stalk list or return the leftover input cells. If an exception occurs, no rollback restores removed input cells, constructed keys, random-number-generator state, or already-appended global observations.

### DEV-009 — Important direct-call errors and degenerate cases

**Source:** `DictySimulator/dicty_sim_test_env.py:461–466`, `508`, `572–589`.

- `sl == 0` raises during `n / sl` before sampling.
- Sampling more cells than remain, or a negative sample size when the loop executes, raises from Python `random.sample`; earlier slugs may already have removed cells from the caller's list.
- No formed slugs produces an empty fruiting body. The first normalized allele-frequency append divides by zero. This includes the ordinary positive-size case `0 <= n < sl`.
- An empty XOR candidate list still reaches `np.random.randint(0, 0)` and raises; there is no fallback assigning that cheater to stalk. One simple route is that every slug cell is prestalk and the first processed prestalk cell has a positive raw cheater count.
- An empty fruiting body after deleting all stalks likewise raises during frequency normalization; it is not returned as a successful extinct population.
- The source performs no general parameter or cell-shape validation inside this function. Python's native errors from the arithmetic, sampling, index operations, helper methods, or measurements remain observable.

### DEV-010 — Deterministic examples to preserve

These examples specify scripted random results, not a claim that the repository provides a seed-based fixture API. Letter labels identify original cells; cloned cells have different keys. All genotype examples use one locus, `ch_eff_rc = res_eff_rc = 1`, passive/discrete mode, and valid measurement globals unless stated otherwise.

1. **Slug ordering and leftovers:** With input `[A,B,C,D,E]`, `n=5`, `sl=2`, and no prestalk selections, return sample indices `[3,0]` for the first slug and `[2,0]` for the second. First clones are `[D',A']`; deletion leaves `[B,C,E]`. Second clones are `[E',B']`; deletion leaves `[C]` in the input. The returned fruiting body is `[D',A',E',B']`.
2. **Repeated-index deletion:** For slug `[A,B,C]`, make `A` wild and `B` a cheater. Select prestalk indices `[0,1]`. Processing `A` appends index 0. Before `B`, the XOR candidates are `{0,2}`. Select candidate 0; `B` can exploit wild `A`, so the stalk list becomes `[0,0]`. Deleting index 0 twice removes `A` and then `B`, leaving only `C`. `total_stalk` increases by 2.
3. **No candidate:** For a two-cell slug, select both indices as prestalk and give its index-0 cell a cheater allele. Initially `A={}`, `U={0,1}`, and `P={0,1}`, so the candidate list is empty and the NumPy integer draw fails before any stalk deletion. The two source cells have already been removed from `dpop_list`.
4. **Non-discrete passive mode:** With resistance type 1 but `discrete_res=0`, every complete slug contributes all its clones to the fruiting body, even if `sp=0`. There are no prestalk uniform draws or target NumPy draws.

## Sexual cycle

### SEX-001 — Founder selection and list ownership

**Source:** `DictySimulator/dicty_sim_test_env.py:617–627`; cell equality: `131–134`.

`sexual_cycle(sexual_pop)` initially aliases `sex_pop = sexual_pop`, creates empty `mc_pop`, samples `variables["mc_count"]` distinct indices with Python `random.sample(list(range(len(sex_pop))), mc_count)`, and creates `return_pop = []`.

It appends the existing input cell object at each sampled index to `mc_pop`, in sample order; founders are not clones. Then it **rebinds** `sex_pop` to a new list formed by `[item for item in sex_pop if item not in mc_pop]`. The original caller list is not shortened. The exclusion tests cell equality, which is equality of `Cell.key`, not genotype. Under normal unique-key populations this excludes each chosen founder exactly once; if a caller supplies repeated references or cells with duplicate keys, all elements equal to a founder are excluded.

Founders are unavailable as partners, including to other founders. Survivors of this filtering retain input list order. Only the new working partner list is subsequently modified.

### SEX-002 — Blank loci and founder processing order

**Source:** `DictySimulator/dicty_sim_test_env.py:629–645`.

Allocate one `blank_list` per sexual-cycle call, containing `gene_pairs` separately constructed `Locus(0,0)` objects in index order. This occurs after founder exclusion, including when there are zero founders. Then process founders in `mc_pop` order.

For each founder:

1. Scan the current `sex_pop` list in order, appending each cell whose mating type is unequal to the founder's mating type to `temp_list`.
2. Select `partner_cell = random.sample(temp_list, 1)[0]` using Python's random module. Only mating-type inequality controls eligibility; all unequal values qualify, with no explicit restriction to types 1, 2, or 3.
3. Remove that partner with `sex_pop.remove(partner_cell)`, using cell key equality and deleting the first equal element from the working list.
4. Construct one temporary progeny cell as `Cell(0, 0, 1, 0, 0, blank_list.copy())`. It has position `(0,0)`, provisional fitness 1, provisional mating type 0, and spore chance 0, and its construction consumes a new cell key.

Only one progeny genotype is generated per founder/partner pair. It will subsequently be cloned `mc_germ_count` times. There is no per-descendant recombination or parental selection.

### SEX-003 — Equal-loci branch means Python list equality

**Source:** `DictySimulator/dicty_sim_test_env.py:647–650`; `DictySimulator/locus.py:1–10`.

First test `cell.loci == partner_cell.loci`. `Locus` defines no `__eq__`, so nonempty list equality compares corresponding locus object identities, not their two allele values. Two independently cloned cells with identical allele values normally fail this equality test. The test can succeed when both lists contain the same locus objects in corresponding positions, when the same list is shared, or when both are empty. It is not a genotype-value optimization.

If the equality test succeeds:

- Assign `progeny_cell.loci = cell.loci.copy()`, a new list with shared parental locus objects.
- Set mating type with `fifty_fifty(cell.mating_type, partner_cell.mating_type)`.
- Do not draw a recombination uniform random value and do not inspect `recomb_chance` in this branch.

### SEX-004 — Different-loci branch, without recombination

**Source:** `DictySimulator/dicty_sim_test_env.py:654–662`.

If the list-equality test fails, draw one Python `random.uniform(0, 1)`. The no-recombination branch is taken when that draw is strictly less than `1 - variables["recomb_chance"]`. The code does not clamp or validate this threshold in the function.

In this branch, set `progeny_cell.loci = fifty_fifty(cell.loci, partner_cell.loci)`. This assigns the selected parent's actual list, without copying it at this step. If `progeny_cell.loci == cell.loci`, assign the founder's mating type; otherwise assign the partner's mating type. Under ordinary distinct-locus parents, this means the offspring receives an intact genome and mating type from the same randomly chosen parent. There is one NumPy integer draw for the whole genome, not one per locus and not an extra draw for mating type.

### SEX-005 — Recombination branch

**Source:** `DictySimulator/dicty_sim_test_env.py:664–671`.

If the different-loci branch's uniform comparison is false, iterate through the temporary progeny's loci in index order. At every index:

1. Set its cheater allele using `fifty_fifty(founder.cheater_allele, partner.cheater_allele)` at that index.
2. Set its resistor allele using a separate `fifty_fifty(founder.resistor_allele, partner.resistor_allele)` at that index.

After all loci, choose the mating type with another `fifty_fifty(founder.mating_type, partner.mating_type)`.

Cheater and resistor alleles at the same locus are therefore drawn independently from the two parents. There is no crossover point, linked segment, mutation, or requirement that the two alleles come from one parent. For a nonnegative integer `gene_pairs` and a completed assortment loop, this branch consumes `2 * gene_pairs + 1` NumPy integer draws after the branch's Python uniform draw, including when corresponding parental allele values happen to be equal. A negative integer `gene_pairs` creates an empty temporary loci list and consumes only the mating-type NumPy draw before the later fitness calculation fails on zero loci. A shape error can stop the loop after a partial sequence of draws. At thresholds equal to the uniform draw, this branch wins because the no-recombination comparison is strict.

### SEX-006 — `fifty_fifty` and the two RNG families

**Source:** `DictySimulator/dicty_sim_test_env.py:242–246`, `620`, `641`, `650–671`.

`fifty_fifty(a, b)` calls `np.random.randint(0, 2)` exactly once, returning `a` when the result is 1 and `b` otherwise (normally 0). Founder selection, partner selection, and the recombination gate use Python's `random`; allele and mating-type choices use NumPy's `np.random`. These are separate generator states. A generic single-RNG rewrite is not an exact random-stream reproduction of these calls.

After initial founder sampling, per-founder high-level random-call sequences are:

| Branch | Calls after deterministic partner-list construction |
| --- | --- |
| Locus lists compare equal | Python partner `sample`; NumPy integer mating-type choice |
| Different lists, no recombination | Python partner `sample`; Python uniform branch draw; NumPy integer whole-parent choice |
| Different lists, recombination | Python partner `sample`; Python uniform branch draw; two NumPy integer choices per locus in cheater/resistor order; NumPy integer mating-type choice |

This counts explicit source API calls; an implementation of `sample` can consume more than one internal generator value.

### SEX-007 — Shallow temporary storage, deep returned clones

**Source:** `DictySimulator/dicty_sim_test_env.py:630–632`, `645–678`; cloning: `135–139`.

The `blank_list.copy()` used for each temporary progeny is a shallow list copy. Consequently the recombination branches for successive founders initially reference the same shared blank locus objects. Every allele at every blank locus is overwritten from the current parents when that branch executes. There is no accumulation of allele states from earlier founders when the parents have the expected shape and the loop completes.

The equal-loci and no-recombination branches also temporarily reference parental locus objects, but this function does not mutate those selected parental loci. Immediately after computing fitness, each returned descendant is produced with `progeny_cell.clone()`, which creates fresh locus objects. Therefore returned descendants are independent of one another, of the parents, and of the reused blank loci. Later recombination does not overwrite descendants already appended to `return_pop`.

An implementation can use different internal ownership mechanisms only if it preserves all observable results. In particular, do not carry a shallow-copy bug into the returned offspring that the current implementation avoids by immediate cloning.

### SEX-008 — Progeny fitness, count, and output order

**Source:** `DictySimulator/dicty_sim_test_env.py:673–681`; effectiveness: `165–190`.

After selecting the genotype and mating type, compute and store:

```text
fitness = ((1 - c_ch * progeny.ch_eff())
         + (1 - c_res * progeny.res_eff())) / 2
```

The grouping and final division by two are explicit in this function. This is distinct from the actual vegetative fitness expression. Do not substitute the vegetative expression here or silently correct vegetative growth to this formula. The `c_ch_res` parameter is not used here. There is no fitness clipping and no germination probability.

Execute `for i in range(0, mc_germ_count)` and append one deep `clone()` of the temporary progeny per iteration. The temporary progeny itself is not returned. Output is grouped in founder sample order, and within each group every descendant has identical genotype, mating type, stored fitness, position `(0,0)`, and spore chance 0, but a distinct key and distinct locus objects. Every processed founder consumes a temporary-cell key even if it creates zero returned descendants.

For valid nonnegative integer counts and successful partner selection, the output contains exactly `mc_count * mc_germ_count` cells. There is no topping up or downsampling to `n`. The unpaired remaining working population, founders, and partners are all absent from the returned population; no cannibalization calculation is performed. On success print `Completed sexual cycle` and return `return_pop`. This function appends no developmental measurements and updates no progress bar.

### SEX-009 — Failure cases and nonvalidated inputs

**Source:** `DictySimulator/dicty_sim_test_env.py:620–678`.

- An invalid founder sample size, including more founders than input positions or a negative count, raises from Python `random.sample`.
- If a founder has no remaining unequal-mating-type partner, `random.sample(temp_list, 1)` raises. There is no retry of founder selection, selfing, skipping a founder, partner reuse fallback, or return of accumulated offspring. Failures can occur even when the original population contained more than one mating type, because all founders are excluded first and earlier founders remove partners.
- `mc_count=0` skips founder processing and successfully prints completion and returns `[]`, provided earlier expressions such as constructing the blank locus range are valid.
- `mc_germ_count=0` or a negative integer still performs founder selection, partner selection, genotype generation, and fitness calculation for every founder, but appends no offspring. Negative integer counts are not rejected by `range`.
- Zero loci leads to division by zero when computing effectiveness for a progeny if a founder reaches that step. Recombination with parents shorter than `gene_pairs` can raise during allele indexing. No shape validation is performed here.
- The caller's input list is not shortened on success or failure, but random state and the global cell-key counter can already have advanced. Exceptions are not caught in this function.

### SEX-010 — Deterministic examples to preserve

1. **Same values, different locus objects:** With founder locus `(1,0)` and partner locus `(1,0)` allocated separately, `founder.loci == partner.loci` is false. The function draws a recombination uniform value even though both parental genotypes have identical allele values. With `recomb_chance=0.5` and a scripted uniform value `0.25`, the no-recombination branch then consumes one NumPy integer draw to choose an entire parent.
2. **Shared locus objects:** With distinct cells of different mating types whose locus lists contain the same `Locus` object, equality succeeds. No recombination uniform value is drawn. A NumPy integer result of 1 gives the founder's mating type; 0 gives the partner's. Returned clones nevertheless receive separate locus objects.
3. **Independent within-locus assortment:** With founder `(1,0)` of type 1 and partner `(0,1)` of type 2, take the recombination branch and script NumPy results `[1,0,0]`. The cheater allele comes from the founder, the resistor allele from the partner, and mating type from the partner, yielding `(1,1)` and type 2. Every descendant of this macrocyst has that same result. If `ch_eff_rc=res_eff_rc=1`, `c_ch=0.2`, and `c_res=0.4`, its stored fitness is `(0.8+0.6)/2 = 0.7` subject to floating-point representation.
4. **Founders deplete partner types before processing:** An input of four cells with mating types `[1,1,2,2]`, `mc_count=2`, and founder indices `[2,3]` leaves types `[1,1]` as partners. Both founders succeed. If instead founder indices are `[0,2]`, the working pool is types `[1,2]`; the type-1 founder must choose the type-2 partner and the type-2 founder then chooses the type-1 partner. A population `[1,1,1,2]` with founder indices `[0,3]` leaves only type-1 partners, so the first type-1 founder fails immediately. All these cases retain the original caller list.
