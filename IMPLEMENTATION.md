# Implementation and verification

## Boundaries

`src` contains the Rust engine and command-line interface. `gui` contains the Python desktop application. Python exchanges a parameter file, a result file, and progress events with the engine; no cells or inner-loop operations cross that boundary.

The source authority is `reference-source/dicty_sim_test_env.py`, recorded by `source-manifest.json`, together with the reviewed requirements in `specs`. The older `dicty_sim_v0.6.py` is not the model implemented here. Captured files and the original repository must remain unchanged.

Compatibility covers configuration-driven runs. Model quirks, phase ordering, measurements, and the legacy output structure remain binding. Internal Python object alias injection and history contamination after failed GUI calls are outside that interface.

Intentional runtime and interface differences are reproducible Rust RNG streams, ascending developmental candidate indices, parallel isolated repeats, clean state per job, structured diagnostics, cooperative cancellation, working parameter import/export, fractional GUI numeric values, safe empty-list plotting, and GUI-relative output paths under Documents/Dicty Simulator. These do not grant permission to change the biological rules.

## Protocol version 1

Launch one worker per GUI job with an absolute executable path and an argument list, never a shell command. Send `--param`, `--result`, `--events`, and optional `--seed` and `--threads`.

Version 0.2 also accepts `--backend auto|cpu|gpu` (default auto) and `--gpu-batch-size` (default 128). The GUI forwards its Computation selection independently of the model parameters. Started events and run metadata include `backend`, `requested_backend`, `device`, `backend_reason`, `threads`, and the effective `gpu_batch_size`; completed events include `backend` and `device`. Device is null for CPU execution. Protocol version remains 1 because these are additive fields.

Every stdout line is one strict JSON object containing `protocol_version: 1`, a string `run_id`, and a `type` discriminator. Types are `started`, `progress`, `completed`, `cancelled`, and `error`. Progress includes `repeat` (one based), `cycle` (zero at initialization), `total_repeats`, `total_cycles`, and `phase`. Completion includes `result_path`, `metadata_path`, and `seed`; paths can be null when ordinary CLI saving is disabled. Diagnostics belong on stderr. The parent drains both pipes concurrently.

Progress adds a monotonic `completed_cycles` count across all repeats. Jobs of 64 or more repeats emit at most ten periodic records per second, plus their initial/final progress; intermediate phase records can be omitted. The GUI uses the global count when available and accepts the older per-repeat progress format. Terminal events are never throttled.

Cancellation is a strict JSON line on stdin: `{"command":"cancel"}`. The GUI escalates to process termination after two seconds and reaps the child. Cancellation never exports partial trajectories. A run is successful only when the completion event, exit code zero, and parsed result agree.

Legacy results use a separate Python-compatible JSON adapter because nonfinite values are part of the captured schema. Run metadata is written as `<result-path>.run.json`, without extending the 21-key result object.

## Verification commands

```powershell
cargo test --locked
cargo build --release --locked
.venv-reference\Scripts\python.exe -B verification\check_source_behavior.py
.venv-build\Scripts\python.exe -m unittest discover -s qa -v
.venv-build\Scripts\python.exe -m unittest discover -s tests_python -v
.venv-build\Scripts\python.exe scripts\benchmark.py
```

The reference environment uses Python 3.12, NumPy 1.26.4, SciPy 1.13.0, and Matplotlib 3.8.4. The application runtime does not depend on SciPy. Reference numerical and differential harness details are documented alongside their scripts in `verification`.

Discrete states and orders must match exactly in scripted differential fixtures. Ordinary finite measurements use absolute tolerance `1e-12` and relative tolerance `1e-10`; confidence widths use `1e-10` and `1e-8`. NaN and infinity status are compared explicitly. Distribution checks supplement, rather than replace, source and transition checks.

`scripts/benchmark.py` runs fresh processes with retained logs and the same input configurations. It reports end-to-end wall time and sampled process-tree peak working-set memory. Python imports are included. It records RNG seeds but does not claim the Python and Rust streams are equivalent. Use `--workers 1` for the single-worker comparison and separate reports for repeat parallelism.

Independent review reports, differential results, runtime checks, and benchmark evidence belong in `verification`. Test claims must identify what was actually executed; bundled-app tests on a development host are not the same as tests on a freshly installed Windows machine.

## Optional GPU path

`src/accelerated.rs` batches repeats and calls the unchanged CPU phases around `src/gpu.rs`. OpenCL is loaded dynamically; `src/kernels/growth.cl` is embedded in the Rust executable and compiled by the driver. No CUDA toolkit, separate shader file, or machine-specific CPU build is required.

The kernel reproduces ChaCha12 word positions and the CPU's 53-bit double conversion, ordered cumulative weights and Python-style bisect, double-precision fitness, mutation comparisons and stale offspring fitness. Floating-point contraction and fast math are disabled. Device buffers are reused across generations and cycles. Device computation succeeds before CPU RNG positions are advanced; NumPy-family streams stay on the CPU. Repeat IDs and aggregation order do not depend on batches or workers. Germination remains a CPU operation called exactly once before each growth phase.

Automatic selection checks workload size, supported numeric parameters, device availability and conservative memory capacity before starting. It reduces the requested batch to fit at most half of reported device memory and individual allocation limits, including potential sexual offspring populations. If even one repeat cannot fit it falls back to CPU. Runtime GPU allocation/driver failures after starting end that run with an error; they do not silently restart it. GPU mode currently supports positive integer cell/locus/growth counts and finite growth costs/mutation thresholds; other CPU-compatible cases remain on CPU in Automatic mode. Values outside [0,1] are not clamped. Explicit GPU requests fail if unsupported.

Hardware verification (requires an FP64 OpenCL GPU):

```powershell
cargo test --release --locked --lib gpu::tests -- --ignored --nocapture --skip gpu_growth_benchmark
$env:DICTY_TEST_GPU = '1'
.venv-build\Scripts\python.exe -m unittest discover -s tests_python -v
.venv-build\Scripts\python.exe scripts\benchmark_gpu.py --cycles 20 --repeats 1000
.venv-build\Scripts\python.exe scripts\check_package.py --backend gpu --report verification\gpu-package-smoke.json
```

The [GPU report](verification/GPU-ACCELERATION.md) records hardware, exact-parity checks, whole-run measurements, CPU usage, and limitations. The original CPU release reports remain a historical baseline.

The [release verification record](verification/RELEASE.md) summarizes the executed checks and both implementation review rounds. [Performance results](verification/PERFORMANCE.md) include the final release measurements and full-workload worker invariance. Run `scripts/check_package.py` with the build Python to repeat frozen-app isolation testing, and `scripts/check_reference_integrity.py` to verify all original and captured file hashes.
