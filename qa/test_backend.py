"""Backend selection/failure tests, including a runtime with no OpenCL symbols."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'target' / 'release' / ('dicty-sim.exe' if os.name == 'nt' else 'dicty-sim')

class BackendSelection(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.work = Path(self.directory.name)
        self.cfg = json.loads((ROOT / 'reference-source' / 'import_template.json').read_text())
        self.cfg.update(n=2048, sl=256, n_runs=64, n_dev=1, vg=2, output_filepath='')

    def run_backend(self, backend, env=None):
        path = self.work / 'parameters.json'
        path.write_text(json.dumps(self.cfg))
        return subprocess.run([str(ENGINE), '--param', str(path), '--backend', backend,
                               '--events', '--seed', '739', '--result', str(self.work / 'result.json')],
                              env=env, capture_output=True, text=True, timeout=30,
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))

    def test_auto_small_workload_uses_cpu(self):
        self.cfg.update(n_runs=2)
        process = self.run_backend('auto')
        self.assertEqual(process.returncode, 0, process.stderr)
        event = json.loads(process.stdout.splitlines()[0])
        self.assertEqual(event['backend'], 'cpu')
        self.assertIn('small workload', event['backend_reason'])

    @unittest.skipUnless(os.name == 'nt', 'Windows runtime fault injection')
    def test_auto_falls_back_and_explicit_gpu_errors_when_runtime_has_no_opencl(self):
        env = os.environ.copy()
        # cl3 loads optional symbols. A normal system DLL stands in for an
        # installed runtime with no usable OpenCL API; no files are changed.
        env['OPENCL_DYLIB_PATH'] = str(Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'kernel32.dll')
        cpu = self.run_backend('cpu', env)
        self.assertEqual(cpu.returncode, 0, cpu.stderr)
        expected = (self.work / 'result.json').read_bytes()
        auto = self.run_backend('auto', env)
        self.assertEqual(auto.returncode, 0, auto.stderr)
        event = json.loads(auto.stdout.splitlines()[0])
        self.assertEqual(event['backend'], 'cpu')
        self.assertIn('CPU fallback:', event['backend_reason'])
        self.assertEqual((self.work / 'result.json').read_bytes(), expected)
        metadata = (self.work / 'result.json.run.json').read_bytes()
        gpu = self.run_backend('gpu', env)
        self.assertEqual(gpu.returncode, 1)
        self.assertEqual(json.loads(gpu.stdout.splitlines()[-1])['type'], 'error')
        self.assertEqual((self.work / 'result.json').read_bytes(), expected)
        self.assertEqual((self.work / 'result.json.run.json').read_bytes(), metadata)

if __name__ == '__main__': unittest.main()
