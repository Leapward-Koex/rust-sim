"""Compare complete CPU and GPU jobs with identical seeds and byte-exact results."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import psutil

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cycles', type=int, default=20)
    parser.add_argument('--repeats', type=int, default=1000)
    parser.add_argument('--samples', type=int, default=1)
    parser.add_argument('--cases', nargs='+', default=['ordinary'], choices=['ordinary', 'sex-heavy', 'higher-locus'])
    parser.add_argument('--batch-size', type=int, default=128)
    parser.add_argument('--gpu-workers', type=int)
    parser.add_argument('--backends', nargs='+', default=['cpu', 'gpu'], choices=['cpu', 'gpu'])
    parser.add_argument('--report', type=Path, default=ROOT / 'verification' / 'gpu-benchmark.json')
    args = parser.parse_args()
    work = ROOT / 'build' / f'gpu-benchmark-{time.time_ns()}'
    work.mkdir(parents=True)
    engine = ROOT / 'target' / 'release' / 'dicty-sim.exe'
    report = {'cycles': args.cycles, 'repeats': args.repeats, 'batch_size': args.batch_size,
              'logical_cpus': os.cpu_count(), 'engine_sha256': hashlib.sha256(engine.read_bytes()).hexdigest(),
              'gpu_workers_requested': args.gpu_workers, 'backends': args.backends,
              'method': 'Fresh process wall time includes startup, GPU compilation/cache, transfers, all phases, aggregation and export. Process CPU time and peak working set sampled every 20ms. Identical seed 20261007; results compared byte for byte across selected backends/samples. CPU uses default logical CPUs minus one; actual workers recorded per run.', 'cases': {}}
    for case in args.cases:
        cfg = json.loads((ROOT / 'reference-source' / 'import_template.json').read_text())
        cfg.update(n_runs=args.repeats, n_dev=args.cycles, output_filepath='')
        if case == 'sex-heavy': cfg.update(sex_cycle_interval=2, ch_start=0.3, res_start=0.2)
        if case == 'higher-locus': cfg.update(gene_pairs=12, ch_start=0.3, res_start=0.2)
        params = work / f'{case}.json'
        params.write_text(json.dumps(cfg))
        runs = report['cases'][case] = []
        expected = None
        for sample in range(args.samples):
            for backend in (args.backends if sample % 2 == 0 else list(reversed(args.backends))):
                result = work / f'{case}-{backend}-{sample}.json'
                log = result.with_suffix('.log')
                command = [str(engine), '--param', str(params), '--seed', '20261007', '--backend', backend,
                           '--gpu-batch-size', str(args.batch_size), '--result', str(result), '--events']
                if backend == 'gpu' and args.gpu_workers is not None:
                    command.extend(['--threads', str(args.gpu_workers)])
                begin = time.perf_counter()
                cpu = peak = 0
                with log.open('wb') as output:
                    proc = subprocess.Popen(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT,
                                            creationflags=subprocess.CREATE_NO_WINDOW)
                    watcher = psutil.Process(proc.pid)
                    while proc.poll() is None:
                        try:
                            mem = watcher.memory_info()
                            peak = max(peak, mem.rss, getattr(mem, 'peak_wset', 0))
                            times = watcher.cpu_times()
                            cpu = times.user + times.system
                        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
                        if time.perf_counter() - begin > 1800:
                            proc.kill(); proc.wait()
                            raise TimeoutError(str(log))
                        time.sleep(.02)
                wall = time.perf_counter() - begin
                if proc.returncode: raise RuntimeError(log.read_text())
                digest = hashlib.sha256(result.read_bytes()).hexdigest()
                if expected is None: expected = digest
                if digest != expected: raise AssertionError(f'CPU/GPU results differ: {case}, {sample}')
                metadata = json.loads(Path(str(result) + '.run.json').read_text())
                record = dict(backend=backend, sample=sample, seconds=wall, cpu_seconds_sampled=cpu,
                              average_cpu_cores=cpu/wall, peak_working_set_bytes=peak,
                              result_sha256=digest, threads=metadata['threads'], device=metadata['device'])
                runs.append(record)
                print(json.dumps(dict(case=case, **record)), flush=True)
                args.report.write_text(json.dumps(report, indent=2))
    report['compared_result_pairs'] = sum(max(0, len(runs) - 1) for runs in report['cases'].values())
    report['exact_results_match'] = True if report['compared_result_pairs'] else None
    args.report.write_text(json.dumps(report, indent=2))

if __name__ == '__main__': main()
