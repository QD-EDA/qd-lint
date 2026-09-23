import unittest
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from qd_lint import normalize_slang


class NormalizedSlangTests(unittest.TestCase):
    def test_positive_coordinates_and_native_provenance(self):
        data=[{'severity':'warning','message':'narrowing','optionName':'width-trunc',
               'location':'rtl/a:b file.sv:12:3','includeStack':['inc.svh:2']}]
        result=normalize_slang(data,'/project')
        self.assertEqual(result['status'],'normalized')
        self.assertEqual(result['findings'][0],{
            'native_pointer':'/0','severity':'warning','message':'narrowing',
            'rule_id':'width-trunc','location':{'reported_path':'rtl/a:b file.sv',
            'absolute_path':'/project/rtl/a:b file.sv','line':12,'column':3,
            'source_verified':False},'location_status':'reported'})
        self.assertEqual(data[0]['includeStack'],['inc.svh:2'])

    def test_global_diagnostic_has_no_invented_location_or_rule(self):
        result=normalize_slang([{'severity':'error','message':'global'}],'/project')
        self.assertEqual(result['status'],'normalized')
        finding=result['findings'][0]
        self.assertIsNone(finding['location'])
        self.assertIsNone(finding['rule_id'])
        self.assertEqual(finding['location_status'],'not-provided')
        self.assertEqual(normalize_slang([],'/project')['findings'],[])

    def test_malformed_records_remain_present_and_marked_unknown(self):
        for patch in ({'location':'a.sv:0:1'}, {'location':'a.sv:1:x'},
                      {'location':'C:\\rtl\\a.sv:1:2'}, {'location':None}, {'location':'a.sv:'+('9'*10000)+':1'},
                      {'message':7}, {'severity':'mystery'}, {'optionName':[]}):
            with self.subTest(patch=patch):
                result=normalize_slang([dict({'severity':'note','message':'kept'},**patch)],'/project')
                self.assertEqual(result['status'],'unknown')
                self.assertEqual(len(result['findings']),1)
                self.assertEqual(result['findings'][0]['native_pointer'],'/0')
                self.assertTrue(result['errors'])

    @unittest.skipUnless(shutil.which('slang'), 'real slang location oracle')
    def test_real_undefined_name_points_to_original_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'a.sv';report=root/'report.json'
            text='module a(output logic y); assign y = missing; endmodule\n'
            source.write_text(text)
            run=subprocess.run([sys.executable,'qd_lint.py','check','--filelist',str(source),
                '--top','a','--engine','slang','--native-diagnostics','--normalize-diagnostics',
                '--json',str(report)],capture_output=True,text=True)
            self.assertEqual(run.returncode,1)
            result=json.loads(report.read_text())['results'][0]
            self.assertEqual(result['normalized_diagnostics']['status'],'normalized')
            finding=next(f for f in result['normalized_diagnostics']['findings'] if 'missing' in f['message'])
            location=finding['location']
            self.assertTrue(Path(location['absolute_path']).samefile(source))
            self.assertEqual(location['line'],1)
            self.assertTrue(text[location['column']-1:].startswith('missing'))
            native=result['native_diagnostics']['data'][int(finding['native_pointer'][1:])]
            self.assertEqual(native['message'],finding['message'])
