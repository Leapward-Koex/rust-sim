"""Check captured Python behavior; this is verification tooling, not a new engine.

Loads unchanged AST function/class bodies from reference-source. GUI/import-time
dependencies are excluded. Real NumPy is used. SciPy calls are inspected through
a spy: these checks do not claim to validate SciPy's numerical implementation.
Run with Python and NumPy installed: python -B verification/check_source_behavior.py
"""

import ast
import contextlib
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import platform
import random
import sys
import time
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'reference-source'
TRACKERS = ('cheater_allele_counts', 'resistor_allele_counts', 'wild_counts',
            'mean_ch_eff', 'mean_res_eff', 'mt1_ratios', 'mt2_ratios',
            'mt3_ratios', 'locus_plot')
FUNCTIONS = {'Cell', 'fifty_fifty', 'mean_confidence_interval', 'initialise_pop',
             'vegetative_growth', 'developmental_cycle', 'sexual_cycle', 'main',
             'submit_form', 'validate_entry'}
RESULTS = []


class StatsSpy:
    def __init__(self):
        self.calls = []
        self.t = SimpleNamespace(ppf=self.ppf)

    def sem(self, a):
        self.calls.append(('sem', list(a)))
        return 2.0

    def ppf(self, q, df):
        self.calls.append(('ppf', q, df))
        return 3.0


def environment(**overrides):
    ns = {'__name__': 'captured_reference'}
    for name in ('global_variables.py', 'locus.py', 'locus_tracker.py'):
        exec(compile((SOURCE / name).read_text(), name, 'exec'), ns)
    ns.update(random=random.Random(1729), math=math, np=np,
              sys=SimpleNamespace(argv=['verification', '--param']),
              json=json, timer=time.perf_counter, st=StatsSpy())
    ns.update({key: [] for key in TRACKERS})
    tree = ast.parse((SOURCE / 'dicty_sim_test_env.py').read_text())
    body = [n for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in FUNCTIONS]
    exec(compile(ast.Module(body=body, type_ignores=[]),
                 'dicty_sim_test_env.py', 'exec'), ns)
    # Apply config after definitions, as CLI/GUI do (important for CI default).
    ns['variables'].update(i_macrocyst=[0], output_filepath='')
    ns['variables'].update(overrides)
    return ns


def cell(ns, pairs=((0, 0),), mt=1):
    return ns['Cell'](0, 0, 1, mt, 0,
                      [ns['Locus'](*pair) for pair in pairs])


def quiet(fn, *args):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args)


def expect_error(kind, fn, *args):
    try:
        quiet(fn, *args)
    except kind:
        return
    raise AssertionError(f'Expected {kind.__name__}')


def check(name, fn):
    try:
        detail = fn()
        RESULTS.append({'check': name, 'status': 'passed', 'detail': detail})
    except Exception as exc:
        RESULTS.append({'check': name, 'status': 'failed',
                        'error': f'{type(exc).__name__}: {exc}'})


def snapshots_match():
    manifest = json.loads((ROOT / 'source-manifest.json').read_text())
    copied = [r for r in manifest['files'] if r['snapshot']]
    for row in copied:
        assert hashlib.sha256((SOURCE / row['path']).read_bytes()).hexdigest() == row['sha256'], row['path']
    return {'files_verified': len(copied)}


def clone_identity():
    ns = environment()
    a = cell(ns)
    b = a.clone()
    assert a.key == 0 and b.key == 1 and a != b
    assert a.loci != b.loci and a.loci[0] is not b.loci[0]
    b.loci[0].cheater_allele = 1
    assert a.cheater_value() == 0
    assert a.loci == a.loci.copy()


def measurements_and_effects():
    ns = environment(gene_pairs=1, n=4, sl=4, sp=1)
    pop = [cell(ns, [p], mt=i % 3 + 1)
           for i, p in enumerate(((0, 0), (1, 0), (0, 1), (1, 1)))]
    quiet(ns['developmental_cycle'], pop)
    assert ns['cheater_allele_counts'] == [.5]
    assert ns['resistor_allele_counts'] == [.5]
    assert ns['wild_counts'] == [.5]
    assert ns['mean_ch_eff'] == [.5] and ns['mean_res_eff'] == [.5]
    t = ns['locus_plot'][0][0]
    assert [t.ch_count, t.res_count, t.both_count] == [1, 1, 1]
    assert ns['mt1_ratios'] == [.5]


