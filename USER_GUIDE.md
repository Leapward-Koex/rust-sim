# Dicty Simulator

The interface uses Tkinter and Matplotlib; all simulation work runs in a separate Rust executable. The model follows the captured `dicty_sim_test_env.py` implementation, including its documented quirks. This is not a corrected biological model.

## Windows application

Extract the entire `DictySimulator-windows-x64.zip` archive, then open `DictySimulator.exe` inside its folder. Keep `dicty-sim.exe` and the `_internal` folder beside it. Python and Rust are bundled or compiled into the application; installing development tools is not required.

The parameter grid retains the original parameter names and arrangement. Hover over a field to read what the current model actually implements. Import and save parameter JSON with the corresponding buttons. Imports replace the complete configuration: missing fields are reported rather than filled from defaults. Extra JSON fields survive import, save, and simulation results.

Select **Run** to calculate and open the two-panel graph. The window remains responsive while the Rust process runs. **Cancel** stops the calculation; cancelled or failed calculations do not replace the previous completed results. Closing the application also stops its worker.

An empty output path disables persistent export but still displays the graph. Relative GUI output paths are resolved under your Documents/Dicty Simulator folder; the resolved path is shown in the interface. The legacy filename rule appends `.json` even if the entered filename already has that extension. Failed exports retain the result so it can be saved elsewhere.

The optional seed reproduces a Rust run with the same engine version, parameters, and platform. A blank seed generates a seed, which is reported with the run. Changing the number of workers does not change a seeded result. Seeds do not reproduce Python's random sequence. Additional seed, version, and timing metadata are saved separately from the legacy result data.

The **Computation** control selects **Automatic**, **CPU**, or **GPU-assisted**. Automatic uses GPU growth for workloads with at least 64 repeats, 2,048 cells, two vegetative generations, and a development cycle, when a compatible device is available. Otherwise it reports why it selected the CPU. GPU-assisted forces GPU execution and reports an error if the device or configuration is unsuitable. The status line shows the actual backend and device.

GPU mode accelerates vegetative fitness, weighted parent selection, cloning, and mutation. Other phases use CPU workers. With Workers blank, GPU mode uses at most eight CPU helpers; CPU mode uses up to the logical processor count minus one. Enter a smaller Workers value to leave more CPU capacity for other applications. More workers do not necessarily make GPU mode faster. Sex-heavy workloads may favour CPU mode; the automatic threshold is a batching heuristic, not a performance guarantee.

GPU mode requires an installed OpenCL graphics driver with double-precision support. It has been tested on an NVIDIA RTX 5070 Ti. No CUDA toolkit is needed. The CPU backend remains available without a GPU driver. CPU and GPU produced byte-identical seeded results in the tests on this machine; other GPU vendors and operating systems have not yet been validated.

## Model details that may be surprising

- Vegetative growth happens every development cycle, with optional sex occurring before growth.
- `c_ch_res` and `ch_self_cheat` have no effect in the captured implementation.
- `confidence_interval` is retained in parameters, but the model calculates 95% intervals. A single repeat produces `NaN` confidence widths.
- Only passive resistance is implemented. Nondiscrete passive resistance retains selected slug cells; other resistance types fail when the resulting empty population is measured.
- The configured population need not be even or divisible by slug size. Development discards cells left outside its complete slugs.
- Fractional effectiveness switches affect effectiveness calculations but do not activate the exact-zero/exact-one exploitation branches.

See the `specs` directory in the source distribution for the full behavior contract.

## Command-line runs

From the application folder in PowerShell:

```powershell
.\dicty-sim.exe --param .\example-parameters.json --seed 739 --threads 1
```

For GPU computation, use:

```powershell
.\dicty-sim.exe --param .\example-parameters.json --backend gpu --seed 739
```

`--backend auto|cpu|gpu` defaults to `auto`. `--gpu-batch-size 128` controls how many repeats share GPU work. The engine reduces this limit if required by device memory capacity and records the actual limit in run metadata. `--threads` controls CPU helper workers in GPU mode. These execution controls are separate from the original parameter JSON. Growth probabilities, selection weights and model quirks are preserved.

The ordinary CLI writes to `output_filepath + ".json"`, relative to its working directory. Empty `output_filepath` suppresses result files. No missing output directories are created automatically.

`--result <file>` writes to an exact transport path while preserving the configured output string in the result. `--events` emits structured version-1 JSON Lines events on stdout; diagnostic messages go to stderr. A JSON Lines `{"command":"cancel"}` message on stdin requests cancellation. Process exit codes are 0 for success, 1 for failure, and 130 for cancellation.

Result files keep the original 21-key schema. They can contain Python-compatible `NaN` or `Infinity` tokens, which strict JSON parsers may reject. The event protocol and run metadata use strict JSON.

## Building from source

Use Rust 1.99.0 with the Windows MSVC toolchain and Python 3.12 with Tkinter. From `rust-sim`:

```powershell
uv venv --python 3.12 .venv-build
uv pip install --python .venv-build\Scripts\python.exe -r requirements-build.lock
cargo test --locked
cargo build --release --locked
.venv-build\Scripts\python.exe -m gui
.venv-build\Scripts\python.exe scripts\build_windows.py
```

The packaging script writes the application folder and ZIP under `dist`. It never modifies the original simulator or captured reference. The engine source is portable; this release's packaging script targets Windows x64.
