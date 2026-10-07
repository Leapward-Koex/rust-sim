"""Differential oracle using unchanged captured Python AST function bodies.

Generate: .venv-reference/Scripts/python -B verification/differential.py generate
Compare:  .venv-reference/Scripts/python -B verification/differential.py compare

No simulation function statements are rewritten. Real pinned NumPy/SciPy execute
the measurements and confidence calculations. RNG proxies record *API results*,
not a cross-language PRNG stream. Developmental targets are identified by cell
index to account explicitly for the permitted set-iteration-order difference.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
from datetime import datetime, timezone
import hashlib
import inspect
import io
import itertools
import json
import math
from pathlib import Path
import platform
import random
import subprocess
import sys
import warnings

import numpy as np
import scipy
from scipy import stats

import check_source_behavior as captured

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "verification"
FIXTURES = HERE / "fixtures.json"
REPORT = HERE / "differential-results.json"
CHANNELS = ("uniforms", "samples", "weighted", "integers")
SCALAR_TRACKERS = ("cheater_allele_counts", "resistor_allele_counts", "wild_counts",
                   "mt1_ratios", "mt2_ratios", "mt3_ratios", "mean_ch_eff", "mean_res_eff")


class RecordedChoices:
    """Seeded high-level API results, optionally overriding a channel prefix."""

    def __init__(self, seed=1729, forced=None):
        self.rng = random.Random(seed)
        self.forced = forced or {}
        self.script = {channel: [] for channel in CHANNELS}
        self.calls = []

    def take(self, channel, fallback, **details):
        index = len(self.script[channel])
        overrides = self.forced.get(channel, [])
        value = overrides[index] if index < len(overrides) else fallback()
        self.script[channel].append(copy.deepcopy(value))
        self.calls.append({"channel": channel, "call": index, **details,
                           "value": copy.deepcopy(value)})
        return value

    def uniform(self, low, high):
        assert (low, high) == (0, 1)
        value = self.take("uniforms", self.rng.random)
        assert 0 <= value <= 1
        return value

    def sample(self, population, k):
        population = list(population)
        # Exercise the original API's rejection before consuming a scripted call.
        if not 0 <= k <= len(population):
            raise ValueError("Sample larger than population or is negative")
        indices = self.take("samples", lambda: self.rng.sample(range(len(population)), k),
                            population_size=len(population), k=k)
        assert len(indices) == k and len(set(indices)) == k
        assert all(0 <= index < len(population) for index in indices)
        return [population[index] for index in indices]

    def choices(self, population, weights=None, *, k):
        population = list(population)
        weights = list(weights) if weights is not None else None
        indices = self.take("weighted", lambda: self.rng.choices(range(len(population)),
                           weights=weights, k=k), population_size=len(population), k=k,
                           weights=weights)
        assert len(indices) == k and all(0 <= index < len(population) for index in indices)
        return [population[index] for index in indices]

    def randint(self, low, high):
        assert low == 0
        if high <= low:
            raise ValueError("high <= 0")
        caller = inspect.currentframe().f_back
        candidates = None
        if caller.f_code.co_name == "developmental_cycle":
            candidates = caller.f_locals["result_list"]
        canonical = sorted(candidates) if candidates is not None else None
        index = self.take("integers", lambda: self.rng.randrange(high),
                          high=high, candidate_cells=canonical)
        assert 0 <= index < high
        # Return the offset for the same target identity in Python's actual set
        # order; Rust consumes the canonical offset into ascending candidates.
        return candidates.index(canonical[index]) if candidates is not None else index


class NumpyProxy:
    def __init__(self, choices):
        self.random = choices

    def __getattr__(self, name):
        return getattr(np, name)


def defaults(**overrides):
    params = captured.environment()["variables"].copy()
    params.update(n=12, sl=4, gene_pairs=2, vg=2, n_dev=3, n_runs=3,
                  mc_count=2, mc_germ_count=6, output_filepath="oracle-captured")
    params.update(overrides)
    return params


def cell(loci=((0, 0),), mt=1, fitness=1.0):
    return {"loci": [list(pair) for pair in loci], "mating_type": mt, "fitness": fitness}


def population(cells):
    return [{"loci": [[l.cheater_allele, l.resistor_allele] for l in c.loci],
             "mating_type": c.mating_type, "fitness": c.fitness} for c in cells]


def measurement(ns):
    if not ns["cheater_allele_counts"]:
        return None
    return {"values": [ns[key][-1] for key in SCALAR_TRACKERS],
            "loci": [[t.ch_count, t.res_count, t.both_count] for t in ns["locus_plot"][-1]]}


def execute_reference(request, seed=1729, forced=None):
    choices = RecordedChoices(seed, forced)
    ns = captured.environment()
    # Defaults are captured at function-definition time above. Replace the entire
    # dictionary afterwards, exactly like the original command-line entrypoint.
    ns["variables"] = copy.deepcopy(request["config"])
    ns.update(random=choices, np=NumpyProxy(choices), st=stats)
    sink = io.StringIO()
    ns["open"] = lambda path, mode: contextlib.nullcontext(sink)
    cells = []
    for value in request.get("cells", []):
        c = captured.cell(ns, value["loci"], value.get("mating_type", 1))
        c.fitness = value.get("fitness", 1.0)
        cells.append(c)
    operation = request["operation"]
    response = {}
    last_pop = []

    def observe(frame, event, value):
        nonlocal last_pop
        if event == "return" and frame.f_globals is ns and frame.f_code.co_name in (
                "initialise_pop", "vegetative_growth", "developmental_cycle", "sexual_cycle"):
            if isinstance(value, list):
                last_pop = population(value)

    prior_profile = sys.getprofile()
    try:
        with warnings.catch_warnings(), contextlib.redirect_stdout(io.StringIO()):
            warnings.simplefilter("ignore")
            if operation == "confidence":
                response["confidence"] = [float(ns["mean_confidence_interval"](data))
                                          for data in request["data"]]
            elif operation == "run":
                sys.setprofile(observe)
                ns["main"]()
                response["result"] = json.loads(sink.getvalue())
                response["population"] = last_pop
            else:
                name = {"initialize": "initialise_pop", "growth": "vegetative_growth",
                        "development": "developmental_cycle", "sex": "sexual_cycle"}[operation]
                result = ns[name]() if operation == "initialize" else ns[name](cells)
                response["population"] = population(result)
                measured = measurement(ns)
                if measured is not None:
                    response["measurement"] = measured
    except Exception as exc:
        response = {"error": f"{type(exc).__name__}: {exc}"}
    finally:
        sys.setprofile(prior_profile)
    response["consumed"] = {key: len(value) for key, value in choices.script.items()}
    request = copy.deepcopy(request)
    request["script"] = choices.script
    return request, response, choices.calls


def make_cases():
    """Named boundary fixtures plus seeded complete-source phase/run fixtures."""
    cases = []

    def add(name, operation, params=None, cells=None, forced=None, seed=1729, **extra):
        request = {"operation": operation, "config": defaults(**(params or {})), **extra}
        if cells is not None:
            request["cells"] = cells
        request, expected, trace = execute_reference(request, seed, forced)
        cases.append({"name": name, "request": request, "expected": expected, "trace": trace})

    add("init_sequential_overlap", "initialize", dict(n=4, gene_pairs=1, ch_start=.25,
        res_start=.25, ch_res_dist=0), forced={"weighted": [[0], [1], [2], [0]]})
    add("init_ties_even_and_whole_genome", "initialize", dict(n=5, ch_start=.5, res_start=.3))
    add("init_fractional_epistasis", "initialize", dict(ch_start=.5, res_start=.5,
        ch_eff_rc=.2, res_eff_rc=.7))
    add("init_nonunit_mating_weights", "initialize", dict(mt1_start=2, mt2_start=3, mt3_start=4))
    add("init_negative_individual_weight", "initialize", dict(mt1_start=-1, mt2_start=3, mt3_start=1))
    add("init_boolean_numeric_switches", "initialize", dict(ch_res_dist=True,
        ch_eff_rc=True, res_eff_rc=False, ch_start=.5, res_start=.5))
    add("init_zero_population_error", "initialize", dict(n=0))
    add("init_zero_loci_error", "initialize", dict(gene_pairs=0))
    add("init_negative_loci", "initialize", dict(gene_pairs=-1, n=2))
    add("init_oversample_error", "initialize", dict(ch_start=1.1))

    add("growth_raw_fitness", "growth", dict(n=1, gene_pairs=1, vg=1,
        c_ch=.2, c_res=.4, m_ch=-1, m_re=-1), [cell([(1, 1)])])
    add("growth_inclusive_zero_mutation", "growth", dict(n=1, gene_pairs=1, vg=1,
        m_ch=0, m_re=0), [cell([(0, 1)])], forced={"uniforms": [0, 0]})
    add("growth_order_and_stale_fitness", "growth", dict(n=2, gene_pairs=2, vg=1,
        m_ch=.5, m_re=.5, c_ch=.2, c_res=.4), [cell([(0, 0), (0, 0)])],
        forced={"weighted": [[0, 0]], "uniforms": [0, 1, 1, 0, 1, 0, 0, 1]})
    for name, draw in (("equal", .5), ("above", .50001)):
        add("growth_germination_" + name, "growth", dict(n=1, gene_pairs=1, vg=0,
            ch_germ=.5), [cell([(1, 0)])], forced={"uniforms": [draw]})
    add("growth_zero_penalty_still_draws", "growth", dict(n=1, gene_pairs=1, vg=0),
        [cell([(1, 1)])], forced={"uniforms": [0]})
    add("growth_negative_weights", "growth", dict(n=8, gene_pairs=1, vg=2,
        c_ch=2, c_res=0, m_ch=.2, m_re=.2), [cell([(1, 0)]), cell(), cell()])

    add("dev_four_genotype_measurement", "development", dict(n=4, sl=4, gene_pairs=1, sp=1),
        [cell([p], i % 3 + 1) for i, p in enumerate(((0, 0), (1, 0), (0, 1), (1, 1)))],
        forced={"samples": [[0, 1, 2, 3]]})
    add("dev_fractional_effectiveness", "development", dict(n=4, sl=4, gene_pairs=1,
        sp=1, ch_eff_rc=.2, res_eff_rc=.7), [cell([p]) for p in ((0, 0), (1, 0), (0, 1), (1, 1))])
    add("dev_order_leftovers", "development", dict(n=5, sl=2, gene_pairs=1, sp=1),
        [cell(mt=i + 1) for i in range(5)], forced={"samples": [[3, 1], [2, 0]]})
    add("dev_nondiscrete_keeps_all", "development", dict(n=4, sl=4, gene_pairs=1,
        sp=0, discrete_res=0), [cell() for _ in range(4)])
    add("dev_duplicate_stalk_xor", "development", dict(n=4, sl=4, gene_pairs=1, sp=.5),
        [cell(mt=1), cell([(1, 0)], 2), cell(mt=3), cell(mt=1)],
        forced={"samples": [[0, 1, 2, 3]], "uniforms": [.1, .1, .9, .9], "integers": [0]})
    add("dev_prestalk_strict_boundary", "development", dict(n=2, sl=2, gene_pairs=1, sp=.5),
        [cell(mt=1), cell(mt=2)], forced={"samples": [[0, 1]], "uniforms": [.5, .4999]})
    add("dev_unsupported_error", "development", dict(n=2, sl=2, gene_pairs=1, resistance_type=2),
        [cell(), cell()])
    add("dev_empty_candidate_error", "development", dict(n=1, sl=1, gene_pairs=1, sp=0),
        [cell([(1, 0)])])
    add("dev_all_stalk_error", "development", dict(n=1, sl=1, gene_pairs=1, sp=0), [cell()])

    for ce, re, actor, target in itertools.product((0, 1), (0, 1), range(4), range(4)):
        bits = lambda value: [(value & 1, value >> 1)]
        add(f"exploit_{ce}{re}_{actor}_{target}", "development", dict(n=3, sl=3,
            gene_pairs=1, sp=.5, ch_eff_rc=ce, res_eff_rc=re),
            [cell(bits(actor), 1), cell(bits(target), 2), cell(mt=3)],
            forced={"samples": [[0, 1, 2]], "uniforms": [.1, .9, .9], "integers": [0]})
    for ce, re in ((.5, 0), (0, .5), (1, .5), (.5, 1)):
        add(f"exploit_fractional_{ce}_{re}", "development", dict(n=3, sl=3,
            gene_pairs=1, sp=.5, ch_eff_rc=ce, res_eff_rc=re),
            [cell([(1, 0)], 1), cell(mt=2), cell(mt=3)],
            forced={"samples": [[0, 1, 2]], "uniforms": [.1, .9, .9], "integers": [0]})

    for recombination in (0, 1):
        add(f"sex_recombination_{recombination}", "sex", dict(gene_pairs=1, mc_count=1,
            mc_germ_count=3, recomb_chance=recombination, c_ch=.2, c_res=.4),
            [cell([(1, 0)], 1), cell([(0, 1)], 2)],
            forced={"samples": [[0], [0]], "uniforms": [0], "integers": [1, 0, 0]})
    add("sex_equal_values_distinct_identity", "sex", dict(gene_pairs=1, mc_count=1,
        mc_germ_count=2, recomb_chance=1), [cell([(1, 0)], 1), cell([(1, 0)], 2)],
        forced={"samples": [[0], [0]], "uniforms": [0], "integers": [1, 0, 0]})
    add("sex_gate_equality_recombines", "sex", dict(gene_pairs=1, mc_count=1,
        mc_germ_count=2, recomb_chance=.5), [cell([(1, 0)], 1), cell([(0, 1)], 2)],
        forced={"samples": [[0], [0]], "uniforms": [.5], "integers": [1, 0, 0]})
    add("sex_founders_excluded_and_partners_removed", "sex", dict(gene_pairs=2, mc_count=2,
        mc_germ_count=2, recomb_chance=1), [cell([(i % 2, 0), (0, i % 2)], i % 2 + 1)
        for i in range(6)], forced={"samples": [[0, 1], [0], [0]], "integers": [1, 0, 1, 0, 1] * 2})
    add("sex_missing_partner_error", "sex", dict(gene_pairs=1, mc_count=1), [cell(), cell()])
    add("sex_zero_macrocysts", "sex", dict(gene_pairs=1, mc_count=0), [cell(), cell(mt=2)])
    add("sex_zero_germinations", "sex", dict(gene_pairs=1, mc_count=1, mc_germ_count=0),
        [cell(), cell(mt=2)])

    for seed in range(12):
        add(f"full_no_sex_seed_{seed}", "run", dict(ch_start=.25, res_start=.33,
            m_ch=.12, m_re=.09, sp=.8, ch_eff_rc=seed % 2, res_eff_rc=(seed // 2) % 2,
            confidence_interval=.1, c_ch_res=23, ch_self_cheat=99,
            extra_user_field={"retain": [True, "NaN remains a string", 1.0]}), seed=seed)
    for seed in range(8):
        # A single sexual event per repeat avoids forcing artificial survival.
        add(f"full_interval_sex_seed_{seed}", "run", dict(n_dev=3, sex_cycle_interval=3,
            ch_start=.25, res_start=.25, m_ch=.04, m_re=.03, sp=.95), seed=seed + 80)
        add(f"full_explicit_sex_seed_{seed}", "run", dict(n_dev=2, i_macrocyst=[1, 1, 99],
            sex_cycle_interval=9, ch_start=.25, res_start=.25, sp=.95), seed=seed + 90)
    for name, scheduling in (("interval", {"sex_cycle_interval": 1}),
                             ("explicit", {"i_macrocyst": [1, 1, 99], "sex_cycle_interval": 2})):
        add("full_balanced_" + name + "_sex", "run", dict(n_dev=1, n_runs=3, vg=1,
            mc_count=3, mc_germ_count=4, ch_start=.25, res_start=.25, sp=1,
            m_ch=.2, m_re=.2, **scheduling), forced={
                "weighted": ([[i % 2] for i in range(12)] + [list(range(12))]) * 3,
                "samples": [[0, 2, 4], [1, 3, 5], [0, 2, 4], [0], [0], [0],
                            [0, 1, 2, 3], [0, 1, 2, 3], [0, 1, 2, 3]] * 3})
    add("full_one_repeat_nan", "run", dict(n_runs=1, n_dev=1, ch_start=.25, sp=1))
    add("full_empty_schedule_interval_zero", "run", dict(i_macrocyst=[], n_dev=1, sp=1))
    add("full_empty_schedule_interval_error", "run", dict(i_macrocyst=[], sex_cycle_interval=1))
    add("full_zero_repeats_error", "run", dict(n_runs=0))
    add("full_negative_cycles", "run", dict(n_dev=-1))
    # Successful lazy-access cases found by fresh source review. Invalid values
    # in an unvisited branch are data, not permission to reject the whole run.
    lazy_start = len(cases)
    add("full_lazy_zero_cycles_fractional_counts", "run", dict(n_dev=0,
        vg=1.5, mc_count=1.5, mc_germ_count=None, recomb_chance=None,
        sp=None, sl=None, c_ch=None, c_res=None, m_ch=None, m_re=None,
        ch_germ=None, sex_cycle_interval=None, i_macrocyst=None,
        c_ch_res=None, ch_self_cheat=None, confidence_interval=None))
    add("full_lazy_no_sex_fractional_germination", "run", dict(n_dev=1,
        i_macrocyst=[], sex_cycle_interval=0, mc_count=1.5,
        mc_germ_count=1.5, recomb_chance=None, sp=1))
    add("full_lazy_nondiscrete_null_spores", "run", dict(n_dev=1,
        discrete_res=0, sp=None))
    add("full_lazy_no_resistors_null_effectiveness", "run", dict(n_dev=1,
        sp=1, ch_start=.25, res_start=0, m_ch=.2, m_re=-1, res_eff_rc=None))
    add("full_lazy_no_carriers_null_effectiveness", "run", dict(n_dev=1,
        sp=1, ch_start=0, res_start=0, m_ch=-1, m_re=-1,
        ch_eff_rc=None, res_eff_rc=None, ch_germ=None))
    # Real decoded JSON objects that collide with serde_json's internal marker
    # must remain objects, including when the key is Unicode-escaped on the wire.
    private_key = "$serde_json::private::Number"
    add("full_json_private_number_objects", "run", dict(n_dev=0, extra_user_field={
        "numeric_string": {private_key: "7"},
        "ordinary_string": {private_key: "hello"},
        "siblings": {private_key: "7", "keep": [1, 1.0, True, None]},
        "nested": [{"child": {private_key: "8"}}, {private_key: "NaN"}],
        "literal_tokens": "NaN Infinity -Infinity 1e309 \\\"quoted\\\""}))
    add("full_json_overflow_and_escaped_marker", "run", dict(n_dev=0,
        extra_user_field={"positive_overflow": json.loads("1e309"),
                          "negative_overflow": json.loads("-1e309"),
                          "escaped": {private_key: "7"},
                          "nan_token": float("nan"),
                          "literal": "Infinity and $serde_json::private::Number"}))
    wire = json.dumps(cases[-1]["request"], allow_nan=True)
    for before, after in (("\"positive_overflow\": Infinity", "\"positive_overflow\": 1e309"),
                          ("\"negative_overflow\": -Infinity", "\"negative_overflow\": -1e309"),
                          ("\"$serde_json::private::Number\": \"7\"", "\"\\u0024serde_json::private::Number\": \"7\"")):
        assert wire.count(before) == 1
        wire = wire.replace(before, after)
    cases[-1]["request_wire"] = wire
    for case in cases[lazy_start:]:
        assert "error" not in case["expected"], (case["name"], case["expected"])

    # Conversely the same invalid values must fail when execution actually
    # reaches the corresponding source expression, without consuming later RNG.
    add("full_active_fractional_growth_error", "run", dict(n_dev=1, vg=1.5))
    add("full_active_fractional_macrocysts_error", "run", dict(n_dev=1,
        i_macrocyst=[1], mc_count=1.5))
    add("full_active_null_spores_error", "run", dict(n_dev=1, sp=None))
    add("confidence_real_scipy", "confidence", dict(confidence_interval=.1), data=[
        [1], [2, 4], [2, 4, 6], [1, 1, 1], [0, 0, 1], [0.0, .1, .2, .9],
        list(range(10)), list(range(100)), [1e9 + i for i in range(10)],
        [1e-15 * i for i in range(10)], [float("nan"), 1, 2], [float("inf"), 1, 2]])
    return cases


def compare_values(expected, actual, path=""):
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(expected) != set(actual):
            raise AssertionError(f"{path}: keys {set(expected)} != {set(actual) if isinstance(actual, dict) else type(actual)}")
        if path.startswith("/result") and list(expected) != list(actual):
            raise AssertionError(f"{path}: serialized result/parameter object key order changed")
        for key, value in expected.items():
            compare_values(value, actual[key], path + "/" + key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            raise AssertionError(f"{path}: list length/type mismatch")
        for index, (left, right) in enumerate(zip(expected, actual)):
            compare_values(left, right, path + f"/{index}")
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            raise AssertionError(f"{path}: expected numeric {expected}, got {actual!r}")
        if "/parameters/" in path and type(expected) is not type(actual):
            raise AssertionError(f"{path}: parameter numeric representation changed: {type(expected).__name__} -> {type(actual).__name__}")
        if math.isnan(expected):
            equal = math.isnan(actual)
        elif math.isinf(expected):
            equal = expected == actual
        elif isinstance(expected, int):
            equal = expected == actual
        else:
            ci = "_ci" in path or "/ci_tracker_dict/" in path or "/confidence/" in path
            equal = math.isclose(expected, actual, rel_tol=1e-8 if ci else 1e-10,
                                 abs_tol=1e-10 if ci else 1e-12)
        if not equal:
            raise AssertionError(f"{path}: {expected!r} != {actual!r}")
    elif type(expected) is not type(actual) or expected != actual:
        raise AssertionError(f"{path}: {expected!r} != {actual!r}")


def generate():
    if np.__version__ != "1.26.4" or scipy.__version__ != "1.13.0":
        raise SystemExit("Use the pinned .venv-reference environment to generate authoritative fixtures")
    cases = make_cases()
    artifact = {"schema": 1, "python": platform.python_version(), "numpy": np.__version__,
                "scipy": scipy.__version__, "source_sha256": hashlib.sha256(
                    (ROOT / "reference-source" / "dicty_sim_test_env.py").read_bytes()).hexdigest(),
                "source_checker_sha256": hashlib.sha256((HERE / "check_source_behavior.py").read_bytes()).hexdigest(),
                "scope": "Unchanged AST bodies, actual SciPy, scripted high-level API results; no Python-seed equivalence.",
                "cases": cases}
    FIXTURES.write_text(json.dumps(artifact, indent=2, allow_nan=True) + "\n", encoding="utf-8")
    errors = [case["name"] for case in cases if "error" in case["expected"]]
    print(json.dumps({"fixtures": len(cases), "successful": len(cases) - len(errors),
                      "source_error_cases": errors, "path": str(FIXTURES)}, indent=2))


def compare(executable, only=None):
    fixture_data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    cases = fixture_data["cases"]
    if only:
        cases = [case for case in cases if only in case["name"]]
    results = []
    for case in cases:
        result = {"name": case["name"]}
        try:
            wire = case.get("request_wire", json.dumps(case["request"], allow_nan=True))
            completed = subprocess.run([str(executable)], input=wire,
                                       text=True, capture_output=True, timeout=30,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            actual = json.loads(completed.stdout)
            expected = case["expected"]
            if "error" in expected:
                assert completed.returncode != 0 and "error" in actual, (
                    f"Expected failure {expected['error']}, got {actual}")
                assert "script" not in actual["error"].lower(), (
                    f"Script adapter failure must not count as an expected model failure: {actual}")
                compare_values(expected["consumed"], actual["consumed"], "/consumed_before_error")
                result["reference_error"] = expected["error"]
                result["rust_error"] = actual["error"]
            else:
                assert completed.returncode == 0, actual
                # Extra Rust diagnostics/measurements are not Python phase outputs.
                compared = {key: actual[key] for key in expected}
                compare_values(expected, compared)
            result["status"] = "passed"
        except Exception as exc:
            result.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        results.append(result)
    report = {"fixture_sha256": hashlib.sha256(FIXTURES.read_bytes()).hexdigest(),
              "executable": str(executable), "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
              "checked_at_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
              "numpy": np.__version__, "scipy": scipy.__version__,
              "passed": sum(row["status"] == "passed" for row in results),
              "failed": sum(row["status"] == "failed" for row in results), "checks": results}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "checks"}, indent=2))
    for row in results:
        if row["status"] == "failed":
            print(row["name"] + ": " + row["error"])
    return bool(report["failed"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "compare"))
    parser.add_argument("--executable", type=Path, default=ROOT / "target" / "debug" / "dicty-fixture.exe")
    parser.add_argument("--only", help="Run fixture names containing this substring")
    args = parser.parse_args()
    if args.command == "generate":
        generate()
        return 0
    return compare(args.executable.resolve(), args.only)


if __name__ == "__main__":
    raise SystemExit(main())