def exploitability_truth_table():
    ns = environment(gene_pairs=1)
    count = 0
    for ce, re, c, r, oc, ore in itertools.product((0, 1), repeat=6):
        ns['variables'].update(ch_eff_rc=ce, res_eff_rc=re)
        actor = cell(ns, [(c, r)])
        target = cell(ns, [(oc, ore)])
        active_actor = bool(c and (ce == 1 or not r))
        protected_cheater = bool(oc and (ce == 1 or not ore))
        vulnerable_resistance = bool(not ore or (re == 0 and oc))
        expected = int(active_actor and not protected_cheater and vulnerable_resistance)
        assert actor.exploitable(target) == expected, (ce, re, c, r, oc, ore)
        count += 1
    ns['variables'].update(ch_eff_rc=.5, res_eff_rc=0)
    assert cell(ns, [(1, 0)]).exploitable(cell(ns)) == 0
    ns['variables'].update(ch_eff_rc=0, res_eff_rc=.5)
    assert cell(ns, [(1, 0)]).exploitable(cell(ns)) == 0
    return {'binary_cases': count, 'fractional_gate_cases': 2}


def init_exclusive_overlap():
    ns = environment(n=4, gene_pairs=1, ch_start=.25, res_start=.25,
                     ch_res_dist=0)
    pop = quiet(ns['initialise_pop'])
    assert [(c.cheater_value(), c.resistor_value()) for c in pop] == [(1, 1), (0, 0), (0, 0), (0, 0)]


def init_rounding_and_whole_genome():
    ns = environment(n=5, gene_pairs=2, ch_start=.5, res_start=0)
    pop = quiet(ns['initialise_pop'])
    assert len(pop) == 5  # No rounding to an even population.
    assert sum(c.cheater_value() > 0 for c in pop) == 2  # round(2.5)==2
    assert all(c.cheater_value() in (0, 2) for c in pop)


def vegetative_fitness():
    ns = environment(n=1, gene_pairs=1, vg=1, c_ch=.2, c_res=.4,
                     m_ch=-1, m_re=-1)
    parent = cell(ns, [(1, 1)])
    children = quiet(ns['vegetative_growth'], [parent])
    assert math.isclose(parent.fitness, 1.1)
    assert children[0].fitness == parent.fitness
    assert children[0].key != parent.key


def mutation_inclusive_zero():
    ns = environment(n=1, gene_pairs=1, vg=1, m_ch=0, m_re=0)
    ns['random'] = SimpleNamespace(uniform=lambda a, b: 0,
                                   choices=lambda *a, **k: [0])
    out = ns['vegetative_growth']([cell(ns, [(0, 1)])])
    assert out[0].cheater_value() == 1 and out[0].resistor_value() == 0


def germination_strict_boundary():
    ns = environment(n=1, gene_pairs=1, vg=0, ch_germ=.5)
    ns['random'] = SimpleNamespace(uniform=lambda a, b: .5)
    pop = [cell(ns, [(1, 0)])]
    assert ns['vegetative_growth'](pop) is pop and len(pop) == 1
    ns['random'] = SimpleNamespace(uniform=lambda a, b: .5001)
    assert ns['vegetative_growth'](pop) is pop and pop == []


def slug_leftovers_and_aliasing():
    ns = environment(n=5, sl=2, gene_pairs=1, sp=1)
    ns['random'] = SimpleNamespace(sample=lambda seq, k: list(seq)[:k], uniform=lambda a, b: .5)
    pop = [cell(ns, mt=i + 1) for i in range(5)]
    leftover = pop[-1]
    out = quiet(ns['developmental_cycle'], pop)
    assert len(out) == 4 and pop == [leftover]
    assert all(c.key >= 5 for c in out)


def nondiscrete_keeps_slug():
    ns = environment(n=4, sl=4, gene_pairs=1, sp=0, discrete_res=0)
    ns['random'] = SimpleNamespace(sample=lambda seq, k: list(seq)[:k])
    assert len(quiet(ns['developmental_cycle'], [cell(ns) for _ in range(4)])) == 4


def passive_only_error():
    ns = environment(n=2, sl=2, gene_pairs=1, resistance_type=2)
    pop = [cell(ns), cell(ns)]
    expect_error(ZeroDivisionError, ns['developmental_cycle'], pop)
    assert pop == []


