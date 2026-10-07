# Independent second review: measurements, output, and verification

Reviewed 7 October 2026. This is a fresh source review of `specs/04-measurements-and-output.md`, `specs/06-compatibility-and-verification.md`, `README.md`, and `verification/check_source_behavior.py`. The authoritative evidence was the active implementation in `../DictySimulator/dicty_sim_test_env.py` and its actual state/default modules, not an earlier review. `specs/00-scope-and-source-authority.md` was also read to assess the authority and portability framing.

## Result

No incorrect core measurement formula, output schema, repeat-aggregation rule, or definition-time confidence-default description was found. One small claim about the retained verification assertions should be tightened or backed by an additional assertion. It does not indicate a defect in the described simulation behavior.

### R2-OUTPUT-1 — Low: “exact SciPy call arguments” is broader than the assertions

`VERIFY-002` at `specs/06-compatibility-and-verification.md:65` says the executable checks cover “exact SciPy call arguments”; `VERIFY-004` at line 77 similarly says the spies verify the confidence function's arguments. However, `confidence_bound_default` at `verification/check_source_behavior.py:286–292` asserts only the final `ppf` call's quantile and degrees of freedom, plus the first multiplication result. `StatsSpy.sem` records its received array at lines 41–43 but returns the same value for every array; no retained assertion checks that recorded input. A wrong array passed to `sem` could therefore escape this check.

Suggested correction: assert the complete call list after each call, for example `[('sem', [2.0, 4.0, 6.0]), ('ppf', .975, 2)]` for the omitted-confidence case and the corresponding appended `('sem', ...)`, `('ppf', .9, 2)` pair for the explicit `.8` case. Alternatively, narrow the wording to “the `t.ppf` arguments, multiplication, and definition-time confidence default.” The current source passes the stronger assertions in an independent in-memory probe.

## Source findings confirmed

- Initialization records its locus snapshot before dividing allele counts; development records the snapshot after the divisions. Empty-population failures therefore leave different partial history. There is no rollback.
- Allele-frequency denominators use configured `gene_pairs * population length`. The wild measurement counts zero allele slots, while conditional effectiveness includes carriers with fully suppressed effectiveness. Unknown mating types remain in the denominator.
- Per-locus categories and snapshots match the source. Count outputs remain absolute counts. The one-locus four-genotype example is correct for both zero and unit epistasis settings.
- Repeat aggregation takes equally weighted means of per-repeat observations, including zero conditional-effectiveness means for no-carrier repeats. The source does not clear history on entering `main`.
- Confidence defaults are bound at function definition to `0.95`. Both changing the dictionary and replacing it leave omitted-confidence calls at that value. Explicit confidence arguments are honored. The configured value can still be serialized even when it differs from the bound value.
- The 21 output keys, insertion order, unconditional `.json` suffix, interval-event duplication across repeats, missing explicit-list events, and save-before-plot ordering match the implementation.
- The console templates and plotted labels/colors/limits correspond to the executable statements. The descriptions distinguish library-dependent GUI behavior from executed verification.
- The README and compatibility document distinguish the active source from the legacy engine, scripted transitions from exact RNG replay, and targeted checks from an installed application run. The source and dependency pins do not establish portable exact trajectories or historical run reconstruction.

## Executed evidence

1. Ran the existing check module through `runpy.run_path(..., run_name='review')`, then invoked each registered check without entering its report-writing block: **31 passed, 0 failed**. `verification/results.json` was not rewritten.
2. Independently hashed all 80 manifest-listed captured files against the corresponding files in the original `DictySimulator` directory: **80 matched, 0 mismatches**. The retained snapshot check also passed for all 80. The initial full-suite run covered 79 files; after the launch configuration was added to the capture during this review, the snapshot and original-file comparisons were repeated against the updated manifest. The latest README and compatibility-document changes for that additional capture were also read.
3. Ran four additional in-memory probe groups using the original source directory through the existing AST loader: **4 passed**. These checked dictionary replacement and the complete confidence spy call sequence; configured-versus-actual locus count and unknown mating type/no-carrier measurements; empty development's untouched tracker histories; and the four-genotype example with both epistasis values set to one and all three mating fractions asserted.

The interpreter was the supplied Python 3.12.14 runtime with NumPy 2.3.5. The extra probes were review evidence only and were not added to the retained suite.

## Limits

The review inspected the numerical formula and original calls but did not run SciPy's numerical implementation, Matplotlib rendering, a full GUI session, the original dependency-pinned application, or a Rust implementation. In particular, one-repeat `NaN` confidence behavior remains a documented library-behavior inference rather than an executed SciPy fixture in this environment. The retained documents already disclose these limits appropriately. This is a targeted review, not exhaustive malformed-input enumeration or proof of exact replay across runtimes.

Only this report was written. Source, specifications, checks, and retained results were left unchanged; no commit or branch was created.

## Resolution verification

On 7 October 2026, independently inspected the author's strengthened `confidence_bound_default` check and ran that check through `runpy.run_path(..., run_name='review')`: **passed**. It now asserts the complete `sem` input and `ppf` argument sequence for both omitted and explicit confidence, and asserts the return value for both calls. **R2-OUTPUT-1 is resolved; no findings remain open from this review.** This follow-up did not rewrite `results.json` or modify any file other than this report. The stated SciPy, GUI, and runtime limitations still apply.
