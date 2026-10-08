# Dicty Simulator — Rust engine and Python desktop UI

This folder contains the Rust simulation library/CLI, a familiar Tkinter and Matplotlib desktop interface, and the reviewed specification and captured source used to verify the port. The implemented model preserves the original rules, including surprising behavior, ineffective options, and apparent bugs. It does not define corrected biology.

## Run the application

Open **[dist/DictySimulator/DictySimulator.exe](dist/DictySimulator/DictySimulator.exe)** on Windows, or extract the complete **[Windows ZIP](dist/DictySimulator-windows-x64.zip)** and open its launcher. Keep the application folder together. No separate Python or Rust installation is needed for the packaged application.

See the [user guide](USER_GUIDE.md) for parameters, output files, seeds, CLI commands, and building from source. The [implementation guide](IMPLEMENTATION.md) explains the process protocol, compatibility boundary, and verification commands. New runtime provenance is stored beside results; the original 21-key result schema is retained.

The engine uses compact population buffers and independent repeat workers. Reproducible Rust seeds do not reproduce Python's random sequence. Scripted differential checks compare state transitions with the original source, and statistical checks use actual pinned SciPy. See the [release verification and limits](verification/RELEASE.md) and [performance measurements](verification/PERFORMANCE.md): 45–74× measured single-worker improvement, with the full default workload completing in about 6 seconds using ten workers on the tested machine.

The `gpu-acceleration` branch adds optional OpenCL GPU computation for vegetative growth, with CPU fallback and a **Computation** selector in the desktop interface. GPU mode retains the existing random streams and model rules. See the [GPU implementation and measurements](verification/GPU-ACCELERATION.md) for the measured speed and CPU-use tradeoff, hardware requirements, and verification.

The reference entry point is `DictySimulator/dicty_sim_test_env.py`, as selected by the existing repository README. The older `dicty_sim_v0.6.py` is a different implementation and is not an interchangeable reference.

The existing VS Code `Sim` launch configuration selects that older version. The specification explicitly records this alternate entry point so it cannot silently change which model a remake follows.

## Specification reading order

1. [Scope and source authority](specs/00-scope-and-source-authority.md)
2. [Configuration and entry points](specs/01-configuration-and-entrypoints.md)
3. [State, initialization, and vegetative growth](specs/02-state-initialization-growth.md)
4. [Development and sexual reproduction](specs/03-development-and-sex.md)
5. [Measurements, aggregation, output, and plots](specs/04-measurements-and-output.md)
6. [Legacy implementation and supporting tools](specs/05-legacy-and-supporting-tools.md)
7. [Compatibility and verification](specs/06-compatibility-and-verification.md)

## Evidence

- [Source manifest](source-manifest.json) records the original Git commit and SHA-256 hashes of tracked files.
- `reference-source/` preserves the Python source, documentation, dependency lists, import template, parameter experiment files, and VS Code launch configuration used for this specification.
- [Executable behavior checks](verification/check_source_behavior.py) load original function bodies from the snapshot and check specific behaviors without modifying the original simulation.
- [Verification results](verification/results.json) record executed checks and their limitations.
- [Review record](verification/REVIEW.md) records independent source reviews and corrections.

Two rounds of fresh independent review are complete, with three reviewers per round and all findings addressed. The retained verification suite passes 31 checks. The documents distinguish source-reviewed behavior from executed checks, including the limits around numerical libraries, GUI rendering, and exact random-stream replay.

The original repository remains in `../DictySimulator`. This folder is a separate Git repository containing the implementation, reference snapshot, specifications, and verification evidence. Build outputs, local environments, caches, and distribution archives are ignored.
