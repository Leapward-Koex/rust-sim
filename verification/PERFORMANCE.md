# Performance measurements

Measured on Windows 11 x64, Intel Family 6 Model 183, 24 logical CPUs, on 2026-10-07. The final Rust release engine SHA-256 is `582505ce2115637d39012bf75d8401e1cd20a97855d408f92533ae78848909bc`.

## Single-worker comparison

Each case uses 10,000 cells, 50 development cycles, 10 vegetative generations per cycle, and one repeat. Values are medians of three fresh processes. File saving and GUI plotting are disabled; progress is redirected to retained logs. Wall time includes interpreter startup, imports, and aggregation. The original captured Python file runs unchanged with Python 3.12.14, NumPy 1.26.4, SciPy 1.13.0, and Matplotlib 3.8.4.

| Workload | Python | Final Rust, one worker | Speedup |
| --- | ---: | ---: | ---: |
| Ordinary, 3 loci | 23.236 s | 0.517 s | 45.0× |
| Sex every 2 cycles, 3 loci, mixed starting population | 26.738 s | 0.594 s | 45.0× |
| 12 loci, mixed starting population | 59.310 s | 0.802 s | 74.0× |

Final Rust working-set peaks were approximately 14–15 MiB; Python peaks were approximately 132–155 MiB. Memory is sampled every 10 ms, using process-tree working sets and Windows peak working-set counters where available; it is not an allocator accounting or byte-exact measurement.

The initial comparison is recorded in [benchmark-results.json](benchmark-results.json). After review fixes and Windows static-CRT linking, Rust was measured again in [benchmark-final-rust.json](benchmark-final-rust.json). The table uses those final Rust measurements against the unchanged Python baseline. The three parameter sets and individual samples are retained in the reports. Python and Rust use different random generators; identical seeds do not imply identical trajectories across languages.

## Full repository workload

The full configured workload—10,000 cells × 500 development cycles × 10 vegetative generations × 10 repeats, 3 loci—completed with seed `20261007`:

| Execution | Wall time | Peak working set |
| --- | ---: | ---: |
| One Rust worker | 47.895 s | 17.2 MiB |
| Ten Rust workers | 5.999 s | 24.4 MiB |

Both executions produced **byte-identical legacy result files**, each containing all 501 measurement points and the 21-key schema. Separate metadata differs in timing and worker count as intended. Evidence: [full-workload.json](full-workload.json).

The full workload was not timed in Python; no full-workload Python speedup is claimed. The measured single-worker comparisons exceed the initial 10× engineering target without additional biological algorithm changes.

## Reproduce

```powershell
.venv-build\Scripts\python.exe scripts\benchmark.py --cycles 50 --samples 3 --workers 1
.venv-build\Scripts\python.exe scripts\verify_full_workload.py
```

The benchmark runner requires the locked build environment (including psutil), the separate reference environment, and release binaries. Performance depends on the processor, workload, background load, and compiler build.
