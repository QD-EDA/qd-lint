"""Resolved input evidence, independent of installed lint engines."""
import hashlib
import json
import os
import contextlib
import io
import tempfile
import unittest
import subprocess
from pathlib import Path
from unittest.mock import patch

from qd_lint import InputError, audit_inputs, main, read_inputs


class InputAuditTests(unittest.TestCase):
    def test_audited_run_detects_changed_header_after_engine(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            header = root / 'header.svh'
            header.write_text('`define WIDTH 8\n')
            source = root / 'a.sv'
            source.write_text('module a; endmodule\n')
            filelist = root / 'design.vf'
            filelist.write_text('+incdir+. a.sv\n')
            output = root / 'report.json'

            def run(argv, **kwargs):
                if '--version' in argv:
                    return subprocess.CompletedProcess(argv, 0, 'fake 1.0\n', '')
                header.write_text('`define WIDTH 16\n')
                return subprocess.CompletedProcess(argv, 0, '', '')

            with patch('sys.argv', ['qd-lint', 'check', '--filelist', str(filelist),
                                    '--top', 'a', '--engine', 'slang', '--audit-inputs',
                                    '--json', str(output)]), \
                 patch('qd_lint.shutil.which', return_value='/fake/slang'), \
                 patch('qd_lint.subprocess.run', side_effect=run), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 1)
            report = json.loads(output.read_text())
            self.assertEqual(report['results'][0]['classification'], 'clean')
            self.assertEqual(report['input_consistency']['status'], 'changed')
            self.assertNotEqual(report['input_manifest_sha256'],
                                report['input_consistency']['post_input_manifest_sha256'])
            original = {item['path']: item['sha256'] for item in report['input_manifest']['files']}
            self.assertEqual(original[str(header)], hashlib.sha256(b'`define WIDTH 8\n').hexdigest())

    def test_audited_run_stable_and_removed_input(self):
        for remove in (False, True):
            with self.subTest(remove=remove), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                source = root / 'a.sv'
                source.write_text('module a; endmodule\n')
                output = root / 'report.json'

                def run(argv, **kwargs):
                    if '--version' in argv:
                        return subprocess.CompletedProcess(argv, 0, 'fake 1.0\n', '')
                    if remove:
                        source.unlink()
                    return subprocess.CompletedProcess(argv, 0, '', '')

                with patch('sys.argv', ['qd-lint', 'check', '--filelist', str(source),
                                        '--top', 'a', '--engine', 'slang', '--audit-inputs',
                                        '--json', str(output)]), \
                     patch('qd_lint.shutil.which', return_value='/fake/slang'), \
                     patch('qd_lint.subprocess.run', side_effect=run), \
                     contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(), 1 if remove else 0)
                report = json.loads(output.read_text())
                self.assertEqual(report['input_consistency']['status'], 'error' if remove else 'stable')
                self.assertEqual(report['results'][0]['classification'], 'clean')

    def test_repeatability_content_and_configuration_sensitivity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'inc').mkdir()
            header = root / 'inc' / 'config'  # Includes need not have an HDL suffix.
            header.write_text('`define WIDTH 8\n')
            (root / 'a.sv').write_text('module a; endmodule\n')
            (root / 'b.sv').write_text('module b; endmodule\n')
            filelist = root / 'design.vf'
            filelist.write_text('+incdir+inc +define+WIDTH=${QD_AUDIT_WIDTH} a.sv b.sv\n')
            with patch.dict(os.environ, QD_AUDIT_WIDTH='8'):
                inputs = read_inputs(filelist)
            original = audit_inputs(*inputs, 'a', 'both')
            self.assertEqual(original, audit_inputs(*inputs, 'a', 'both'))
            self.assertFalse(original['dependency_closure_complete'])
            hashes = {item['path']: item['sha256'] for item in original['files']}
            self.assertEqual(hashes[str(header)], hashlib.sha256(header.read_bytes()).hexdigest())
            variants = [audit_inputs(*inputs, 'b', 'both'), audit_inputs(*inputs, 'a', 'slang')]
            with patch.dict(os.environ, QD_AUDIT_WIDTH='16'):
                variants.append(audit_inputs(*read_inputs(filelist), 'a', 'both'))
            sources, incdirs, defines, lists = inputs
            variants.append(audit_inputs(list(reversed(sources)), incdirs, defines, lists, 'a', 'both'))
            header.write_text('`define WIDTH 16\n')
            variants.append(audit_inputs(*inputs, 'a', 'both'))
            header.unlink()
            variants.append(audit_inputs(*inputs, 'a', 'both'))
            for changed in variants:
                self.assertNotEqual(json.dumps(original, sort_keys=True), json.dumps(changed, sort_keys=True))

    def test_empty_include_directory_and_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            dirs = [root / 'first', root / 'second']
            for path in dirs:
                path.mkdir()
            source = root / 'a.sv'
            source.write_text('module a; endmodule\n')
            a = audit_inputs([source], dirs, [], [], 'a', 'both')
            b = audit_inputs([source], list(reversed(dirs)), [], [], 'a', 'both')
            self.assertEqual(len(a['files']), 1)
            self.assertNotEqual(a['include_directories'], b['include_directories'])

    def test_symlinks_and_special_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            link = root / 'loop'
            link.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(InputError, 'symlink'):
                audit_inputs([], [root], [], [], 'a', 'both')
            source, filelist = root / 'a.sv', root / 'design.vf'
            source.write_text('module a; endmodule\n')
            filelist.write_text('+incdir+. a.sv\n')
            with patch('sys.argv', ['qd-lint', 'check', '--filelist', str(filelist),
                                    '--top', 'a', '--audit-inputs']), \
                 patch('qd_lint.shutil.which') as engine_lookup, \
                 contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(), 2)
                engine_lookup.assert_not_called()
            link.unlink()
            link.symlink_to(root / 'absent')
            with self.assertRaisesRegex(InputError, 'symlink'):
                audit_inputs([], [root], [], [], 'a', 'both')
            link.unlink()
            os.mkfifo(root / 'pipe')
            with self.assertRaisesRegex(InputError, 'regular file'):
                audit_inputs([], [root], [], [], 'a', 'both')

    def test_cli_fingerprint_and_legacy_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source, output = root / 'a.sv', root / 'report.json'
            source.write_text('module a; endmodule\n')
            argv = ['qd-lint', 'check', '--filelist', str(source),
                    '--top', 'a', '--json', str(output)]
            reports = []
            for audit in (False, True):
                with patch('sys.argv', argv + (['--audit-inputs'] if audit else [])), \
                     patch('qd_lint.shutil.which', return_value=None), \
                     contextlib.redirect_stdout(io.StringIO()), \
                     contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(), 1)  # Missing engines never pass.
                reports.append(json.loads(output.read_text()))
            legacy, audited = reports
            self.assertNotIn('input_manifest', legacy)
            self.assertEqual(legacy['results'], audited['results'])
            self.assertEqual(legacy['source_snapshot_sha256'], audited['source_snapshot_sha256'])
            canonical = json.dumps(audited['input_manifest'], sort_keys=True, separators=(',', ':'))
            self.assertEqual(audited['input_manifest_sha256'], hashlib.sha256(canonical.encode()).hexdigest())

    def test_unreadable_inventory_fails_closed(self):
        with patch('qd_lint.os.walk', side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):
                audit_inputs([], [Path('.')], [], [], 'a', 'both')


if __name__ == '__main__':
    unittest.main()
