# Fresh review, round 2: state and biological phases

Reviewed on 2026-10-07 against the original files in `DictySimulator`, without consulting earlier review reports or treating existing specification assertions as evidence.

## Findings

No actionable inaccuracies or substantive omissions found in the reviewed scope. No specification changes are requested by this review.

## Covered scope

Compared `specs/02-state-initialization-growth.md` in full and `specs/03-development-and-sex.md` in full with:

- `DictySimulator/dicty_sim_test_env.py:111–225`: cell construction, equality and hashing, clone ownership, allele counts, effectiveness, and every exploitability branch.
- `DictySimulator/dicty_sim_test_env.py:242–246`: `fifty_fifty`.
- `DictySimulator/dicty_sim_test_env.py:256–451`: initialization, initial measurements, germination, fitness, reproduction, mutation, and return ownership.
- `DictySimulator/dicty_sim_test_env.py:453–681`: slug construction and deletion, fate processing, developmental measurements, partner selection, all sexual branches, fitness, and offspring construction.
- All of `DictySimulator/locus.py` and `DictySimulator/locus_tracker.py`.

Also checked the pertinent RNG, comparison, ordering, identity, coverage-map, and easily-missed-behavior claims in `specs/06-compatibility-and-verification.md`. Read the measurement rules in specification 04 to verify the references delegated there, the main-loop phase calls at source lines 757–786, and the external `cell.py` class used as a comparison in STATE-001.

The review included each deterministic example in specifications 02 and 03, the exhaustive binary genotype table, the separate nonbinary branch rules, short-target accesses, source versus returned-list ownership, mutation and germination boundaries, XOR target ownership, identity-based genome comparison, parent-list versus temporary-locus aliases, random API call ordering, and partial state on failure.

SHA-256 comparisons confirmed that the three primary original files match their copies in `reference-source`. The original engine hash was `7638ecf8f59ee28a56a6ea288025d75529437b99b188757b6b52f2855f9c7d3a`.

## Independent executable evidence

Ran two fresh in-memory probe programs using Python 3.12.14 and NumPy 2.3.5. These compiled the unchanged class and function AST bodies directly from the original `DictySimulator` files. They did not run the existing verification suite, rewrite the simulation, import its GUI startup, or write simulation results. Scripted RNG APIs exercised exact control-flow paths; assertions checked observable results and call order.

All probes passed:

- All 64 one-locus binary actor/target/epistasis cases and all 1,024 two-locus binary cases matched the listed branch table and its multilocus OR rule.
- Ninety-six nonbinary switch cases, including NaN switch fallthrough, produced no exploitation. Short target lists were accessed only on executed branches; a prior success avoided a later missing target locus. The `(2,0)` sum-equals-two `both()` case also matched.
- The sequential initialization example produced three cheater-only cells, one both-allele cell, two resistor-only cells, and four wild cells, with the stated measurements. Negative gene-pair counts returned empty-locus cells with signed-zero fractions; zero gene pairs failed after appending the initial tracker snapshot.
- Vegetative growth used the literal fitness expression, consumed germination then selection then mutation calls in order, constructed all new cell keys before the first mutation, retained stale copied fitness after mutation, and kept parent and sibling loci independent. Exact zero mutation draws and germination threshold equality behaved as specified. A zero-generation call returned the same input list, including after deletion of its last cell.
- Development reproduced the repeated-index example, removing the original index-zero and then the cell shifted into that position. All prestalk draws preceded the target draw. Returned cells were clones, while source-list removal remained visible. Empty candidate failure occurred after source cells had been removed. A non-discrete passive call retained the whole slug without fate draws.
- Sexual probes covered distinct but equal-valued genomes, shared-identity genomes, intact-parent inheritance, independent within-locus assortment, and equality at the recombination threshold. All returned clones were independent. A configured zero gene-pair count still allowed a nonempty inherited parental genome in the branches that replace the temporary list, consistent with the documented actual-list assignments.
- Zero founders returned an empty result without allocating a temporary cell. A negative germination count still performed selection and genotype generation and consumed the temporary cell key.
- Two successive recombining founders preserved the first pair's offspring while overwriting the shared temporary loci for the second pair. The working partner pool depleted in the documented order, the caller's original list remained intact, and returned keys `[5,6,8,9]` showed the two omitted temporary-cell keys.

## Limits

This review establishes agreement between the inspected source and these specifications for the stated scope; it is not a proof for every possible Python object, malformed configuration, or external mutation. The executable probes used ordinary numeric allele records and selected invalid inputs. They did not exhaustively enumerate nonbinary allele combinations or all malformed types.

The checks do not establish historical seed replay, internal RNG bit consumption, another Python/NumPy version's set or sampling behavior, GUI rendering, SciPy numerical results, full orchestration/output behavior, the other 76 captured files, or compatibility with a Rust implementation. The three-file snapshot comparisons are not an independent audit of the entire manifest. No source or specification file was modified, and no branch or commit was created.
