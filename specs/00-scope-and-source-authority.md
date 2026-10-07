# Scope and source authority

## Reference implementation

**SCOPE-001.** The authoritative engine is `dicty_sim_test_env.py`, including its inline `Cell` class. The repository README lines 4–7 names this entry point. Its line 16 comments out the import of the other `Cell` implementation. Active dependencies defining simulation state are `global_variables.py`, `locus.py`, and `locus_tracker.py`. `GUI/tooltip.py` supplies GUI tooltips. All source paths and line numbers in these specifications refer to the captured source under `../reference-source/`, unless expressly identified as another artifact.

**SCOPE-002.** Source baseline: original repository commit `62d707eee5f348320d6e50ab034b18a3a1a45b23`, branch `main`, with a clean working tree at capture. Capture date: 7 October 2026, Pacific/Auckland. `source-manifest.json` records exact file hashes. The commit alone does not prescribe Python, NumPy, SciPy, operating system, or library runtime behavior.

**SCOPE-003.** Executable statements take precedence over comments, tooltips, filenames, and scientific expectations. Statements described here as quirks or apparent bugs are still part of the captured behavior. A future correction must be identified as a deliberate behavioral change; it must not silently replace this reference.

**SCOPE-004.** The specification describes the normal standalone CLI/GUI flow and relevant direct-function behavior. The CLI accepts arbitrary decoded JSON rather than a validated schema, so the configuration tables describe defaults and actual accesses, not newly imposed legal ranges. Examples of exceptional inputs document observed or mechanically derived behavior, not a complete enumeration of all possible malformed Python/JSON values.

**SCOPE-005.** `dicty_sim_v0.6.py` and `cell.py` are preserved for comparison only. Their different algorithms must not fill perceived gaps in the active engine. Supporting plotting and batch scripts are documented separately; saved experiment result files are data, not executable definitions of the model.

The shipped VS Code `Sim` launch configuration instead targets the legacy `dicty_sim_v0.6.py` with a Windows virtual-environment interpreter. Thus “launch the simulation” is not an unambiguous instruction across existing tooling. The baseline above follows the README and batch runner; it is not a claim that every existing launch path selects that baseline. Source: `.vscode/launch.json:5–10`; see RUN-004 and LEGACY-001.

## Biological state represented by the code

**SCOPE-006.** The simulation tracks individual cell records with mating type and an ordered list of loci. Each locus stores a cheater allele and a resistor allele, normally each 0 or 1. A repeat starts with a newly initialized population. Each numbered development cycle optionally performs sexual reproduction first, then vegetative growth, then development into surviving spores. The measured population at cycle zero is the initialized population; subsequent measurements are the surviving fruiting-body populations after development. Sources: `dicty_sim_test_env.py:111–225,256–681,757–786`.

**SCOPE-007.** There is no implemented spatial movement, geometry, environmental field, nutrient diffusion, explicit cannibalized-cell accounting, or lineage output. Coordinates are initialized/copied fields. The simulation does not compute a stalk geometry or a macrocyst object; these processes are represented by cell selection and population replacement. Sources: `dicty_sim_test_env.py:114–139,256–310,453–522,617–681`.

## Required distinction for a faithful remake

**SCOPE-008.** Preserving transition rules and distributions is different from reproducing a particular random trajectory. The original engine uses both Python `random` and NumPy's module-level `np.random` state, without a seed option or recorded state. Python list ordering, set iteration, cell-key equality, locus-object identity comparisons, floating-point evaluation, and library sampling implementations can affect results. Exact random-stream compatibility is not established merely by assigning the same numeric seed in Rust. See [compatibility and verification](06-compatibility-and-verification.md).

**SCOPE-009.** This specification introduces no corrected defaults, input validation, parallel execution, genotype compression, new seed interface, or revised output format as existing requirements. Those are possible future design decisions and must remain separate from the captured behavior.
