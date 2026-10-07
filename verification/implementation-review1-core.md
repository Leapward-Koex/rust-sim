# Independent implementation review 1: core and serialization

Reviewer: fresh agent `implementation_review1_core`, which did not author the
implementation. Date: 2026-10-07. This review read `src/config.rs`, `model.rs`,
`engine.rs`, `random.rs`, `aggregate.rs`, `json.rs`, the private fixture adapter,
native sampling tests, the captured active Python source, and the reviewed
specifications. No implementation or captured-source files were changed.

## Findings

### R1-CORE-01 — P2: eager configuration conversion rejects successful reference runs

**Implementation:** `src/config.rs:39-70`, especially the unconditional `vg`,
`mc_count`, and `mc_germ_count` conversions at lines 45 and 62-63.

**Reference:** `reference-source/dicty_sim_test_env.py:751-785` only calls the
relevant biological phase when its cycle is reached; `vegetative_growth:415`
reads `vg`, and `sexual_cycle:620,677` reads the sexual counts when those
operations execute. Initialization and initial measurements do not read those
fields. This is the unvalidated, config-driven behavior described in CONFIG-002,
VEG-003, SEX-009, and RUN-002, rather than an externally injected Python object
case.

Using `verification.differential.execute_reference` with its normal complete
configuration and actual captured `main()` confirms all of the following:

| Configuration changes | Captured Python | Current Rust fixture |
| --- | --- | --- |
| `n_dev=0, mc_count=1.5` | Successful result | `mc_count: Expected an integer` |
| `n_dev=0, vg=1.5` | Successful result | `vg: Expected an integer` |
| `n_dev=1, i_macrocyst=[], sex_cycle_interval=0, mc_germ_count=1.5` | Successful result | `mc_germ_count: Expected an integer` |
| `n_dev=0, ch_germ=null` | Successful result | `ch_germ: Expected a number` |
| `n_dev=0, sl=null` | Successful result | `sl: Expected a number` |

This also affects omitted or otherwise unused phase-specific fields: a blanket
schema validation is stricter than the reference. The approved addition of
typed errors does not authorize making source-successful runs fail.

**Recommendation:** retain the raw values and defer conversions and missing-key
errors to the actual operations that use them, including conditional branches.
Do not replace rejected values with numerical defaults. Add whole-run
differential fixtures for initialization-only runs and runs without scheduled
sex using non-integer unused phase counts. Retain fixtures where those same
values fail after the relevant phase is reached.

### R1-CORE-02 — P2: arbitrary-precision JSON sentinel collides with user objects

**Implementation:** `src/json.rs:80-81` parses into `serde_json::Value` while
`Cargo.toml` enables `serde_json`'s `arbitrary_precision` feature.

**Reference:** the original CLI uses Python `json.load` and saves the full
parameter object through `json.dump` (`dicty_sim_test_env.py:910-934,1015-1021`).
Unknown parameter fields must retain their values and shapes (CONFIG-001 and
the approved result compatibility boundary).

The serde value deserializer treats a map whose first key is
`$serde_json::private::Number` as its private arbitrary-precision number
representation. The following are ordinary legal user JSON objects, including
when stored inside an unknown parameter field:

| Value of unknown field `user_extra` | Captured Python result | Current Rust result |
| --- | --- | --- |
| `{"$serde_json::private::Number":"123"}` | Same object | Number `123` |
| `{"$serde_json::private::Number":"hello"}` | Same object | Parameter parse error |
| `{"$serde_json::private::Number":"123","b":2}` | Same object | Parameter parse error |

All three were reproduced by running actual captured `main()` and the current
debug fixture with `n_dev=0`. This does not require malformed JSON.

**Recommendation:** make parsing collision-safe, for example by escaping this
object key token to a dynamically absent marker before the intermediate Value
parse and restoring object keys afterward, or by using a dedicated compatible
JSON deserializer. Cover plain and Unicode-escaped spellings, nested maps,
sibling keys, and preservation of real arbitrary-precision integers and literal
strings in regression tests.

## Verified observations

- Sequential initialization, overlap assignment, whole-genome random assignment,
  ties-to-even sample counts, and initial observation denominators match the
  source's operations for the inspected numeric configurations.
- Growth preserves one germination pass, raw-count fitness grouping, clone-before-
  mutation order, inclusive mutation comparisons, and stale copied fitness.
- Development uses the configured slug count, sample ordering, leftover discard,
  passive/non-discrete branches, XOR candidate membership, and repeated shrinking-
  list deletion. Stable ascending candidate order is the approved RNG adaptation.
- Sexual founder exclusion, partner availability/order, whole-parent and
  recombination branches, identity-sensitive equal-loci handling for reachable
  populations, offspring grouping, and fitness grouping match source behavior.
- The native sample algorithm is partial Fisher-Yates and produces uniform
  ordered samples without replacement. Native integer choices are unbiased;
  weighted selection preserves cumulative/bisect-right semantics even for
  negative individual weights. Python-family and NumPy-family streams are
  separated and repeat-derived. Native frequency tests supplement scripted
  fixtures rather than claiming exact Python seed replay.
- Aggregation uses repeat-index order, equally weighted means, the captured 95%
  Student-t interval, and one-repeat NaN. All 21 output keys and locus series
  structures are represented. Negative development counts yield empty aggregate
  series while still running initialization, matching the source.
- The nonfinite JSON scanner is token-aware and protects existing user strings
  against its own generated marker. The separate serde-reserved-key collision
  above remains actionable.

## Additional executed checks

Beyond inspecting the existing 138-case differential suite, this review ran
150 small complete-source cases with a fixed test-generation seed of 4321.
Numeric parameters included negative/zero cycle and locus counts, out-of-range
probabilities/costs, alternate distribution modes, passive-mode selectors, and
small populations/slug sizes. Fifty cases completed and matched all states,
results, and scripted-call counts using the suite's existing comparison
tolerances. One hundred cases failed in both implementations; this supplemental
failure classification did not assert identical error wording or random-call
counts and is not presented as exhaustive failure parity.

The five deferred-validation probes and three JSON sentinel probes above are
additional confirmed mismatches, outside that numeric sampling pass. They were
reported to the parent and engine author before writing this report.

No expensive performance benchmark was run during this review. GUI behavior,
clean-machine packaging, and post-optimization code are outside this round's
scope. Re-run targeted probes after repairs and retain this report as the
original independent finding record, appending dispositions rather than deleting
the findings.
