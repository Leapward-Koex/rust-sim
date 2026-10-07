"""Generate an explicit requirement-to-evidence map; fail on unclassified IDs."""
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def entries():
    rows = {}

    def put(ids, kind, evidence, boundary=""):
        for name in ids.split():
            assert name not in rows, name
            rows[name] = (kind, evidence, boundary)

    def numbered(prefix, start, stop):
        return " ".join(f"{prefix}-{n:03d}" for n in range(start, stop + 1))

    put("SCOPE-001 SCOPE-002", "Reference integrity", "Original checker: snapshots_match; fixtures source/checker SHA-256", "The active inline Cell is the authority; snapshots stay unchanged.")
    put("SCOPE-003 SCOPE-006", "Differential", "All phase and full_* fixtures", "Exact scripted choices; no scientific corrections.")
    put("SCOPE-004 CONFIG-002 CONFIG-003", "Differential + boundary", "Named *_error fixtures; full_lazy_* successes versus full_active_* failures; init_boolean_numeric_switches", "Arbitrary injected Python objects, mutation-after-exception observations, and unlimited integer sizes are outside the config-driven API.")
    put("SCOPE-005 LEGACY-001 LEGACY-002", "Excluded by plan", "Original specification/source review", "Legacy engine and separately imported cell.py are captured but not ported.")
    put("SCOPE-007", "Source review", "Population model and fixture cell schema", "No spatial model, geometry, diffusion, lineage, or new biological processes.")
    put("SCOPE-008 STATE-011 COMPAT-002", "Adapted by plan", "Differential script counts and semantic candidate identities; seeded worker-invariance tests", "ChaCha streams intentionally differ from Python/NumPy seeded trajectories.")
    put("SCOPE-009", "Adapted by plan", "Implementation plan and runtime/interface checks", "Seeds, isolated repeat execution, parallelism, typed errors, process/UI improvements are explicit additions.")
    put("CONFIG-001 RUN-001", "Differential + interface", "All fixtures preserve full parameters; full_json_* private-marker/overflow extras; full_lazy_* phase-access cases; CLI/GUI config tests", "CLI dictionary replacement retained; GUI defaults normalize schedule to [0].")
    put("RUN-002", "Differential", "full_balanced_interval_sex; full_balanced_explicit_sex; full_empty_schedule_*; original interval_orchestration/list_orchestration")
    put("RUN-003 AGG-002", "Adapted + differential", "full_* repeat results; original stale_measurements_at_main_entry/failed_run_contaminates_next_run", "Fresh processes remove stale globals; independent repeat RNG streams replace persistent module RNG state.")
    put("RUN-004", "Excluded by plan", "Original .vscode/launch.json source review", "Old launcher starts legacy Python; new documented launcher starts the Rust-backed UI.")
    put("UI-001 UI-002 DISPLAY-001 DISPLAY-002", "Adapted by plan", "GUI/process tests and manual packaged smoke test", "Responsive progress, import/save, cancellation, error dialogs and tooltips replace broken legacy handling.")
    put("DISPLAY-003 DISPLAY-004", "UI verification", "Matplotlib artist assertions and packaged graph smoke test", "Retain styling/duplicate marker data; empty schedule renders without markers.")

    put("STATE-001", "Reference integrity", "Original environment() compiles captured inline Cell AST")
    put("STATE-002 STATE-003", "Differential + boundary", "Ordered normalized population comparison in all phase fixtures; original clone_identity", "Production-reachable binary loci retained; external object aliases/cross-run Cell IDs are not public interfaces.")
    put("STATE-004", "Differential", "growth_order_and_stale_fitness; sex_recombination_*; full_*; original clone_identity", "Returned genotype rows are independent; identity affects branch outcomes, not displayed IDs.")
    put("STATE-005 STATE-006 STATE-009 STATE-010", "Differential", "dev_four_genotype_measurement; dev_fractional_effectiveness; init_fractional_epistasis; full_*", "Only binary alleles reachable from JSON-configured simulation are part of Rust cell storage.")
    put("STATE-007 STATE-008", "Differential", "64 exploit_* binary one-locus cases; four exploit_fractional_* cases; original exploitability_truth_table", "Arbitrary nonbinary manually injected locus values are excluded.")
    put("STATE-012 COMPAT-001 COMPAT-004", "Differential", "Named rounding/boundary/fitness/identity/XOR fixtures; all script-consumption comparisons")
    put("INIT-001 INIT-002", "Differential", "init_* populations, initial measurements and weighted-call counts")
    put("INIT-003 INIT-005", "Differential", "init_ties_even_and_whole_genome; init_fractional_epistasis")
    put("INIT-004 INIT-009", "Differential", "init_sequential_overlap; original init_exclusive_overlap")
    put("INIT-006 INIT-007 INIT-008", "Differential", "init_* measurement values/locus counts; full_* time zero")
    put("INIT-010", "Differential + boundary", "init_zero_population_error; init_zero_loci_error; init_negative_loci; init_oversample_error", "Errors are structured; partial internal mutation before failure is not public state.")
    put("VEG-001 VEG-002 VEG-003", "Differential", "growth_germination_equal/above; growth_zero_penalty_still_draws", "Caller-owned Python-list identity is excluded; output ordering and draws are retained.")
    put("VEG-004 VEG-005", "Differential + sampler tests", "growth_raw_fitness; growth_negative_weights; real Rust cumulative-weight sampler unit tests", "Fixture weighted calls prescribe indices; they do not by themselves validate the real sampler.")
    put("VEG-006 VEG-007 VEG-008 VEG-009 VEG-011", "Differential", "growth_inclusive_zero_mutation; growth_order_and_stale_fitness; full_* and consumed counts")
    put("VEG-010", "Differential + source review", "growth_negative_weights; spontaneous full_* source failures; real Rust weight-error tests", "No clamping or reinitialization; failure text/partial object mutation not byte-compatible.")
    put("DEV-001 DEV-002", "Differential", "dev_order_leftovers; full_*; original slug_leftovers_and_aliasing")
    put("DEV-003", "Differential", "dev_nondiscrete_keeps_all; dev_unsupported_error")
    put("DEV-004", "Differential", "dev_prestalk_strict_boundary; all dev/exploit consumed counts")
    put("DEV-005 DEV-006", "Differential + adaptation", "dev_duplicate_stalk_xor; full_*; RNG trace candidate_cells", "Sort candidates ascending; replay chooses the same target identity in source set order.")
    put("DEV-007", "Differential", "exploit_* binary/fractional fixtures")
    put("DEV-008 DEV-010", "Differential", "dev_four_genotype_measurement; dev_fractional_effectiveness; dev_duplicate_stalk_xor")
    put("DEV-009", "Differential", "dev_empty_candidate_error; dev_all_stalk_error; dev_unsupported_error; full_* natural failures")
    put("SEX-001 SEX-002", "Differential", "sex_founders_excluded_and_partners_removed; full_balanced_*_sex")
    put("SEX-003", "Differential + boundary", "sex_equal_values_distinct_identity; original sex_shared_loci_identity_branch", "Shared manually injected locus objects are excluded; equal-valued independent parents still consume recombination draws.")
    put("SEX-004 SEX-005 SEX-006 SEX-010", "Differential", "sex_recombination_0/1; sex_gate_equality_recombines; full_balanced_*_sex")
    put("SEX-007 SEX-008", "Differential", "sex_founders_excluded_and_partners_removed; sex_recombination_*; original sex_alleles_independent_and_clones")
    put("SEX-009", "Differential", "sex_missing_partner_error; sex_zero_macrocysts; sex_zero_germinations")

    put(numbered("MEASURE", 1, 5) + " MEASURE-007", "Differential", "dev_four_genotype_measurement; dev_fractional_effectiveness; all init/full measurements")
    put("MEASURE-006", "Adapted boundary", "Original empty_init_errors; dev_all_stalk_error", "Snapshot values preserved; internal partial histories after failure are not exposed by isolated Rust runs.")
    put("AGG-001 AGG-003 AGG-007", "Differential", "All successful full_* results against actual Python main and real SciPy", "Floating accumulation compared within declared tolerances; discrete states exact.")
    put("AGG-004 AGG-005 AGG-006", "Differential", "confidence_real_scipy; full_one_repeat_nan; full_no_sex_* with confidence_interval=.1; full_zero_repeats_error")
    put("OUTPUT-001", "Interface verification", "Original interval_orchestration suffix capture; CLI export/suppression tests", "Exact --result transport path and atomic/recoverable GUI exports are deliberate additions.")
    put("OUTPUT-002 OUTPUT-003 OUTPUT-004 OUTPUT-005", "Differential + interface", "All successful full_* 21-key results; full_balanced_interval/explicit_sex; full_one_repeat_nan; full_json_* objects/escaped-marker/1e309", "Run metadata lives outside legacy result; JSON whitespace need not match byte-for-byte.")
    put(numbered("TOOL", 1, 7), "Excluded by plan", "Original supporting-tool specifications/source review", "Standalone legacy plot/batch/demo scripts are not rebuilt; legacy result schema is retained for their consumers.")
    put("TOOL-008 COMPAT-006", "Environment evidence", "reference-requirements.lock; fixtures Python/NumPy/SciPy versions; benchmark report", "Historical unspecified Python/Tcl versions cannot be reconstructed.")
    put("COMPAT-003", "Differential + adaptation", "Separated Python-family channels and NumPy integers; production RNG stream unit tests", "New master seed and per-repeat stream derivation are deliberate differences.")
    put("COMPAT-005", "Differential + boundary", "init_ties_even_and_whole_genome; boolean switches; identity/XOR fixtures", "Fixed storage limits fail explicitly; arbitrary direct Python aliases/nonbinary loci excluded.")
    put(numbered("VERIFY", 1, 5), "Verification evolution", "Unchanged check_source_behavior.py retained; 31 results; new differential.py and real SciPy fixtures", "Original verification limitations describe the earlier report. New checks supplement rather than rewrite that record.")
    return rows


