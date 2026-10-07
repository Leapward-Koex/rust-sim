# Implementation review round 1: configuration, statistics, output, and CLI

Reviewer: fresh independent data/CLI reviewer. Date: 2026-10-07.

Scope: `src/config.rs`, `src/json.rs`, `src/aggregate.rs`, `src/main.rs`, worker construction and result ordering in `src/engine.rs`/`src/random.rs`, the captured active Python source, specifications 01/04, and differential/native test coverage. No implementation changes were made by this reviewer. The config-driven compatibility boundary and deliberately different PRNG sequence were honored.

## Findings at the reviewed revision

### P2: Arbitrary extra JSON objects can be silently converted to numbers

Location: `src/json.rs`, `Json::parse`, the `serde_json::from_str::<Value>` call (lines 80-81 when reviewed).

Enabling serde_json's `arbitrary_precision` feature makes the exact object key `$serde_json::private::Number` special when decoding into `Value`. The nonfinite token scanner protects its own marker but does not protect this independent reserved key. A valid Python configuration with `extra: {"$serde_json::private::Number": "7"}` completes successfully and preserves that nested object in Python. The Rust fixture also completes but serializes `extra: 7`. Changing the string to `"hello"`, or adding another member to that nested object, instead causes an invalid-JSON error in Rust while Python succeeds.

Reproduction: used `verification/differential.py:execute_reference` with `operation="run"`, `n=2`, `n_dev=0`, `n_runs=1`, otherwise complete defaults; replayed the returned script through `target/debug/dicty-fixture.exe`. All three examples were independently reproduced. The first case is silent parameter/provenance corruption, not merely an error-message difference.

Required resolution: shield every user object key from serde_json's private representation or use a decoder that distinguishes lexical numbers from ordinary maps. Preserve exact decoded keys and insertion order, including escaped spellings and nested objects. Add the three examples as regressions alongside the existing nonfinite-marker tests.

### P2: Failed result replacement changes the previous result's seed metadata

Location: `src/main.rs`, `execute`, the consecutive metadata and result `atomic_write` calls.

Metadata is replaced first. If committing the result then fails, the old scientific result remains but its `.run.json` describes the new run. This breaks the reproducibility association the metadata exists to provide.

Reproduction on Windows: run a complete 2-cell, zero-development-cycle, one-repeat configuration to an explicit result path with seed 10; mark that result file read-only; run again to the same path with seed 20. The second process exits 1 and emits a structured `error` event. Result bytes remain unchanged, but `.run.json` now contains seed 20 and the failed run's ID. The test restored the file permissions and removed its own workspace temporary directory afterwards.

Required resolution: stage both files and implement a consistent commit/rollback policy so an ordinary failed replacement retains the old result and its matching metadata. Reversing write order alone moves the same failure to the other file. Test failure committing either member of an existing pair and successful replacement of both.

## Checks without findings

- Statistics use the captured 95% default, sample SEM, and Student-t half-width; the 21-key output order and per-locus shape match the source contract.
- Independently compared 40 confidence datasets against real pinned SciPy: sample sizes 1, 2, 3, 4, 8, 10, 30, 100, and 1,000; ordinary, near-constant, large-offset, and very large-scale values; NaN/Infinity and constant data. All met the plan's confidence tolerances, including matching NaN classification.
- Reviewed distinct Python/NumPy-family ChaCha streams, per-repeat seed derivation, the explicit sequential branch, ordered parallel collection, and ordered aggregation. No worker-order dependence found.
- Reviewed numeric booleans, integer-versus-float counts, nonfinite tokens, preserved arbitrary-size unknown integer values, unknown fields, negative development/repeat behavior, filename suffixing, and the private GUI result override. No further reproducible finding in the inspected ordinary config-driven surface.
- CLI stdout events are strict JSON and diagnostics use stderr; cancellation is communicated through stdin and cooperative checks, with completion gated after calculation and serialization. Argument-parser errors occur before the event protocol is established.

## Review limitations and closure

This is a targeted independent review, not proof for every malformed JSON value or resource-exhaustion input. Existing biological differential checks were inspected rather than rerun wholesale; a separate fresh reviewer owns biological transitions. UI process handling belongs to the separate UI review. This reviewer ran only small isolated probes and did not interfere with the ongoing performance benchmark.

Both findings were reported promptly to the implementation owner. Their status in this document is **open pending implementation and regression verification**; later follow-up should record fixes rather than erase the original evidence.
