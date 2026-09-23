"""Compilation-unit choice is explicit, reproducible and engine-specific."""
import contextlib
import io
import json
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from qd_lint import main


class CompilationUnitTests(unittest.TestCase):
    def run_case(self, engine='both', single=False, status=0, diagnostic=''):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'a.sv').write_text('module a; endmodule\n')
            output = root/'report.json'
            argv = ['qd-lint', 'check', '--filelist', str(root/'a.sv'), '--top', 'a',
                    '--engine', engine, '--audit-inputs', '--json', str(output)]
            calls = []
            def run(args, **kwargs):
                calls.append(args)
                return subprocess.CompletedProcess(args, 0 if '--version' in args else status,
                                                   stdout='test version' if '--version' in args else '',
                                                   stderr='' if '--version' in args else diagnostic)
            with patch('sys.argv', argv + (['--slang-single-unit'] if single else [])), \
                 patch('qd_lint.shutil.which', side_effect=lambda name: '/test/'+name), \
                 patch('qd_lint.subprocess.run', side_effect=run), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = main()
            return code, json.loads(output.read_text()), calls

    def test_explicit_option_only_reaches_slang(self):
        code, report, calls = self.run_case(single=True)
        self.assertEqual(code, 0)
        lint_calls = [args for args in calls if '--version' not in args]
        self.assertEqual(len(lint_calls), 2)
        self.assertNotIn('--single-unit', lint_calls[0])
        self.assertIn('--single-unit', lint_calls[1])
        self.assertEqual(report['input_manifest']['slang_compilation_unit'], 'single')
        self.assertEqual(report['slang_compilation_unit'], 'single')
        manifest = report['input_manifest']
        canonical = json.dumps(manifest, sort_keys=True, separators=(',', ':'))
        self.assertEqual(report['input_manifest_sha256'], hashlib.sha256(canonical.encode()).hexdigest())
        del manifest['slang_compilation_unit']
        default = json.dumps(manifest, sort_keys=True, separators=(',', ':'))
        self.assertNotEqual(report['input_manifest_sha256'], hashlib.sha256(default.encode()).hexdigest())

    def test_default_does_not_add_option_or_change_manifest_shape(self):
        _, report, calls = self.run_case()
        self.assertTrue(all('--single-unit' not in args for args in calls))
        self.assertNotIn('slang_compilation_unit', report)
        self.assertNotIn('slang_compilation_unit', report['input_manifest'])

    def test_verilator_only_rejects_unused_slang_option(self):
        with self.assertRaises(SystemExit) as error:
            self.run_case(engine='verilator', single=True)
        self.assertEqual(error.exception.code, 2)

    def test_warning_and_engine_failure_remain_failures(self):
        for status, diagnostic in ((0, 'warning: retained\n'), (1, 'error: retained\n')):
            code, report, _ = self.run_case(engine='slang', single=True, status=status, diagnostic=diagnostic)
            self.assertEqual(code, 1)
            self.assertEqual(report['results'][0]['diagnostics'], diagnostic)
            self.assertEqual(report['results'][0]['exit_status'], status)

    @unittest.skipUnless(shutil.which('slang'), 'optional real slang regression')
    def test_real_macro_scope_and_source_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'defs.svh').write_text('`define QD_VALUE 1\n')
            (root/'a.sv').write_text('module a(output logic y); assign y = `QD_VALUE; endmodule\n')
            for single, reverse, expected in ((False, False, 1), (True, False, 0), (True, True, 1)):
                sources = ['defs.svh', 'a.sv']
                if reverse: sources.reverse()
                (root/'input.vf').write_text('\n'.join(sources))
                args = [sys.executable, str(Path(__file__).parent/'qd_lint.py'), 'check',
                        '--filelist', str(root/'input.vf'), '--top', 'a', '--engine', 'slang',
                        '--json', str(root/'report.json')]
                run = subprocess.run(args + (['--slang-single-unit'] if single else []),
                                     capture_output=True, text=True)
                self.assertEqual(run.returncode, expected, run.stdout + run.stderr)
                report = json.loads((root/'report.json').read_text())
                direct = subprocess.run(['slang', '--lint-only', '--top', 'a'] +
                                        (['--single-unit'] if single else []) +
                                        [str(root/name) for name in sources], capture_output=True, text=True)
                self.assertEqual(report['results'][0]['exit_status'], direct.returncode)