def main():
    mapping = entries()
    found = []
    for path in sorted((ROOT / "specs").glob("*.md")):
        for match in re.finditer(r"^(?:#{2,3} |\*\*)([A-Z]+-\d{3})", path.read_text(encoding="utf-8"), re.M):
            found.append((match.group(1), path.name))
    names = {name for name, _ in found}
    assert len(found) == len(names) == 115, (len(found), len(names))
    assert names == set(mapping), {"unmapped": sorted(names - mapping.keys()), "unknown": sorted(mapping.keys() - names)}
    rows = [{"requirement": name, "specification": file, "verification_kind": mapping[name][0],
             "evidence": mapping[name][1], "boundary": mapping[name][2]} for name, file in found]
    (HERE / "coverage-map.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    lines = ["# Implementation compatibility coverage", "", "All 115 numbered baseline requirements are classified below. This is a traceability map, not a claim of exhaustive test coverage. The actual pass/fail evidence is in `results.json`, `differential-results.json`, engine tests, UI/process tests, and reviewer reports. A listed source-review item must be checked during independent review; it is not automatically proven by a passing nearby fixture.", "", "Original-checker evidence establishes Python behavior only. Differential fixtures compare that behavior to Rust. Error fixtures require a reported nonzero failure but do not require identical exception wording or internal mutation timing. The implementation plan explicitly excludes arbitrary externally aliased Python objects and changes UI/runtime mechanics.", "", "| Requirement | Verification | Evidence | Approved boundary / remaining review |", "| --- | --- | --- | --- |"]
    for row in rows:
        lines.append("| " + " | ".join(row[key] for key in ("requirement", "verification_kind", "evidence", "boundary")) + " |")
    (HERE / "COVERAGE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Mapped all {len(rows)} requirements to explicit evidence or scope boundaries.")


if __name__ == "__main__":
    main()
