import json
import os
from pathlib import Path
import tempfile
import unittest
import contextlib
import io
import subprocess
from unittest.mock import patch

from qd_lint import InputError, audit_inputs, portable_edam_identity, read_edam, main


class EdamTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        (self.root/'a.sv').write_text('module a; endmodule\n')
        (self.root/'inc').mkdir();(self.root/'inc/defs.svh').write_text('`define V 1\n')
        self.path=self.root/'input.json'
        self.data={'version':'0.2.1','toplevel':'a','name':'fixture','files':[
            {'name':'inc/defs.svh','file_type':'systemVerilogSource','is_include_file':True},
            {'name':'a.sv','file_type':'systemVerilogSource'}],
            'parameters':{},'tool_options':{'icarus':{}},'filters':[],
            'flow_options':{},'hooks':{},'vpi':[]}

    def read(self):
        self.path.write_text(json.dumps(self.data));return read_edam(self.path,'a')

    def test_order_includes_and_configuration_are_preserved(self):
        self.data['files'].append(dict(self.data['files'][1]))
        sources,includes,defines,configs=self.read()
        self.assertEqual(sources,[self.root/'a.sv']*2)
        self.assertEqual(includes,[self.root/'inc'])
        self.assertEqual(defines,[]);self.assertEqual(configs,[self.path,self.root/'inc/defs.svh'])
        self.data['files'][0]['include_path']='.'
        self.assertEqual(self.read()[1],[self.root])

    def test_unsupported_configuration_is_rejected(self):
        for key,value in [('version','0.3'),('toplevel','other'),('parameters',{'X':{}}),
                          ('hooks',{'pre_build':[]}),('filters',['copy']),('vpi',[{}]),
                          ('flow_options',{'tool':'slang'}),('tool_options',{'icarus':{'iverilog_options':['-DQUIET']}}),
                          ('future_option',{})]:
            with self.subTest(key=key):
                saved=self.data.copy();self.data[key]=value
                with self.assertRaises(InputError):self.read()
                self.data=saved

    def test_unsupported_and_malformed_files_are_rejected(self):
        (self.root/'a.v').write_text('module a; endmodule\n')
        for patch in [{'file_type':'vlt'},{'file_type':'verilogSource'},{'name':'a.v'},{'name':'missing.sv'},{'is_include_file':'false'},
                      {'logical_name':'lib'},{'include_path':'inc'}, {'copyto':'elsewhere'}]:
            with self.subTest(patch=patch):
                original=self.data['files'][1];self.data['files'][1]=dict(original,**patch)
                with self.assertRaises(InputError):self.read()
                self.data['files'][1]=original
        self.data['files']=[]
        with self.assertRaises(InputError):self.read()

    def test_duplicate_keys_and_wrong_envelopes_fail(self):
        for text in ['null','[]','{"files":[],"files":[]}','{broken']:
            self.path.write_text(text)
            with self.assertRaises(InputError):read_edam(self.path,'a')

    def test_cli_audits_header_outside_override_directory(self):
        (self.root/'override').mkdir()
        self.data['files'][0]['include_path']='override'
        self.read()
        report=self.root/'report.json';hashes=[]
        args=['qd-lint','check','--edam-json',str(self.path),'--top','a','--engine','slang',
              '--audit-inputs','--json',str(report)]
        for value in ('0','1'):
            (self.root/'inc/defs.svh').write_text('`define V '+value+'\n')
            with patch('sys.argv',args),patch('qd_lint.shutil.which',return_value='/fake/slang'), \
                 patch('qd_lint.subprocess.run',return_value=subprocess.CompletedProcess([],0,'','')), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(),0)
            data=json.loads(report.read_text())
            self.assertEqual(data['input_format'],'edam-json-0.2.1')
            self.assertIn(str(self.root/'inc/defs.svh'),data['input_manifest']['filelists'])
            hashes.append(data['source_snapshot_sha256'])
        self.assertNotEqual(*hashes)

    def test_bad_edam_fails_before_engine_invocation(self):
        self.data['filters']=['unsupported'];self.path.write_text(json.dumps(self.data))
        with patch('sys.argv',['qd-lint','check','--edam-json',str(self.path),'--top','a']), \
             patch('qd_lint.subprocess.run',side_effect=AssertionError('engine must not run')), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(),2)

    def test_portable_identity_across_exports_and_changed_core(self):
        identities = []
        for label in ('first', 'second'):
            root = self.root/label
            source, export = root/'source', root/'export'
            source.mkdir(parents=True); export.mkdir()
            (source/'core.core').write_text('CAPI=2:\n')
            (export/'a.sv').write_text('module a; endmodule\n')
            (export/'inc').mkdir(); (export/'inc/defs.svh').write_text('`define V 1\n')
            data = dict(self.data, cores={'fixture:core': {'core_file': os.path.relpath(source/'core.core', export),
                                                          'dependencies': [], 'license': None}})
            edam = export/'input.json'; edam.write_text(json.dumps(data))
            inputs = read_edam(edam, 'a')
            manifest = audit_inputs(*inputs, 'a', 'slang')
            identities.append((edam, source, manifest, portable_edam_identity(edam, source, manifest)))
        self.assertEqual(identities[0][3]['sha256'], identities[1][3]['sha256'])
        self.assertNotEqual(identities[0][2]['sources'], identities[1][2]['sources'])
        edam, source, manifest, original = identities[0]
        (source/'core.core').write_text('changed\n')
        self.assertNotEqual(original['sha256'], portable_edam_identity(edam, source, manifest)['sha256'])
        (source/'core.core').unlink()
        with self.assertRaisesRegex(InputError, 'missing or not regular'):
            portable_edam_identity(edam, source, manifest)
        with self.assertRaisesRegex(InputError, 'leaves its declared root'):
            portable_edam_identity(edam, self.root/'second/source', manifest)

    def test_portable_identity_detects_core_change_during_engine(self):
        source = self.root/'source'; source.mkdir()
        core = source/'core.core'; core.write_text('first\n')
        self.data['cores'] = {'fixture:core': {'core_file': os.path.relpath(core, self.root),
                                              'dependencies': [], 'license': None}}
        self.read()
        report = self.root/'report.json'
        def run(argv, **kwargs):
            if '--version' in argv:
                return subprocess.CompletedProcess(argv, 0, 'fake 1.0\n', '')
            core.write_text('changed\n')
            return subprocess.CompletedProcess(argv, 0, '', '')
        args = ['qd-lint', 'check', '--edam-json', str(self.path), '--edam-source-root', str(source),
                '--top', 'a', '--engine', 'slang', '--audit-inputs', '--json', str(report)]
        with patch('sys.argv', args), patch('qd_lint.shutil.which', return_value='/fake/slang'), \
             patch('qd_lint.subprocess.run', side_effect=run), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(), 1)
        data = json.loads(report.read_text())
        self.assertEqual(data['results'][0]['classification'], 'clean')
        self.assertEqual(data['input_consistency']['status'], 'stable')
        self.assertEqual(data['portable_edam_consistency']['status'], 'changed')

    def test_portable_identity_requires_edam_and_audit(self):
        for arguments in (['--edam-json', str(self.path)],
                          ['--filelist', str(self.root/'a.sv'), '--audit-inputs']):
            with self.subTest(arguments=arguments), patch('sys.argv',
                    ['qd-lint', 'check', *arguments, '--edam-source-root', str(self.root), '--top', 'a']), \
                 contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main()
                self.assertEqual(error.exception.code, 2)

    def test_edam_change_between_parse_and_audit_is_rejected_before_engine(self):
        source = self.root/'source'; source.mkdir()
        core = source/'core.core'; core.write_text('core\n')
        self.data['cores'] = {'fixture:core': {'core_file': os.path.relpath(core, self.root),
                                              'dependencies': [], 'license': None}}
        self.read()
        (self.root/'b.sv').write_text('module b; endmodule\n')
        original = read_edam

        def mutate_after_parse(path, top):
            selected = original(path, top)
            self.data['files'].append({'name': 'b.sv', 'file_type': 'systemVerilogSource'})
            self.path.write_text(json.dumps(self.data))
            return selected

        report = self.root/'report.json'
        args = ['qd-lint', 'check', '--edam-json', str(self.path), '--edam-source-root', str(source),
                '--top', 'a', '--engine', 'slang', '--audit-inputs', '--json', str(report)]
        with patch('sys.argv', args), patch('qd_lint.read_edam', side_effect=mutate_after_parse), \
             patch('qd_lint.subprocess.run', side_effect=AssertionError('engine must not run')), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(), 2)
        self.assertFalse(report.exists())
