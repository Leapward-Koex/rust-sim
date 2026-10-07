# Implementation compatibility coverage

All 115 numbered baseline requirements are classified below. This is a traceability map, not a claim of exhaustive test coverage. The actual pass/fail evidence is in `results.json`, `differential-results.json`, engine tests, UI/process tests, and reviewer reports. A listed source-review item must be checked during independent review; it is not automatically proven by a passing nearby fixture.

Original-checker evidence establishes Python behavior only. Differential fixtures compare that behavior to Rust. Error fixtures require a reported nonzero failure but do not require identical exception wording or internal mutation timing. The implementation plan explicitly excludes arbitrary externally aliased Python objects and changes UI/runtime mechanics.

| Requirement | Verification | Evidence | Approved boundary / remaining review |
| --- | --- | --- | --- |
| SCOPE-001 | Reference integrity | Original checker: snapshots_match; fixtures source/checker SHA-256 | The active inline Cell is the authority; snapshots stay unchanged. |
| SCOPE-002 | Reference integrity | Original checker: snapshots_match; fixtures source/checker SHA-256 | The active inline Cell is the authority; snapshots stay unchanged. |
| SCOPE-003 | Differential | All phase and full_* fixtures | Exact scripted choices; no scientific corrections. |
| SCOPE-004 | Differential + boundary | Named *_error fixtures; full_lazy_* successes versus full_active_* failures; init_boolean_numeric_switches | Arbitrary injected Python objects, mutation-after-exception observations, and unlimited integer sizes are outside the config-driven API. |
| SCOPE-005 | Excluded by plan | Original specification/source review | Legacy engine and separately imported cell.py are captured but not ported. |
| SCOPE-006 | Differential | All phase and full_* fixtures | Exact scripted choices; no scientific corrections. |
| SCOPE-007 | Source review | Population model and fixture cell schema | No spatial model, geometry, diffusion, lineage, or new biological processes. |
| SCOPE-008 | Adapted by plan | Differential script counts and semantic candidate identities; seeded worker-invariance tests | ChaCha streams intentionally differ from Python/NumPy seeded trajectories. |
| SCOPE-009 | Adapted by plan | Implementation plan and runtime/interface checks | Seeds, isolated repeat execution, parallelism, typed errors, process/UI improvements are explicit additions. |
| CONFIG-001 | Differential + interface | All fixtures preserve full parameters; full_json_* private-marker/overflow extras; full_lazy_* phase-access cases; CLI/GUI config tests | CLI dictionary replacement retained; GUI defaults normalize schedule to [0]. |
| CONFIG-002 | Differential + boundary | Named *_error fixtures; full_lazy_* successes versus full_active_* failures; init_boolean_numeric_switches | Arbitrary injected Python objects, mutation-after-exception observations, and unlimited integer sizes are outside the config-driven API. |
| RUN-001 | Differential + interface | All fixtures preserve full parameters; full_json_* private-marker/overflow extras; full_lazy_* phase-access cases; CLI/GUI config tests | CLI dictionary replacement retained; GUI defaults normalize schedule to [0]. |
| RUN-002 | Differential | full_balanced_interval_sex; full_balanced_explicit_sex; full_empty_schedule_*; original interval_orchestration/list_orchestration |  |
| RUN-003 | Adapted + differential | full_* repeat results; original stale_measurements_at_main_entry/failed_run_contaminates_next_run | Fresh processes remove stale globals; independent repeat RNG streams replace persistent module RNG state. |
| RUN-004 | Excluded by plan | Original .vscode/launch.json source review | Old launcher starts legacy Python; new documented launcher starts the Rust-backed UI. |
| UI-001 | Adapted by plan | GUI/process tests and manual packaged smoke test | Responsive progress, import/save, cancellation, error dialogs and tooltips replace broken legacy handling. |
| UI-002 | Adapted by plan | GUI/process tests and manual packaged smoke test | Responsive progress, import/save, cancellation, error dialogs and tooltips replace broken legacy handling. |
| CONFIG-003 | Differential + boundary | Named *_error fixtures; full_lazy_* successes versus full_active_* failures; init_boolean_numeric_switches | Arbitrary injected Python objects, mutation-after-exception observations, and unlimited integer sizes are outside the config-driven API. |
| STATE-001 | Reference integrity | Original environment() compiles captured inline Cell AST |  |
| STATE-002 | Differential + boundary | Ordered normalized population comparison in all phase fixtures; original clone_identity | Production-reachable binary loci retained; external object aliases/cross-run Cell IDs are not public interfaces. |
| STATE-003 | Differential + boundary | Ordered normalized population comparison in all phase fixtures; original clone_identity | Production-reachable binary loci retained; external object aliases/cross-run Cell IDs are not public interfaces. |
| STATE-004 | Differential | growth_order_and_stale_fitness; sex_recombination_*; full_*; original clone_identity | Returned genotype rows are independent; identity affects branch outcomes, not displayed IDs. |
| STATE-005 | Differential | dev_four_genotype_measurement; dev_fractional_effectiveness; init_fractional_epistasis; full_* | Only binary alleles reachable from JSON-configured simulation are part of Rust cell storage. |
| STATE-006 | Differential | dev_four_genotype_measurement; dev_fractional_effectiveness; init_fractional_epistasis; full_* | Only binary alleles reachable from JSON-configured simulation are part of Rust cell storage. |
| STATE-007 | Differential | 64 exploit_* binary one-locus cases; four exploit_fractional_* cases; original exploitability_truth_table | Arbitrary nonbinary manually injected locus values are excluded. |
| STATE-008 | Differential | 64 exploit_* binary one-locus cases; four exploit_fractional_* cases; original exploitability_truth_table | Arbitrary nonbinary manually injected locus values are excluded. |
| STATE-009 | Differential | dev_four_genotype_measurement; dev_fractional_effectiveness; init_fractional_epistasis; full_* | Only binary alleles reachable from JSON-configured simulation are part of Rust cell storage. |
| STATE-010 | Differential | dev_four_genotype_measurement; dev_fractional_effectiveness; init_fractional_epistasis; full_* | Only binary alleles reachable from JSON-configured simulation are part of Rust cell storage. |
| INIT-001 | Differential | init_* populations, initial measurements and weighted-call counts |  |
| INIT-002 | Differential | init_* populations, initial measurements and weighted-call counts |  |
| INIT-003 | Differential | init_ties_even_and_whole_genome; init_fractional_epistasis |  |
| INIT-004 | Differential | init_sequential_overlap; original init_exclusive_overlap |  |
| INIT-005 | Differential | init_ties_even_and_whole_genome; init_fractional_epistasis |  |
| INIT-006 | Differential | init_* measurement values/locus counts; full_* time zero |  |
| INIT-007 | Differential | init_* measurement values/locus counts; full_* time zero |  |
| INIT-008 | Differential | init_* measurement values/locus counts; full_* time zero |  |
| INIT-009 | Differential | init_sequential_overlap; original init_exclusive_overlap |  |
| INIT-010 | Differential + boundary | init_zero_population_error; init_zero_loci_error; init_negative_loci; init_oversample_error | Errors are structured; partial internal mutation before failure is not public state. |
| VEG-001 | Differential | growth_germination_equal/above; growth_zero_penalty_still_draws | Caller-owned Python-list identity is excluded; output ordering and draws are retained. |
| VEG-002 | Differential | growth_germination_equal/above; growth_zero_penalty_still_draws | Caller-owned Python-list identity is excluded; output ordering and draws are retained. |
| VEG-003 | Differential | growth_germination_equal/above; growth_zero_penalty_still_draws | Caller-owned Python-list identity is excluded; output ordering and draws are retained. |
| VEG-004 | Differential + sampler tests | growth_raw_fitness; growth_negative_weights; real Rust cumulative-weight sampler unit tests | Fixture weighted calls prescribe indices; they do not by themselves validate the real sampler. |
| VEG-005 | Differential + sampler tests | growth_raw_fitness; growth_negative_weights; real Rust cumulative-weight sampler unit tests | Fixture weighted calls prescribe indices; they do not by themselves validate the real sampler. |
| VEG-006 | Differential | growth_inclusive_zero_mutation; growth_order_and_stale_fitness; full_* and consumed counts |  |
| VEG-007 | Differential | growth_inclusive_zero_mutation; growth_order_and_stale_fitness; full_* and consumed counts |  |
| VEG-008 | Differential | growth_inclusive_zero_mutation; growth_order_and_stale_fitness; full_* and consumed counts |  |
| VEG-009 | Differential | growth_inclusive_zero_mutation; growth_order_and_stale_fitness; full_* and consumed counts |  |
| VEG-010 | Differential + source review | growth_negative_weights; spontaneous full_* source failures; real Rust weight-error tests | No clamping or reinitialization; failure text/partial object mutation not byte-compatible. |
| VEG-011 | Differential | growth_inclusive_zero_mutation; growth_order_and_stale_fitness; full_* and consumed counts |  |
| STATE-011 | Adapted by plan | Differential script counts and semantic candidate identities; seeded worker-invariance tests | ChaCha streams intentionally differ from Python/NumPy seeded trajectories. |
| STATE-012 | Differential | Named rounding/boundary/fitness/identity/XOR fixtures; all script-consumption comparisons |  |
| DEV-001 | Differential | dev_order_leftovers; full_*; original slug_leftovers_and_aliasing |  |
| DEV-002 | Differential | dev_order_leftovers; full_*; original slug_leftovers_and_aliasing |  |
| DEV-003 | Differential | dev_nondiscrete_keeps_all; dev_unsupported_error |  |
| DEV-004 | Differential | dev_prestalk_strict_boundary; all dev/exploit consumed counts |  |
| DEV-005 | Differential + adaptation | dev_duplicate_stalk_xor; full_*; RNG trace candidate_cells | Sort candidates ascending; replay chooses the same target identity in source set order. |
| DEV-006 | Differential + adaptation | dev_duplicate_stalk_xor; full_*; RNG trace candidate_cells | Sort candidates ascending; replay chooses the same target identity in source set order. |
| DEV-007 | Differential | exploit_* binary/fractional fixtures |  |
| DEV-008 | Differential | dev_four_genotype_measurement; dev_fractional_effectiveness; dev_duplicate_stalk_xor |  |
| DEV-009 | Differential | dev_empty_candidate_error; dev_all_stalk_error; dev_unsupported_error; full_* natural failures |  |
| DEV-010 | Differential | dev_four_genotype_measurement; dev_fractional_effectiveness; dev_duplicate_stalk_xor |  |
| SEX-001 | Differential | sex_founders_excluded_and_partners_removed; full_balanced_*_sex |  |
| SEX-002 | Differential | sex_founders_excluded_and_partners_removed; full_balanced_*_sex |  |
| SEX-003 | Differential + boundary | sex_equal_values_distinct_identity; original sex_shared_loci_identity_branch | Shared manually injected locus objects are excluded; equal-valued independent parents still consume recombination draws. |
| SEX-004 | Differential | sex_recombination_0/1; sex_gate_equality_recombines; full_balanced_*_sex |  |
| SEX-005 | Differential | sex_recombination_0/1; sex_gate_equality_recombines; full_balanced_*_sex |  |
| SEX-006 | Differential | sex_recombination_0/1; sex_gate_equality_recombines; full_balanced_*_sex |  |
| SEX-007 | Differential | sex_founders_excluded_and_partners_removed; sex_recombination_*; original sex_alleles_independent_and_clones |  |
| SEX-008 | Differential | sex_founders_excluded_and_partners_removed; sex_recombination_*; original sex_alleles_independent_and_clones |  |
| SEX-009 | Differential | sex_missing_partner_error; sex_zero_macrocysts; sex_zero_germinations |  |
| SEX-010 | Differential | sex_recombination_0/1; sex_gate_equality_recombines; full_balanced_*_sex |  |
| MEASURE-001 | Differential | dev_four_genotype_measurement; dev_fractional_effectiveness; all init/full measurements |  |
| MEASURE-002 | Differential | dev_four_genotype_measurement; dev_fractional_effectiveness; all init/full measurements |  |
| MEASURE-003 | Differential | dev_four_genotype_measurement; dev_fractional_effectiveness; all init/full measurements |  |
| MEASURE-004 | Differential | dev_four_genotype_measurement; dev_fractional_effectiveness; all init/full measurements |  |
| MEASURE-005 | Differential | dev_four_genotype_measurement; dev_fractional_effectiveness; all init/full measurements |  |
| MEASURE-006 | Adapted boundary | Original empty_init_errors; dev_all_stalk_error | Snapshot values preserved; internal partial histories after failure are not exposed by isolated Rust runs. |
| MEASURE-007 | Differential | dev_four_genotype_measurement; dev_fractional_effectiveness; all init/full measurements |  |
| AGG-001 | Differential | All successful full_* results against actual Python main and real SciPy | Floating accumulation compared within declared tolerances; discrete states exact. |
| AGG-002 | Adapted + differential | full_* repeat results; original stale_measurements_at_main_entry/failed_run_contaminates_next_run | Fresh processes remove stale globals; independent repeat RNG streams replace persistent module RNG state. |
| AGG-003 | Differential | All successful full_* results against actual Python main and real SciPy | Floating accumulation compared within declared tolerances; discrete states exact. |
| AGG-004 | Differential | confidence_real_scipy; full_one_repeat_nan; full_no_sex_* with confidence_interval=.1; full_zero_repeats_error |  |
| AGG-005 | Differential | confidence_real_scipy; full_one_repeat_nan; full_no_sex_* with confidence_interval=.1; full_zero_repeats_error |  |
| AGG-006 | Differential | confidence_real_scipy; full_one_repeat_nan; full_no_sex_* with confidence_interval=.1; full_zero_repeats_error |  |
| AGG-007 | Differential | All successful full_* results against actual Python main and real SciPy | Floating accumulation compared within declared tolerances; discrete states exact. |
| OUTPUT-001 | Interface verification | Original interval_orchestration suffix capture; CLI export/suppression tests | Exact --result transport path and atomic/recoverable GUI exports are deliberate additions. |
| OUTPUT-002 | Differential + interface | All successful full_* 21-key results; full_balanced_interval/explicit_sex; full_one_repeat_nan; full_json_* objects/escaped-marker/1e309 | Run metadata lives outside legacy result; JSON whitespace need not match byte-for-byte. |
| OUTPUT-003 | Differential + interface | All successful full_* 21-key results; full_balanced_interval/explicit_sex; full_one_repeat_nan; full_json_* objects/escaped-marker/1e309 | Run metadata lives outside legacy result; JSON whitespace need not match byte-for-byte. |
| OUTPUT-004 | Differential + interface | All successful full_* 21-key results; full_balanced_interval/explicit_sex; full_one_repeat_nan; full_json_* objects/escaped-marker/1e309 | Run metadata lives outside legacy result; JSON whitespace need not match byte-for-byte. |
| OUTPUT-005 | Differential + interface | All successful full_* 21-key results; full_balanced_interval/explicit_sex; full_one_repeat_nan; full_json_* objects/escaped-marker/1e309 | Run metadata lives outside legacy result; JSON whitespace need not match byte-for-byte. |
| DISPLAY-001 | Adapted by plan | GUI/process tests and manual packaged smoke test | Responsive progress, import/save, cancellation, error dialogs and tooltips replace broken legacy handling. |
| DISPLAY-002 | Adapted by plan | GUI/process tests and manual packaged smoke test | Responsive progress, import/save, cancellation, error dialogs and tooltips replace broken legacy handling. |
| DISPLAY-003 | UI verification | Matplotlib artist assertions and packaged graph smoke test | Retain styling/duplicate marker data; empty schedule renders without markers. |
| DISPLAY-004 | UI verification | Matplotlib artist assertions and packaged graph smoke test | Retain styling/duplicate marker data; empty schedule renders without markers. |
| LEGACY-001 | Excluded by plan | Original specification/source review | Legacy engine and separately imported cell.py are captured but not ported. |
| LEGACY-002 | Excluded by plan | Original specification/source review | Legacy engine and separately imported cell.py are captured but not ported. |
| TOOL-001 | Excluded by plan | Original supporting-tool specifications/source review | Standalone legacy plot/batch/demo scripts are not rebuilt; legacy result schema is retained for their consumers. |
| TOOL-002 | Excluded by plan | Original supporting-tool specifications/source review | Standalone legacy plot/batch/demo scripts are not rebuilt; legacy result schema is retained for their consumers. |
| TOOL-003 | Excluded by plan | Original supporting-tool specifications/source review | Standalone legacy plot/batch/demo scripts are not rebuilt; legacy result schema is retained for their consumers. |
| TOOL-004 | Excluded by plan | Original supporting-tool specifications/source review | Standalone legacy plot/batch/demo scripts are not rebuilt; legacy result schema is retained for their consumers. |
| TOOL-005 | Excluded by plan | Original supporting-tool specifications/source review | Standalone legacy plot/batch/demo scripts are not rebuilt; legacy result schema is retained for their consumers. |
| TOOL-006 | Excluded by plan | Original supporting-tool specifications/source review | Standalone legacy plot/batch/demo scripts are not rebuilt; legacy result schema is retained for their consumers. |
| TOOL-007 | Excluded by plan | Original supporting-tool specifications/source review | Standalone legacy plot/batch/demo scripts are not rebuilt; legacy result schema is retained for their consumers. |
| TOOL-008 | Environment evidence | reference-requirements.lock; fixtures Python/NumPy/SciPy versions; benchmark report | Historical unspecified Python/Tcl versions cannot be reconstructed. |
| COMPAT-001 | Differential | Named rounding/boundary/fitness/identity/XOR fixtures; all script-consumption comparisons |  |
| COMPAT-002 | Adapted by plan | Differential script counts and semantic candidate identities; seeded worker-invariance tests | ChaCha streams intentionally differ from Python/NumPy seeded trajectories. |
| COMPAT-003 | Differential + adaptation | Separated Python-family channels and NumPy integers; production RNG stream unit tests | New master seed and per-repeat stream derivation are deliberate differences. |
| COMPAT-004 | Differential | Named rounding/boundary/fitness/identity/XOR fixtures; all script-consumption comparisons |  |
| COMPAT-005 | Differential + boundary | init_ties_even_and_whole_genome; boolean switches; identity/XOR fixtures | Fixed storage limits fail explicitly; arbitrary direct Python aliases/nonbinary loci excluded. |
| COMPAT-006 | Environment evidence | reference-requirements.lock; fixtures Python/NumPy/SciPy versions; benchmark report | Historical unspecified Python/Tcl versions cannot be reconstructed. |
| VERIFY-001 | Verification evolution | Unchanged check_source_behavior.py retained; 31 results; new differential.py and real SciPy fixtures | Original verification limitations describe the earlier report. New checks supplement rather than rewrite that record. |
| VERIFY-002 | Verification evolution | Unchanged check_source_behavior.py retained; 31 results; new differential.py and real SciPy fixtures | Original verification limitations describe the earlier report. New checks supplement rather than rewrite that record. |
| VERIFY-003 | Verification evolution | Unchanged check_source_behavior.py retained; 31 results; new differential.py and real SciPy fixtures | Original verification limitations describe the earlier report. New checks supplement rather than rewrite that record. |
| VERIFY-004 | Verification evolution | Unchanged check_source_behavior.py retained; 31 results; new differential.py and real SciPy fixtures | Original verification limitations describe the earlier report. New checks supplement rather than rewrite that record. |
| VERIFY-005 | Verification evolution | Unchanged check_source_behavior.py retained; 31 results; new differential.py and real SciPy fixtures | Original verification limitations describe the earlier report. New checks supplement rather than rewrite that record. |
