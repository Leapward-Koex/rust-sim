# Independent second-pass review: configuration, entry points, and supporting tools

Reviewed 7 October 2026 against the original `C:/Dev/Dicty sim/DictySimulator` checkout. This review independently read the current specifications and original sources; it did not use first-pass review reports as evidence. This reviewer changed only this report; no source, specification, branch, or commit was changed by this reviewer.

Reviewed specifications:

- `specs/00-scope-and-source-authority.md`
- `specs/01-configuration-and-entrypoints.md`
- `specs/05-legacy-and-supporting-tools.md`

## Result

No material mismatch found in the active engine's parameter defaults, GUI conversions, CLI loading, scheduling, repeat lifecycle, or the documented helper-script behavior. One low-priority source-authority omission was found and subsequently resolved and independently verified, as recorded below. No findings remain open from this review.

## Finding R2-CONFIG-01 — Document the shipped VS Code launcher selecting the legacy engine (P3)

**Affected specification:** `00-scope-and-source-authority.md`, SCOPE-001/SCOPE-005; `05-legacy-and-supporting-tools.md`, LEGACY-001.

**Original source:** `DictySimulator/.vscode/launch.json:5-10` defines a `Sim` debug configuration whose interpreter is `${workspaceFolder}/venv/Scripts/python.exe` and whose program is `${workspaceFolder}/dicty_sim_v0.6.py`. It supplies no `--param` argument. This differs from the README-directed active entry point (`README.md:4-5`) and the batch runner's target (`directory_run.py:12-14`). The launch file is tracked and hashed by `source-manifest.json`, but has `snapshot: false` and is not present in `reference-source`.

**Why it matters:** The specifications correctly choose `dicty_sim_test_env.py` as their explicit baseline. However, an implementer or verifier using the repository's existing `Sim` debug configuration would run the excluded legacy engine, including its different mutation, development, and output behavior. The currently listed entry-point sources do not expose that divergence.

**Concrete fix:** Add a short note to LEGACY-001 or the source-authority section that the shipped VS Code `Sim` configuration runs the legacy file using the checkout-local Windows `venv` interpreter, and that it must not be mistaken for a launch of the selected baseline. Explicitly cite the original `.vscode/launch.json` because it is not in the snapshot. Alternatively, copy that file byte-for-byte into the snapshot and update only its manifest `snapshot` flag. This is a documentation/source-inventory clarification; it does not require changing either simulator or choosing a different baseline.

## Verified coverage and evidence