def duplicate_stalk_deletion():
    ns = environment(n=4, sl=4, gene_pairs=1, sp=.5)
    draws = iter((.1, .1, .9, .9))
    ns['random'] = SimpleNamespace(sample=lambda seq, k: list(seq)[:k], uniform=lambda a, b: next(draws))
    ns['np'] = SimpleNamespace(random=SimpleNamespace(randint=lambda low, high: 0))
    pop = [cell(ns, [(0, 0)], mt=1), cell(ns, [(1, 0)], mt=2),
           cell(ns, [(0, 0)], mt=3), cell(ns, [(0, 0)], mt=1)]
    out = quiet(ns['developmental_cycle'], pop)
    assert [c.mating_type for c in out] == [3, 1]
    assert pop == []
    return 'XOR candidate set {0,2,3}; index 0 selected twice; two front cells deleted. Set-list order is this runtime\'s order.'


def all_stalk_failure():
    ns = environment(n=1, sl=1, gene_pairs=1, sp=0)
    expect_error(ZeroDivisionError, ns['developmental_cycle'], [cell(ns)])
    ns = environment(n=1, sl=1, gene_pairs=1, sp=0)
    expect_error(ValueError, ns['developmental_cycle'], [cell(ns, [(1, 0)])])


def sex_setup(**params):
    ns = environment(gene_pairs=1, mc_count=1, mc_germ_count=2, **params)
    ns['random'] = SimpleNamespace(sample=lambda seq, k: list(seq)[:k], uniform=lambda a, b: 0)
    return ns


def sex_equal_values_still_recombines():
    ns = sex_setup(recomb_chance=1)
    calls = []
    ns['np'] = SimpleNamespace(random=SimpleNamespace(randint=lambda a, b: calls.append((a, b)) or 1))
    parents = [cell(ns, [(1, 0)], 1), cell(ns, [(1, 0)], 2)]
    out = quiet(ns['sexual_cycle'], parents)
    assert len(calls) == 3  # Two alleles + mating type, not equality branch's one.
    assert len(parents) == 2 and len(out) == 2
    assert out[0].loci[0] is not out[1].loci[0]


def sex_shared_loci_identity_branch():
    ns = sex_setup(recomb_chance=1)
    ns['random'] = SimpleNamespace(sample=lambda seq, k: list(seq)[:k])
    calls = []
    ns['np'] = SimpleNamespace(random=SimpleNamespace(randint=lambda a, b: calls.append((a, b)) or 1))
    a, b = cell(ns, [(1, 0)], 1), cell(ns, [(1, 0)], 2)
    b.loci = a.loci.copy()
    out = quiet(ns['sexual_cycle'], [a, b])
    assert len(calls) == 1 and out[0].mating_type == 1


def sex_no_recombination_inherits_parent():
    ns = sex_setup(recomb_chance=0)
    ns['np'] = SimpleNamespace(random=SimpleNamespace(randint=lambda a, b: 0))
    out = quiet(ns['sexual_cycle'], [cell(ns, [(1, 0)], 1), cell(ns, [(0, 1)], 2)])
    assert all((c.cheater_value(), c.resistor_value(), c.mating_type) == (0, 1, 2) for c in out)


def sex_alleles_independent_and_clones():
    ns = sex_setup(recomb_chance=1)
    draws = iter((1, 0, 0))
    ns['np'] = SimpleNamespace(random=SimpleNamespace(randint=lambda a, b: next(draws)))
    out = quiet(ns['sexual_cycle'], [cell(ns, [(1, 0)], 1), cell(ns, [(0, 1)], 2)])
    assert all((c.cheater_value(), c.resistor_value(), c.mating_type) == (1, 1, 2) for c in out)
    out[0].loci[0].cheater_allele = 0
    assert out[1].cheater_value() == 1


def sex_partner_failure():
    ns = sex_setup()
    # Use real sample so empty-partner selection raises, rather than the simple stub.
    ns['random'] = random.Random(1729)
    expect_error(ValueError, ns['sexual_cycle'], [cell(ns), cell(ns)])


def confidence_bound_default():
    ns = environment(confidence_interval=.1)
    assert ns['mean_confidence_interval']([2, 4, 6]) == 6
    assert ns['st'].calls == [('sem', [2.0, 4.0, 6.0]), ('ppf', .975, 2)]
    assert ns['mean_confidence_interval']([2, 4, 6], .8) == 6
    assert ns['st'].calls == [('sem', [2.0, 4.0, 6.0]), ('ppf', .975, 2),
                              ('sem', [2.0, 4.0, 6.0]), ('ppf', .9, 2)]
    return 'Checks original function call wiring with spy sem=2 and ppf=3; not a SciPy numeric result.'


