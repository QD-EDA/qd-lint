#!/usr/bin/env python3
"""Resolve pinned Earlgrey pinmux and compare EDAM import with Edalize's reader."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import yaml
from edalize.icarus import Icarus

repo = Path(__file__).resolve().parents[1]
opentitan, out = map(lambda p: Path(p).resolve(), sys.argv[1:])
out.mkdir()
commands = []


def require_pinmux_sources(files):
    names = [Path(file['name']).name for file in files]
    assert names.count('pinmux_reg_pkg.sv') == 1
    assert names.count('pinmux.sv') == 1


def run(name, argv, cwd=repo):
    start = time.monotonic()
    result = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=120)
    (out/(name+'.stdout')).write_bytes(result.stdout)
    (out/(name+'.stderr')).write_bytes(result.stderr)
    commands.append(dict(name=name, argv=argv, cwd=str(cwd), exit_status=result.returncode,
                         seconds=time.monotonic()-start))
    (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    return result


assert subprocess.check_output(['git','-C',str(opentitan),'rev-parse','HEAD'],text=True).strip() == '7a3ad34b6d483f4d1d69ac670ddb1c45f1172e19'
assert not subprocess.check_output(['git','-C',str(opentitan),'status','--porcelain'])
fusesoc, slang, verilator = (shutil.which(tool) for tool in ('fusesoc', 'slang', 'verilator'))
assert fusesoc and slang and verilator, 'FuseSoC, slang, and Verilator are mandatory'
for name, tool in [('fusesoc',fusesoc),('slang',slang),('verilator',verilator)]:
    assert run(name+'-version',[tool,'--version']).returncode == 0
help_result = run('verilator-help',[verilator,'--help'])
verilator_sarif = b'--diagnostics-sarif-output' in help_result.stdout + help_result.stderr
(out/'verilator-sarif-status.txt').write_text('available\n' if verilator_sarif else 'UNSUPPORTED by this Verilator\n')
setup = run('resolve',[fusesoc,'--cores-root='+str(opentitan),'run',
    '--mapping=lowrisc:prim_generic:all:0.1','--mapping=lowrisc:systems:top_earlgrey:0.1',
    '--target=default','--tool=icarus','--setup','--build-root='+str(out/'build'),
    'lowrisc:earlgrey_ip:pinmux:0.1'])
assert setup.returncode == 0
assert b'Non-deterministic selection' not in setup.stdout + setup.stderr
manifests = list((out/'build').rglob('*.eda.yml'))
assert len(manifests) == 1
manifest = manifests[0]
data = yaml.safe_load(manifest.read_text())
assert len(data['files']) == 224 and data['parameters'] == {} and data['tool_options'] == {'icarus':{}}
assert not [core for core in data['cores'] if ':prim_' in core and ':prim_generic:' not in core]
assert {core for core in data['cores'] if '_constants:' in core} == {
    'lowrisc:earlgrey_constants:top_pkg:0','lowrisc:earlgrey_constants:top_racl_pkg:0.1'}
require_pinmux_sources(data['files'])
export = manifest.with_suffix('.json')
export.write_text(json.dumps(data,indent=2)+'\n')
shutil.copyfile(export,out/'resolved-edam.json')
(out/'edam-source-directory.txt').write_text(str(manifest.parent)+'\n')
wrapper_args = [sys.executable,str(repo/'qd_lint.py'),'check','--edam-json',str(export),
    '--top','pinmux','--engine','slang','--slang-single-unit','--audit-inputs',
    '--slang-dependencies','--native-diagnostics','--normalize-diagnostics',
    '--json',str(out/'lint.json')]
assert run('wrapper',wrapper_args).returncode == 0
report = json.loads((out/'lint.json').read_text())
result = report['results'][0]
sources, includes = Icarus(data,work_root=str(manifest.parent))._get_fileset_files()
assert len(sources) == 215 and len(includes) == 4
assert report['input_manifest']['sources'] == [str((manifest.parent/f.name).resolve()) for f in sources]
assert report['input_manifest']['include_directories'] == [str((manifest.parent/p).resolve()) for p in includes]
native = [slang,'--lint-only','--top','pinmux','--single-unit',
          '--diag-json',str(out/'native.json'),'--all-deps',str(out/'native.deps')]
for include in includes:
    native += ['-I',include]
native += [f.name for f in sources]
direct_slang = run('native',native,manifest.parent)
assert direct_slang.returncode == result['exit_status'] == 0
assert (direct_slang.stdout + direct_slang.stderr).decode() == result['diagnostics']
assert json.loads((out/'native.json').read_text()) == result['native_diagnostics']['data'] == []
paths = {(manifest.parent/p).resolve() for p in (out/'native.deps').read_text().splitlines()}
assert len(paths) == 221
assert {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths} == {
    f['path']:f['sha256'] for f in result['dependencies']['files']}
verilator_args = [sys.executable,str(repo/'qd_lint.py'),'check','--edam-json',str(export),
    '--top','pinmux','--engine','verilator','--audit-inputs']
if verilator_sarif:
    verilator_args.append('--native-diagnostics')
verilator_args += ['--json',str(out/'verilator-lint.json')]
wrapped_verilator = run('verilator-wrapper',verilator_args)
verilator_report = json.loads((out/'verilator-lint.json').read_text())
verilator_result = verilator_report['results'][0]
assert verilator_report['input_manifest']['sources'] == report['input_manifest']['sources']
assert verilator_report['input_manifest']['include_directories'] == report['input_manifest']['include_directories']
verilator_native = [verilator,'--lint-only','--top-module','pinmux']
verilator_native += ['-I'+str(include) for include in includes]
verilator_native += [str((manifest.parent/f.name).resolve()) for f in sources]
if verilator_sarif:
    verilator_native += ['--diagnostics-sarif-output',str(out/'verilator-native.sarif')]
direct_verilator = run('verilator-native',verilator_native,manifest.parent)
assert direct_verilator.returncode == verilator_result['exit_status'] == wrapped_verilator.returncode
assert (direct_verilator.stdout + direct_verilator.stderr).decode() == verilator_result['diagnostics']
if verilator_sarif:
    assert verilator_result['native_diagnostics']['status'] == 'captured'
    direct_sarif = json.loads((out/'verilator-native.sarif').read_text())
    assert [sarif_run['results'] for sarif_run in direct_sarif['runs']] == [
        sarif_run['results'] for sarif_run in verilator_result['native_diagnostics']['data']['runs']]
else:
    assert 'native_diagnostics' not in verilator_result
missing_data = dict(data, files=[f for f in data['files'] if not f['name'].endswith('/pinmux_reg_pkg.sv')])
assert len(missing_data['files']) == len(data['files']) - 1
try:
    require_pinmux_sources(missing_data['files'])
except AssertionError:
    pass
else:
    raise AssertionError('missing pinmux register package escaped configuration gate')
missing_top = manifest.with_name('pinmux-missing-top.json')
missing_data = dict(data, files=[f for f in data['files'] if not f['name'].endswith('/pinmux.sv')])
assert len(missing_data['files']) == len(data['files']) - 1
missing_top.write_text(json.dumps(missing_data,indent=2)+'\n')
missing_args = [sys.executable,str(repo/'qd_lint.py'),'check','--edam-json',str(missing_top),
    '--top','pinmux','--engine','slang','--slang-single-unit','--native-diagnostics',
    '--json',str(out/'missing-top.json')]
assert run('missing-top',missing_args).returncode != 0
missing_result = json.loads((out/'missing-top.json').read_text())['results'][0]
assert missing_result['classification'] == 'error'
assert "'pinmux' is not a valid top-level module" in missing_result['diagnostics']
wrong_top = wrapper_args.copy()
wrong_top[wrong_top.index('--top')+1] = 'wrong_pinmux_top'
wrong_top[wrong_top.index('--json')+1] = str(out/'wrong-top.json')
negative = run('reject-top-mismatch',wrong_top)
assert negative.returncode == 2 and b'matching scalar toplevel' in negative.stderr
assert not (out/'wrong-top.json').exists()
assert not subprocess.check_output(['git','-C',str(opentitan),'status','--porcelain'])
print('PASS: mapped pinmux EDAM and per-engine direct invocations match; qualification UNKNOWN')
