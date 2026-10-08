# GPU-assisted simulation

Implemented on branch `gpu-acceleration`, engine version 0.2.0. No commit was created for these changes. The captured Python source and the original simulator remain unchanged.

## Implementation

Vegetative growth runs in batches on an OpenCL GPU: fitness assignment, cumulative weights, weighted parent selection, cloning, and mutation. Initialization, germination, sex, development and measurement use the existing CPU functions. This targets the largest measured cost: growth was approximately 82% of an ordinary run, and weighted selection was about 72% of growth ([profile](GPU-CPU-PROFILE.md)). Aggregation of 1,000 repeats was approximately 0.11 seconds and was not the bottleneck.

The GPU executes the same ChaCha12 stream as CPU growth, retaining exact word offsets across phase boundaries. Ordered double-precision accumulation and bisect selection preserve negative individual weight behavior. The kernel retains inclusive mutation comparisons, offspring order, mating types and stale stored fitness. No fast math or floating-point contraction is enabled. This deliberately limits some parallel reductions to retain the model's implemented behavior.

Automatic mode uses GPU for at least 64 repeats, 2,048 cells and two growth generations when development runs and a compatible device/configuration is available. Device memory limits reduce the batch size before execution; if a repeat cannot fit, Automatic falls back to CPU. Explicit GPU mode reports unsupported configurations or hardware. GPU execution uses at most eight CPU helpers by default. These choices are separate from the 31 legacy parameters and are recorded in metadata; the 21 result fields are unchanged.

Large jobs now report at most ten periodic progress events per second, with an exact global completed-cycle count. This avoids up to millions of JSON messages and GUI queue entries when `n_runs` is 1,000.

## Hardware and scope

Test machine: Windows 11 x64, Intel Core i7-13700K with 24 logical CPU processors; NVIDIA GeForce RTX 5070 Ti, driver 617.14, approximately 16 GiB graphics memory. The device exposed OpenCL 3.0, OpenCL C 1.2 and double precision. The Intel integrated GPU did not expose the required double precision and was excluded. OpenCL is dynamically loaded from the installed driver; no CUDA toolkit or build SDK is required for the packaged application.

GPU speed varies with hardware and workload. Automatic selection is a batching heuristic, not a claim that the GPU always wins. Sex-heavy runs retain more CPU work and can be slower with GPU assistance. The explicit CPU option remains available. GPU memory usage and host transfer buffers are greater than the CPU-only implementation. Other GPU vendors, Linux/macOS GPU execution, and a genuinely clean Windows installation have not been tested.

## Measurements

The benchmark uses the original import template, changing repeat/cycle counts and output path. All runs use seed 20261007. CPU mode uses the existing default of 23 repeat workers; GPU mode uses eight CPU helpers and batches of 128 repeats. Wall time includes process startup, driver initialization, transfers, all simulation phases, aggregation and result export. CPU time and process peak working set are sampled every 20 ms. GPU driver/device allocations are not part of the process working-set metric. Every comparison requires byte-identical result files.

Initial 10,000-cell, 1,000-repeat, 20-cycle checks:

| Workload | CPU seconds | GPU seconds | CPU core-equivalents, CPU / GPU | Host peak working set, CPU / GPU |
| --- | ---: | ---: | ---: | ---: |
| Ordinary | 12.47 | 10.97 | 21.19 / 3.61 | 36.4 / 282.5 MiB |
| Sex every two cycles | 15.40 | 16.90 | 21.11 / 5.04 | 38.7 / 292.6 MiB |
| 12 loci | 22.44 | 15.71 | 19.75 / 4.03 | 46.5 / 329.6 MiB |

These initial timings overlapped some verification/build activity and establish direction only ([raw data](gpu-benchmark-initial.json)). A separate ordinary batch-256 run was essentially unchanged at 12.45 seconds CPU / 10.92 seconds GPU, so the smaller default batch was retained ([data](gpu-benchmark-batch256.json)). The isolated growth phase was approximately four times faster than eight CPU workers; that is not a whole-application speedup claim.

Full **10,000 cells × 500 cycles × 1,000 repeats**, with no concurrent build, simulation or hardware-test workloads started by this task during measurement:

| Backend | Wall time | Sampled CPU time | Average CPU cores | Host peak working set |
| --- | ---: | ---: | ---: | ---: |
| CPU, 23 workers | 346.81 s (5:47) | 7,651.58 s | 22.06 | 125.3 MiB |
| GPU, 8 CPU helpers | 323.16 s (5:23) | 1,590.22 s | 4.92 | 355.4 MiB |

GPU throughput was **1.073×** the CPU baseline: approximately **6.8% less elapsed time**, **79.2% less CPU time**, and **77.7% lower average CPU use**. This is a modest speed improvement with a substantial reduction in CPU demand. The two complete result files have the same SHA-256: `58bcf9ab8c45c43b127ea331f84ecd08453566715bb82e0e8803c663f7acd535`. One full sample per backend was measured, not a statistical confidence bound on performance. [Full raw report](gpu-benchmark-full.json).

CPU-helper tuning on a separate **50-cycle, 1,000-repeat** ordinary job: GPU with [16 helpers](gpu-benchmark-workers16.json) took **24.90 seconds**, versus **30.15 seconds** with [eight helpers](gpu-benchmark-workers8.json), a 17.4% reduction in elapsed time. Average CPU use rose from 4.48 to 6.37 cores. Both tuning outputs have SHA-256 `4bfb68eb94eec093e287d857ab7df0f3820f2999787bb51d2f5e277952568b6f`. Select Workers **16** for the faster measured setting on this machine, or leave it blank for the conservative eight-helper default. Sixteen helpers were not measured on the full 500-cycle workload. The tuning reports contain one GPU timing each; equality is established by comparing their hashes, not by an internal CPU run in those reports.

## Verification

- All 148 existing scripted differential cases against captured Python passed: [report](gpu-branch-differential.json).
- All 31 retained source behavior checks passed: [report](gpu-source-checks.json).
- Twelve ordinary Rust tests passed, including mocked GPU memory-budget boundaries. Three additional hardware correctness tests passed: exact ChaCha12 values at odd offsets/block boundaries, exact growth state and following CPU RNG streams, and invalid-weight rejection without RNG advancement. Tests cover 1–67 loci, mixed input sizes, negative individual weights, and 10,000-cell growth. The manual growth benchmark is separately ignored by default.
- All 14 CLI tests passed, including automatic CPU selection and injected unavailable OpenCL API behavior. Automatic fallback matched CPU bytes; explicit GPU failed without replacing previous results.
- All 25 GUI/controller tests and five hardware CLI integration tests passed. The integration matrix compared 30 GPU runs across ten configurations and three worker/batch settings against exact CPU result bytes. It covers sex schedules, nonzero germination, fractional effectiveness, mutation boundaries, 97 loci, one-repeat NaN widths, throttled progress and cancellation. An additional eligible-workload test verifies that Automatic actually selects GPU and matches CPU results. Cooperative and forced cancellation preserved earlier result files.
- Both CPU and GPU packaged-app checks passed from spaces/Unicode paths, with unrelated working directories and no Python or Rust on PATH: [GPU](gpu-package-smoke.json), [CPU](gpu-package-cpu-smoke.json). The GUI opened a plot and stayed responsive in both checks. These run on the development host, not a freshly installed OS.
- Source integrity: all 205 original files and 80 snapshot files match their recorded hashes.
- Fresh kernel/random-stream and integration reviewers examined the changes. One automatic GPU memory-capacity finding was fixed and re-reviewed: [review](GPU-REVIEW.md).

## Use and reproduce

Open `dist/DictySimulator/DictySimulator.exe` and select **GPU-assisted**, or leave **Automatic** for a large run. Select **CPU** to compare. Keep Workers blank for the defaults above, or enter a smaller value to limit CPU helpers.

```powershell
cd 'C:\Dev\Dicty sim\rust-sim'
.\target\release\dicty-sim.exe --param .\reference-source\import_template.json --backend gpu --seed 739
.\.venv-build\Scripts\python.exe scripts\benchmark_gpu.py --cycles 500 --repeats 1000 --report verification\gpu-benchmark-full.json
```

The first command uses the parameter file's existing ten repeats; change `n_runs` in your own parameter file or through the GUI for larger jobs. The benchmark script creates private configurations and logs under `build`, without modifying the template. Cancellation is checked between GPU generations and CPU phase loops; a driver-stalled kernel remains subject to the GUI's two-second forced-process termination policy.
