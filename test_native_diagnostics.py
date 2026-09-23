import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from qd_lint import main


class NativeDiagnosticsTests(unittest.TestCase):
    def run_case(self, engine, payload, status=0, log='', enabled=True):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, report = root / 'a.sv', root / 'report.json'
            source.write_text('module a; endmodule\n')
            calls = []

            def run(argv, **kwargs):
                calls.append(argv)
                if argv[-1] == '--version':
                    return subprocess.CompletedProcess(argv, 0, stdout='test engine', stderr='')
                option = '--diag-json' if engine == 'slang' else '--diagnostics-sarif-output'
                if enabled:
                    target = Path(argv[argv.index(option) + 1])
                    if payload is not None:
                        target.write_text(payload)
                else:
                    self.assertNotIn(option, argv)
                return subprocess.CompletedProcess(argv, status, stdout='', stderr=log)

            argv = ['qd-lint', 'check', '--filelist', str(source), '--top', 'a',
                    '--engine', engine, '--json', str(report)]
            with patch('sys.argv', argv + (['--native-diagnostics'] if enabled else [])), \
                 patch('qd_lint.shutil.which', return_value='/test/' + engine), \
                 patch('qd_lint.subprocess.run', side_effect=run), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = main()
            return code, json.loads(report.read_text())['results'][0]

    def test_native_data_and_console_preserved_for_both_engines(self):
        cases = [('slang', '[{"severity":"warning","message":"width","location":"a.sv:1:2"}]'),
                 ('verilator', '{"version":"2.1.0","runs":[{"results":[]}]}')]
        for engine, payload in cases:
            with self.subTest(engine=engine):
                code, result = self.run_case(engine, payload, 1, 'warning: retained\n')
                self.assertEqual(code, 1)
                self.assertEqual(result['diagnostics'], 'warning: retained\n')
                self.assertEqual(result['exit_status'], 1)
                native = result['native_diagnostics']
                self.assertEqual(native['status'], 'captured')
                self.assertEqual(native['raw'], payload)
                self.assertEqual(native['data'], json.loads(payload))

    def test_clean_empty_native_report(self):
        code, result = self.run_case('slang', '[]')
        self.assertEqual(code, 0)
        self.assertEqual(result['native_diagnostics']['data'], [])

    def test_missing_malformed_and_wrong_shape_never_pass(self):
        for payload in (None, '', '{broken', '{}', 'null'):
            with self.subTest(payload=payload):
                code, result = self.run_case('slang', payload)
                self.assertEqual(code, 1)
                self.assertEqual(result['exit_status'], 0)
                self.assertEqual(result['classification'], 'error')
                self.assertEqual(result['native_diagnostics']['status'], 'error')
                self.assertEqual(result['native_diagnostics']['raw'], payload)
                self.assertTrue(result['native_diagnostics']['error'])

    def test_native_findings_cannot_be_clean_when_console_is_empty(self):
        for engine, payload in (
            ('slang', '[{"severity":"warning","message":"width"}]'),
            ('verilator', '{"version":"2.1.0","runs":[{"results":[{"level":"error","message":{"text":"broken"}}]}]}'),
        ):
            code, result = self.run_case(engine, payload)
            self.assertEqual(code, 1)
            self.assertNotEqual(result['classification'], 'clean')
            self.assertEqual(result['exit_status'], 0)

    def test_invalid_sarif_retained(self):
        payload = '{"version":"2.1.0","runs":[{"tool":{} "invocations":[]}]}'
        code, result = self.run_case('verilator', payload)
        self.assertEqual(code, 1)
        self.assertEqual(result['native_diagnostics']['raw'], payload)

    def test_default_invocation_is_unchanged(self):
        code, result = self.run_case('slang', None, enabled=False)
        self.assertEqual(code, 0)
        self.assertNotIn('native_diagnostics', result)


if __name__ == '__main__':
    unittest.main()
