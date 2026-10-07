# Specification review record

The source baseline is commit `62d707eee5f348320d6e50ab034b18a3a1a45b23`, captured on 7 October 2026. The user requested repeated checks with fresh reviewers. Authors performed source checks while drafting; independent review rounds use newly created reviewers with no inherited drafting conversation.

## First independent round

Three fresh reviewers received only the task scope and source/document locations, with no inherited drafting conversation.

| Reviewer scope | Report | Resolution |
| --- | --- | --- |
| Configuration, entry points, legacy variant, and tools | [Configuration review](review-round1-config.md) | Corrected locus identity terminology, removed invented elapsed-time output, limited candidate selection to prestalk cheaters, expanded legacy JSON incompatibility, replaced misleading “disjoint” wording, specified tooltip coordinates, and linked the preserved snapshot. |
| State, initialization, growth, development, and sexual reproduction | [Core review](review-round1-core.md) | Qualified negative slug-loop bounds and recombination RNG counts for negative loci or interrupted operations. Ordinary-input transition rules matched source. |
| Measurements, aggregation, output, and verification harness | [Output review](review-round1-output.md) | Added exact legend labels and GUI console spelling; corrected the same elapsed-time contradiction in specification 01. Extended retained checks for partial initialization state, distinct scalar-series wiring, and failed-run history contamination. |

The root author independently reconciled each finding with the source before editing. Follow-up edge checks also cover negative locus/slug bounds and mutation call order with stale stored fitness. The retained suite then passed 31 checks.

## Second independent round

Three additional fresh reviewers independently checked the revised documents against the original source. They did not inherit drafting or first-review conversations.

| Reviewer scope | Report | Resolution |
| --- | --- | --- |
| Configuration, entry points, legacy variant, and tools | [Second configuration review](review-round2-config.md) | Added the shipped VS Code launcher, which selects the excluded legacy model, to the entry-point inventory and source snapshot. Reviewer independently verified all added claims and the copied file hash. |
| State and all biological transitions | [Second core review](review-round2-core.md) | No actionable inaccuracies or substantive omissions found. Independent probes included 64 one-locus and 1,024 two-locus binary exploitability cases, call ordering, boundary behavior, ownership, and successive recombination. |
| Measurements, output, compatibility, and verification claims | [Second output review](review-round2-output.md) | Strengthened the retained confidence check to assert complete `sem` and `ppf` call sequences and both return values. Reviewer independently ran the corrected check and marked the finding resolved. |

No findings remain open from either review round. The reports preserve the findings as originally reported, followed by the resolutions here and, where applicable, in the individual report. Earlier counts of 79 snapshot files and 28/30 checks refer to earlier review states; the delivered snapshot has 80 files and the final retained suite has 31 checks.

## Final verification

- Retained suite: **31 passed, 0 failed**, including the complete 64-case binary one-locus exploitability table and 80 captured-file hash checks.
- Runtime used by the retained suite: Python 3.12.14, NumPy 2.3.5, Windows; exact environment details are in `results.json`.
- Source baseline: all 205 tracked original files match their captured manifest hashes. The original Git repository remains clean at its recorded commit on `main`.
- All local document links resolve, and requirement identifiers are unique.
- No Rust engine, Git repository, branch, or commit was created. The new Python file is verification tooling that executes original source bodies, not a replacement simulator.
- SciPy numerical execution, full Tk/Matplotlib rendering, a full dependency-pinned application run, exhaustive malformed-input behavior, and Rust equivalence were not verified. These limits are stated in the specification and reports.

## Executable evidence

The retained verification script checks source snapshots and selected behaviors by executing original function/class bodies. See [results.json](results.json) and [verification limits](../specs/06-compatibility-and-verification.md). These checks supplement source review and do not prove equivalence of a future Rust engine.
