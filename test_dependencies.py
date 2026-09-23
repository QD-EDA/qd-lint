import contextlib
import hashlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from qd_lint import main


class DependencyTests(unittest.TestCase):
    def run_case(self, payload='valid', native=False, engine='slang'):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();source=root/'unit.sv';header=root/'header space.svh'
            source.write_text('module unit; endmodule\n');header.write_text('`define X 1\n')
            report=root/'report.json'
            def run(argv, **kwargs):
                if '--version' in argv:return subprocess.CompletedProcess(argv,0,stdout='test',stderr='')
                if '--all-deps' not in argv:
                    return subprocess.CompletedProcess(argv,0,stdout='raw console\n',stderr='')
                target=Path(argv[argv.index('--all-deps')+1])
                if payload=='valid':target.write_text(str(source)+'\n'+str(header)+'\n')
                elif payload=='missing-source':target.write_text(str(header)+'\n')
                elif payload=='bad-file':target.write_text(str(source)+'\n'+str(root/'absent')+'\n')
                elif payload=='directory':target.write_text(str(source)+'\n'+str(root)+'\n')
                elif payload=='invalid-utf8':target.write_bytes(b'\xff')
                elif payload=='empty':target.write_text('')
                if native:Path(argv[argv.index('--diag-json')+1]).write_text('[]')
                return subprocess.CompletedProcess(argv,0,stdout='raw console\n',stderr='')
            args=['qd-lint','check','--filelist',str(source),'--top','unit','--engine',engine,
                  '--slang-dependencies','--json',str(report)]+(['--native-diagnostics'] if native else [])
            with patch('sys.argv',args),patch('qd_lint.shutil.which',return_value='/fake/slang'), \
                 patch('qd_lint.subprocess.run',side_effect=run),contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(io.StringIO()):
                code=main()
            results=json.loads(report.read_text())['results']
            if engine=='both':self.assertNotIn('dependencies',results[0])
            return code,results[-1],str(header)

    def test_capture_hashes_files_and_retains_native_console(self):
        for native in (False,True):
            code,result,header=self.run_case(native=native)
            self.assertEqual(code,0)
            capture=result['dependencies']
            self.assertEqual(capture['status'],'captured')
            self.assertFalse(capture['dependency_closure_complete'])
            self.assertEqual(result['diagnostics'],'raw console\n')
            entry=next(f for f in capture['files'] if f['path']==header)
            self.assertEqual(entry['sha256'],hashlib.sha256(b'`define X 1\n').hexdigest())
            if native:self.assertEqual(result['native_diagnostics']['status'],'captured')

    def test_incomplete_or_bad_dependency_capture_fails_closed(self):
        for payload in ('missing','empty','missing-source','bad-file','directory','invalid-utf8'):
            code,result,_=self.run_case(payload)
            self.assertEqual(code,1,payload)
            self.assertEqual(result['exit_status'],0)
            self.assertEqual(result['dependencies']['status'],'error')
            if payload=='invalid-utf8':self.assertEqual(result['dependencies']['raw_base64'],'/w==')

    def test_both_engines_capture_only_slang(self):
        code,result,_=self.run_case(engine='both')
        self.assertEqual(code,0)
        self.assertEqual(result['dependencies']['status'],'captured')

    def test_report_required(self):
        with patch('sys.argv',['qd-lint','check','--filelist','unused','--top','unit',
                              '--engine','slang','--slang-dependencies']), \
             contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as error:
            main()
        self.assertEqual(error.exception.code,2)

    def test_verilator_only_rejected(self):
        with self.assertRaises(SystemExit) as error:self.run_case(engine='verilator')
        self.assertEqual(error.exception.code,2)

    @unittest.skipUnless(shutil.which('slang'),'optional real slang dependency oracle')
    def test_real_source_relative_header_changes_observed_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'unit.sv';header=root/'header space.svh';report=root/'r.json'
            source.write_text('`include "header space.svh"\nmodule unit(output logic y); assign y=`VALUE; endmodule\n')
            hashes=[]
            for value in (0,1):
                header.write_text('`define VALUE '+str(value)+'\n')
                args=['qd-lint','check','--filelist',str(source),'--top','unit','--engine','slang',
                      '--slang-dependencies','--json',str(report)]
                with patch('sys.argv',args),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(main(),0)
                result=json.loads(report.read_text())['results'][0]
                self.assertEqual(len(result['dependencies']['files']),2)
                hashes.append(result['dependencies']['observed_files_sha256'])
            self.assertNotEqual(*hashes)
