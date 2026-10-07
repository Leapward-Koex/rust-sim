# Implementation review round 2: CLI, data compatibility, and packaging

Reviewer: fresh independent second-round data/CLI reviewer. Date: 2026-10-07.

Scope: final `src/main.rs`, `src/config.rs`, `src/json.rs`, `src/aggregate.rs`, the configuration-dependent engine calls, the captured active Python entrypoint, CLI regression tests, Windows build/package-check scripts, frozen engine resolution, dependency locks, and target-specific Cargo configuration. No implementation files were changed by this reviewer. The release engine tested had SHA-256 `582505ce2115637d39012bf75d8401e1cd20a97855d408f92533ae78848909bc`.

## Outcome

**No new actionable findings in this scope.** Both first-round data/CLI findings are closed by inspected fixes and independently repeated release-executable regressions. This is a targeted review and test result, not proof for all malformed inputs, resource-exhaustion cases, or filesystem failures.

## First-round finding closure

- **Reserved serde number key:** every user object key is escaped before decoding into serde's arbitrary-precision representation and restored afterwards. The original `$serde_json::private::Number` examples remain objects, including nested values, sibling keys, escaped spellings, and non-numeric strings. The marker selection also inspects decoded strings, preventing escaped user text from colliding with the internal nonfinite marker.
- **Result/metadata mismatch after a refused replacement:** both files are staged and flushed before either destination changes; existing destinations are backed up before commits; failure committing the second member restores the already-committed first member. The Windows read-only result case preserves both old files. The read-only metadata case preserves both old files, and removes a newly committed result when no previous result existed. Backup copies remain writable so refused read-only replacements do not leave undeletable read-only backups. A failed rollback retains backups and includes their location in the error. This policy covers ordinary I/O failures, without claiming power-loss atomicity across two files.
- **Lazy parameter conversions:** cached conversion results are returned only when the corresponding operation consumes them. Independently reran success cases with unused null/fractional growth or sexual parameters. No eager validation regression was found in the reviewed paths.

## Executed checks

- All **12 `qa.test_cli` tests passed** against the final release executable: result shape, transport output with saving disabled, strict event JSON, repeat-worker invariance, nonfinite confidence values and extras, reserved serde keys, unused invalid phase values, both read-only rollback directions, legacy suffixing, empty schedules, representative failure cases, interval history duplication, and cooperative cancellation.
- Ran **65 additional independent JSON round-trip probes** through the release CLI. These included nested objects/arrays, reserved serde keys, potential marker collisions, quoted and escaped keys, Unicode keys and values, arbitrary-size integers, integers versus floats, negative zero, very small floats, booleans/nulls, and `NaN`/positive and negative infinity. Python-decoded extra values and representation types matched after result serialization in every case.
- Ran **8 invalid-input probes**: non-object roots, missing required configuration, invalid nonfinite-token suffixes, and invalid trailing-comma syntax. Every case exited with structured `error` events and preserved an existing completed result.
- Tests used a workspace-local temporary directory. An initial invocation could not write to this agent sandbox's default temporary directory; after setting `TEMP`/`TMP` within `build/review2-data`, the complete suite passed. The initial failure occurred before simulation execution and was not an application defect.

## Source checks

- Legacy result keys/order, nonfinite result serialization, the captured 95% confidence default, separate strict-JSON run metadata, literal `.json` suffixing, exact `--result` transport paths, and relative CLI paths remain consistent with the specified contract.
- The stdout event channel and stderr diagnostic channel remain separate. Events carry version and run identity. Cooperative cancellation is checked before aggregation/export; completed events follow successful result/metadata commit. Clap argument errors occur before the event protocol begins.
- Default worker calculation leaves one logical CPU available when possible and is bounded by repeat count; explicit positive worker counts remain supported. Indexed collection and ordered aggregation preserve worker-count-independent result bytes, as also exercised by the CLI test.
- The Windows CRT setting is scoped to `x86_64-pc-windows-msvc` and does not enable host-specific instruction sets. `Cargo.lock` fixes crate versions. Python build dependencies are explicitly version-locked. The toolchain file deliberately uses this host's installed `stable` alias; it is not an immutable compiler-version pin.
- The packaging script builds only the release engine for distribution, places it beside the frozen GUI, and includes the guide and example parameters. Runtime engine resolution uses the frozen executable directory or bundle directory rather than searching the host PATH. Python imports and Matplotlib/Tk resources are collected by PyInstaller. SciPy is absent from application runtime dependencies.
- The package-check script copies the application into a Unicode path with spaces, changes to an unrelated working directory, removes Python/Tk environment overrides, restricts PATH to Windows System32, and verifies that imported modules and the engine came from that copied application. Its report explicitly distinguishes isolation on a development machine from a clean Windows installation.

## Limits and remaining release checks

No builds, full benchmarks, or duplicate package-smoke runs were initiated by this reviewer, to avoid interfering with the implementation owner's final benchmark and rebuild. Final rebuilt-package smoke verification remains with that owner; previously saved package-smoke evidence was inspected but is not claimed as a fresh run by this reviewer. A separate clean Windows installation was not available to this review. Biological transition details and GUI interaction are covered by the other independent second-round reviewers.