def orchestrated(interval, schedule):
    ns = environment(n_runs=2, n_dev=4, gene_pairs=1,
                     sex_cycle_interval=interval, i_macrocyst=schedule)
    events = []
    point = [0]
    def record():
        for index, key in enumerate(TRACKERS[:-1]):
            ns[key].append(float(point[0] + index * 100))
        ns['locus_plot'].append([ns['LocusTracker']('Locus0', point[0], 2, 3)])
        point[0] += 1
    def init():
        events.append('init')
        record()
        return []
    def veg(pop):
        events.append('veg')
        return pop
    def dev(pop):
        events.append('dev')
        record()
        return pop
    def sex(pop):
        events.append('sex')
        return pop
    ns.update(initialise_pop=init, vegetative_growth=veg,
              developmental_cycle=dev, sexual_cycle=sex)
    # Main orchestration/aggregation runs unchanged; stage functions are spies.
    class CapturedFile(io.StringIO):
        def __exit__(self, *args):
            return False
    captured = CapturedFile()
    opened = []
    def capture_open(path, mode):
        opened.append((path, mode))
        return captured
    ns['open'] = capture_open
    ns['variables']['output_filepath'] = 'result.json'
    result = quiet(ns['main'])
    assert result is None
    assert opened == [('result.json.json', 'w')]
    data = json.loads(captured.getvalue())
    assert all(ns[key] == [] for key in TRACKERS)
    return data, events


def interval_orchestration():
    data, events = orchestrated(2, [0])
    assert data['sex_cycle_list'] == [2, 4, 2, 4]
    assert events == (['init', 'veg', 'dev', 'sex', 'veg', 'dev',
                       'veg', 'dev', 'sex', 'veg', 'dev'] * 2)
    assert data['mean_ch'] == [2.5, 3.5, 4.5, 5.5, 6.5]
    output_series = ['mean_ch', 'mean_res', 'mean_wild', 'graph_mean_ch_eff',
                     'graph_mean_res_eff', 'mean_mt1', 'mean_mt2', 'mean_mt3']
    for index, key in enumerate(output_series):
        assert data[key] == [index * 100 + 2.5 + t for t in range(5)], key
    assert data['average_tracker_dict']['gene_pair0'] == [[2.5, 3.5, 4.5, 5.5, 6.5], [2.0]*5, [3.0]*5]
    assert data['ch_ci'] == [6.0]*5
    assert list(data) == ['parameters','sex_cycle_list','x_axis_values','mean_ch','ch_ci','mean_res','res_ci','mean_wild','wild_ci','mean_mt1','mt1_ci','mean_mt2','mt2_ci','mean_mt3','mt3_ci','graph_mean_ch_eff','ch_eff_ci','graph_mean_res_eff','res_eff_ci','average_tracker_dict','ci_tracker_dict']
    return 'Original main with stage spies and StatsSpy; schema, averaging, resets, scheduling checked.'


def list_orchestration():
    data, events = orchestrated(2, [1, 3])
    assert data['sex_cycle_list'] == []
    assert events == (['init', 'sex', 'veg', 'dev', 'veg', 'dev',
                       'sex', 'veg', 'dev', 'veg', 'dev'] * 2)


def invalid_scheduler_list():
    ns = environment(n_runs=1, n_dev=1, gene_pairs=1, n=2, i_macrocyst=[], sex_cycle_interval=2)
    expect_error(IndexError, ns['main'])
    ns = environment(n_runs=1, n_dev=1, gene_pairs=1, n=2, i_macrocyst='0')
    expect_error(TypeError, ns['main'])


def no_runs_error():
    ns = environment(n_runs=0)
    expect_error(IndexError, ns['main'])


def gui_numeric_mismatch():
    ns = environment()
    assert ns['validate_entry']('') is True
    assert ns['validate_entry']('0.5') is True
    ns['entry_widgets'] = {'ch_eff_rc': SimpleNamespace(get=lambda: '0.5')}
    expect_error(ValueError, ns['submit_form'])


def empty_init_errors():
    for params in ({'n': 0}, {'gene_pairs': 0}):
        ns = environment(**params)
        expect_error(ZeroDivisionError, ns['initialise_pop'])
        assert len(ns['locus_plot']) == 1
        assert all(ns[key] == [] for key in TRACKERS[:-1])


def negative_locus_and_slug_bounds():
    ns = environment(n=2, gene_pairs=-1)
    out = quiet(ns['initialise_pop'])
    assert len(out) == 2 and all(c.loci == [] for c in out)
    assert math.copysign(1, ns['cheater_allele_counts'][0]) == -1
    ns = environment(n=-2, sl=1, gene_pairs=1)
    pop = [cell(ns)]
    expect_error(ZeroDivisionError, ns['developmental_cycle'], pop)
    assert len(pop) == 1  # Negative range bound creates no slugs.
    ns = environment(gene_pairs=-1, mc_count=1, mc_germ_count=1, recomb_chance=1)
    ns['random'] = SimpleNamespace(sample=lambda seq, k: list(seq)[:k], uniform=lambda a, b: .5)
    draws = []
    ns['np'] = SimpleNamespace(random=SimpleNamespace(randint=lambda a, b: draws.append((a, b)) or 1))
    expect_error(ZeroDivisionError, ns['sexual_cycle'], [cell(ns, mt=1), cell(ns, mt=2)])
    assert draws == [(0, 2)]


