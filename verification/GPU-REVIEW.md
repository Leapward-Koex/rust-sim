# GPU implementation review

Date: 2026-10-07. Branch: `gpu-acceleration`.

This record covers independent source review, not test execution. The integration reviewer did not implement the reviewed production changes and did not run builds or benchmarks while performance measurements were underway. Only this review record was written by that reviewer.

## Scope and outcome

The integration review examined `src/accelerated.rs`, the changes to `src/main.rs` and `src/engine.rs`, backend controls and process handling in `gui/`, and the packaging smoke-test changes. The follow-up also examined GPU capacity calculations, allocation checks, the growth kernel, and its random-stream interface.

No unresolved actionable defects were found in this scope after the capacity fix described below. This conclusion does not replace the hardware parity tests, process tests, or packaged-application checks.

The review confirmed that:

- Repeat seeds use global repeat indices across batches. Results remain in repeat order, independent of CPU helper scheduling.
- Each cycle retains the CPU sequence of optional sex, germination, vegetative growth, development, and measurement. Germination runs exactly once. Interval sex history is appended after successful development, matching the CPU implementation.
- Growth uses the existing Python-family ChaCha12 stream; CPU germination and subsequent phases consume the same per-repeat stream. The NumPy-family stream remains on the CPU. The kernel preserves ordered cumulative sums, bisect selection, inclusive mutation comparisons, cloned mating types, and stale parental fitness.
- The event mutex serializes the global completed-cycle count with emitted progress. GUI progress uses this count when present, retaining compatibility with older progress fixtures. Actual backend and device information survive phase updates and completion.
- GUI backend selection is an execution option, separate from legacy parameters. Cancellation, terminal-event validation, private result transport, and preservation of prior completed results retain their existing lifecycle.
- OpenCL is loaded dynamically. The CPU execution path does not require an OpenCL import DLL, and kernels are compiled into the Rust executable as source text rather than relying on a loose packaged file.

## Capacity finding and resolution

The initial GPU review identified that automatic selection checked device availability before a run, but deferred memory-capacity validation until growth. A valid CPU workload could therefore select GPU automatically and then fail because its requested batch exceeded the device budget.

The revised selection performs a preflight before the `started` event. It bounds population capacity by `n` and, when sex may run, `mc_count * mc_germ_count`; it uses checked arithmetic and does not reject malformed fields that are unused by the selected model path. Germination and development cannot increase this bound.

`GpuGrowth::maximum_batch` and `Buffers::new` now share the same budget calculation. The calculation accounts for power-of-two population strides, both population buffers, metadata arrays, total memory allowance, and the maximum single-allocation size, including the 32-byte random key per repeat. It reduces the batch when necessary. Automatic mode selects CPU if even one repeat cannot fit; explicitly requested GPU mode reports the error. The effective batch size is used for execution and recorded in the start event and run metadata.

The follow-up source review found this resolution consistent with the reachable population sizes and actual allocations. Driver allocation failure or device loss during execution remains a reported run failure; the implementation does not silently restart an already-running simulation on another backend.
