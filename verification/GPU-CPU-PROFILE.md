# CPU phase profile for GPU acceleration

Measured on 2026-10-07 on the existing Windows host. `nvidia-smi` identified an
NVIDIA GeForce RTX 5070 Ti with 16 GiB VRAM and driver 617.14. No Dicty simulation
process was running when the profiling started. The profiler uses one CPU worker;
its build was limited to two compiler workers. The original benchmark reports
remain unchanged.

Raw timings: [gpu-cpu-profile.json](gpu-cpu-profile.json). Probe source:
[profile_cpu.rs](../src/bin/profile_cpu.rs).

These are phase attribution measurements, not controlled before/after GPU
benchmarks. Other development work was in progress, and ordinary phase totals
varied between successive runs. They exclude GUI work, result serialization,
process startup, and compilation. Every biological phase in the main table calls
the unchanged production CPU function with `NativeChoices`, seed `20261007`.

| Workload | Wall time | Growth | Development | Sex | Measurements |
|---|---:|---:|---:|---:|---:|
| 10,000 cells, 50 cycles, 10 repeats, ordinary | 5.634 s | 4.325 s | 1.247 s | 0 | 0.054 s |
| Same, mixed starting population | 5.076 s | 3.871 s | 1.149 s | 0 | 0.047 s |
| Same, sex every two cycles | 5.900 s | 3.891 s | 1.293 s | 0.660 s | 0.048 s |
| 10,000 cells, 2 cycles, 1,000 repeats | 17.154 s | 15.273 s | 1.079 s | 0 | 0.144 s |

All cases use three loci and ten vegetative generations per cycle. Aggregating
1,000 synthetic histories of 501 measurement points took **0.108 s**. Those
histories were constructed by repeating real measurements; this does not claim
that 1,000 complete 500-cycle simulations were executed.

## Growth attribution

The probe additionally times a diagnostic copy of the growth loop, with timers
only at stage boundaries. After every growth phase it checks genotype, mating
type, and stored fitness against the production implementation using an identical
random stream. Both paths then execute development before the next cycle. This
check passed for all 50 cycles of a mixed-population repeat.

| Growth operation | Total over 500 generations |
|---|---:|
| Germination (50 passes) | 0.00346 s |
| Fitness weights | 0.01289 s |
| Weighted parent selection | **0.27580 s** |
| Cloning | 0.01421 s |
| Mutation | 0.07645 s |

Weighted parent selection consumes about **72% of growth time**, approximately
0.55 ms per 10,000-parent generation. It is the first GPU target. Offloading only
fitness or measurements would address a small fraction of the runtime.

## Compatibility and implementation implications

- Keep the existing CPU backend as the reference and fallback. Development's
  sequential XOR candidate updates, possible repeated stalk indices, and ordered
  population removal make it a poor first GPU kernel.
- A conservative GPU boundary is weighted-selection bisection. Build the f64
  cumulative array on the CPU in the original summation order, generate the same
  random draws on the CPU, and evaluate each independent binary search on the
  GPU. This can preserve existing seeded trajectories, including negative
  individual weights with a positive finite total.
- The GPU search must use f64 multiplication and comparisons and the existing
  `bisect_right(..., high=n-1)` bounds. Replacing doubles with f32, rejecting all
  negative weights, sorting the cumulative array, or parallelizing its sum can
  change branch decisions.
- Preserving RNG consumption matters beyond the selected parents: weighted
  selection, mutation, germination, and sampling share the Python-family stream.
  Each repeat already has independent Python and NumPy family streams.
- For 10,000 parents, cumulative weights and draws require roughly 160 KiB input
  transfer and indices require 40–80 KiB output. Kernel dispatch and transfer
  latency must be measured end-to-end; a fast kernel alone does not prove a
  faster simulation. Reusing buffers, batching requests, or retaining multiple
  generations on-device can reduce overhead.
- If a larger GPU backend changes RNG construction or summation order, record
  that explicitly in run metadata and verify controlled-choice transitions;
  do not claim it reproduces CPU seeds. Avoid making this change merely to
  obtain an attractive benchmark.
- Growth accounts for roughly three quarters of the ordinary longer runs, with
  development and sexual reproduction limiting the eventual overall speedup.
  Aggregation is too small to justify GPU complexity in this workload.

## Reproduce

```powershell
& "$env:USERPROFILE\.cargo\bin\cargo.exe" run --release --locked --offline --bin profile_cpu -j 2
```

The command emits JSON on stdout and does not save simulation results or modify
the reference source. Redirect stdout to a new report to retain another sample.