def mutation_draw_order_and_stale_fitness():
    ns = environment(n=2, gene_pairs=2, vg=1, m_ch=.5, m_re=.5, c_ch=.2, c_res=.4)
    draws = iter((0, 1, 1, 0, 1, 0, 0, 1))
    events = []
    def choose(*args, **kwargs):
        events.append(('choices', kwargs['k'], list(kwargs['weights'])))
        return [0, 0]
    def uniform(a, b):
        value = next(draws)
        events.append(('uniform', value))
        return value
    ns['random'] = SimpleNamespace(choices=choose, uniform=uniform)
    parent = cell(ns, [(0, 0), (0, 0)])
    out = ns['vegetative_growth']([parent])
    assert events[0] == ('choices', 2, [1.5])
    assert [e[1] for e in events[1:]] == [0, 1, 1, 0, 1, 0, 0, 1]
    assert [[(l.cheater_allele, l.resistor_allele) for l in c.loci] for c in out] == [[(1, 0), (0, 1)], [(0, 1), (1, 0)]]
    assert all(c.fitness == 1.5 for c in out)
    assert parent.cheater_value() == parent.resistor_value() == 0


def stale_measurements_at_main_entry():
    ns = environment(n_runs=0, n_dev=-1)
    ns['cheater_allele_counts'] = [123]
    quiet(ns['main'])
    assert ns['cheater_allele_counts'] == [123]


def failed_run_contaminates_next_run():
    ns = environment(n_runs=1, n_dev=1, n=2, sl=2, gene_pairs=1,
                     i_macrocyst=[], sex_cycle_interval=1, ch_start=0)
    expect_error(IndexError, ns['main'])
    assert all(len(ns[key]) == 1 for key in TRACKERS)
    ns['variables'].update(n_dev=0, ch_start=1, i_macrocyst=[0],
                           sex_cycle_interval=0, output_filepath='captured')
    sink = io.StringIO()
    ns['open'] = lambda path, mode: contextlib.nullcontext(sink)
    quiet(ns['main'])
    output = json.loads(sink.getvalue())
    assert output['parameters']['ch_start'] == 1
    assert output['mean_ch'] == [0.0]
    assert all(ns[key] == [] for key in TRACKERS)


def json_nonfinite_defaults():
    assert json.dumps({'ci': float('nan')}) == '{"ci": NaN}'


CHECKS = [snapshots_match, clone_identity, measurements_and_effects,
          exploitability_truth_table, init_exclusive_overlap,
          init_rounding_and_whole_genome, vegetative_fitness,
          mutation_inclusive_zero, germination_strict_boundary,
          slug_leftovers_and_aliasing, nondiscrete_keeps_slug,
          passive_only_error, duplicate_stalk_deletion, all_stalk_failure,
          sex_equal_values_still_recombines, sex_shared_loci_identity_branch,
          sex_no_recombination_inherits_parent, sex_alleles_independent_and_clones,
          sex_partner_failure, confidence_bound_default, interval_orchestration,
          list_orchestration, invalid_scheduler_list, no_runs_error,
          gui_numeric_mismatch, empty_init_errors, negative_locus_and_slug_bounds,
          mutation_draw_order_and_stale_fitness, stale_measurements_at_main_entry,
          failed_run_contaminates_next_run, json_nonfinite_defaults]

if __name__ == '__main__':
    for fn in CHECKS:
        check(fn.__name__, fn)
    report = {'source_commit': '62d707eee5f348320d6e50ab034b18a3a1a45b23',
              'python': platform.python_version(), 'numpy': np.__version__,
              'platform': platform.platform(),
              'scope': 'Unchanged source AST bodies. Controlled RNG draws in named checks. Main scheduling/aggregation uses stage spies. SciPy numerical routines, full GUI and end-to-end installed application are not executed.',
              'passed': sum(r['status'] == 'passed' for r in RESULTS),
              'failed': sum(r['status'] == 'failed' for r in RESULTS),
              'checks': RESULTS}
    (ROOT / 'verification' / 'results.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    sys.exit(bool(report['failed']))
