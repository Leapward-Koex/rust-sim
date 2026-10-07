# Reproducing compatibility verification

The original `check_source_behavior.py` is retained unchanged. Its 31 checks still
validate the captured source, including some direct Python object behaviors that
the approved config-driven Rust interface intentionally does not expose.

`differential.py` supplements those checks with a real numerical oracle. It imports
the original checker's loader, compiles the captured function/class AST bodies
without changing their statements, replaces the complete configuration dictionary
after definitions, and supplies pinned NumPy 1.26.4 and SciPy 1.13.0. Actual
`main()` and the biological phases execute; no phase or statistics spies stand in
for them. An in-memory `open` intercept captures the original result serialization.
A return-event profile hook observes final populations without changing functions.

## Commands

From `rust-sim`, with CPython 3.12 available:

```powershell
uv venv --python 3.12 .venv-reference
uv pip install --python .venv-reference/Scripts/python.exe -r verification/reference-requirements.lock
.venv-reference/Scripts/python.exe -B verification/check_source_behavior.py
.venv-reference/Scripts/python.exe -B verification/differential.py generate
cargo build --bin dicty-fixture
.venv-reference/Scripts/python.exe -B verification/differential.py compare
.venv-reference/Scripts/python.exe -B verification/coverage.py
```

Pass `--executable <path>` to compare with a release fixture executable or use
`--only <name-substring>` to investigate a failing group. Both scripts return a
nonzero exit status on failed checks. The generator records source/checker hashes
and exact numerical dependency versions. Do not regenerate expected fixtures from
Rust output.

## What the scripts compare

Each fixture contains a complete configuration, optional input cells, operation,
high-level random-call script, reference result, and diagnostic call trace. The
script separates `uniforms`, `samples`, `weighted`, and NumPy `integers` channels.
Each sample or weighted entry specifies the returned indices for one API call.
NumPy integers cover both developmental target selection and fifty-fifty bits
(`1` chooses the first parent). Consumption counts detect skipped/extra calls.

Developmental candidate selection records an offset into **ascending cell
indices**. The oracle reads the source frame's already-computed candidate list
and returns its offset for the same target identity. This makes the approved
set-order difference explicit; it does not rewrite the XOR operation or silently
claim Python's PRNG stream was reproduced.

Population order, allele values, mating types, result keys and shapes, and integer
counts must match. Result and nested parameter object key order must also match.
Ordinary finite values use absolute tolerance `1e-12` and
relative tolerance `1e-10`; confidence widths use `1e-10` and `1e-8`. Nonfinite
classification/sign is checked explicitly. Configuration numeric representation
is checked separately so `1` and `1.0` remain distinguishable in saved parameters.

Error fixtures require a nonzero failure with a structured error and the same
random-call counts before failure. Script exhaustion or adapter failures cannot
masquerade as expected model failures. They do not compare exception text or
partial private state. Some seeded small runs intentionally reach natural source failures (for
example, loss of a mating type). These are retained instead of retrying until a
successful trajectory appears.

Fresh-review regression fixtures distinguish unused invalid parameters from the
same values when execution reaches their phase: zero development cycles allow
fractional growth counts and null phase parameters; no sexual event allows
fractional macrocyst counts; nondiscrete development does not read `sp`; absent
resistance carriers do not require resistance-effectiveness arithmetic. These
new success cases are asserted successful during fixture generation. JSON
regressions preserve objects containing serde's private number-marker key,
including nested/sibling objects, an escaped key, and literal `1e309` input
that Python decodes as infinity. They do not merely require a matching error.

The scripted weighted outputs do **not** validate the production weighted sampler
or seed derivation. Separate Rust sampler tests, worker-invariance tests, CLI/UI
tests, performance measurements, and independent source reviews cover those
boundaries. `COVERAGE.md` maps every baseline requirement, including exclusions
and review-only items. A passing suite is evidence, not proof for every possible
malformed parameter or arbitrary Python object graph.
