# Independent implementation review 2: core, configuration, and statistics

Reviewer: fresh agent `implementation_review2_core`, which did not author the
implementation. Date: 2026-10-07. Scope: the current Rust configuration, compact
population, engine, random adapters, statistics, JSON compatibility layer, CLI
result-pair replacement, and MSVC build configuration, compared with the captured
active Python source and reviewed specifications. No implementation, original
simulation, or reference snapshot files were edited.

## Finding status

**No open actionable findings in the reviewed scope.** This is a targeted review
and executed comparison, not proof over arbitrary malformed inputs or an exact
Python PRNG replay claim. GUI behavior and clean-machine packaging are owned by
the separate second-round review and release checks.

## Independent executed checks

These checks used the pinned reference environment, unmodified captured Python
function bodies through `verification/differential.py:execute_reference`, and the
current debug Rust fixture. They were executed from inline scripts without
altering the maintained fixture corpus.

- **387 whole-run parameter-type probes:** null, false, true, integer-valued
  floats, fractional floats, NaN, positive infinity, and negative infinity across
  14 or 15 relevant parameter fields. Three models covered a wild population with
  development, initialization-only mixed genotypes, and mixed genotypes with a
  scheduled sexual phase. All **330 source-successful cases** matched complete
  results, final ordered populations, and scripted API call consumption using the
  declared tolerances. The other **57 cases failed in both implementations**;
  identical error wording and failure-side call consumption were not asserted.
- **Missing-field probes:** individually removed each of the 31 default fields
  from an initialization-only run and a one-development-cycle run. The **25
  source-successful core cases** matched; **35 core cases failed in both**. The
  remaining two probes omitted `output_filepath`: the private Rust fixture does
  not execute CLI file output, whereas captured `main()` does. This is a harness
  boundary, not a product acceptance mismatch: the current CLI explicitly calls
  `cfg.output.string()?` after aggregation, including with `--result`, so a
  missing output field fails in the product. CLI output is not covered merely by
  running the private engine fixture.
- **27 JSON preservation probes:** nested objects with the serde private number
  key, generated-marker-like strings and keys, quotes, backslashes, Unicode,
  sibling members, NaN/Infinity values, and a large integer all survived complete
  source-versus-Rust round trips. The probe subprocesses explicitly decoded
  UTF-8, matching the product protocol.

The existing maintained differential report at review time independently records
**148 passing cases and zero failures** with Python 3.12.14, NumPy 1.26.4, and
SciPy 1.13.0. This reviewer inspected that report rather than representing it as
a fresh full-suite run by this agent.

## Source review observations

- Deferred parameter conversions resolve the first review's rejected-successful-
  run issue without substituting defaults. Numeric booleans, float-versus-integer
  counts, unused phase fields, conditional germination access, and separately
  evaluated cheating/resistance effectiveness were inspected and exercised.
- Key escaping occurs before serde's arbitrary-precision `Value` deserializer;
  decoded keys are restored afterward. It resolves the original private-number
  sentinel collision while retaining insertion order and nonfinite tokens.
- Contiguous genotypes retain independent clone storage, per-cell order, mating
  type, and copied stale fitness. The inspected initialization, clone-before-
  mutation, developmental XOR membership, repeated shrinking-list deletions,
  sexual partner removal, and offspring grouping follow the captured source.
- Reachable nonempty genomes remain independent locus identities; the Rust sex
  implementation therefore correctly avoids substituting equal allele values
  for Python object identity. The empty-genome branch is represented separately.
- Native cumulative selection retains the captured bisect-right behavior for
  negative individual weights with a valid positive finite total. Ordered
  samples are uniform without replacement. Developmental candidate order is the
  documented ascending-index adaptation, not an assertion about Python set or
  RNG replay.
- Repeat streams are indexed independently of worker scheduling. Parallel
  collection and final aggregation use repeat order. Statistics retain equal
  repeat weighting, the captured 95% interval, sample SEM, Student-t half-width,
  and one-repeat NaN; no new statistics change was introduced by the repairs.
- The CLI's current paired-write procedure stages and flushes both files,
  prepares originals before replacement, and restores already-replaced members
  after an ordinary later replacement failure. The previous metadata-first
  inconsistency is no longer present in the inspected source. Power-loss
  atomicity is expressly not claimed; actual injected I/O-failure regressions
  belong to the implementation owner's final verification.
- `.cargo/config.toml` enables `+crt-static` for the Windows MSVC target only.
  No host-specific CPU optimization flag was found in Cargo, packaging, or
  scripts. This is runtime bundling, not a changed simulation instruction set.

## Reviewed source identifiers

SHA-256 values captured after the probes:

| File | SHA-256 |
| --- | --- |
| `src/config.rs` | `CF1AD566E9D7B87B51AAC91071277E2B4A5F7AE1388DD037B5B922BE0283A082` |
| `src/model.rs` | `16965605FC986C423FD61580DBD83D7889BCD3077DA4AE289C1FDDC9AEB81844` |
| `src/engine.rs` | `20CEB72B2D8060940C8B5477ACF311B02FC84111DF17BD738756ED96586AF967` |
| `src/json.rs` | `427B3AE68CF35430A872F6861CEC0F159FB6266735DE1F8FE9E2A3D3DBA1C215` |
| `src/aggregate.rs` | `43027D3DE7999D2CDC514AFD081C8B5B4F9D2B3C05B221A322F34003CF04DA7D` |
| `src/random.rs` | `78A55C73D43C6FE14A886524ED02824706D54E534BA55B8B9EACA81D255391C9` |
| `src/main.rs` | `443135DACC79ABD322E93BDCB38D558DF2B7C56D13AD10E95EA456369AF07ED8` |
