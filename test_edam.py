import json
from pathlib import Path
import tempfile
import unittest
import contextlib
import io
import subprocess
from unittest.mock import patch

from qd_lint import InputError, read_edam, main


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
        for patch in [{'file_type':'vlt'},{'name':'missing.sv'},{'is_include_file':'false'},
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