| Area | Independent evidence and result |
|---|---|
| Source identity | Original checkout is clean on `main` at `62d707eee5f348320d6e50ab034b18a3a1a45b23`. All 205 tracked paths match the manifest's path set; all 205 original file sizes and SHA-256 hashes match; all 79 copied files match their original hashes; the snapshot contains 79 files. |
| Scope and authority | README directs GUI and CLI users to `dicty_sim_test_env.py`; its external Cell import is commented out. The active implementation imports the local globals, locus, tracker, and tooltip modules. The older executable is correctly excluded rather than blended into the baseline. |
| Parameter defaults | Compared every key, value, representation, and order in `global_variables.py:1-33` and `import_template.json:1-31`. Both contain the same 31 ordered keys. The specification records the string-versus-array schedule, integer-versus-float literal differences, and distinct output basenames correctly. |
| Executed parameter meanings | Checked active reads in `dicty_sim_test_env.py:165-225,256-310,398-522,617-681,734-741,757-904`. Unused `c_ch_res` and `ch_self_cheat`, exact numeric branch comparisons, lack of rounding/validation, growth on every development iteration, and definition-time confidence capture agree with the specification. Detailed transition formulas remain the responsibility of the state/development specifications. |
| CLI | Checked `dicty_sim_test_env.py:1013-1024`: first literal `--param` token, immediate following token, JSON replacement of the whole dictionary, no default merge or conversion, and GUI fallback without that token. Checked progress/plot gating and working-directory-relative output paths at `610-613,858-862,907-934,937-1006`. |
| Scheduling | Independently executed the original cycle-loop AST with phase-recording stubs. `[0]`/interval 0 performs growth then development only; `[0,2]`/interval 3 performs sex at 3; explicit `[2,2,-1,0,20]` performs sex once at 2; interval -2 performs sex at 2 and 4; empty list/interval 0 performs no sex; empty list/nonzero interval raises `IndexError`; string `"0"`/interval 0 raises `TypeError`. Source `762-786` matches RUN-002. |
| Repeat lifecycle | Read `683-904`: local aggregate initialization; single shared interval-event list; sequential repeat loop; initialization sample before cycles; copying into aggregates before resetting all nine global histories; IDs/RNG not reset; progress reset after each repeat; zero/negative count and negative-development control flow. No discrepancy found. |
| GUI conversion and validation | Executed the original `submit_form` and `validate_entry` ASTs using inert entry/progress/main stubs. All 13 integer conversions and remaining float/path/list conversions match UI-001. Empty numeric text, `1.0`, `0.5`, `NaN`, and infinities pass key validation; ordinary invalid text fails. List `"0"` becomes `[0]`; `"1, 5"` becomes `[1,5]`; bracket notation, empty text, and trailing comma raise `ValueError`. Construction, disabled controls, synchronous callback, event re-entry opportunity, seven-row grouping, and tooltip behavior match original `82-108,227-239,1025-1079` and `GUI/tooltip.py`. |
| Legacy boundary | Checked legacy imports, mutation operators and typo, discrete/additive development, unusable obsolete resistance branches, string schedule conversion, and output key structure (`dicty_sim_v0.6.py:16-19,313-323,362-590,919-939,1038-1054`). Independently normalized and compared both `Cell` class ASTs: `cell.py` and the active inline class are identical apart from source locations/comments. The cross-module dictionary-binding trap is correctly described. |
| Batch runner | Read every line of `directory_run.py`: positional directory, hardcoded checkout/interpreter/script, unsorted single-directory case-sensitive `.json` selection, quoted shell command, sequential calls, inherited working directory, and no return-code check all agree with TOOL-001. |
| Plotting helpers | Read all four helper sources, including file-selection order, exact series/CI keys, axes, hardcoded titles, labels, colors, legends, and sexual markers. `grapher.py`'s unplotted type-3 mean with retained CI band, scalar-axis problem for one locus, and count-axis limit are correctly recorded. Four-panel, three-file overlay, and four-file resistance-only workflows agree with TOOL-004 through TOOL-006. |
| Other supporting sources | Read `test.py`, `requirements.txt`, `mac_reqs.txt`, and the original README. The demonstration-only test file and dependency pin/version limitations are accurately characterized. |

## Verification limits

This review did not launch native Tk windows or render Matplotlib figures. GUI and plotting conclusions are based on original executable statements; GUI conversion and scheduling probes executed original AST bodies with inert dependency stubs. The temporary probes ran on the available Python 3.14 interpreter and do not claim historical Python/Tk/NumPy/SciPy runtime reproduction. Neither the simulations nor saved result data were modified.

## Resolution verification

After the finding was reported, the coordinating agent added the launcher distinction after SCOPE-005, added RUN-004 to the entry-point specification, and added the same boundary to LEGACY-001. This reviewer reread all three additions against the original launch file. The configuration name, `debugpy` type, launch request, interpreter, legacy program, integrated-terminal setting, absence of arguments, and resulting GUI branch are accurate. The README-selected active baseline and legacy exclusion remain explicit.

The coordinating agent also captured `reference-source/.vscode/launch.json` and changed its existing manifest entry to `snapshot: true`. This reviewer independently verified that original, snapshot, and manifest all have SHA-256 `440b7050ec46d5b4642cc89988cbc90d6efda12a8cdc4d6192ba04aad1dd7650`, with manifest size 353 bytes. The manifest still contains 205 tracked paths and now identifies 80 snapshot files. The earlier 79-file counts and absence of the launcher in the finding describe the state at initial review, before this addition. **R2-CONFIG-01 is resolved.**
